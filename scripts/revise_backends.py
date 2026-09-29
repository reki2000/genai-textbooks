#!/usr/bin/env python3
"""推敲の候補を LLM に作らせるバックエンドと、その待機プロセスのプール。

バックエンドはどれも「プロセスを先に起動しておき、依頼を1件だけ標準入力へ
流して閉じる」形に揃える。起動にかかる時間を利用者から隠しつつ、会話の履歴を
積まないため（1件ごとに捨てるので、前の依頼が次の案に混ざらない）。

キャッシュはプロセスではなくプロンプトの先頭に紐づく。system を作法カード＋
骨格に固定し、同じキーのプロセスはすべて同じ system で起動する。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator

# claude/codex に作業ディレクトリのプロジェクト指示（CLAUDE.md・AGENTS.md）を
# 読ませないため、空のディレクトリで起動する。作法は system で明示的に渡す。
NEUTRAL_CWD: str | None = None  # 遅延生成（下の neutral_cwd()）


def neutral_cwd() -> str:
    global NEUTRAL_CWD
    if NEUTRAL_CWD is None:
        NEUTRAL_CWD = tempfile.mkdtemp(prefix="revise-cwd-")
    return NEUTRAL_CWD


class BackendError(RuntimeError):
    pass


@dataclass
class TierSpec:
    """1つのティア×バックエンドの設定。"""

    backend: str
    model: str = ""
    effort: str = ""
    thinking: bool = True

    def key(self) -> tuple[str, str, str, bool]:
        return (self.backend, self.model, self.effort, self.thinking)


@dataclass
class Event:
    """バックエンドからの出力。`delta` は本文の断片、`done` は完了と使用量。"""

    kind: str  # "delta" | "done"
    text: str = ""
    usage: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# バックエンド
# --------------------------------------------------------------------------


class Backend:
    name = ""

    def command(self, spec: TierSpec, system: str) -> list[str]:
        raise NotImplementedError

    def env(self, spec: TierSpec) -> dict[str, str]:
        return dict(os.environ)

    def request_bytes(self, system: str, user: str) -> bytes:
        raise NotImplementedError

    def parse(self, lines: Iterator[str]) -> Iterator[Event]:
        raise NotImplementedError


class ClaudeBackend(Backend):
    """`claude -p` を stream-json で使う。

    Claude Code 既定のシステムプロンプト・ツール定義・設定・MCP を外し、
    `--system-prompt` だけを持たせる。思考を切るのは `MAX_THINKING_TOKENS=0`。
    """

    name = "claude"

    def command(self, spec: TierSpec, system: str) -> list[str]:
        command = [
            "claude", "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--tools", "",
            "--system-prompt", system,
            "--no-session-persistence",
            "--strict-mcp-config",
            "--setting-sources", "",
        ]
        if spec.model:
            command += ["--model", spec.model]
        if spec.effort:
            command += ["--effort", spec.effort]
        return command

    def env(self, spec: TierSpec) -> dict[str, str]:
        env = dict(os.environ)
        if not spec.thinking:
            env["MAX_THINKING_TOKENS"] = "0"
        return env

    def request_bytes(self, system: str, user: str) -> bytes:
        message = {"type": "user", "message": {"role": "user", "content": user}}
        return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")

    def parse(self, lines: Iterator[str]) -> Iterator[Event]:
        for line in lines:
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if data.get("type") == "stream_event":
                event = data.get("event") or {}
                delta = event.get("delta") or {}
                if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    yield Event("delta", delta.get("text", ""))
            elif data.get("type") == "result":
                if data.get("is_error"):
                    raise BackendError(str(data.get("result") or data.get("subtype") or "claude error"))
                usage = dict(data.get("usage") or {})
                usage["cost_usd"] = data.get("total_cost_usd")
                usage["api_ms"] = data.get("duration_api_ms")
                yield Event("done", usage=usage)
                return


class CodexBackend(Backend):
    """`codex exec --json` を使う。未検証（この実装を書いた環境に codex が無い）。

    codex には system を差し替える口が無いので、system を user の前へ連結して
    1つのプロンプトとして標準入力に流す。先頭が固定なので、先頭一致の
    キャッシュはそのまま効く見込み。`exec --json` は項目単位のイベントしか
    出さないので、候補は完了時にまとめて届く（逐次表示にはならない）。
    """

    name = "codex"

    def command(self, spec: TierSpec, system: str) -> list[str]:
        command = [
            "codex", "exec", "--json",
            "--skip-git-repo-check",
            "--sandbox", "read-only",
            "--color", "never",
        ]
        if spec.model:
            command += ["-m", spec.model]
        effort = spec.effort or ("minimal" if not spec.thinking else "")
        if effort:
            command += ["-c", f"model_reasoning_effort={json.dumps(effort)}"]
        return command + ["-"]

    def request_bytes(self, system: str, user: str) -> bytes:
        return (system + "\n\n---\n\n" + user).encode("utf-8")

    def parse(self, lines: Iterator[str]) -> Iterator[Event]:
        usage: dict = {}
        for line in lines:
            try:
                data = json.loads(line)
            except ValueError:
                continue
            kind = data.get("type") or (data.get("msg") or {}).get("type") or ""
            item = data.get("item") or {}
            if kind == "item.completed" and item.get("type") in {"agent_message", "assistant_message"}:
                yield Event("delta", str(item.get("text") or ""))
            elif kind in {"agent_message", "agent_message_delta"}:
                message = data.get("msg") or data
                yield Event("delta", str(message.get("message") or message.get("delta") or ""))
            elif kind in {"turn.completed", "token_count"}:
                usage = dict(data.get("usage") or (data.get("msg") or {}).get("info") or {})
            elif kind in {"turn.failed", "error"}:
                error = data.get("error") or data.get("message") or data
                raise BackendError(f"codex: {error}")
        yield Event("done", usage=usage)


class FakeBackend(Backend):
    """試験と画面確認用。LLM を呼ばず、決まった候補を返す。

    `python3 scripts/revise_backends.py --fake-child` を子プロセスとして起動し、
    本物と同じ経路（プール・標準入出力・逐次表示）を通す。
    """

    name = "fake"

    def command(self, spec: TierSpec, system: str) -> list[str]:
        return [os.environ.get("PYTHON", "python3"), os.path.abspath(__file__), "--fake-child"]

    def request_bytes(self, system: str, user: str) -> bytes:
        return user.encode("utf-8")

    def parse(self, lines: Iterator[str]) -> Iterator[Event]:
        for line in lines:
            data = json.loads(line)
            if data["kind"] == "delta":
                yield Event("delta", data["text"])
            else:
                yield Event("done", usage=data.get("usage") or {})
                return


BACKENDS: dict[str, Backend] = {
    backend.name: backend for backend in (ClaudeBackend(), CodexBackend(), FakeBackend())
}


# --------------------------------------------------------------------------
# プール
# --------------------------------------------------------------------------


@dataclass
class Warm:
    process: subprocess.Popen
    key: tuple
    spawned: float


class Pool:
    """キーごとに起動済みのプロセスを `size` 本ずつ待たせる。

    キーは (バックエンド, モデル, effort, 思考, system の hash)。system が変われば
    キーが変わるので、骨格や作法カードを更新すると新しい system のプロセスへ
    自然に入れ替わる（古いキーのプロセスは `idle_ttl` で落ちる）。
    """

    def __init__(self, sizes: dict[str, int] | None = None, idle_ttl: float = 600.0,
                 spawner: Callable[..., subprocess.Popen] | None = None) -> None:
        self.sizes = sizes or {}
        self.idle_ttl = idle_ttl
        self.spawner = spawner or subprocess.Popen
        self.lock = threading.Lock()
        self.warm: dict[tuple, list[Warm]] = {}

    def _spawn(self, backend: Backend, spec: TierSpec, system: str, key: tuple) -> Warm:
        try:
            process = self.spawner(
                backend.command(spec, system),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=neutral_cwd(),
                env=backend.env(spec),
            )
        except FileNotFoundError as exc:
            raise BackendError(f"{backend.name} のコマンドが見つからない: {exc.filename}") from exc
        return Warm(process, key, time.monotonic())

    @staticmethod
    def key_for(spec: TierSpec, system: str) -> tuple:
        import hashlib

        return spec.key() + (hashlib.sha256(system.encode("utf-8")).hexdigest()[:16],)

    def acquire(self, spec: TierSpec, system: str, tier: str = "") -> subprocess.Popen:
        """待機中のプロセスを1本取り出し、減った分を補充する。"""
        backend = BACKENDS[spec.backend]
        key = self.key_for(spec, system)
        with self.lock:
            queue = self.warm.setdefault(key, [])
            chosen = None
            while queue:
                candidate = queue.pop(0)
                if candidate.process.poll() is None:
                    chosen = candidate
                    break
            if chosen is None:
                chosen = self._spawn(backend, spec, system, key)
            want = max(self.sizes.get(tier, 1), 0)
            while len(queue) < want:
                queue.append(self._spawn(backend, spec, system, key))
        return chosen.process

    def prewarm(self, spec: TierSpec, system: str, tier: str = "") -> None:
        backend = BACKENDS[spec.backend]
        key = self.key_for(spec, system)
        with self.lock:
            queue = self.warm.setdefault(key, [])
            want = max(self.sizes.get(tier, 1), 0)
            while len(queue) < want:
                queue.append(self._spawn(backend, spec, system, key))

    def reap(self, now: float | None = None) -> int:
        """使われないまま `idle_ttl` を過ぎたプロセスを落とす。"""
        now = time.monotonic() if now is None else now
        dropped = 0
        with self.lock:
            for key in list(self.warm):
                keep = []
                for warm in self.warm[key]:
                    if warm.process.poll() is not None:
                        continue
                    if now - warm.spawned > self.idle_ttl:
                        _kill(warm.process)
                        dropped += 1
                        continue
                    keep.append(warm)
                if keep:
                    self.warm[key] = keep
                else:
                    del self.warm[key]
        return dropped

    def close(self) -> None:
        with self.lock:
            for queue in self.warm.values():
                for warm in queue:
                    _kill(warm.process)
            self.warm.clear()

    def count(self) -> int:
        with self.lock:
            return sum(len(queue) for queue in self.warm.values())


def _kill(process: subprocess.Popen) -> None:
    try:
        process.kill()
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        pass


def run(process: subprocess.Popen, backend: Backend, system: str, user: str,
        timeout: float = 300.0) -> Iterator[Event]:
    """取り出したプロセスへ依頼を1件流し、イベントを逐次返す。"""
    assert process.stdin is not None and process.stdout is not None
    stderr_tail: list[bytes] = []

    def drain_stderr() -> None:
        if process.stderr is None:
            return
        for chunk in iter(lambda: process.stderr.readline(), b""):
            stderr_tail.append(chunk)
            del stderr_tail[:-20]

    threading.Thread(target=drain_stderr, daemon=True).start()
    timer = threading.Timer(timeout, _kill, args=(process,))
    timer.start()
    try:
        try:
            process.stdin.write(backend.request_bytes(system, user))
            process.stdin.close()
        except BrokenPipeError as exc:
            raise BackendError(_failure(backend, stderr_tail, "起動直後に終了した")) from exc
        lines = (raw.decode("utf-8", "replace") for raw in iter(process.stdout.readline, b""))
        finished = False
        for event in backend.parse(lines):
            if event.kind == "done":
                finished = True
            yield event
            if finished:
                break
        if not finished:
            process.wait(timeout=5)
            raise BackendError(_failure(backend, stderr_tail, f"応答が完了しなかった (exit={process.returncode})"))
    finally:
        timer.cancel()
        _kill(process)


def _failure(backend: Backend, stderr_tail: list[bytes], message: str) -> str:
    tail = b"".join(stderr_tail).decode("utf-8", "replace").strip()
    return f"{backend.name}: {message}" + (f"\n{tail[-800:]}" if tail else "")


# --------------------------------------------------------------------------
# 偽バックエンドの子プロセス
# --------------------------------------------------------------------------


def _fake_child() -> int:
    """依頼の <target> を読み、機械的に書き換えた候補を JSONL で返す。"""
    import re
    import sys

    request = sys.stdin.read()
    match = re.search(r"<target>\n(.*?)\n?</target>", request, re.DOTALL)
    target = match.group(1) if match else ""
    count_match = re.search(r"案を(\d+)", request)
    count = int(count_match.group(1)) if count_match else 2
    variants = [
        (target.replace("。", "！", 1), "句点を感嘆符にした（偽の候補）"),
        (target.replace("お。", "だお。", 1), "語尾を変えた（偽の候補）"),
        (target.rstrip("\n") + "（追記）\n" if target.endswith("\n") else target + "（追記）", "末尾に追記（偽の候補）"),
    ]
    delay = float(os.environ.get("REVISE_FAKE_DELAY", "0"))
    for new, why in variants[:count]:
        line = json.dumps({"new": new, "why": why}, ensure_ascii=False) + "\n"
        for start in range(0, len(line), 7):  # 1行を細切れにして逐次表示の経路を通す
            print(json.dumps({"kind": "delta", "text": line[start:start + 7]}, ensure_ascii=False), flush=True)
            if delay:
                time.sleep(delay)
    print(json.dumps({"kind": "done", "usage": {"input_tokens": len(request), "output_tokens": 0}}), flush=True)
    return 0


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--fake-child"]:
        raise SystemExit(_fake_child())
    print("usage: revise_backends.py --fake-child", file=sys.stderr)
    raise SystemExit(2)
