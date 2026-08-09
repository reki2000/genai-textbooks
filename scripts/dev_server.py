#!/usr/bin/env python3
"""Rebuild and serve the site while source files are being edited.

編集中のプレビューに加えて、プレビュー上でコメントを付けるための API を持つ。
コメントの永続化・アンカーの解決はすべて `comments.py` に委ね、ここは HTTP 層
だけを持つ。ファイルが唯一の真実で、ブラウザも `comments.py wait` で待っている
エージェントも、同じ `comments/{book}/*.md` を見ている。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import posixpath
import re
import select
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comments as comments_module  # noqa: E402
import generate_site  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DOCS_DIR = ROOT / "docs"
SITE_BASE_PATH = "/genai-textbooks"
REVISION_PATH = "/__dev/revision"
COMMENT_UI_PATH = "/__dev/comment-ui.js"
COMMENT_API_PATH = "/__dev/comments"
COMMENT_UI_FILE = ROOT / "scripts" / "dev_comment_ui.js"
WATCH_PATHS = (
    DOCS_DIR,
    ROOT / "scripts" / "generate_site.py",
    ROOT / "scripts" / "site_template.html",
    ROOT / ".claude" / "skills" / "yaruo-count" / "scripts",
)
# 本文だけが変わったときは、全書籍のコピーとルビ変換をやり直さずにその1枚だけ
# 差し替える。コメントを連打しているときの待ち時間はここに集中するため。
FAST_REBUILD_RE = re.compile(r"^books/[a-z0-9-]+/README(?:\.[0-9]+)?\.md$")
COMMENT_POLL_INTERVAL = 0.3
# 待機のロングポールが切れてからこの秒数までは、担当は編集中とみなす。編集の間は
# 名乗りに来られないので、切れた瞬間に「未接続」にすると点滅してしまう。
WAITER_GRACE_SECONDS = 120.0

DOCSIFY_TAG = '<script src="https://cdn.jsdelivr.net/npm/docsify@4"></script>'
COMMENT_UI_TAG = f'<script src="{COMMENT_UI_PATH}"></script>'


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


def fast_rebuild(relative_paths: list[str]) -> bool:
    """本文 Markdown だけを `build/` へ差し替える。

    サイドバーの読了時間などは据え置きになるが、それらは次の全体ビルドで揃う。
    編集中のプレビューでの体感を優先する。
    """
    try:
        for relative in relative_paths:
            source = DOCS_DIR / relative
            target = BUILD_DIR / relative
            if not source.is_file():
                return False
            text = source.read_text(encoding="utf-8")
            text = generate_site.convert_ruby_to_html(text)
            text = generate_site.convert_footnote_backrefs(text)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    except OSError as exc:
        log(f"Fast rebuild failed ({exc}); falling back to a full build.")
        return False
    log(f"Updated {', '.join(relative_paths)}.")
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


def comments_snapshot() -> dict[Path, int]:
    state: dict[Path, int] = {}
    for path in comments_module.COMMENTS_DIR.rglob("*.md"):
        try:
            state[path] = path.stat().st_mtime_ns
        except OSError:
            continue
    return state


class WaiterRegistry:
    """コメントを拾う担当の在席管理。

    担当は待機のロングポール（GET /__dev/comments/wait）で自分のモデルと effort を
    名乗る。**接続を掴んでいる間が「待機中」**で、切れれば居なくなる。ファイルに
    置かないのは、掴んでいる接続そのものが生存の証拠として一番正確だから。
    """

    def __init__(self, grace: float = WAITER_GRACE_SECONDS) -> None:
        self.grace = grace
        self.lock = threading.Lock()
        self.books: dict[str, dict] = {}

    def enter(self, book: str, session: str, model: str, effort: str, phase: str = "waiting") -> None:
        """待機を登録する。他の担当が受け持っていれば `WaiterBusy`。"""
        with self.lock:
            competing_keys = list(self.books) if not book else [book, ""]
            for key in competing_keys:
                competing = self._live(key)
                if competing and competing["session"] != session:
                    raise comments_module.WaiterBusy(
                        "既に別の対応エージェントが受け持っています: "
                        f"{competing['model'] or 'モデル不明'} / effort={competing['effort'] or '不明'} "
                        f"(session={competing['session']})"
                    )
            current = self._live(book)
            if current and current["session"] != session:
                raise comments_module.WaiterBusy(
                    "既に別の対応エージェントが受け持っています: "
                    f"{current['model'] or 'モデル不明'} / effort={current['effort'] or '不明'} "
                    f"({'待機中' if current['held'] else '対応中'}, session={current['session']})"
                )
            entry = current or {"session": session, "held": 0}
            entry.update({
                "session": session,
                "model": model,
                "effort": effort,
                "phase": phase,
                "seen": time.time(),
            })
            entry["held"] = entry.get("held", 0) + 1
            self.books[book] = entry

    def leave(self, book: str) -> None:
        with self.lock:
            entry = self.books.get(book)
            if not entry:
                return
            entry["held"] = max(0, entry.get("held", 0) - 1)
            entry["seen"] = time.time()

    def drop(self, book: str) -> None:
        """接続が切れていた担当を即座に消す。

        `leave` との違いは猶予を与えないこと。正常に払い出して編集へ移ったのか、
        落ちたのかは接続の切れ方で区別できるので、落ちたと分かったものを
        「対応中」として残さない。
        """
        with self.lock:
            self.books.pop(book, None)

    def status(self, book: str) -> dict[str, object]:
        with self.lock:
            entry = self._live(book) or self._live("")
            if not entry:
                return {"state": "disconnected"}
            phase = entry.get("phase", "waiting")
            return {
                "state": phase if phase == "initializing" else ("waiting" if entry["held"] else "working"),
                "model": entry["model"],
                "effort": entry["effort"],
                "session": entry["session"],
            }

    def assign(self, book: str, session: str, phase: str) -> None:
        """教材未指定の担当を、コメントが来た教材へ移す。"""
        with self.lock:
            entry = self._live("")
            current = self._live(book)
            if current and current["session"] != session:
                raise comments_module.WaiterBusy("対象教材は既に別の対応エージェントが受け持っています")
            if not entry or entry["session"] != session:
                return
            self.books.pop("", None)
            entry["phase"] = phase
            self.books[book] = entry

    def _live(self, book: str) -> dict | None:
        entry = self.books.get(book)
        if not entry:
            return None
        if entry.get("held"):
            return entry
        if time.time() - entry.get("seen", 0.0) > self.grace:
            del self.books[book]
            return None
        return entry


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, PreviewHandler)
        self.revision = 1
        # 直前のビルドで書き換わった build/ 相対パス。ブラウザはこれを見て、
        # 開いているページの Markdown だけならページ全体を捨てずに再取得する。
        self.changed: list[str] = []
        self.comment_revision = 0
        self.comment_condition = threading.Condition()
        self.create_lock = threading.Lock()
        self.waiters = WaiterRegistry()

    def bump(self, changed: list[str]) -> None:
        self.changed = changed
        self.revision += 1

    def notify_comments(self) -> None:
        with self.comment_condition:
            self.comment_revision += 1
            self.comment_condition.notify_all()


class PreviewHandler(BaseHTTPRequestHandler):
    server: PreviewServer

    def do_HEAD(self) -> None:
        self._serve(send_body=False)

    def do_GET(self) -> None:
        self._serve(send_body=True)

    def do_POST(self) -> None:
        request = urlsplit(self.path)
        path = unquote(request.path)
        if not path.startswith(COMMENT_API_PATH):
            self.send_error(404)
            return
        if not self._check_origin():
            self.send_error(403, "cross-origin request rejected")
            return

        rest = path[len(COMMENT_API_PATH) :].strip("/")
        try:
            if not rest:
                self._create_comment()
                return
            parts = rest.split("/")
            if len(parts) == 3 and parts[2] == "followup":
                self._add_followup(parts[0], parts[1])
                return
            if len(parts) == 3 and parts[2] in comments_module.STATUS_ACTIONS:
                self._set_status(parts[0], parts[1], parts[2])
                return
        except comments_module.CommentConflict as exc:
            self._send_bytes(str(exc).encode("utf-8"), "text/plain; charset=utf-8", True, status=409)
            return
        except comments_module.CommentError as exc:
            self._send_bytes(str(exc).encode("utf-8"), "text/plain; charset=utf-8", True, status=400)
            return
        self.send_error(404)

    # -- comment API -------------------------------------------------------

    def _check_origin(self) -> bool:
        """ローカルの他ページから書き込まれないようにする。

        dev_server は書き込み口を持つので、Origin の無い/合わない POST は弾く。
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # curl などヘッダを付けない素の POST
        host = self.headers.get("Host", "")
        return urlsplit(origin).netloc == host

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 1_000_000:
            raise comments_module.CommentError("本文が空か大きすぎる")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise comments_module.CommentError(f"JSON として読めない: {exc}") from exc

    def _create_comment(self) -> None:
        payload = self._read_json()
        with self.server.create_lock:  # id の採番が競合しないように直列化する
            comment = comments_module.create_comment(
                book=str(payload.get("book", "")),
                part=int(payload.get("part", 1) or 1),
                kind=str(payload.get("kind", "wording")),
                unit=str(payload.get("unit", "sentence")),
                body=str(payload.get("body", "")),
                heading=str(payload.get("heading", "")),
                heading_level=int(payload.get("heading_level", 0) or 0),
                heading_path=[str(item) for item in payload.get("heading_path", []) or []],
                quote=str(payload.get("quote", "")),
                quote_tail=str(payload.get("quote_tail", "")),
                occurrence=int(payload.get("occurrence", 1) or 1),
            )
        self.server.notify_comments()
        log(f"comment {comment.book}/{comment.id} at line {comment.anchor.line_hint}")
        self._send_json({"id": comment.id, "line": comment.anchor.line_hint})

    def _set_status(self, book: str, comment_id: str, action: str) -> None:
        comment = comments_module.find_comment(book, comment_id)
        status = comments_module.STATUS_ACTIONS[action]
        comments_module.set_status(comment, status)
        self.server.notify_comments()
        self._send_json({"id": comment.id, "status": status})

    def _add_followup(self, book: str, comment_id: str) -> None:
        payload = self._read_json()
        with self.server.create_lock:
            comment = comments_module.find_comment(book, comment_id)
            comments_module.add_followup(comment, str(payload.get("body", "")))
        self.server.notify_comments()
        log(f"follow-up comment {comment.book}/{comment.id}")
        self._send_json({"id": comment.id, "status": comment.status})

    def _list_comments(self, query: dict[str, list[str]]) -> None:
        book = (query.get("book") or [""])[0]
        try:
            found = comments_module.load_comments(book or None)
        except comments_module.CommentError as exc:
            self._send_bytes(str(exc).encode("utf-8"), "text/plain; charset=utf-8", True, status=400)
            return
        self._send_json(
            {
                "agent": self.server.waiters.status(book) if book else {"state": "disconnected"},
                "comments": [
                    {
                        "id": comment.id,
                        "book": comment.book,
                        "part": comment.part,
                        "kind": comment.kind,
                        "unit": comment.unit,
                        "status": comment.status,
                        "body": comment.body,
                        "answer": comment.answer,
                        "messages": [
                            {"role": message.role, "created": message.created, "body": message.body}
                            for message in comment.messages()
                        ],
                        "anchor": {
                            "quote": comment.anchor.quote,
                            "occurrence": comment.anchor.occurrence,
                            "heading": comment.anchor.heading,
                            "line_hint": comment.anchor.line_hint,
                            "current_line": comment.anchor.current_line,
                            "current_heading": comment.anchor.current_heading,
                            "located_at": comment.anchor.located_at,
                        },
                    }
                    for comment in found
                ]
            }
        )

    def _wait_comments(self, query: dict[str, list[str]]) -> None:
        """未処理のコメントが現れるまでレスポンスを保留する（ロングポール）。

        `comments.py wait` が教材未指定でこれを叩き、応答で対象教材を受け取る。
        outline 作成中は同じ入口へ `phase=initializing` で接続を保つ。
        """
        book = (query.get("book") or [""])[0]
        phase = (query.get("phase") or ["waiting"])[0]
        try:
            timeout = min(float((query.get("timeout") or ["60"])[0]), 300.0)
        except ValueError:
            timeout = 60.0

        try:
            self.server.waiters.enter(
                book,
                (query.get("session") or [""])[0],
                (query.get("model") or [""])[0],
                (query.get("effort") or [""])[0],
                phase,
            )
        except comments_module.WaiterBusy as exc:
            self._send_bytes(str(exc).encode("utf-8"), "text/plain; charset=utf-8", True, status=409)
            return

        deadline = time.monotonic() + timeout
        registry_book = book
        try:
            while True:
                try:
                    if phase == "initializing":
                        if comments_module.outline_path(book).is_file():
                            self._send_json({"initialized": True, "book": book})
                            return
                    else:
                        pending = comments_module.open_comments(book or None)
                        if pending:
                            assigned_book = pending[0].book
                            initializing = not comments_module.outline_path(assigned_book).is_file()
                            if not book:
                                self.server.waiters.assign(
                                    assigned_book,
                                    (query.get("session") or [""])[0],
                                    "initializing" if initializing else "waiting",
                                )
                                registry_book = assigned_book
                            self._send_json({
                                "pending": True,
                                "book": assigned_book,
                                "initializing": initializing,
                            })
                            return
                except comments_module.CommentError as exc:
                    self._send_bytes(str(exc).encode("utf-8"), "text/plain; charset=utf-8", True, status=400)
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.send_response(204)
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                if self._peer_gone():
                    log(f"waiter for {book} disconnected")
                    self.server.waiters.drop(book)
                    return
                with self.server.comment_condition:
                    self.server.comment_condition.wait(min(remaining, 1.0))
        except (BrokenPipeError, ConnectionResetError):
            log(f"waiter for {book} disconnected")
            self.server.waiters.drop(book)
        finally:
            self.server.waiters.leave(registry_book)

    def _peer_gone(self) -> bool:
        """保留中の接続が既に切れていないか。

        待っている間はこちらから書かないので、担当が落ちても書き込み時まで
        気づけない。相手が閉じた TCP は読み取り可能かつ EOF になるので、それを
        覗いて即座に「未接続」へ落とす。
        """
        try:
            readable, _, _ = select.select([self.connection], [], [], 0)
            if not readable:
                return False
            return self.connection.recv(1, socket.MSG_PEEK) == b""
        except OSError:
            return True

    # -- static files ------------------------------------------------------

    def _serve(self, *, send_body: bool) -> None:
        request = urlsplit(self.path)
        request_path = unquote(request.path)
        query = parse_qs(request.query)

        if request_path == REVISION_PATH:
            payload = json.dumps(
                {"revision": self.server.revision, "changed": self.server.changed}
            ).encode("utf-8")
            self._send_bytes(payload, "application/json; charset=utf-8", send_body)
            return

        if request_path == COMMENT_UI_PATH:
            self._send_file(COMMENT_UI_FILE, send_body)
            return

        if request_path == COMMENT_API_PATH + "/wait":
            self._wait_comments(query)
            return

        if request_path == COMMENT_API_PATH:
            self._list_comments(query)
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
            payload = self._inject(payload.decode("utf-8")).encode("utf-8")
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix in {".md", ".yml", ".yaml", ".xml"}:
            content_type += "; charset=utf-8"
        self._send_bytes(payload, content_type, send_body)

    def _inject(self, html: str) -> str:
        """docsify のシェルにだけコメント UI を差し込む。

        marp のスライド HTML には docsify が無いので、そちらへは入れない。
        docsify 本体より前に置くのは、UI が `$docsify.plugins` へ登録して
        `doneEach` と vm を受け取るため（本体が走ったあとでは登録できない）。
        """
        if DOCSIFY_TAG not in html:
            return html
        return html.replace(DOCSIFY_TAG, COMMENT_UI_TAG + "\n  " + DOCSIFY_TAG, 1)

    def _send_json(self, payload: dict) -> None:
        self._send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            True,
        )

    def _send_bytes(self, payload: bytes, content_type: str, send_body: bool, status: int = 200) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if send_body:
                self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            # ページ遷移や再取得でブラウザが先に接続を閉じるのは正常。応答の送信を
            # 諦めるだけでよく、ThreadingHTTPServer に例外を伝えてログを汚さない。
            return

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging docsify's many asset and Markdown requests.
        return


