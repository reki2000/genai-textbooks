#!/usr/bin/env python3
"""やる夫式教材の会話表記を整形する。

話者行に続く発言は外枠の「」で囲まず、継続行も全角空白で字下げしない。
話者ブロック内で行頭が「の区間をすべて探し、対応する」がその行の
末尾にある場合だけ、その一組を発言外枠として削除する。前後に通常文、
数式、表があっても判定は変えない。
対応する」が行末以外にある場合は両方を保存する。閉じ」がない場合は、
壊れた発言外枠として先頭の「だけを削除し、warning を出す。

usage: format_dialogue.py <file.md> [--check]
  --check: 変更せず、変更が必要な行番号を表示して終了コード1を返す
"""

import re
import sys


FWSP = "　"
# 話者行・登場人物欄の判定規則は count_textbooks.py / fix_dialogue_periods.py と
# 同一。check_dialogue_constraints.py は主役2名に限定した同等版。ここを変えるとき
# は各スクリプトの SPEAKER_RE とロースター走査も同期すること。
SPEAKER_RE = re.compile(r"^\*\*([^*\n]+)\*\*[^*:：\n]*[:：]\s*$")
ROSTER_RE = re.compile(r"^\*\*([^*\n]+)\*\*")
SECTION_RE = re.compile(r"^(?:---\s*$|#{1,6}\s)")
DEFAULT_SPEAKERS = {"やる夫", "やらない夫"}


def split_newline(line):
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def find_matching_close(lines, first, stop):
    """first 行頭の「に対応する」の (行index, 文字index) を返す。"""
    depth = 1
    for line_index in range(first, stop):
        body, _ = split_newline(lines[line_index])
        start = 1 if line_index == first else 0
        for char_index in range(start, len(body)):
            char = body[char_index]
            if char == "「":
                depth += 1
            elif char == "」":
                depth -= 1
                if depth == 0:
                    return line_index, char_index
    return None


def process(lines):
    out = list(lines)
    changes = {}  # 1-indexed line number -> set of reasons
    warnings = []

    normalized_bodies = [split_newline(line)[0].lstrip(FWSP) for line in out]
    marker_counts = {}
    for body in normalized_bodies:
        match = SPEAKER_RE.match(body)
        if match:
            name = match.group(1)
            marker_counts[name] = marker_counts.get(name, 0) + 1

    # **名前**（注記）：も含め、標準話者、登場人物欄、複数回現れる
    # ラベルから話者名を確定する。
    # これにより、全角空白を除去した後も **項目**：を話者と誤認しない。
    speaker_names = set(DEFAULT_SPEAKERS)
    speaker_names.update(name for name, count in marker_counts.items() if count >= 2)
    in_roster = False
    for body in normalized_bodies:
        if re.match(r"^##\s+登場人物\s*$", body):
            in_roster = True
            continue
        if in_roster and SECTION_RE.match(body):
            in_roster = False
        if in_roster:
            match = ROSTER_RE.match(body)
            if match:
                speaker_names.add(match.group(1))

    speaker_lines = {
        i
        for i, body in enumerate(normalized_bodies)
        if (match := SPEAKER_RE.match(body)) and match.group(1) in speaker_names
    }

    def changed(line_index, reason):
        changes.setdefault(line_index + 1, set()).add(reason)

    # 発言の継続行を含め、行頭の全角空白はすべて除去する。
    # Markdown の hard break（空白2個）は保ち、単独の行末空白だけ除去する。
    for i, line in enumerate(out):
        body, newline = split_newline(line)
        stripped = body.lstrip(FWSP)
        if stripped != body:
            changed(i, "remove leading fullwidth space")
        trailing = re.search(r"[ \t]+$", stripped)
        if trailing and len(trailing.group()) == 1:
            stripped = stripped[: trailing.start()]
            changed(i, "remove single trailing whitespace")
        out[i] = stripped + newline

    i = 0
    while i < len(out):
        body, _ = split_newline(out[i])
        if i not in speaker_lines:
            i += 1
            continue

        stop = i + 1
        while stop < len(out):
            candidate, _ = split_newline(out[stop])
            if stop in speaker_lines or SECTION_RE.match(candidate):
                break
            stop += 1

        cursor = i + 1
        while cursor < stop:
            first_body, first_newline = split_newline(out[cursor])
            if not first_body.startswith("「"):
                cursor += 1
                continue

            close = find_matching_close(out, cursor, stop)
            if close is None:
                out[cursor] = first_body[1:] + first_newline
                changed(cursor, "remove unmatched dialogue opener")
                warnings.append(
                    f"line {cursor + 1}: unmatched dialogue opener removed"
                )
                cursor += 1
                continue

            close_line, close_char = close
            close_body, close_newline = split_newline(out[close_line])
            if close_body[close_char + 1 :].strip():
                cursor = close_line + 1
                continue

            if cursor == close_line:
                chars = list(first_body)
                del chars[close_char]
                del chars[0]
                out[cursor] = "".join(chars) + first_newline
            else:
                out[cursor] = first_body[1:] + first_newline
                out[close_line] = (
                    close_body[:close_char]
                    + close_body[close_char + 1 :]
                    + close_newline
                )
            changed(cursor, "remove dialogue opener")
            changed(close_line, "remove dialogue closer")
            cursor = close_line + 1
        i += 1

    # 閉じカッコの直前に空白があった場合、カッコ削除後に単独の行末空白が
    # 露出する。1回の実行で完了するよう、最後にもう一度だけ除去する。
    for i, line in enumerate(out):
        body, newline = split_newline(line)
        trailing = re.search(r"[ \t]+$", body)
        if trailing and len(trailing.group()) == 1:
            out[i] = body[: trailing.start()] + newline
            changed(i, "remove single trailing whitespace")

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

    for line_number in sorted(changes):
        reasons = ", ".join(sorted(changes[line_number]))
        print(f"{path}:{line_number}: {reasons}")
    for warning in warnings:
        print(f"{path}: warning: {warning}")

    if check:
        print(f"{len(changes)} line(s) need dialogue formatting")
        return 1 if changes else 0

    if changes:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.writelines(out)
    print(f"{path}: {len(changes)} line(s) formatted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
