#!/usr/bin/env python3
"""やる夫式教材の台本形式（@形式）を読み書きする。

教材の正本を `docs/books/{ID}/script/NN.txt`（幕ごとの@形式）に置き、
`README.md` はそこから生成する。`README.md` を読む既存の道具（lint・字数集計・
差分ページ・コメント・docsify）はそのまま動き、`generate_site.py` は両者が
食い違えばビルドを止める。

@形式の文法:

    @u7f3a やる夫
    （発言の本文。Markdown・数式・表・図をそのまま書ける）
    @end

- `@<ID> <話者>[注記]` で発言を開き、`@end` で閉じる。注記は `（老いて）` など。
  ID を省いた `@ やる夫` は `fmt` が採番して書き戻す。
- ブロックの外は素通しの Markdown（見出し・区切り・地の文・図・参考文献）。
- `@` で始まる行を本文に書くときは `@@` と1文字重ねる（読むときに1文字外す）。
- ID は教材の中で一意で、発言を並べ替えても書き換えても変えない。発言を
  丸ごと書き直したときだけ新しい ID にする。

使い方:

    python3 scripts/yaruo_script.py convert docs/books/statistics   # README.md → script/
    python3 scripts/yaruo_script.py render  docs/books/statistics   # script/ → README.md
    python3 scripts/yaruo_script.py absorb  docs/books/statistics   # 手で直した README.md を script/ へ戻す（ID を保つ）
    python3 scripts/yaruo_script.py fmt     docs/books/statistics   # ID の採番と整形
    python3 scripts/yaruo_script.py check   docs/books/*            # 構文・同期の検査
    python3 scripts/yaruo_script.py roundtrip docs/books/*          # README.md → @ → README.md の往復検査
    python3 scripts/yaruo_script.py json    docs/books/statistics   # 構造を JSON で出す
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yaruo_markdown import (  # noqa: E402
    CAPTION_LINE,
    IMAGE_LINE,
    SPEAKER_LINE,
    non_prose_lines,
    speaker_names,
)

SCRIPT_DIR_NAME = "script"
README_NAME = "README.md"
OPEN_LINE = re.compile(r"^@(u[0-9a-f]{4,8})? (\S.*)$")
END_LINE = "@end"
ID_PATTERN = re.compile(r"^u[0-9a-f]{4,8}$")
ACT_HEADING = re.compile(r"^## (?!登場人物\s*$)")
SPEAKER_NOTE = re.compile(r"^([^\s（(]+)(.*)$")


class ScriptError(Exception):
    """@形式の構文エラー。ファイル名と行番号を持つ。"""


@dataclass
class Raw:
    lines: list[str]


@dataclass
class Utterance:
    id: str | None
    speaker: str
    note: str
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


Item = Raw | Utterance


@dataclass
class Act:
    name: str  # ファイル名（拡張子なし）。00 は前付け
    items: list[Item] = field(default_factory=list)

    @property
    def heading(self) -> str:
        for item in self.items:
            if isinstance(item, Raw):
                for line in item.lines:
                    if line.startswith("## "):
                        return line[3:].strip()
        return ""


# ---------------------------------------------------------------- 読み書き


def _escape(line: str) -> str:
    return "@" + line if line.startswith("@") else line


def _unescape(line: str) -> str:
    return line[1:] if line.startswith("@@") else line


def parse_act(text: str, name: str = "", source: str = "") -> Act:
    act = Act(name=name)
    raw: list[str] = []
    current: Utterance | None = None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, start=1):
        where = f"{source}:{number}"
        if current is not None:
            if line == END_LINE:
                act.items.append(current)
                current = None
            elif line.startswith("@") and not line.startswith("@@"):
                raise ScriptError(f"{where}: 発言の中に `@` で始まる行がある（閉じ忘れか、`@@` へのエスケープ漏れ）: {line}")
            else:
                current.lines.append(_unescape(line))
            continue
        if line == END_LINE:
            raise ScriptError(f"{where}: 対応する開きのない `@end`")
        if line.startswith("@") and not line.startswith("@@"):
            match = OPEN_LINE.match(line)
            if not match:
                raise ScriptError(f"{where}: 開き行の形式が違う（`@u1a2b やる夫` か `@ やる夫`）: {line}")
            speaker_match = SPEAKER_NOTE.match(match.group(2))
            assert speaker_match
            if raw:
                act.items.append(Raw(raw))
                raw = []
            current = Utterance(match.group(1), speaker_match.group(1), speaker_match.group(2), [])
            continue
        raw.append(_unescape(line))
    if current is not None:
        raise ScriptError(f"{source}: 発言 {current.id or '(ID未採番)'} {current.speaker} が `@end` で閉じていない")
    if raw:
        act.items.append(Raw(raw))
    return act


def serialize_act(act: Act) -> str:
    out: list[str] = []
    for item in act.items:
        if isinstance(item, Raw):
            out.extend(_escape(line) for line in item.lines)
        else:
            head = f"@{item.id or ''} {item.speaker}{item.note}"
            out.append(head)
            out.extend(_escape(line) for line in item.lines)
            out.append(END_LINE)
    return "\n".join(out) + "\n"


def load_script(book_dir: Path) -> list[Act]:
    script_dir = book_dir / SCRIPT_DIR_NAME
    files = sorted(script_dir.glob("*.txt"))
    if not files:
        raise ScriptError(f"{script_dir}: 幕ファイル（NN.txt）が無い")
    return [parse_act(path.read_text(encoding="utf-8"), path.stem, str(path)) for path in files]


def write_script(book_dir: Path, acts: list[Act]) -> None:
    script_dir = book_dir / SCRIPT_DIR_NAME
    script_dir.mkdir(exist_ok=True)
    wanted = {f"{act.name}.txt" for act in acts}
    for path in script_dir.glob("*.txt"):
        if path.name not in wanted:
            path.unlink()
    for act in acts:
        path = script_dir / f"{act.name}.txt"
        text = serialize_act(act)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- Markdown との変換


def render_markdown(acts: list[Act]) -> str:
    out: list[str] = []
    for act in acts:
        for item in act.items:
            if isinstance(item, Raw):
                out.extend(item.lines)
            else:
                out.append(f"**{item.speaker}**{item.note}：")
                out.extend(item.lines)
    return "\n".join(out) + "\n"


def _trailing_tail(lines: list[str], start: int, end: int) -> int:
    """発言 [start, end) の末尾から、発言に属さない部分（空行と、末尾の図版ブロック）の
    開始位置を返す。図は話者の台詞ではなく、地の文として発言の外に出す。"""
    cut = end
    while True:
        k = cut
        while k > start and lines[k - 1].strip() == "":
            k -= 1
        # 末尾が「画像[ + 空行 + キャプション]」なら発言の外へ出す
        j = k
        if j > start and CAPTION_LINE.match(lines[j - 1].strip()):
            i = j - 1
            while i > start and lines[i - 1].strip() == "":
                i -= 1
            if i > start and IMAGE_LINE.match(lines[i - 1].strip()):
                j = i - 1
            else:
                j = k
        elif j > start and IMAGE_LINE.match(lines[j - 1].strip()):
            j -= 1
        if j == k:
            return k
        cut = j


def markdown_to_items(text: str) -> list[Item]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    names = speaker_names(lines)
    protected = non_prose_lines(lines)
    boundaries: list[int] = []
    speakers: dict[int, tuple[str, str]] = {}
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if index in protected or in_fence:
            continue
        match = SPEAKER_LINE.match(line)
        if match and match.group(1) in names and line.endswith("："):
            name = match.group(1)
            note = line[len(name) + 4 : -1]
            speakers[index] = (name, note)
            boundaries.append(index)
        elif line == "---" or line.startswith("#"):
            boundaries.append(index)
    boundaries.append(len(lines))

    items: list[Item] = []
    raw: list[str] = []
    cursor = 0

    def flush_raw(until: int) -> None:
        nonlocal raw
        raw.extend(lines[cursor:until])

    for position, start in enumerate(boundaries[:-1]):
        if start not in speakers:
            continue
        flush_raw(start)
        if raw:
            items.append(Raw(raw))
            raw = []
        end = next(b for b in boundaries[position + 1 :])
        tail = _trailing_tail(lines, start + 1, end)
        name, note = speakers[start]
        items.append(Utterance(None, name, note, lines[start + 1 : tail]))
        cursor = tail
    flush_raw(len(lines))
    if raw:
        items.append(Raw(raw))
    return items


def split_acts(items: list[Item]) -> list[Act]:
    """`## ` 見出し（登場人物を除く）ごとに幕ファイルへ分ける。前付けは 00。"""
    acts = [Act("00")]
    for item in items:
        if isinstance(item, Raw):
            chunk: list[str] = []
            for line in item.lines:
                if ACT_HEADING.match(line) and (chunk or acts[-1].items or len(acts) > 1):
                    # 見出しの直前の区切り `---` と空行は前の幕に残す
                    if chunk:
                        acts[-1].items.append(Raw(chunk))
                    chunk = []
                    acts.append(Act(f"{len(acts):02d}"))
                chunk.append(line)
            if chunk:
                acts[-1].items.append(Raw(chunk))
        else:
            acts[-1].items.append(item)
    return [act for act in acts if act.items]


def merge_adjacent_raw(items: list[Item]) -> list[Item]:
    merged: list[Item] = []
    for item in items:
        if isinstance(item, Raw) and merged and isinstance(merged[-1], Raw):
            merged[-1] = Raw(merged[-1].lines + item.lines)
        else:
            merged.append(item)
    return merged


# ---------------------------------------------------------------- ID


def all_utterances(acts: list[Act]) -> list[Utterance]:
    return [item for act in acts for item in act.items if isinstance(item, Utterance)]


def assign_ids(acts: list[Act]) -> int:
    used = {u.id for u in all_utterances(acts) if u.id}
    assigned = 0
    for utterance in all_utterances(acts):
        if utterance.id:
            continue
        while True:
            candidate = "u" + secrets.token_hex(2)
            if candidate not in used:
                break
        used.add(candidate)
        utterance.id = candidate
        assigned += 1
    return assigned


def validate(acts: list[Act], book_dir: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    markdown_lines = render_markdown(acts).split("\n")
    roster = speaker_names(markdown_lines)
    for act in acts:
        for item in act.items:
            if not isinstance(item, Utterance):
                continue
            where = f"{book_dir / SCRIPT_DIR_NAME / (act.name + '.txt')}"
            if not item.id:
                errors.append(f"{where}: ID未採番の発言がある（fmt で採番する）: {item.speaker}")
            elif not ID_PATTERN.match(item.id):
                errors.append(f"{where}: ID の形式が違う: {item.id}")
            elif item.id in seen:
                errors.append(f"{where}: ID {item.id} が重複している（{seen[item.id]} と）")
            else:
                seen[item.id] = act.name
            if item.speaker not in roster:
                errors.append(f"{where}: 話者「{item.speaker}」が登場人物欄にも2回以上の発言にも無い")
            if not any(line.strip() for line in item.lines):
                errors.append(f"{where}: 発言 {item.id} が空")
    return errors


# ---------------------------------------------------------------- absorb（README.md の手直しを ID を保って戻す）


def _key(u: Utterance) -> str:
    return u.speaker + "\x00" + u.text


def carry_ids(old: list[Utterance], new: list[Utterance]) -> dict[str, int]:
    """新しい発言列へ旧 ID を引き継ぐ。完全一致を対応づけ、残りは同じ話者で
    十分似ていれば同じ発言の書き換えとみなす。似ていなければ新しい ID になる。"""
    stats = {"kept": 0, "edited": 0, "new": 0}
    matcher = difflib.SequenceMatcher(a=[_key(u) for u in old], b=[_key(u) for u in new], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                new[j1 + k].id = old[i1 + k].id
                stats["kept"] += 1
            continue
        pool = list(range(i1, i2))
        for j in range(j1, j2):
            best, best_ratio = None, 0.0
            for i in pool:
                if old[i].speaker != new[j].speaker:
                    continue
                ratio = difflib.SequenceMatcher(a=old[i].text, b=new[j].text, autojunk=False).ratio()
                if ratio > best_ratio:
                    best, best_ratio = i, ratio
            if best is not None and best_ratio >= 0.5:
                new[j].id = old[best].id
                pool = [i for i in pool if i > best]
                stats["edited"] += 1
            else:
                stats["new"] += 1
    return stats


def acts_from_markdown(text: str) -> list[Act]:
    return split_acts(merge_adjacent_raw(markdown_to_items(text)))


# ---------------------------------------------------------------- JSON


def to_json(acts: list[Act], book_dir: Path) -> dict:
    out_acts = []
    section = ""
    for act in acts:
        blocks = []
        for item in act.items:
            if isinstance(item, Raw):
                for line in item.lines:
                    if line.startswith("### "):
                        section = line[4:].strip()
                blocks.append({"type": "raw", "md": "\n".join(item.lines)})
            else:
                blocks.append(
                    {
                        "type": "u",
                        "id": item.id,
                        "speaker": item.speaker,
                        "note": item.note,
                        "md": item.text,
                        "section": section,
                    }
                )
        out_acts.append({"name": act.name, "heading": act.heading, "blocks": blocks})
    return {"book": book_dir.name, "acts": out_acts}


# ---------------------------------------------------------------- CLI


def book_dirs(paths: list[str]) -> list[Path]:
    return [Path(p) for p in paths if Path(p).is_dir()]


def sync_error(book_dir: Path) -> str | None:
    """script/ を持つ教材で README.md が生成結果と一致しなければ理由を返す。"""
    if not (book_dir / SCRIPT_DIR_NAME).is_dir():
        return None
    acts = load_script(book_dir)
    errors = validate(acts, book_dir)
    if errors:
        return "\n".join(errors)
    readme = book_dir / README_NAME
    expected = render_markdown(acts)
    if not readme.exists() or readme.read_text(encoding="utf-8") != expected:
        return (
            f"{readme} が {book_dir / SCRIPT_DIR_NAME}/ から生成した内容と違う。"
            f"script/ を直したなら `python3 scripts/yaruo_script.py render {book_dir}`、"
            f"README.md を直したなら `python3 scripts/yaruo_script.py absorb {book_dir}` を実行する"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["convert", "render", "absorb", "fmt", "check", "roundtrip", "json"])
    parser.add_argument("books", nargs="+")
    parser.add_argument("--force", action="store_true", help="convert: 既存の script/ を上書きする")
    args = parser.parse_args(argv)
    status = 0
    for book_dir in book_dirs(args.books):
        readme = book_dir / README_NAME
        try:
            if args.command == "roundtrip":
                if not readme.exists():
                    continue
                text = readme.read_text(encoding="utf-8")
                acts = acts_from_markdown(text)
                assign_ids(acts)
                reparsed = [parse_act(serialize_act(a), a.name) for a in acts]
                back = render_markdown(reparsed)
                errors = validate(reparsed, book_dir)
                if back != text:
                    status = 1
                    diff = list(difflib.unified_diff(text.split("\n"), back.split("\n"), lineterm="", n=1))
                    print(f"NG {book_dir.name}: 往復で差分\n" + "\n".join(diff[:20]))
                elif errors:
                    status = 1
                    print(f"NG {book_dir.name}:\n  " + "\n  ".join(errors[:10]))
                else:
                    n = len(all_utterances(reparsed))
                    print(f"ok {book_dir.name}: {len(reparsed)}幕 {n}発言")
            elif args.command == "convert":
                if (book_dir / SCRIPT_DIR_NAME).exists() and not args.force:
                    raise ScriptError(f"{book_dir}: script/ が既にある（--force で上書き、手直しの取り込みは absorb）")
                acts = acts_from_markdown(readme.read_text(encoding="utf-8"))
                assign_ids(acts)
                write_script(book_dir, acts)
                print(f"converted {book_dir}: {len(acts)}幕 {len(all_utterances(acts))}発言")
            elif args.command == "render":
                acts = load_script(book_dir)
                assign_ids(acts)
                write_script(book_dir, acts)
                errors = validate(acts, book_dir)
                if errors:
                    raise ScriptError("\n".join(errors))
                readme.write_text(render_markdown(acts), encoding="utf-8")
                print(f"rendered {readme}")
            elif args.command == "absorb":
                old_acts = load_script(book_dir)
                new_acts = acts_from_markdown(readme.read_text(encoding="utf-8"))
                stats = carry_ids(all_utterances(old_acts), all_utterances(new_acts))
                assign_ids(new_acts)
                write_script(book_dir, new_acts)
                readme.write_text(render_markdown(new_acts), encoding="utf-8")
                print(f"absorbed {readme}: 維持{stats['kept']} 書換{stats['edited']} 新規{stats['new']}")
            elif args.command == "fmt":
                acts = load_script(book_dir)
                n = assign_ids(acts)
                write_script(book_dir, acts)
                print(f"fmt {book_dir}: {n}件採番")
            elif args.command == "check":
                if not (book_dir / SCRIPT_DIR_NAME).is_dir():
                    continue
                error = sync_error(book_dir)
                if error:
                    status = 1
                    print(f"NG {book_dir.name}: {error}")
                else:
                    print(f"ok {book_dir.name}")
            elif args.command == "json":
                acts = load_script(book_dir)
                json.dump(to_json(acts, book_dir), sys.stdout, ensure_ascii=False, indent=1)
                print()
        except ScriptError as error:
            print(f"error: {error}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