def changed_relative_paths(previous: dict[Path, tuple[int, int]], current: dict[Path, tuple[int, int]]) -> list[str] | None:
    """本文 Markdown だけの変更なら `docs/` 相対パスを返す。それ以外は None。"""
    touched = {path for path in set(previous) | set(current) if previous.get(path) != current.get(path)}
    relative: list[str] = []
    for path in touched:
        try:
            name = path.relative_to(DOCS_DIR).as_posix()
        except ValueError:
            return None
        if not FAST_REBUILD_RE.match(name):
            return None
        relative.append(name)
    return sorted(relative)


def watch(server: PreviewServer, interval: float) -> None:
    previous = snapshot()
    while True:
        time.sleep(interval)
        current = snapshot()
        if current == previous:
            continue

        # Wait one extra interval so an editor that saves multiple files in a
        # burst triggers one build instead of several overlapping builds.
        settled = current
        time.sleep(interval)
        current = snapshot()
        if current != settled:
            settled = current

        fast_paths = changed_relative_paths(previous, settled)
        if fast_paths and fast_rebuild(fast_paths):
            server.bump(fast_paths)
        elif build():
            server.bump([])
        # Keep the pre-build snapshot. If another save happened during a slow
        # build, the next poll sees it and schedules one more build.
        previous = settled


def watch_comments(server: PreviewServer, interval: float) -> None:
    """コメントの状態はエージェントが直接ファイルへ書くので、ここで拾って
    待っている側（ブラウザとロングポール）を起こす。"""
    previous = comments_snapshot()
    while True:
        time.sleep(interval)
        current = comments_snapshot()
        if current != previous:
            previous = current
            server.notify_comments()


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
    threading.Thread(target=watch, args=(server, args.interval), daemon=True).start()
    threading.Thread(target=watch_comments, args=(server, COMMENT_POLL_INTERVAL), daemon=True).start()

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
