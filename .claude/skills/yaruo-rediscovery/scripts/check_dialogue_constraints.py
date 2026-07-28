#!/usr/bin/env python3
"""やる夫式教材の会話量、発言長の分布、実効往復、数値表記を検査する。"""

from __future__ import annotations

import argparse
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path


# 話者行の判定は yaruo-format / yaruo-count と同一の規則に合わせる（全角・半角
# コロン両対応、**名前**（注記）：の形も許容）。往復数の判定対象は主役2名のみ
# なので名前は限定する。ここを変えるときは format_dialogue.py / count_textbooks.py /
# fix_dialogue_periods.py の SPEAKER_RE も同期すること。
#
# 会話量と発言長は yaruo-count と同じUnicodeコードポイント数で数える。発言長の帯は
# 節を分類するためでなく、節内のテンポ分布を診断するために使う。
LENGTH_BANDS = (
    ("瞬発", 35),
    ("短い推論", 75),
    ("展開", 130),
    ("錨", None),
)
MIN_EFFECTIVE_TURNS = 4
MANY_TURNS = 18
SECTION_CHAR_MIN = 1200
SECTION_CHAR_MAX = 1800
SPEECH_CHAR_REVIEW = 220
SPEECH_LINE_LIMIT = 7
RAPID_MAX_CHARS = 75
RAPID_MIN_UTTERANCES = 4
UNIFORM_BAND_RATIO = 0.75
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
    speakers: list[str] = field(default_factory=list)
    speech_lines: list[int] = field(default_factory=list)
    speech_chars: list[int] = field(default_factory=list)

    def should_check(self) -> bool:
        if not self.speakers:
            return False
        return self.level == "###" or self.title.startswith(("幕間", "終幕", "演習"))

    @property
    def turns(self) -> int:
        """同一話者の連続ブロックを畳み込んだ実効往復数。"""
        collapsed: list[str] = []
        for speaker in self.speakers:
            if not collapsed or collapsed[-1] != speaker:
                collapsed.append(speaker)
        return len(collapsed) // 2

    @property
    def median_chars(self) -> float:
        return statistics.median(self.speech_chars) if self.speech_chars else 0.0

    @property
    def min_chars(self) -> int:
        return min(self.speech_chars, default=0)

    @property
    def max_chars(self) -> int:
        return max(self.speech_chars, default=0)

    @property
    def total_chars(self) -> int:
        return sum(self.speech_chars)

    def band_counts(self) -> list[tuple[str, int]]:
        counts = {label: 0 for label, _ in LENGTH_BANDS}
        for chars in self.speech_chars:
            for label, upper in LENGTH_BANDS:
                if upper is None or chars <= upper:
                    counts[label] += 1
                    break
        return [(label, counts[label]) for label, _ in LENGTH_BANDS]

    def rapid_runs(self) -> list[tuple[int, int]]:
        """75字以下が4発言以上続く区間を、1始まりの閉区間で返す。"""
        runs: list[tuple[int, int]] = []
        start: int | None = None
        for index, chars in enumerate(self.speech_chars, 1):
            if chars <= RAPID_MAX_CHARS:
                if start is None:
                    start = index
                continue
            if start is not None and index - start >= RAPID_MIN_UTTERANCES:
                runs.append((start, index - 1))
            start = None
        if start is not None and len(self.speech_chars) + 1 - start >= RAPID_MIN_UTTERANCES:
            runs.append((start, len(self.speech_chars)))
        return runs

    def shape(self) -> str:
        bands = "／".join(f"{label}{count}" for label, count in self.band_counts())
        return (
            f"{self.turns}実効往復、{len(self.speech_chars)}発言、"
            f"発言字数 {self.min_chars}〜{self.median_chars:g}〜{self.max_chars}、"
            f"{bands}、計{self.total_chars}字"
        )


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
            current.speakers.append(speaker.group(1))
            current.speech_lines.append(0)
            current.speech_chars.append(0)
            in_speech = True
            continue
        if in_speech:
            if line.strip() == "":
                continue
            if line.strip() == "---":
                in_speech = False
                continue
            current.speech_lines[-1] += 1
            current.speech_chars[-1] += len(line)
    if current is not None:
        sections.append(current)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="節ごとの実効往復、発言長分布、高速区間を表示する",
    )
    args = parser.parse_args()
    lines = args.path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []
    warnings: list[str] = []
    diagnostics: list[str] = []

    for section in parse_sections(lines):
        if not section.should_check():
            continue
        shape = section.shape()
        rapid = section.rapid_runs()
        rapid_text = (
            "、高速区間 "
            + "・".join(f"{start}〜{end}発言目" for start, end in rapid)
            if rapid
            else ""
        )
        diagnostics.append(
            f"{args.path}:{section.line}: {section.title} ({shape}{rapid_text})"
        )
        if section.turns < MIN_EFFECTIVE_TURNS:
            warnings.append(
                f"{args.path}:{section.line}: {MIN_EFFECTIVE_TURNS}実効往復未満: "
                f"{section.title}（核心概念なら不足、{shape}）"
            )
        if section.turns > MANY_TURNS:
            warnings.append(
                f"{args.path}:{section.line}: {MANY_TURNS}実効往復超: {section.title} "
                f"（核心概念が二つ競合していないか確認、{shape}）"
            )
        if section.total_chars < SECTION_CHAR_MIN:
            warnings.append(
                f"{args.path}:{section.line}: 会話量が少ない: {section.title} "
                f"({section.total_chars}字 < {SECTION_CHAR_MIN}字、{shape})"
            )
        elif section.total_chars > SECTION_CHAR_MAX:
            warnings.append(
                f"{args.path}:{section.line}: 会話量が多い: {section.title} "
                f"({section.total_chars}字 > {SECTION_CHAR_MAX}字、{shape})"
            )
        long_speeches = sum(1 for n in section.speech_lines if n > SPEECH_LINE_LIMIT)
        if long_speeches:
            warnings.append(
                f"{args.path}:{section.line}: {SPEECH_LINE_LIMIT}行超の発言が"
                f"{long_speeches}件: {section.title}"
            )
        oversized = sum(1 for n in section.speech_chars if n > SPEECH_CHAR_REVIEW)
        if oversized:
            warnings.append(
                f"{args.path}:{section.line}: {SPEECH_CHAR_REVIEW}字超の発言が"
                f"{oversized}件: {section.title} "
                "（感情の頂点または不可分な導出か確認）"
            )
        band_counts = section.band_counts()
        if len(section.speech_chars) >= 8:
            dominant_label, dominant_count = max(band_counts, key=lambda item: item[1])
            if dominant_count / len(section.speech_chars) >= UNIFORM_BAND_RATIO:
                warnings.append(
                    f"{args.path}:{section.line}: 発言長が「{dominant_label}」へ"
                    f"{dominant_count}/{len(section.speech_chars)}件集中: "
                    f"{section.title}（テンポ一定でないか確認、{shape}）"
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

    if args.verbose and diagnostics:
        print("\n".join(f"info: {item}" for item in diagnostics))
    if warnings:
        print("\n".join(f"warning: {w}" for w in warnings))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
