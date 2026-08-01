#!/usr/bin/env python3
"""Rebuild and serve the site while source files are being edited."""

from __future__ import annotations

import argparse
import json
import mimetypes
import posixpath
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
SITE_BASE_PATH = "/genai-textbooks"
REVISION_PATH = "/__dev/revision"
WATCH_PATHS = (
    ROOT / "docs",
    ROOT / "scripts" / "generate_site.py",
    ROOT / "scripts" / "site_template.html",
    ROOT / ".claude" / "skills" / "yaruo-count" / "scripts",
)

LIVE_RELOAD_SCRIPT = f"""
<script>
  (function () {{
    var revision;
    function checkForRebuild() {{
      fetch('{REVISION_PATH}', {{ cache: 'no-store' }})
        .then(function (response) {{ return response.json(); }})
        .then(function (status) {{
          if (revision === undefined) revision = status.revision;
          else if (status.revision !== revision) window.location.reload();
        }})
        .catch(function () {{}});
    }}
    checkForRebuild();
    window.setInterval(checkForRebuild, 750);
  }})();
</script>
"""


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def build() -> bool:
    log("Building site...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_site.py")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        log("Build failed; keeping the last successful preview.")
        return False
    log("Build completed.")
    return True


def iter_watched_files() -> list[Path]:
    files: list[Path] = []
    for path in WATCH_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
    return files


def snapshot() -> dict[Path, tuple[int, int]]:
    state: dict[Path, tuple[int, int]] = {}
    for path in iter_watched_files():
        try:
            stat = path.stat()
        except OSError:
            continue
        state[path] = (stat.st_mtime_ns, stat.st_size)
    return state


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, PreviewHandler)
        self.revision = 1


class PreviewHandler(BaseHTTPRequestHandler):
    server: PreviewServer

    def do_HEAD(self) -> None:
        self._serve(send_body=False)

    def do_GET(self) -> None:
        self._serve(send_body=True)

    def _serve(self, *, send_body: bool) -> None:
        request_path = unquote(urlsplit(self.path).path)

        if request_path == REVISION_PATH:
            payload = json.dumps({"revision": self.server.revision}).encode("utf-8")
            self._send_bytes(payload, "application/json; charset=utf-8", send_body)
            return

        if request_path == "/":
            self.send_response(302)
            self.send_header("Location", SITE_BASE_PATH + "/")
            self.end_headers()
            return

        if request_path == SITE_BASE_PATH:
            self.send_response(302)
            self.send_header("Location", SITE_BASE_PATH + "/")
            self.end_headers()
            return

        prefix = SITE_BASE_PATH + "/"
        if not request_path.startswith(prefix):
            self.send_error(404)
            return

        relative_path = posixpath.normpath(request_path[len(prefix) :]).lstrip("/")
        candidate = (BUILD_DIR / relative_path).resolve()
        try:
            candidate.relative_to(BUILD_DIR.resolve())
        except ValueError:
            self.send_error(404)
            return

        if candidate.is_dir():
            candidate = candidate / "index.html"

        if candidate.is_file():
            self._send_file(candidate, send_body)
            return

        # Missing assets and Markdown must remain 404s. In particular, docsify
        # relies on a missing nested _sidebar.md returning 404 before it walks
        # up to the site-wide sidebar.
        suffix = Path(relative_path).suffix
        if suffix and not suffix[1:].isdigit():
            self.send_error(404)
            return

        # History-mode routes have no matching file. Return the closest shell;
        # docsify will then request the route's Markdown file in the browser.
        shell = BUILD_DIR / "index.html"
        parts = Path(relative_path).parts
        if len(parts) >= 2 and parts[0] == "books":
            book_shell = BUILD_DIR / "books" / parts[1] / "index.html"
            if book_shell.is_file():
                shell = book_shell
        if shell.is_file():
            self._send_file(shell, send_body)
        else:
            self.send_error(404, "Run the site build first")

    def _send_file(self, path: Path, send_body: bool) -> None:
        try:
            payload = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".html":
            html = payload.decode("utf-8").replace("</body>", LIVE_RELOAD_SCRIPT + "</body>")
            payload = html.encode("utf-8")
            content_type = "text/html; charset=utf-8"
        elif path.suffix in {".md", ".yml", ".yaml", ".xml"}:
            content_type += "; charset=utf-8"
        self._send_bytes(payload, content_type, send_body)

    def _send_bytes(self, payload: bytes, content_type: str, send_body: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging docsify's many asset and Markdown requests.
        return


def watch(server: PreviewServer, interval: float) -> None:
    previous = snapshot()
    while True:
        time.sleep(interval)
        current = snapshot()
        if current == previous:
            continue

        # Wait one extra interval so an editor that saves multiple files in a
        # burst triggers one build instead of several overlapping builds.
        previous = current
        time.sleep(interval)
        current = snapshot()
        if current != previous:
            previous = current

        build_input = current
        if build():
            server.revision += 1
        # Keep the pre-build snapshot. If another save happened during a slow
        # build, the next poll sees it and schedules one more build.
        previous = build_input


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to bind (default: 127.0.0.1)",
    )
    parser.add_argument("--port", type=int, default=3000, help="port to bind (default: 3000)")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="file polling interval in seconds (default: 0.5)",
    )
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    if not build():
        return 1

    server = PreviewServer((args.host, args.port))
    watcher = threading.Thread(target=watch, args=(server, args.interval), daemon=True)
    watcher.start()

    host, port = server.server_address[:2]
    display_host = "localhost" if host in {"127.0.0.1", "::1"} else host
    log(f"Preview: http://{display_host}:{port}{SITE_BASE_PATH}/")
    log("Watching for changes. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopping development server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
