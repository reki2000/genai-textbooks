#!/usr/bin/env python3
"""やる夫式教材の会話量、発言長、実効往復、構造、脚注、数値表記を検査する。

このファイルは数値制約の**正本**である。1節の字数帯、実効往復の下限、発言長の帯、
1発言の行数上限といった数値は、スキルの散文（SKILL.md / references/*.md）には
書かず、ここの定数だけを参照する。散文と定数が食い違ったらこちらが正しい。

検出は二段階に分ける。

- problems (exit 1)：機械的に白黒がつくもの。脚注の未使用・未定義、節番号の破れ、
  終端マーカーの表記揺れ、見出しの揺れ、禁止見出し、数値表記。
- warnings (exit 0)：判断が要るヒューリスティック。字数帯、往復数、発言長の偏り、
  節末を教師が締めている疑い、承認語のインフレなど。人が内容を見て可否を決める。
"""

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

# 節末を教師の長い発言で締めていないか。既存教材で較正した結果、最近の教材は
# この比率が0.00、講義調が残る古い教材は0.4〜0.5になる。閾値は「展開」帯の上限。
TEACHER_CLOSING_CHARS = 130
# 承認語の密度。既存教材の中央値は0.08件/節で、0.4を超えるのは明らかな外れ値。
APPROVAL_PER_SECTION = 0.4

END_MARKER = "**── 完 ──**"
# `**── I部 完 ──**` のような分冊の部完結マーカーも正当な形として認める。
# 太字や罫線を欠いた `── 完 ──`・`**完**`・`完` だけを表記揺れとして弾く。
END_MARKER_OK_RE = re.compile(r"^\*\*[─—―-]{2,4}\s*(?:\S+\s+)?完\s*[─—―-]{2,4}\*\*$")
END_MARKER_LIKE_RE = re.compile(
    r"^\*{0,2}\s*[─—―-]{0,4}\s*(?:\S+\s+)?完\s*[─—―-]{0,4}\s*\*{0,2}$"
)
SPEAKER_RE = re.compile(r"^\*\*(やる夫|やらない夫)\*\*[^*:：\n]*[:：]\s*$")
HEADING_RE = re.compile(r"^(##|###)\s+(.+?)\s*$")
ACT_RE = re.compile(r"^第(\d+)幕")
SECTION_NO_RE = re.compile(r"^(\d+)-(\d+)(?=[　\s])")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
FOOTNOTE_USE_RE = re.compile(r"\[\^([^\]]+)\](?!:)")
FOOTNOTE_BARE_RE = re.compile(r"参照[.。]?\s*$")
APPROVAL_RE = re.compile(r"鋭い|いい問いだ|良い言語化|完璧な直観")
BOILERPLATE_END_RE = re.compile(r"分かったのは|わかったのは|まとめると|要するに")
FORBIDDEN_HEADINGS = ("はじめに", "この教材について", "本書の狙い", "対象読者", "扱う範囲", "学習の流れ")
FENCE_RE = re.compile(r"^\s*```")

