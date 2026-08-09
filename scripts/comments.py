#!/usr/bin/env python3
"""プレビュー上のコメントの保存・アンカー解決・窓の切り出し。

`dev_server.py` は HTTP 層だけを持ち、コメントの永続化と位置の解決はすべて
ここを通す（`yaruo_lint.py` が書式検査の唯一の入口であるのと同じ役割）。

コメントは OKF (Open Knowledge Format) v0.1 に沿って、YAML frontmatter 付きの
Markdown を `comments/{book}/{id}.md` へ1件1ファイルで置く。`docs/` の外に置く
のは、`generate_site.py` が `docs/` を丸ごと `build/` へコピーするため、配下に
置くとコメントがサイトに公開されてしまうから。

## アンカー

行番号は編集で必ず陳腐化するので、正本は「見出し＋引用文字列＋節内の出現順」
とし、行番号は毎回ここで引き直す（`line_hint` は表示用の目安でしかない）。
引用は本文の見出しどおりの文字列ではなく、ブラウザに描画された文字列なので、
両側を `normalize()` で正規化してから突き合わせる：ルビの読み、強調記号、
リンクの URL、空白（`breaks: true` による改行の差）を落とす。

引用が見つからなければ `stale` として、当てずっぽうの位置には決して落とさない。
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaruo_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COMMENTS_DIR = ROOT / "comments"
BOOKS_DIR = ROOT / "docs" / "books"

BOOK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COMMENT_ID_RE = re.compile(r"^[0-9]{4}$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

KINDS = ("wording", "substance")
UNITS = ("sentence", "paragraph", "section")
STATUSES = ("open", "answered", "resolved", "stale")
# 操作名 → 遷移先。`resolve` という動詞と `resolved` という状態を取り違えない。
STATUS_ACTIONS = {"resolve": "resolved", "stale": "stale", "reopen": "open"}

# 軽微な指摘は段落の周りだけ、内容の指摘は節ごと渡す。全文を読ませないための
# 出し分けで、コメント投稿時に人が選ぶ。
WORDING_CONTEXT_LINES = 6
SECTION_WINDOW_LIMIT = 400
MAX_BODY_CHARS = 4000
MAX_QUOTE_CHARS = 400
COMMENT_SCHEMA = "comment/v1"
LEGACY_COMMENT_SCHEMA = "comment/v0-legacy"
EDIT_ANCHOR_MAX_LINES = 12
EDIT_ANCHOR_MAX_CHARS = 1200



class CommentError(ValueError):
    """入力が不正でコメントを作れない。HTTP 層は 400 として返す。"""


class CommentConflict(CommentError):
    """読み込み後に別の更新が入り、安全に保存できない。HTTP 層は 409 にする。"""


class WaiterBusy(RuntimeError):
    """別の対応エージェントが既にその教材を受け持っている。dev_server が判定する。"""


# --------------------------------------------------------------------------
# 正規化と索引
# --------------------------------------------------------------------------

_MATH_RE = re.compile(r"\$\$[^$]*\$\$|\$[^$\n]*\$")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)\s]*(?:\s+\"[^\"]*\")?\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)\s]*(?:\s+\"[^\"]*\")?\)")
_FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]\n]+\]")
_MARKUP_RE = re.compile(r"[*`~_<>]|&nbsp;|‌|​")
_WS_RE = re.compile(r"[\s　]+")


def normalize(text: str) -> str:
    """突き合わせ用の正規形。ソース側と DOM 側の両方に同じ関数を掛ける。

    ルビの読み・強調記号・リンク URL・空白を落とし、NFKC で全角半角を畳む。
    空白を全部落とすのは、`breaks: true` の改行が DOM では `<br>`、ソースでは
    改行と行頭の全角空白になり、そのままでは一致しないため。
    """
    text = yaruo_markdown.strip_ruby(text)
    # 数式は KaTeX が描画結果を作り替えてしまい、ソースの `$…$` とは一致しない。
    # 両側から落とすことで、数式を含む文にもコメントを付けられるようにする
    # （dev_comment_ui.js は描画側の .katex を落とす）。
    text = _MATH_RE.sub("", text)
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _FOOTNOTE_REF_RE.sub("", text)
    text = _MARKUP_RE.sub("", text)
    text = _WS_RE.sub("", text)
    return unicodedata.normalize("NFKC", text)


@dataclass
class LineIndex:
    """正規化した本文と、その1文字ごとの元の行番号（0-indexed）。"""

    text: str
    line_of_char: list[int]
    start_line: int
    end_line: int  # exclusive

    def line_at(self, char_index: int) -> int:
        if not self.line_of_char:
            return self.start_line
        index = min(max(char_index, 0), len(self.line_of_char) - 1)
        return self.line_of_char[index]


def build_index(lines: list[str], start_line: int = 0, end_line: int | None = None) -> LineIndex:
    if end_line is None:
        end_line = len(lines)
    pieces: list[str] = []
    line_of_char: list[int] = []
    for index in range(start_line, end_line):
        body = yaruo_markdown.split_eol(lines[index])[0]
        piece = normalize(body)
        if not piece:
            continue
        pieces.append(piece)
        line_of_char.extend([index] * len(piece))
    return LineIndex("".join(pieces), line_of_char, start_line, end_line)


# --------------------------------------------------------------------------
# 見出しと節
# --------------------------------------------------------------------------


@dataclass
class Heading:
    line: int
    level: int
    text: str
    normalized: str


def headings(lines: list[str]) -> list[Heading]:
    """フェンスコード・数式ブロックの中の `#` は見出しにしない。"""
    skip = yaruo_markdown.non_prose_lines(lines)
    found: list[Heading] = []
    for index, line in enumerate(lines):
        if index in skip:
            continue
        match = HEADING_RE.match(yaruo_markdown.split_eol(line)[0])
        if match:
            text = match.group(2)
            found.append(Heading(index, len(match.group(1)), text, normalize(text)))
    return found


def section_range(lines: list[str], heading_text: str, level: int | None = None) -> tuple[int, int] | None:
    """見出し行から、同位以上の次の見出しの直前までを (start, end) で返す。"""
    target = normalize(heading_text)
    if not target:
        return None
    found = headings(lines)
    for position, heading in enumerate(found):
        if heading.normalized != target:
            continue
        if level is not None and heading.level != level:
            continue
        end = len(lines)
        for later in found[position + 1 :]:
            if later.level <= heading.level:
                end = later.line
                break
        return heading.line, end
    return None


def heading_path_at(lines: list[str], line: int) -> list[str]:
    """その行を含む見出しの経路（幕 → 節）。表示用。"""
    stack: list[tuple[int, str]] = []
    for heading in headings(lines):
        if heading.line > line:
            break
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        stack.append((heading.level, heading.text))
    return [text for _, text in stack]


# --------------------------------------------------------------------------
# コメント
# --------------------------------------------------------------------------


@dataclass
class Anchor:
    heading: str = ""
    heading_level: int = 0
    heading_path: list[str] = field(default_factory=list)
    quote: str = ""
    quote_tail: str = ""
    occurrence: int = 1
    line_hint: int = 0
    current_line: int = 0
    current_heading: str = ""
    located_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "heading": self.heading,
            "heading_level": self.heading_level,
            "heading_path": list(self.heading_path),
            "quote": self.quote,
            "quote_tail": self.quote_tail,
            "occurrence": self.occurrence,
            "line_hint": self.line_hint,
            "current_line": self.current_line,
            "current_heading": self.current_heading,
            "located_at": self.located_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Anchor":
        return cls(
            heading=str(data.get("heading", "")),
            heading_level=int(data.get("heading_level", 0) or 0),
            heading_path=[str(item) for item in data.get("heading_path", []) or []],
            quote=str(data.get("quote", "")),
            quote_tail=str(data.get("quote_tail", "")),
            occurrence=int(data.get("occurrence", 1) or 1),
            line_hint=int(data.get("line_hint", 0) or 0),
            current_line=int(data.get("current_line", 0) or 0),
            current_heading=str(data.get("current_heading", "")),
            located_at=str(data.get("located_at", "")),
        )


@dataclass
class ThreadMessage:
    role: str
    created: str
    body: str


@dataclass
class Comment:
    id: str
    book: str
    part: int
    kind: str
    unit: str
    status: str
    created: str
    anchor: Anchor
    body: str
    answer: str = ""
    answered: str = ""
    history: list[ThreadMessage] = field(default_factory=list)
    schema: str = COMMENT_SCHEMA
    revision: int = 0
    _source_hash: str | None = field(default=None, repr=False, compare=False)

    @property
    def path(self) -> Path:
        return COMMENTS_DIR / self.book / f"{self.id}.md"

    def to_frontmatter(
        self, *, schema: str | None = None, revision: int | None = None
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": "comment",  # OKF v0.1 の唯一の必須フィールド
            "schema": schema if schema is not None else self.schema,
            "revision": revision if revision is not None else self.revision,
            "id": self.id,
            "book": self.book,
            "part": self.part,
            "kind": self.kind,
            "unit": self.unit,
            "status": self.status,
            "created": self.created,
            "anchor": self.anchor.to_dict(),
        }
        if self.answered:
            data["answered"] = self.answered
        return data

    def render(self, *, schema: str | None = None, revision: int | None = None) -> str:
        front = yaml.safe_dump(
            self.to_frontmatter(schema=schema, revision=revision),
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        parts = ["---\n", front, "---\n\n"]
        user_count = 0
        for message in self.messages():
            if message.role == "user":
                user_count += 1
                label = "指摘" if user_count == 1 else "追加指摘"
            else:
                label = "対応"
            parts.append(f"## {label} [{message.created}]\n\n{message.body.strip()}\n\n")
        return "".join(parts)

    def messages(self) -> list[ThreadMessage]:
        if self.history:
            return list(self.history)
        messages = [ThreadMessage("user", self.created, self.body)]
        if self.answer:
            messages.append(ThreadMessage("assistant", self.answered, self.answer))
        return messages

    def source_path(self) -> Path:
        return source_path(self.book, self.part)

    def source_lines(self) -> list[str]:
        return read_lines(self.source_path())


_FRONTMATTER_RE = re.compile(r"\A---\n(?P<front>.*?)\n---\n?(?P<body>.*)\Z", re.DOTALL)
_SECTION_RE = re.compile(
    r"^##\s+(指摘|追加指摘|対応)(?:\s+\[([^\]]+)\])?\s*$", re.MULTILINE
)


def parse_comment(text: str) -> Comment:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise CommentError("frontmatter が無い")
    front = yaml.safe_load(match.group("front")) or {}
    if not isinstance(front, dict) or front.get("type") != "comment":
        raise CommentError("type: comment ではない")
    raw_schema = front.get("schema")
    if raw_schema is None:
        schema = LEGACY_COMMENT_SCHEMA
        revision = 0
    elif raw_schema == COMMENT_SCHEMA:
        raw_revision = front.get("revision")
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 1:
            raise CommentError(f"{COMMENT_SCHEMA} の revision が不正")
        schema = COMMENT_SCHEMA
        revision = raw_revision
    else:
        raise CommentError(f"未対応の comment schema: {raw_schema!r}")
    anchor_data = front.get("anchor", {}) or {}
    if not isinstance(anchor_data, dict):
        raise CommentError("anchor が mapping ではない")
    body_text = match.group("body")

    answer = ""
    body = body_text.strip()
    history: list[ThreadMessage] = []
    matches = list(_SECTION_RE.finditer(body_text))
    sections = [
        (item.group(1), item.group(2) or "", body_text[item.end() : matches[index + 1].start() if index + 1 < len(matches) else len(body_text)].strip())
        for index, item in enumerate(matches)
    ]
    is_thread_format = any(label == "追加指摘" or timestamp for label, timestamp, _ in sections)
    if is_thread_format:
        for label, timestamp, content in sections:
            role = "assistant" if label == "対応" else "user"
            history.append(ThreadMessage(role, timestamp, content))
        user_messages = [message for message in history if message.role == "user"]
        if user_messages:
            body = user_messages[-1].body
        if history and history[-1].role == "assistant":
            answer = history[-1].body
    elif sections:
        # 旧形式は「対応」が「指摘」より先に置かれていたため、時系列へ並べ直す。
        for label, _, content in sections:
            if label == "対応":
                answer = content
            elif label == "指摘":
                body = content
        history = [ThreadMessage("user", str(front.get("created", "")), body)]
        if answer:
            history.append(ThreadMessage("assistant", str(front.get("answered", "")), answer))

    try:
        part = int(front.get("part", 1) or 1)
    except (TypeError, ValueError) as exc:
        raise CommentError("part が不正") from exc
    comment = Comment(
        id=str(front.get("id", "")),
        book=str(front.get("book", "")),
        part=part,
        kind=str(front.get("kind", "wording")),
        unit=str(front.get("unit", "sentence")),
        status=str(front.get("status", "open")),
        created=str(front.get("created", "")),
        anchor=Anchor.from_dict(anchor_data),
        body=body,
        answer=answer,
        answered=str(front.get("answered", "")),
        history=history,
        schema=schema,
        revision=revision,
        _source_hash=_text_hash(text),
    )
    _validate_comment(comment)
    return comment


# --------------------------------------------------------------------------
# 保存場所
# --------------------------------------------------------------------------


def check_book_id(book: str) -> str:
    if not BOOK_ID_RE.match(book or ""):
        raise CommentError(f"book id が不正: {book!r}")
    return book


def source_path(book: str, part: int) -> Path:
    check_book_id(book)
    if part < 1:
        raise CommentError(f"part が不正: {part}")
    name = "README.md" if part == 1 else f"README.{part}.md"
    path = BOOKS_DIR / book / name
    if not path.is_file():
        raise CommentError(f"本文が無い: {path.relative_to(ROOT)}")
    return path


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def load_comments(book: str | None = None) -> list[Comment]:
    if book is not None:
        check_book_id(book)
        directories: Iterable[Path] = [COMMENTS_DIR / book]
    else:
        directories = sorted(p for p in COMMENTS_DIR.glob("*") if p.is_dir())
    comments: list[Comment] = []
    for directory in directories:
        for path in sorted(directory.glob("[0-9][0-9][0-9][0-9].md")):
            try:
                comments.append(parse_comment(path.read_text(encoding="utf-8")))
            except (CommentError, yaml.YAMLError) as exc:
                print(f"skip {path}: {exc}", file=sys.stderr)
    comments.sort(key=lambda c: (c.book, c.id))
    return comments


def find_comment(book: str, comment_id: str) -> Comment:
    check_book_id(book)
    if not COMMENT_ID_RE.match(comment_id):
        raise CommentError(f"comment id が不正: {comment_id!r}")
    path = COMMENTS_DIR / book / f"{comment_id}.md"
    if not path.is_file():
        raise CommentError(f"コメントが無い: {path.relative_to(ROOT)}")
    return parse_comment(path.read_text(encoding="utf-8"))


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_comment(comment: Comment) -> None:
    if not COMMENT_ID_RE.match(comment.id):
        raise CommentError(f"comment id が不正: {comment.id!r}")
    check_book_id(comment.book)
    if comment.part < 1:
        raise CommentError(f"part が不正: {comment.part}")
    if comment.kind not in KINDS:
        raise CommentError(f"kind が不正: {comment.kind!r}")
    if comment.unit not in UNITS:
        raise CommentError(f"unit が不正: {comment.unit!r}")
    if comment.status not in STATUSES:
        raise CommentError(f"status が不正: {comment.status!r}")


def _atomic_replace_text(path: Path, text: str) -> None:
    """同じディレクトリの一時ファイルを同期してから原子的に置き換える。"""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_comment(comment: Comment) -> Path:
    """hash/revision を検査し、競合が無い場合だけ1 revision進めて保存する。"""
    _validate_comment(comment)
    path = comment.path
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".comments-write.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            if path.exists():
                current_text = path.read_text(encoding="utf-8")
                current_hash = _text_hash(current_text)
                if comment._source_hash is None:
                    raise CommentConflict(f"コメントが既に存在するため作成できない: {path.name}")
                if current_hash != comment._source_hash:
                    raise CommentConflict(
                        f"コメント {comment.book}/{comment.id} は読み込み後に更新された。再読してやり直すこと"
                    )
                current = parse_comment(current_text)
                if current.schema != comment.schema or current.revision != comment.revision:
                    raise CommentConflict(
                        f"コメント {comment.book}/{comment.id} の revision が変わった。再読してやり直すこと"
                    )
            elif comment._source_hash is not None or comment.revision != 0:
                raise CommentConflict(
                    f"コメント {comment.book}/{comment.id} が読み込み後に削除された。再読してやり直すこと"
                )

            next_revision = comment.revision + 1
            rendered = comment.render(schema=COMMENT_SCHEMA, revision=next_revision)
            _atomic_replace_text(path, rendered)
            comment.schema = COMMENT_SCHEMA
            comment.revision = next_revision
            comment._source_hash = _text_hash(rendered)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return path


def next_comment_id(book: str) -> str:
    check_book_id(book)
    directory = COMMENTS_DIR / book
    used = [
        int(path.stem)
        for path in directory.glob("[0-9][0-9][0-9][0-9].md")
        if path.stem.isdigit()
    ]
    return f"{(max(used) + 1) if used else 1:04d}"


def outline_path(book: str) -> Path:
    check_book_id(book)
    return BOOKS_DIR / book / "outline.md"


def readme_modified_at(book: str) -> str:
    """README.md のファイル更新日時を UTC の ISO 8601 形式で返す。"""
    modified = source_path(book, 1).stat().st_mtime
    return datetime.fromtimestamp(modified, timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# アンカーの解決
# --------------------------------------------------------------------------


def resolve(comment: Comment, lines: list[str] | None = None) -> tuple[int, int] | None:
    """アンカーを今の本文へ引き直し、(start, end) を 0-indexed 包含で返す。

    見つからなければ None。呼び出し側は `stale` にする。似た別の場所へ落とす
    ことは決してしない（AI が無関係な箇所を書き換える事故を防ぐため）。
    """
    if lines is None:
        lines = comment.source_lines()
    anchor = comment.anchor

    span = None
    if anchor.heading:
        span = section_range(lines, anchor.heading, anchor.heading_level or None)
    if span is None and anchor.heading:
        span = section_range(lines, anchor.heading)

    if comment.unit == "section":
        if span is None:
            return None
        return span[0], max(span[0], span[1] - 1)

    quote = normalize(anchor.quote)
    if not quote:
        return None

    candidates = [span] if span else []
    candidates.append((0, len(lines)))  # 節が改題・移動していたら全文へ広げる
    for start_line, end_line in candidates:
        index = build_index(lines, start_line, end_line)
        position = _nth_index(index.text, quote, anchor.occurrence)
        if position < 0:
            position = index.text.find(quote)
        if position < 0:
            continue
        start = index.line_at(position)
        tail = normalize(anchor.quote_tail) or quote
        tail_position = index.text.find(tail, position)
        if tail_position < 0:
            tail_position = position + len(quote) - 1
        end = index.line_at(tail_position + max(len(tail) - 1, 0))
        return start, max(start, end)
    return None


def _nth_index(haystack: str, needle: str, occurrence: int) -> int:
    position = -1
    for _ in range(max(occurrence, 1)):
        position = haystack.find(needle, position + 1)
        if position < 0:
            return -1
    return position


def record_current_position(
    comment: Comment, lines: list[str], span: tuple[int, int], *, located_at: str | None = None
) -> None:
    """解決に成功した位置だけを anchor の補助情報へ記録する。"""
    comment.anchor.current_line = span[0] + 1
    path = heading_path_at(lines, span[0])
    comment.anchor.current_heading = path[-1] if path else comment.anchor.heading
    comment.anchor.located_at = located_at or now_iso()


def refresh_current_position(comment: Comment, *, write: bool = False) -> bool:
    """現在位置を再解決する。失敗時は最後に成功した値を維持する。"""
    lines = comment.source_lines()
    span = resolve(comment, lines)
    if span is None:
        return False
    record_current_position(comment, lines, span)
    if write:
        write_comment(comment)
    return True


# --------------------------------------------------------------------------
# 窓の切り出し
# --------------------------------------------------------------------------


def window_for(
    comment: Comment, lines: list[str], span: tuple[int, int], scope: str = "auto"
) -> tuple[int, int]:
    """エージェントへ渡す範囲。全文を読ませないための中核。

    `scope` は対応する側からの明示的な要求。選択範囲は「どこへのコメントか」を
    示すだけで、どこまで直すかはコメントの内容しだいなので、狭い選択に全体の
    指摘が書かれていたら `section` や `part` で引き直せるようにしてある。
    """
    start, end = span
    if scope == "part":
        return 0, len(lines)
    if scope == "paragraph":
        pass
    elif scope == "section" or comment.kind == "substance" or comment.unit == "section":
        section = section_range(lines, comment.anchor.heading, comment.anchor.heading_level or None)
        if section:
            window_start, window_end = section[0], section[1]
        else:
            window_start, window_end = start, end + 1
        if window_end - window_start > SECTION_WINDOW_LIMIT:
            middle = (start + end) // 2
            half = SECTION_WINDOW_LIMIT // 2
            window_start = max(window_start, middle - half)
            window_end = min(window_end, middle + half)
        return window_start, min(window_end, len(lines))

    # 軽微な指摘：空行で区切られた段落まで広げ、さらに前後数行。
    window_start = start
    while window_start > 0 and lines[window_start - 1].strip():
        window_start -= 1
    window_end = end + 1
    while window_end < len(lines) and lines[window_end].strip():
        window_end += 1
    window_start = max(0, window_start - WORDING_CONTEXT_LINES)
    window_end = min(len(lines), window_end + WORDING_CONTEXT_LINES)
    return window_start, window_end


def edit_anchor(
    lines: list[str], span: tuple[int, int], *, unit: str = "sentence"
) -> tuple[str, bool]:
    """編集ツールの old_string 候補と、その一意性。

    一意でなければ前の行を足して伸ばす。ここで一意性まで確かめておくと、
    エージェント側が本文を検索し直す必要が無くなる。
    """
    if unit == "section":
        return "", False
    source = "".join(lines)
    start, end = span
    for top in range(start, max(start - 6, -1), -1):
        candidate = "".join(lines[top : end + 1])
        if end - top + 1 > EDIT_ANCHOR_MAX_LINES or len(candidate) > EDIT_ANCHOR_MAX_CHARS:
            return "", False
        if candidate and source.count(candidate) == 1:
            return candidate, True
    candidate = "".join(lines[start : end + 1])
    if end - start + 1 > EDIT_ANCHOR_MAX_LINES or len(candidate) > EDIT_ANCHOR_MAX_CHARS:
        return "", False
    return candidate, False


# --------------------------------------------------------------------------
# コメントの作成と状態遷移
# --------------------------------------------------------------------------


def create_comment(
    *,
    book: str,
    part: int,
    kind: str,
    unit: str,
    body: str,
    heading: str,
    heading_level: int,
    heading_path: list[str],
    quote: str,
    quote_tail: str,
    occurrence: int,
) -> Comment:
    """プレビューからの投稿を1件保存する。

    アンカーは**投稿時に同期的に解決**する。解決できない選択（数式の内側など）
    はここで弾き、その場でユーザーへ知らせる。あとから `stale` として黙って
    捨てられるより、書き直せる今のうちに失敗させるほうがよい。
    """
    check_book_id(book)
    if kind not in KINDS:
        raise CommentError(f"kind が不正: {kind!r}")
    if unit not in UNITS:
        raise CommentError(f"unit が不正: {unit!r}")
    body = (body or "").strip()
    if not body:
        raise CommentError("コメントが空")
    if len(body) > MAX_BODY_CHARS:
        raise CommentError(f"コメントが長すぎる（{MAX_BODY_CHARS}字まで）")
    if len(quote or "") > MAX_QUOTE_CHARS:
        quote = quote[:MAX_QUOTE_CHARS]
    if len(quote_tail or "") > MAX_QUOTE_CHARS:
        quote_tail = quote_tail[-MAX_QUOTE_CHARS:]

    path = source_path(book, part)
    lines = read_lines(path)

    comment = Comment(
        id=next_comment_id(book),
        book=book,
        part=part,
        kind=kind,
        unit=unit,
        status="open",
        created=now_iso(),
        anchor=Anchor(
            heading=heading,
            heading_level=heading_level,
            heading_path=heading_path,
            quote=quote,
            quote_tail=quote_tail,
            occurrence=occurrence,
        ),
        body=body,
    )

    span = resolve(comment, lines)
    if span is None:
        raise CommentError(
            "選択範囲を本文から特定できなかった。"
            "数式や図の内側を避け、地の文を選び直してほしい"
        )
    comment.anchor.line_hint = span[0] + 1
    record_current_position(comment, lines, span, located_at=comment.created)
    if not comment.anchor.heading_path:
        comment.anchor.heading_path = heading_path_at(lines, span[0])
    write_comment(comment)
    return comment


def set_status(comment: Comment, status: str, *, answer: str = "") -> Comment:
    if status not in STATUSES:
        raise CommentError(f"status が不正: {status!r}")
    refresh_current_position(comment)
    comment.status = status
    if answer:
        comment.history = comment.messages()
        comment.answer = answer.strip()
        comment.answered = now_iso()
        comment.history.append(ThreadMessage("assistant", comment.answered, comment.answer))
    write_comment(comment)
    return comment


def add_followup(comment: Comment, body: str) -> Comment:
    body = body.strip()
    if comment.status != "answered":
        raise CommentError("追加コメントは対応済みのコメントにだけ送れる")
    if not body:
        raise CommentError("追加コメントが空")
    if len(body) > MAX_BODY_CHARS:
        raise CommentError(f"追加コメントが長すぎる（{MAX_BODY_CHARS}文字まで）")
    comment.history = comment.messages()
    comment.history.append(ThreadMessage("user", now_iso(), body))
    comment.body = body
    comment.answer = ""
    comment.answered = ""
    comment.status = "open"
    write_comment(comment)
    return comment


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# 待機
# --------------------------------------------------------------------------


def open_comments(book: str | None = None) -> list[Comment]:
    return [comment for comment in load_comments(book) if comment.status == "open"]


def wait_for_open(
    book: str | None, timeout: float, server: str | None, *, session: str, model: str, effort: str
) -> tuple[str | None, list[Comment]]:
    """未処理のコメントが現れるまで待つ。

    dev_server を指定したときはロングポールで待つ（遅延ゼロ・ポーリング無し）。
    サーバへ接続できなければエラーにする。黙ってファイル監視へ退避すると、担当が
    待っているように見えるのに画面では「未接続」という偽の接続状態になるため。
    ファイル監視へ明示的に退避するときだけ `--server ''` を使う。

    自分のモデルと effort はこの GET で名乗る。教材未指定なら応答の `book` で
    対象を確定する。**繋いでいる間が「待機中」**で、切れれば dev_server 側から
    居なくなる。二重起動の判定もサーバが持つ。
    """
    deadline = time.monotonic() + timeout
    identity = {"session": session, "model": model, "effort": effort}

    if not server:
        # サーバ抜きの退避経路。名乗る先が無いので、画面表示も排他も効かない。
        print("warning: dev_server に繋がずに待つ（担当表示と二重起動の検出は効かない）", file=sys.stderr)
        while time.monotonic() < deadline:
            pending = open_comments(book)
            if pending:
                return book or pending[0].book, pending
            time.sleep(0.3)
        return book, open_comments(book)

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return book, []
        # 溜まっている分があってもまず名乗る。サーバはすぐ返してくるので、
        # 「登録されないまま処理を始める」経路を作らない。
        result = _long_poll(server, book or "", max(1.0, min(30.0, remaining)), identity)
        assigned_book = str(result.get("book", "")) if result else ""
        if assigned_book:
            book = assigned_book
        pending = open_comments(book)
        if pending:
            return book or pending[0].book, pending


def _long_poll(
    server: str, book: str, timeout: float, identity: dict[str, str], *, phase: str = "waiting"
) -> dict[str, Any]:
    """新着があるまでサーバに保留してもらう。この接続そのものが「待機中」の証。"""
    import urllib.error
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode({"book": book, "timeout": int(timeout), "phase": phase, **identity})
    url = f"{server.rstrip('/')}/__dev/comments/wait?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout + 10) as response:
            if response.status == 204:
                return {}
            return dict(json.load(response))
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            raise WaiterBusy(exc.read().decode("utf-8", "replace").strip()) from exc
        time.sleep(min(1.0, timeout))
        return {}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", exc)
        raise CommentError(
            f"dev_server に接続できない: {url} ({reason})。"
            "開発サーバの URL を確認し、接続できる環境で待ち直すこと"
        ) from exc


# --------------------------------------------------------------------------
# 出力
# --------------------------------------------------------------------------


def render_payload(comment: Comment, *, group: list[Comment] | None = None, scope: str = "auto") -> str:
    """エージェントが編集に使う一式。本文を読み直させないために、窓・見出し経路・
    old_string 候補までここで揃える。"""
    lines = comment.source_lines()
    group = group or [comment]
    spans: dict[str, tuple[int, int] | None] = {c.id: resolve(c, lines) for c in group}

    for item in group:
        span = spans[item.id]
        if span is not None:
            record_current_position(item, lines, span)
            write_comment(item)

    resolved = [c for c in group if spans[c.id] is not None]
    if not resolved:
        return _render_stale(comment)

    starts = [spans[c.id][0] for c in resolved]  # type: ignore[index]
    ends = [spans[c.id][1] for c in resolved]  # type: ignore[index]
    hull = (min(starts), max(ends))
    window_start, window_end = window_for(comment, lines, hull, scope)

    out: list[str] = []
    relative = comment.source_path().relative_to(ROOT)
    for item in group:
        span = spans[item.id]
        out.append(f"--- comment {item.id} ({item.kind} / {item.unit}) ---")
        path_text = " / ".join(item.anchor.heading_path) or "(見出しなし)"
        if span is None:
            out.append(f"{path_text}   [stale: 引用が今の本文に無い]")
        else:
            out.append(f"{path_text}   {relative}:{span[0] + 1}-{span[1] + 1}")
        out.append("")
        if len(item.messages()) == 1:
            out.append(item.body.strip())
        else:
            out.append("履歴:")
            for message in item.messages():
                speaker = "ユーザー" if message.role == "user" else "対応側"
                out.append(f"[{speaker} {message.created}] {message.body.strip()}")
        out.append("")

    out.append(f"--- window ({relative}:{window_start + 1}-{window_end}) ---")
    marked = {
        line
        for span in spans.values()
        if span
        for line in range(span[0], span[1] + 1)
    }
    for index in range(window_start, window_end):
        prefix = ">" if index in marked else " "
        body = yaruo_markdown.split_eol(lines[index])[0]
        out.append(f"{prefix} {index + 1:5d} | {body}")
    out.append("")

    if len(resolved) == 1:
        resolved_comment = resolved[0]
        candidate, unique = edit_anchor(
            lines, spans[resolved_comment.id], unit=resolved_comment.unit  # type: ignore[arg-type]
        )
        out.append("--- edit anchor ---")
        if not candidate:
            out.append("一意性: 該当なし（選択範囲が広すぎる。窓から修正箇所を選ぶこと）")
        else:
            out.append("一意性: " + ("OK（この文字列で置換できる）" if unique else "NG（窓から広げて特定すること）"))
        out.append(repr(candidate))
        out.append("")

    outline = outline_path(comment.book)
    state = "あり" if outline.is_file() else "未作成（初回は全文を読んで作る）"
    out.append(f"outline: {outline.relative_to(ROOT)} … {state}")
    if not outline.is_file():
        out.append(f"README.md 最終更新日時: {readme_modified_at(comment.book)}")
    remaining = len(open_comments(comment.book)) - len(group)
    if remaining > 0:
        out.append(f"queue: 残り {remaining} 件")
    return "\n".join(out)


def _render_stale(comment: Comment) -> str:
    return (
        f"--- comment {comment.id} (stale) ---\n"
        f"引用が今の本文に見つからない。直後の修正で書き換わった可能性が高い。\n"
        f"status を stale にして人へ差し戻すこと:\n"
        f"  python3 scripts/comments.py stale --book {comment.book} --id {comment.id}\n\n"
        f"{comment.body.strip()}\n"
    )


def group_with_same_section(comments: list[Comment]) -> list[Comment]:
    """キュー掃き：先頭と同じ節に載っている未処理コメントをまとめて返す。

    タイマーで待つ代わりに「今キューにある分だけ」まとめる。待たないので即時性は
    落ちず、連打されたときだけ自然に合流する。
    """
    head = comments[0]
    key = (head.part, normalize(head.anchor.heading))
    return [c for c in comments if (c.part, normalize(c.anchor.heading)) == key]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    comments = load_comments(args.book)
    if args.status:
        comments = [c for c in comments if c.status == args.status]
    if not comments:
        print("コメントなし")
        return 0
    for comment in comments:
        path_text = " / ".join(comment.anchor.heading_path) or "-"
        head = comment.body.strip().splitlines()[0][:40]
        print(
            f"{comment.book}/{comment.id}  {comment.status:8s} {comment.kind:9s} "
            f"part{comment.part} {path_text}  {head}"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    comment = find_comment(args.book, args.id)
    print(render_payload(comment, scope=args.scope))
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    # セッションを渡さない場合はモデルと effort を identity にする。同じ担当が
    # 待ち直すたびに別人と見なされないようにするための既定値で、本当の排他が
    # ほしければ担当が固有の値を渡す。
    if not args.session:
        args.session = f"{args.model}:{args.effort}" or "default"
    try:
        book, pending = wait_for_open(
            None,
            args.timeout,
            args.server,
            session=args.session,
            model=args.model,
            effort=args.effort,
        )
    except WaiterBusy as exc:
        print(str(exc), file=sys.stderr)
        print("二重に処理しないよう、ここで終了する。")
        return 2
    if not pending or not book:
        print("(timeout: 未処理のコメントなし)")
        return 1
    outline = outline_path(book)
    if not outline.is_file():
        print(f"book: {book}")
        print(f"outline: {outline.relative_to(ROOT)} … 未作成")
        print(f"README.md 最終更新日時: {readme_modified_at(book)}")
        print("outline を作成すること。作成を検知するまで初期化中として接続を保つ。", flush=True)
        while not outline.is_file():
            if args.server:
                _long_poll(
                    args.server,
                    book,
                    max(1.0, min(300.0, args.timeout)),
                    {"session": args.session, "model": args.model, "effort": args.effort},
                    phase="initializing",
                )
            else:
                time.sleep(0.3)
        if args.server:
            _long_poll(
                args.server,
                book,
                1.0,
                {"session": args.session, "model": args.model, "effort": args.effort},
                phase="working",
            )
        pending = open_comments(book)
        if not pending:
            print("(初期化中に未処理コメントが無くなった)")
            return 1
    group = group_with_same_section(pending) if args.group else pending[:1]
    print(render_payload(group[0], group=group, scope=args.scope))
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    comment = find_comment(args.book, args.id)
    set_status(comment, "answered", answer=args.message)
    print(f"answered: {comment.path.relative_to(ROOT)}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    comment = find_comment(args.book, args.id)
    set_status(comment, args.new_status)
    print(f"{args.new_status}: {comment.path.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="コメント一覧")
    listing.add_argument("--book")
    listing.add_argument("--status", choices=STATUSES)
    listing.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="1件を窓つきで表示")
    show.add_argument("--book", required=True)
    show.add_argument("--id", required=True)
    show.add_argument(
        "--scope",
        choices=("auto", "paragraph", "section", "part"),
        default="auto",
        help="窓の広さ。コメントの内容がもっと広い範囲に関わるときに引き直す",
    )
    show.set_defaults(func=cmd_show)

    wait = sub.add_parser("wait", help="未処理のコメントが来るまで待って表示")
    wait.add_argument("--timeout", type=float, default=900.0)
    wait.add_argument("--server", default="http://127.0.0.1:3000", help="dev_server の URL（空でファイル監視）")
    wait.add_argument("--no-group", dest="group", action="store_false", help="同一節のまとめ処理をしない")
    wait.add_argument("--scope", choices=("auto", "paragraph", "section", "part"), default="auto")
    wait.add_argument("--model", default="", help="自分のモデル名（画面に出る）")
    wait.add_argument("--effort", default="", help="自分の effort（画面に出る）")
    wait.add_argument(
        "--session",
        default="",
        help="セッションを識別する任意の文字列。同じ担当が待ち直すときは同じ値を渡す",
    )
    wait.set_defaults(func=cmd_wait, group=True)

    answer = sub.add_parser("answer", help="対応内容を書いて answered にする")
    answer.add_argument("--book", required=True)
    answer.add_argument("--id", required=True)
    answer.add_argument("--message", required=True)
    answer.set_defaults(func=cmd_answer)

    for name, help_text in (("resolve", "人が確認して閉じる"), ("stale", "位置を見失ったので差し戻す"), ("reopen", "open へ戻す")):
        status = sub.add_parser(name, help=help_text)
        status.add_argument("--book", required=True)
        status.add_argument("--id", required=True)
        status.set_defaults(func=cmd_status, new_status=STATUS_ACTIONS[name])

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CommentConflict as exc:
        print(f"conflict: {exc}", file=sys.stderr)
        return 2
    except CommentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
