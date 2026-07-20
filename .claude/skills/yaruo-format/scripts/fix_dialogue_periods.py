#!/usr/bin/env python3
"""やる夫式教材の発言末に句点を補う。

話者ブロックの最後が自然言語行で、終止約物がない場合だけ ``。`` を補う。
強調記号・脚注参照・閉じカッコは末尾判定から除外するが、句点自体は行末へ
追加する。コード、数式、表などで終わる発言ブロックは変更しない。冪等。

usage: fix_dialogue_periods.py <file.md> [--check]
  --check: 変更せず、変更が必要な行番号を表示して終了コード1を返す
"""

import re
import sys


SPEAKER_RE = re.compile(r"^\*\*([^*\n]+)\*\*[^*:：\n]*[:：]\s*$")
ROSTER_RE = re.compile(r"^\*\*([^*\n]+)\*\*")
SECTION_RE = re.compile(r"^(?:---\s*$|#{1,6}\s)")
DEFAULT_SPEAKERS = {"やる夫", "やらない夫"}
FOOTNOTE_RE = re.compile(r"\[\^[^]\n]+\]$")
TERMINAL_CHARS = frozenset("。．.!！?？…")
CLOSING_CHARS = frozenset("」』）】〕〉》〗〙〛")


def split_newline(line):
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def speaker_names(lines):
    bodies = [split_newline(line)[0].lstrip("　") for line in lines]
    counts = {}
    for body in bodies:
        match = SPEAKER_RE.match(body)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1

    names = set(DEFAULT_SPEAKERS)
    names.update(name for name, count in counts.items() if count >= 2)
    in_roster = False
    for body in bodies:
        if re.match(r"^##\s+登場人物\s*$", body):
            in_roster = True
            continue
        if in_roster and SECTION_RE.match(body):
            in_roster = False
        if in_roster:
            match = ROSTER_RE.match(body)
            if match:
                names.add(match.group(1))
    return names


def protected_lines(lines):
    """フェンスコードと $$ 数式ブロックに属する行indexを返す。"""
    protected = set()
    in_fence = False
    in_math = False
    for i, line in enumerate(lines):
        body = split_newline(line)[0]
        stripped = body.lstrip("　 \t")
        if in_fence:
            protected.add(i)
            if stripped.startswith("```"):
                in_fence = False
            continue
        if in_math:
            protected.add(i)
            if body.count("$$") % 2 == 1:
                in_math = False
            continue
        if stripped.startswith("```"):
            protected.add(i)
            in_fence = True
        elif stripped.startswith("$$"):
            protected.add(i)
            if body.count("$$") % 2 == 1:
                in_math = True
    return protected


def semantic_end(body):
    """Markdown末尾装飾と閉じカッコを除いた判定対象文字列を返す。"""
    text = body.rstrip()
    while text:
        before = text
        if text.endswith("**"):
            text = text[:-2].rstrip()
        match = FOOTNOTE_RE.search(text)
        if match:
            text = text[: match.start()].rstrip()
        while text and text[-1] in CLOSING_CHARS:
            text = text[:-1].rstrip()
        if text == before:
            break
    return text


def is_non_prose_ending(body, line_index, protected):
    stripped = body.lstrip()
    return (
        line_index in protected
        or stripped.startswith("|")
        or stripped.startswith(">")
        or re.match(r"^(?:[-+*]|\d+[.)])\s", stripped) is not None
        or stripped.startswith("[^" )
    )


def process(lines):
    out = list(lines)
    changes = []
    warnings = []
    names = speaker_names(lines)
    protected = protected_lines(lines)
    speakers = {
        i for i, line in enumerate(lines)
        if (match := SPEAKER_RE.match(split_newline(line)[0].lstrip("　")))
        and match.group(1) in names
    }

    for start in sorted(speakers):
        stop = start + 1
        while stop < len(lines):
            body = split_newline(lines[stop])[0]
            if stop in speakers or SECTION_RE.match(body):
                break
            stop += 1

        last = stop - 1
        while last > start and not split_newline(lines[last])[0].strip():
            last -= 1
        if last == start:
            continue

        body, newline = split_newline(lines[last])
        if is_non_prose_ending(body, last, protected):
            continue
        end = semantic_end(body)
        if not end:
            continue
        if end.endswith("──") or end[-1] in TERMINAL_CHARS:
            continue
        if end[-1] in "、，,：:；;":
            warnings.append((last + 1, f"発言末が {end[-1]!r} のため要確認"))
            continue

        out[last] = body.rstrip() + "。" + newline
        changes.append(last + 1)

    return out, changes, warnings


def main():
    args = [arg for arg in sys.argv[1:] if arg != "--check"]
    check = "--check" in sys.argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    path = args[0]
    with open(path, encoding="utf-8", newline="") as file:
        lines = file.readlines()
    out, changes, warnings = process(lines)

    for line_number in changes:
        print(f"{path}:{line_number}: needs dialogue-final period")
    for line_number, warning in warnings:
        print(f"{path}:{line_number}: warning: {warning}")
    if check:
        print(f"{len(changes)} line(s) need dialogue-final periods")
        return 1 if changes else 0
    if changes:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.writelines(out)
    print(f"{path}: {len(changes)} line(s) fixed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