# 「何十兆円」「数千億円」のような概数の慣用表現は対象外（算用数字へ直せない）。
# 「一元化」「二元論」「二元代表制」は人民元ではないので、通貨の直後に
# 論・性・的・化・代・方 が続く場合は除く。
KANJI_MONEY_RE = re.compile(
    r"(?<![0-9０-９何数])[〇一二三四五六七八九十百千]"
    r"[〇一二三四五六七八九十百千万億兆・]*(?:円|ドル|ユーロ|ポンド|元)(?![論性的化代方])"
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
    speech_texts: list[str] = field(default_factory=list)

    def should_check(self) -> bool:
        if not self.speakers:
            return False
        return self.level == "###" or self.title.startswith(("幕間", "終幕", "演習"))

    @property
    def speech_chars(self) -> list[int]:
        return [len(text) for text in self.speech_texts]

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
        return statistics.median(self.speech_chars) if self.speech_texts else 0.0

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
        tail = len(self.speech_texts) + 1 - start if start is not None else 0
        if start is not None and tail >= RAPID_MIN_UTTERANCES:
            runs.append((start, len(self.speech_texts)))
        return runs

    def shape(self) -> str:
        bands = "／".join(f"{label}{count}" for label, count in self.band_counts())
        return (
            f"{self.turns}実効往復、{len(self.speech_texts)}発言、"
            f"発言字数 {self.min_chars}〜{self.median_chars:g}〜{self.max_chars}、"
            f"{bands}、計{self.total_chars}字"
        )


def parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    in_speech = False
    in_fence = False
    for line_no, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        heading = HEADING_RE.match(line) if not in_fence else None
        if heading:
            if current is not None:
                sections.append(current)
            current = Section(heading.group(1), heading.group(2), line_no)
            in_speech = False
            continue
        if current is None:
            continue
        speaker = SPEAKER_RE.match(line) if not in_fence else None
        if speaker:
            current.speakers.append(speaker.group(1))
            current.speech_lines.append(0)
            current.speech_texts.append("")
            in_speech = True
            continue
        if in_speech:
            if line.strip() == "":
                continue
            if line.strip() == "---":
                in_speech = False
                continue
            current.speech_lines[-1] += 1
            current.speech_texts[-1] += line
    if current is not None:
        sections.append(current)
    return sections


def check_dialogue(
    path: Path, sections: list[Section], warnings: list[str], diagnostics: list[str]
) -> None:
    """節ごとの会話量、実効往復、発言長の分布、節末の締め方を診断する。"""
    checked = [s for s in sections if s.should_check()]
    previous_boilerplate = False
    for section in checked:
        shape = section.shape()
        rapid = section.rapid_runs()
        rapid_text = (
            "、高速区間 " + "・".join(f"{start}〜{end}発言目" for start, end in rapid)
            if rapid
            else ""
        )
        diagnostics.append(f"{path}:{section.line}: {section.title} ({shape}{rapid_text})")

        if section.turns < MIN_EFFECTIVE_TURNS:
            warnings.append(
                f"{path}:{section.line}: {MIN_EFFECTIVE_TURNS}実効往復未満: "
                f"{section.title}（核心概念なら不足、{shape}）"
            )
        if section.turns > MANY_TURNS:
            warnings.append(
                f"{path}:{section.line}: {MANY_TURNS}実効往復超: {section.title} "
                f"（核心概念が二つ競合していないか確認、{shape}）"
            )
        if section.total_chars < SECTION_CHAR_MIN:
            warnings.append(
                f"{path}:{section.line}: 会話量が少ない: {section.title} "
                f"({section.total_chars}字 < {SECTION_CHAR_MIN}字、{shape})"
            )
        elif section.total_chars > SECTION_CHAR_MAX:
            warnings.append(
                f"{path}:{section.line}: 会話量が多い: {section.title} "
                f"({section.total_chars}字 > {SECTION_CHAR_MAX}字、{shape})"
            )

        long_speeches = sum(1 for n in section.speech_lines if n > SPEECH_LINE_LIMIT)
        if long_speeches:
            warnings.append(
                f"{path}:{section.line}: {SPEECH_LINE_LIMIT}行超の発言が"
                f"{long_speeches}件: {section.title}"
            )
        oversized = sum(1 for n in section.speech_chars if n > SPEECH_CHAR_REVIEW)
        if oversized:
            warnings.append(
                f"{path}:{section.line}: {SPEECH_CHAR_REVIEW}字超の発言が"
                f"{oversized}件: {section.title} （感情の頂点または不可分な導出か確認）"
            )

        band_counts = section.band_counts()
        if len(section.speech_texts) >= 8:
            dominant_label, dominant_count = max(band_counts, key=lambda item: item[1])
            if dominant_count / len(section.speech_texts) >= UNIFORM_BAND_RATIO:
                warnings.append(
                    f"{path}:{section.line}: 発言長が「{dominant_label}」へ"
                    f"{dominant_count}/{len(section.speech_texts)}件集中: "
                    f"{section.title}（テンポ一定でないか確認、{shape}）"
                )

        # 節末の理解の所有権。教師の長い発言で閉じていれば講義的総括の疑いがある。
        if (
            section.speakers[-1] == "やらない夫"
            and section.speech_chars[-1] > TEACHER_CLOSING_CHARS
        ):
            warnings.append(
                f"{path}:{section.line}: 節末が やらない夫 の"
                f"{section.speech_chars[-1]}字の発言: {section.title}"
                "（講義的総括になっていないか、理解の所有権をやる夫へ返したか確認）"
            )

        boilerplate = bool(BOILERPLATE_END_RE.search(section.speech_texts[-1]))
        if boilerplate and previous_boilerplate:
            warnings.append(
                f"{path}:{section.line}: 節末の要約定型が連続: {section.title}"
                "（前節も同じ型で閉じている。発見・次の行動・感情的余波などへ散らす）"
            )
        previous_boilerplate = boilerplate

    approvals = sum(
        len(APPROVAL_RE.findall(text)) for s in sections for text in s.speech_texts
    )
    if checked and approvals / len(checked) > APPROVAL_PER_SECTION:
        warnings.append(
            f"{path}: 承認語が{approvals}件／{len(checked)}節 "
            f"(={approvals / len(checked):.2f}件/節)"
            "（「鋭い」「いい問いだ」等のインフレ。重要な転換点へ絞る）"
        )


def check_structure(
    path: Path, lines: list[str], sections: list[Section],
    problems: list[str], warnings: list[str],
) -> None:
    """幕・節番号の連番、終端マーカー、見出しの揺れ、演習の形式を検査する。"""
    act: int | None = None
    previous_no: int | None = None
    for section in sections:
        title = section.title
        if section.level == "##":
            # 幕が変わると節番号は 1 から振り直す。終幕・幕間は幕番号を持たないが
            # 通し番号の節を抱えることがある（例：終幕の下に 8-1〜8-6）ので、
            # 幕との一致は問わず連番だけを見る。
            act_match = ACT_RE.match(title)
            act = int(act_match.group(1)) if act_match else None
            previous_no = 0
            if "参考文献" in title and title != "参考文献":
                problems.append(
                    f"{path}:{section.line}: 参考文献の見出しが揺れている: "
                    f"『{title}』（`## 参考文献` に統一する）"
                )
        if title in FORBIDDEN_HEADINGS or title.startswith(FORBIDDEN_HEADINGS):
            problems.append(
                f"{path}:{section.line}: 全体説明の節: 『{title}』"
                "（冒頭説明は catalog.yml の question / plot が担う。第1幕の場面から始める）"
            )
        if section.level == "###":
            no_match = SECTION_NO_RE.match(title)
            if no_match:
                major, minor = int(no_match.group(1)), int(no_match.group(2))
                if act is not None and major != act:
                    problems.append(
                        f"{path}:{section.line}: 節番号が幕と不一致: 『{title}』"
                        f"（第{act}幕の中なので {act}-{minor} が期待値）"
                    )
                elif previous_no is not None and minor != previous_no + 1:
                    problems.append(
                        f"{path}:{section.line}: 節番号が連番でない: 『{title}』"
                        f"（直前が -{previous_no}）"
                    )
                previous_no = minor
        if title.startswith("演習") and not section.speakers:
            warnings.append(
                f"{path}:{section.line}: 演習に会話が無い: 『{title}』"
                "（設問の箇条書きだけにせず、誤答→手掛かり→自己修正の対話にする）"
            )

    marker_lines: list[int] = []
    for line_no, line in enumerate(lines, 1):
        text = line.strip()
        if not text or not END_MARKER_LIKE_RE.match(text):
            continue
        if END_MARKER_OK_RE.match(text):
            marker_lines.append(line_no)
        else:
            problems.append(
                f"{path}:{line_no}: 終端マーカーの表記揺れ: 『{text}』（`{END_MARKER}` に統一する）"
            )
    if not marker_lines:
        warnings.append(f"{path}: 終端マーカー `{END_MARKER}` が無い（終幕の後に `---` と併せて置く）")
    else:
        previous = next(
            (lines[i - 1].strip() for i in range(marker_lines[0] - 1, 0, -1) if lines[i - 1].strip()),
            "",
        )
        if previous != "---":
            warnings.append(
                f"{path}:{marker_lines[0]}: 終端マーカーの直前が `---` でない"
                f"（現在は『{previous[:30]}』）"
            )


def check_footnotes(
    path: Path, lines: list[str], problems: list[str], warnings: list[str]
) -> None:
    """脚注の未使用・未定義と、出典表記だけで解説が無い脚注を検査する。"""
    definitions: dict[str, int] = {}
    uses: dict[str, int] = {}
    bare: list[int] = []
    in_fence = False
    for line_no, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        definition = FOOTNOTE_DEF_RE.match(line)
        if definition:
            definitions.setdefault(definition.group(1), line_no)
            if FOOTNOTE_BARE_RE.search(definition.group(2)):
                bare.append(line_no)
            continue
        for name in FOOTNOTE_USE_RE.findall(line):
            uses.setdefault(name, line_no)

    for name in sorted(definitions.keys() - uses.keys()):
        problems.append(
            f"{path}:{definitions[name]}: 未使用の脚注定義: [^{name}]"
            "（節を削除・統合した際の取り残しでないか確認）"
        )
    for name in sorted(uses.keys() - definitions.keys()):
        problems.append(f"{path}:{uses[name]}: 未定義の脚注参照: [^{name}]")
    if bare:
        warnings.append(
            f"{path}:{bare[0]}: 出典表記だけで解説の無い脚注が{len(bare)}件"
            "（本文のどの主張を裏づけるか、要点の事実・数値・年号を一文添える）"
        )


def check_notation(path: Path, lines: list[str], problems: list[str]) -> None:
    """金額・割合の表記を検査する。"""
    patterns = (
        (KANJI_MONEY_RE, "漢数字の金額"),
        (KANJI_PERCENT_RE, "パーセント表記"),
        (FULLWIDTH_NUMBER_RE, "全角数字"),
        (FULLWIDTH_PERCENT_RE, "全角%"),
    )
    for line_no, line in enumerate(lines, 1):
        for pattern, label in patterns:
            match = pattern.search(line)
            if match:
                problems.append(f"{path}:{line_no}: {label}: {match.group(0)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="節ごとの実効往復、発言長分布、高速区間を表示する",
    )
    args = parser.parse_args()
    lines = args.path.read_text(encoding="utf-8").splitlines()
    sections = parse_sections(lines)

    problems: list[str] = []
    warnings: list[str] = []
    diagnostics: list[str] = []

    check_dialogue(args.path, sections, warnings, diagnostics)
    check_structure(args.path, lines, sections, problems, warnings)
    check_footnotes(args.path, lines, problems, warnings)
    check_notation(args.path, lines, problems)

    if args.verbose and diagnostics:
        print("\n".join(f"info: {item}" for item in diagnostics))
    if warnings:
        print("\n".join(f"warning: {w}" for w in warnings))
    if problems:
        print("\n".join(f"error: {p}" for p in problems))
        return 1
    print(f"OK: {args.path}（warning {len(warnings)}件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
