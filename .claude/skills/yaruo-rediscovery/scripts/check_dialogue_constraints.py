#!/usr/bin/env python3
"""やる夫式教材の最低往復数と数値表記を検査する。"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


SPEAKER_RE = re.compile(r"^\*\*(やる夫|やらない夫)\*\*.*：\s*$")
HEADING_RE = re.compile(r"^(##|###)\s+(.+?)\s*$")
KANJI_MONEY_RE = re.compile(
    r"(?<![0-9０-９])[〇一二三四五六七八九十百千]"
    r"[〇一二三四五六七八九十百千万億兆・]*(?:円|ドル|ユーロ|ポンド|元)"
)
KANJI_PERCENT_RE = re.compile(r"[〇一二三四五六七八九十百千万億兆・]+パーセント")
FULLWIDTH_NUMBER_RE = re.compile(r"[０-９][０-９,.]*(?:円|ドル|ユーロ|ポンド|元|％)")
FULLWIDTH_PERCENT_RE = re.compile(r"(?:[0-9０-９]+(?:[.,．][0-9０-９]+)?)％")


@dataclass
class Section:
    level: str
    title: str
    line: int
    yaruo: int = 0
    yaranai: int = 0

    def should_check(self) -> bool:
        if self.yaruo + self.yaranai == 0:
            return False
        return self.level == "###" or self.title.startswith(("幕間", "終幕", "演習"))


def parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    for line_no, line in enumerate(lines, 1):
        heading = HEADING_RE.match(line)
        if heading:
            if current is not None:
                sections.append(current)
            current = Section(heading.group(1), heading.group(2), line_no)
            continue
        if current is None:
            continue
        speaker = SPEAKER_RE.match(line)
        if speaker and speaker.group(1) == "やる夫":
            current.yaruo += 1
        elif speaker:
            current.yaranai += 1
    if current is not None:
        sections.append(current)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    lines = args.path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []

    for section in parse_sections(lines):
        if section.should_check() and min(section.yaruo, section.yaranai) < 5:
            problems.append(
                f"{args.path}:{section.line}: 5往復未満: {section.title} "
                f"(やる夫{section.yaruo}回／やらない夫{section.yaranai}回)"
            )

    notation_patterns = (
        (KANJI_MONEY_RE, "漢数字の金額"),
        (KANJI_PERCENT_RE, "パーセント表記"),
        (FULLWIDTH_NUMBER_RE, "全角数字"),
        (FULLWIDTH_PERCENT_RE, "全角%"),
    )
    for line_no, line in enumerate(lines, 1):
        for pattern, label in notation_patterns:
            match = pattern.search(line)
            if match:
                problems.append(
                    f"{args.path}:{line_no}: {label}: {match.group(0)}"
                )

    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
