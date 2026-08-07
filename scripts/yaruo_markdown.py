#!/usr/bin/env python3
"""やる夫式教材の Markdown を解析する共通モジュール。

話者行の判定と非散文領域（フェンスコード・$$ 数式ブロック）の判定は、以前
`format_dialogue.py` / `fix_dialogue_periods.py` / `count_textbooks.py` /
`check_dialogue_constraints.py` の4箇所へ複製され、「ここを変えたら同期すること」
というコメントで整合を保っていた。その複製をここへ一本化する。

解析器は**全話者を返す**。「主役2名だけを数える」といった限定は、解析ではなく
ルール側のフィルタとして表現する。

利用者: scripts/yaruo_lint.py, .claude/skills/yaruo-count/scripts/count_textbooks.py
"""

from __future__ import annotations

import re

FULLWIDTH_SPACE = "　"

# `**やる夫**：` および注記つきの `**やる夫**（老いて）：`。全角・半角コロン両対応。
SPEAKER_LINE = re.compile(r"^\*\*([^*\n]+)\*\*[^*:：\n]*[:：]\s*$")
ROSTER_LINE = re.compile(r"^\*\*([^*\n]+)\*\*")
# 区切り行は空白を含まない `---` の完全一致とする。前後の改行数は
# `yaruo_lint.py` の structure-delimiter が正規化する。
SECTION_LINE = re.compile(r"^(?:---$|#{1,6}\s)")
ROSTER_HEADING = re.compile(r"^##\s+登場人物\s*$")
# 単独行の画像（図版）。本文ではなく図として扱い、句点や表記の検査対象から外す。
IMAGE_LINE = re.compile(r"^!\[[^\]]*\]\([^)\s]+\)$")
DEFAULT_SPEAKERS = frozenset({"やる夫", "やらない夫"})


def split_eol(line: str) -> tuple[str, str]:
    """行を本文と改行コード（\\r\\n / \\n / 空）に分ける。newline="" で読むため。"""
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def bodies_of(lines: list[str]) -> list[str]:
    """行頭の全角空白と改行を落とした本文列を返す。話者判定の入力になる。"""
    return [split_eol(line)[0].lstrip(FULLWIDTH_SPACE) for line in lines]


def speaker_names(lines: list[str]) -> set[str]:
    """本文から話者名の集合を確定する。

    標準話者、`## 登場人物` 欄で宣言された名前、そして2回以上現れるラベルを
    話者とみなす。2回以上という条件により、`**項目**：` のような単発のラベルを
    話者と誤認しない。
    """
    bodies = bodies_of(lines)
    counts: dict[str, int] = {}
    for body in bodies:
        if match := SPEAKER_LINE.match(body):
            name = match.group(1)
            counts[name] = counts.get(name, 0) + 1

    names = set(DEFAULT_SPEAKERS)
    names.update(name for name, count in counts.items() if count >= 2)

    in_roster = False
    for body in bodies:
        if ROSTER_HEADING.match(body):
            in_roster = True
            continue
        if in_roster and SECTION_LINE.match(body):
            in_roster = False
        if in_roster and (match := ROSTER_LINE.match(body)):
            names.add(match.group(1))
    return names


def speaker_line_indices(lines: list[str], names: set[str] | None = None) -> set[int]:
    """話者行の 0-indexed 行番号集合を返す。"""
    if names is None:
        names = speaker_names(lines)
    return {
        index
        for index, body in enumerate(bodies_of(lines))
        if (match := SPEAKER_LINE.match(body)) and match.group(1) in names
    }


def is_speaker_line(body: str, names: set[str]) -> bool:
    match = SPEAKER_LINE.match(body)
    return bool(match) and match.group(1) in names


def non_prose_lines(lines: list[str]) -> set[int]:
    """フェンスコード・$$ 数式ブロック・単独行の画像の 0-indexed 行番号を返す。

    フェンス行・`$$` 行そのものも含む。1行内で `$$` が偶数個閉じている場合は
    ブロックに入らない（行内数式扱い）。
    """
    protected: set[int] = set()
    in_fence = False
    in_math = False
    for index, line in enumerate(lines):
        body = split_eol(line)[0]
        stripped = body.lstrip("　 \t")
        if in_fence:
            protected.add(index)
            if stripped.startswith("```"):
                in_fence = False
            continue
        if in_math:
            protected.add(index)
            if body.count("$$") % 2 == 1:
                in_math = False
            continue
        if stripped.startswith("```"):
            protected.add(index)
            in_fence = True
        elif stripped.startswith("$$"):
            protected.add(index)
            if body.count("$$") % 2 == 1:
                in_math = True
        elif IMAGE_LINE.match(stripped.rstrip()):
            protected.add(index)
    return protected
