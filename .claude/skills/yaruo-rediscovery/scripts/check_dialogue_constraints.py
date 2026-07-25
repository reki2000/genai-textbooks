#!/usr/bin/env python3
"""やる夫式教材の会話量（1発言の分量と往復数の帯）と数値表記を検査する。"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path


# 話者行の判定は yaruo-format / yaruo-count と同一の規則に合わせる（全角・半角
# コロン両対応、**名前**（注記）：の形も許容）。往復数の判定対象は主役2名のみ
# なので名前は限定する。ここを変えるときは format_dialogue.py / count_textbooks.py /
# fix_dialogue_periods.py の SPEAKER_RE も同期すること。

# 1発言の分量から、その節に許される往復数の帯を決める。SKILL.md「人物と節運びの
# 必須ルール」の表と同期すること。(平均字数の下限, 平均行数の下限, 最小往復, 最大往復)
BANDS = (
    (130, 5.0, 4, 7),   # 濃い発言：数式、表、数値計算を含む
    (90, 3.5, 5, 9),    # 中間
    (0, 0.0, 6, 11),    # 短い応酬が主
)
ABSOLUTE_MIN_TURNS = 4      # 絶対的な下限。これを割るとエラー（帯の下限割れは警告）
SECTION_CHAR_LIMIT = 1800   # 1節の会話量の上限（字）
SPEECH_LINE_LIMIT = 7       # 1発言の行数の上限
SPEAKER_RE = re.compile(r"^\*\*(やる夫|やらない夫)\*\*[^*:：\n]*[:：]\s*$")
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
    speech_lines: list[int] = field(default_factory=list)
    speech_chars: list[int] = field(default_factory=list)

    def should_check(self) -> bool:
        if self.yaruo + self.yaranai == 0:
            return False
        return self.level == "###" or self.title.startswith(("幕間", "終幕", "演習"))

    @property
    def turns(self) -> int:
        return min(self.yaruo, self.yaranai)

    @property
    def avg_lines(self) -> float:
        return sum(self.speech_lines) / len(self.speech_lines) if self.speech_lines else 0.0

    @property
    def avg_chars(self) -> float:
        return sum(self.speech_chars) / len(self.speech_chars) if self.speech_chars else 0.0

    @property
    def total_chars(self) -> int:
        return sum(self.speech_chars)

    def band(self) -> tuple[int, int]:
        for min_chars, min_lines, low, high in BANDS:
            if self.avg_chars >= min_chars or self.avg_lines >= min_lines:
                return low, high
        return BANDS[-1][2], BANDS[-1][3]


def parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    in_speech = False
    for line_no, line in enumerate(lines, 1):
        heading = HEADING_RE.match(line)
        if heading:
            if current is not None:
                sections.append(current)
            current = Section(heading.group(1), heading.group(2), line_no)
            in_speech = False
            continue
        if current is None:
            continue
        speaker = SPEAKER_RE.match(line)
        if speaker:
            if speaker.group(1) == "やる夫":
                current.yaruo += 1
            else:
                current.yaranai += 1
            current.speech_lines.append(0)
            current.speech_chars.append(0)
            in_speech = True
            continue
        if in_speech:
            if line.strip() == "":
                in_speech = False
                continue
            current.speech_lines[-1] += 1
            current.speech_chars[-1] += len(line.encode("utf-8")) // 3
    if current is not None:
        sections.append(current)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    lines = args.path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []
    warnings: list[str] = []

    for section in parse_sections(lines):
        if not section.should_check():
            continue
        low, high = section.band()
        shape = (
            f"1発言 平均{section.avg_lines:.1f}行／{section.avg_chars:.0f}字、"
            f"帯 {low}〜{high}往復"
        )
        if section.turns < ABSOLUTE_MIN_TURNS:
            problems.append(
                f"{args.path}:{section.line}: {ABSOLUTE_MIN_TURNS}往復未満: {section.title} "
                f"({section.turns}往復、{shape})"
            )
        elif section.turns < low:
            warnings.append(
                f"{args.path}:{section.line}: 帯の下限未満: {section.title} "
                f"({section.turns}往復、{shape})"
            )
        elif section.turns > high:
            warnings.append(
                f"{args.path}:{section.line}: 帯の上限超過: {section.title} "
                f"({section.turns}往復、{shape})"
            )
        if section.total_chars > SECTION_CHAR_LIMIT:
            warnings.append(
                f"{args.path}:{section.line}: 会話量が多い: {section.title} "
                f"({section.total_chars}字 > {SECTION_CHAR_LIMIT}字)"
            )
        long_speeches = sum(1 for n in section.speech_lines if n > SPEECH_LINE_LIMIT)
        if long_speeches:
            warnings.append(
                f"{args.path}:{section.line}: {SPEECH_LINE_LIMIT}行超の発言が"
                f"{long_speeches}件: {section.title}"
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

    if warnings:
        print("\n".join(f"warning: {w}" for w in warnings))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
