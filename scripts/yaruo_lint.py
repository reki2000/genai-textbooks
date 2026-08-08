#!/usr/bin/env python3
"""やる夫式教材の検査・整形を行う単一の入口。

以前は `format_dialogue.py` / `fix_emphasis.py` / `fix_tables.py` /
`fix_dialogue_periods.py` / `check_dialogue_constraints.py` /
`normalize_financial_numbers.py` の6本に分かれ、話者判定の正規表現が複製されて
いた。本スクリプトはそれらのルールを1つのレジストリへ統合する。

    python3 scripts/yaruo_lint.py <file.md>...            # 検査（既定）
    python3 scripts/yaruo_lint.py <file.md> --fix         # 自動修正可能なものを適用
    python3 scripts/yaruo_lint.py <file.md> --rules table-delimiter
    python3 scripts/yaruo_lint.py --list-rules

レベルは3段。

    error   : 機械的に白黒がつく欠陥。終了コード1。
    warning : 判断が要るヒューリスティック。人が内容を見て可否を決める。
    info    : 診断値。**合否に使わない。**

`--fix` は fixable なルールだけを適用する。修正は冪等で、適用順は
REGISTRY の並び順に固定する（会話表記を確定させてから強調・表・句点を直す）。
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yaruo_markdown import (  # noqa: E402
    FULLWIDTH_SPACE,
    SECTION_LINE,
    SPEAKER_LINE,
    non_prose_lines,
    speaker_line_indices,
    speaker_names,
    split_eol,
)

LEVELS = ("error", "warning", "info")


@dataclass
class Finding:
    line: int | None
    level: str
    rule: str
    message: str


@dataclass
class Result:
    lines: list[str]
    findings: list[Finding] = field(default_factory=list)

    def add(self, line: int | None, level: str, rule: str, message: str) -> None:
        self.findings.append(Finding(line, level, rule, message))


# --------------------------------------------------------------------------
# rule: dialogue-frame（旧 format_dialogue.py）
# --------------------------------------------------------------------------

def _find_matching_close(lines: list[str], first: int, stop: int):
    """first 行頭の「に対応する」の (行index, 文字index) を返す。"""
    depth = 1
    for line_index in range(first, stop):
        body, _ = split_eol(lines[line_index])
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


def rule_dialogue_frame(lines: list[str], result: Result) -> list[str]:
    """発言外枠の「」と行頭全角空白を除去する。

    話者ブロック内で行頭が「の区間を探し、対応する」がその行の末尾にある場合
    だけ、その一組を発言外枠として削除する。閉じ」が無ければ先頭の「だけを
    削除し warning を出す。
    """
    out = list(lines)
    changes: dict[int, set[str]] = {}

    def changed(line_index: int, reason: str) -> None:
        changes.setdefault(line_index + 1, set()).add(reason)

    speaker_lines = speaker_line_indices(out)

    # 発言の継続行を含め、行頭の全角空白はすべて除去する。
    # Markdown の hard break（空白2個）は保ち、単独の行末空白だけ除去する。
    for i, line in enumerate(out):
        body, newline = split_eol(line)
        stripped = body.lstrip(FULLWIDTH_SPACE)
        if stripped != body:
            changed(i, "行頭の全角空白を除去")
        trailing = re.search(r"[ \t]+$", stripped)
        if trailing and len(trailing.group()) == 1:
            stripped = stripped[: trailing.start()]
            changed(i, "単独の行末空白を除去")
        out[i] = stripped + newline

    i = 0
    while i < len(out):
        if i not in speaker_lines:
            i += 1
            continue

        stop = i + 1
        while stop < len(out):
            candidate, _ = split_eol(out[stop])
            if stop in speaker_lines or SECTION_LINE.match(candidate):
                break
            stop += 1

        cursor = i + 1
        while cursor < stop:
            first_body, first_newline = split_eol(out[cursor])
            if not first_body.startswith("「"):
                cursor += 1
                continue

            close = _find_matching_close(out, cursor, stop)
            if close is None:
                out[cursor] = first_body[1:] + first_newline
                changed(cursor, "対応しない発言外枠の「を除去")
                result.add(
                    cursor + 1,
                    "warning",
                    "dialogue-frame",
                    "壊れた発言外枠（対応する」が無い）。先頭の「だけ削除した。閉じ位置を確認する",
                )
                cursor += 1
                continue

            close_line, close_char = close
            close_body, close_newline = split_eol(out[close_line])
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
            changed(cursor, "発言外枠の「を除去")
            changed(close_line, "発言外枠の」を除去")
            cursor = close_line + 1
        i += 1

    # 閉じカッコの直前に空白があった場合、カッコ削除後に単独の行末空白が
    # 露出する。1回の実行で完了するよう、最後にもう一度だけ除去する。
    for i, line in enumerate(out):
        body, newline = split_eol(line)
        trailing = re.search(r"[ \t]+$", body)
        if trailing and len(trailing.group()) == 1:
            out[i] = body[: trailing.start()] + newline
            changed(i, "単独の行末空白を除去")

    for line_number in sorted(changes):
        result.add(
            line_number,
            "error",
            "dialogue-frame",
            "、".join(sorted(changes[line_number])),
        )
    return out


# --------------------------------------------------------------------------
# rule: emphasis-flanking（旧 fix_emphasis.py）
# --------------------------------------------------------------------------

RUN_RE = re.compile(r"(?<!\*)\*+(?!\*)")
# インラインコード・行内数式（マスクして * の検出から除外する）
INLINE_SKIP_RE = re.compile(r"`[^`]*`|\$\$[^$]+\$\$|\$[^$\n]+\$")


def _is_space(char: str) -> bool:
    # 行頭・行末（空文字）は CommonMark では空白扱い
    return char == "" or char.isspace()


def _is_punct(char: str) -> bool:
    # CommonMark 0.30 の「Unicode punctuation」= P* および S* カテゴリ
    return char != "" and unicodedata.category(char)[0] in ("P", "S")


def _is_ascii_punct(char: str) -> bool:
    if char == "":
        return False
    code = ord(char)
    return 0x0021 <= code <= 0x007E and not char.isalnum()


def _left_flanking(before: str, after: str) -> bool:
    if _is_space(after):
        return False
    if not _is_punct(after):
        return True
    return _is_space(before) or _is_punct(before)


def _right_flanking(before: str, after: str) -> bool:
    if _is_space(before):
        return False
    if not _is_punct(before):
        return True
    return _is_space(after) or _is_punct(after)


def _emphasis_line(body: str) -> tuple[str, bool, list[str]]:
    """1行を処理し (修正後の行, 修正したか, 警告リスト) を返す。"""
    masked = INLINE_SKIP_RE.sub(lambda m: "\x00" * len(m.group()), body)
    runs = [
        m
        for m in RUN_RE.finditer(masked)
        if m.start() == 0 or masked[m.start() - 1] != "\\"
    ]
    # 長さ2でない `*` の連続は違反ではない。単独 `*` はイタリックまたは箇条書き、
    # `***` は複合強調になり得る。bold の対応と flanking だけを独立に診断するので、
    # 同じ行に `*書名*` があっても壊れた `**強調**` を見落とさない。
    runs = [m for m in runs if len(m.group()) == 2]
    if not runs:
        return body, False, []

    inserts: list[int] = []
    warns: list[str] = []

    def inspect(op: re.Match[str], cl: re.Match[str]) -> None:
        ob = masked[op.start() - 1] if op.start() > 0 else ""
        oa = masked[op.end()] if op.end() < len(masked) else ""
        cb = masked[cl.start() - 1] if cl.start() > 0 else ""
        ca = masked[cl.end()] if cl.end() < len(masked) else ""

        if not _left_flanking(ob, oa):
            if _is_space(oa):
                warns.append(f"col {op.start() + 1}: ** の直後が空白（手動修正が必要）")
            else:
                inserts.append(op.start())
        if not _right_flanking(cb, ca):
            if _is_space(cb):
                warns.append(f"col {cl.start() + 1}: ** の直前が空白（手動修正が必要）")
            else:
                inserts.append(cl.end())
        # 直前が半角約物で直後が句点の場合は修正対象
        elif _is_ascii_punct(cb) and ca in ("。", "！", "？"):
            inserts.append(cl.end())

    if len(runs) % 2 == 1:
        # 奇数個は複数行強調の可能性。複数あるときだけ最初と最後を対にして見る。
        if len(runs) > 1:
            inspect(runs[0], runs[-1])
    else:
        for k in range(0, len(runs), 2):
            inspect(runs[k], runs[k + 1])

    for pos in sorted(inserts, reverse=True):
        body = body[:pos] + " " + body[pos:]
    return body, bool(inserts), warns


def rule_emphasis_flanking(lines: list[str], result: Result) -> list[str]:
    """約物と隣接して壊れた ** を、外側へ半角スペースを挿入して直す。

    CommonMark の flanking 規則では、`**` の外側が文字で内側が約物に接している
    と強調として解釈されず `**` がそのまま表示される。日本語はスペースを入れずに
    書くため頻発する。
    """
    out: list[str] = []
    in_fence = False
    in_math = False

    for i, line in enumerate(lines, 1):
        body, eol = split_eol(line)
        stripped = body.lstrip("　 \t")

        if in_fence:
            if stripped.startswith("```"):
                in_fence = False
            out.append(line)
            continue
        if in_math:
            if body.count("$$") % 2 == 1:
                in_math = False
            out.append(line)
            continue
        if stripped.startswith("```"):
            in_fence = True
            out.append(line)
            continue
        if stripped.startswith("$$") and body.count("$$") % 2 == 1:
            in_math = True
            out.append(line)
            continue

        fixed, did, warns = _emphasis_line(body)
        if did:
            result.add(i, "error", "emphasis-flanking", "約物に隣接して壊れた ** がある")
        for warning in warns:
            result.add(i, "warning", "emphasis-flanking", warning)
        out.append(fixed + eol)

    return out


# --------------------------------------------------------------------------
# rule: table-delimiter（旧 fix_tables.py）
# --------------------------------------------------------------------------

DELIM_CELL_RE = re.compile(r"^\s*:?-+:?\s*$")


def _cells(body: str) -> list[str]:
    text = body.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return re.split(r"(?<!\\)\|", text)


def _is_delim_row(body: str) -> bool:
    cells = _cells(body)
    return len(cells) > 0 and all(DELIM_CELL_RE.match(cell) for cell in cells)


def rule_table_delimiter(lines: list[str], result: Result) -> list[str]:
    """GFM の表に必須の区切り行を補い、行頭空白を除去する。

    `|` で始まる行が2行以上連続するブロックを表とみなす。1行だけの場合は本文の
    可能性があるため触らない。
    """
    out: list[str] = []
    in_fence = False
    in_math = False
    prev_body = ""
    i = 0
    total = len(lines)

    while i < total:
        line = lines[i]
        body, _ = split_eol(line)
        stripped = body.lstrip("　 \t")

        if in_fence:
            if stripped.startswith("```"):
                in_fence = False
            out.append(line)
            prev_body = body
            i += 1
            continue
        if in_math:
            if body.count("$$") % 2 == 1:
                in_math = False
            out.append(line)
            prev_body = body
            i += 1
            continue
        if stripped.startswith("```"):
            in_fence = True
            out.append(line)
            prev_body = body
            i += 1
            continue
        if stripped.startswith("$$") and body.count("$$") % 2 == 1:
            in_math = True
            out.append(line)
            prev_body = body
            i += 1
            continue

        if not body.lstrip().startswith("|"):
            out.append(line)
            prev_body = body
            i += 1
            continue

        start = i
        block: list[str] = []
        while i < total:
            candidate, _ = split_eol(lines[i])
            if not candidate.lstrip().startswith("|"):
                break
            block.append(candidate)
            i += 1

        if len(block) < 2:
            out.extend(lines[start:i])
            prev_body = block[-1]
            continue

        if prev_body.strip() and prev_body.count("|") >= 2:
            result.add(
                start + 1,
                "warning",
                "table-delimiter",
                "直前の行に | が含まれる（ヘッダ行が別の文と同一行に融合している可能性。手動修正が必要）",
            )
            out.extend(lines[start:i])
            prev_body = block[-1]
            continue
        if prev_body.strip() and not prev_body.lstrip().startswith("#"):
            result.add(
                start + 1,
                "warning",
                "table-delimiter",
                "表の直前が空行でない（段落の続きと解釈され表にならない可能性）",
            )

        _, eol = split_eol(lines[start])
        eol = eol or "\n"
        fixed: list[str] = []
        for k, candidate in enumerate(block):
            deindented = candidate.lstrip("　 \t")
            if deindented != candidate:
                result.add(start + k + 1, "error", "table-delimiter", "表の行頭空白を除去")
            fixed.append(deindented)

        header, second = fixed[0], fixed[1]
        if _is_delim_row(second):
            if len(_cells(second)) != len(_cells(header)):
                result.add(
                    start + 2,
                    "warning",
                    "table-delimiter",
                    "区切り行の列数がヘッダ行と一致しない（手動修正が必要）",
                )
        else:
            result.add(start + 1, "error", "table-delimiter", "表の区切り行が無い")
            fixed = [header, "|" + "|".join(["---"] * len(_cells(header))) + "|"] + fixed[1:]

        out.extend(candidate + eol for candidate in fixed)
        prev_body = fixed[-1]

    return out


# --------------------------------------------------------------------------
# rule: dialogue-period（旧 fix_dialogue_periods.py）
# --------------------------------------------------------------------------

FOOTNOTE_TAIL_RE = re.compile(r"\[\^[^]\n]+\]$")
SCENE_TRANSITION_RE = re.compile(r"^〜〜\s*\S(?:.*\S)?\s*〜〜$")
TERMINAL_CHARS = frozenset("。．.!！?？…")
CLOSING_CHARS = frozenset("」』）】〕〉》〗〙〛")


def _semantic_end(body: str) -> str:
    """Markdown末尾装飾と閉じカッコを除いた判定対象文字列を返す。"""
    text = body.rstrip()
    while text:
        before = text
        if text.endswith("**"):
            text = text[:-2].rstrip()
        match = FOOTNOTE_TAIL_RE.search(text)
        if match:
            text = text[: match.start()].rstrip()
        while text and text[-1] in CLOSING_CHARS:
            text = text[:-1].rstrip()
        if text == before:
            break
    return text


def _is_non_prose_ending(body: str, line_index: int, protected: set[int]) -> bool:
    stripped = body.lstrip()
    return (
        line_index in protected
        or stripped.startswith("|")
        or stripped.startswith(">")
        or re.match(r"^(?:[-+*]|\d+[.)])\s", stripped) is not None
        or stripped.startswith("[^")
    )


def rule_dialogue_period(lines: list[str], result: Result) -> list[str]:
    """発言ブロックの最後が自然文で終止約物を欠くとき、句点を補う。

    コード・数式・表・箇条書きで終わる発言ブロックは変更しない。
    """
    out = list(lines)
    protected = non_prose_lines(lines)
    speakers = speaker_line_indices(lines)

    for start in sorted(speakers):
        stop = start + 1
        while stop < len(lines):
            body = split_eol(lines[stop])[0]
            if stop in speakers or SECTION_LINE.match(body) or SCENE_TRANSITION_RE.match(body.strip()):
                break
            stop += 1

        last = stop - 1
        while last > start and not split_eol(lines[last])[0].strip():
            last -= 1
        if last == start:
            continue

        body, newline = split_eol(lines[last])
        if _is_non_prose_ending(body, last, protected):
            continue
        end = _semantic_end(body)
        if not end:
            continue
        if end.endswith("──") or end[-1] in TERMINAL_CHARS:
            continue
        if end[-1] in "、，,：:；;":
            result.add(
                last + 1,
                "warning",
                "dialogue-period",
                f"発言末が {end[-1]!r}（文が途中で切れていないか確認）",
            )
            continue

        out[last] = body.rstrip() + "。" + newline
        result.add(last + 1, "error", "dialogue-period", "発言末に句点が無い")

    return out


# --------------------------------------------------------------------------
# rule: invisible-chars（新設。外部で執筆されたテキストの受け入れ検査）
# --------------------------------------------------------------------------

# 別モデルの出力に紛れ込む引用マークアップ（`citeturn…`）、BOM、ゼロ幅文字。
# 表示上は不可視または豆腐になり、`grep citeturn` のような素朴な検索にも掛からない。
# 文意の判断を伴うため自動修正はしない。
INVISIBLE_NAMES = {
    "﻿": "BOM / ZERO WIDTH NO-BREAK SPACE",
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER",
    "‎": "LEFT-TO-RIGHT MARK",
    "‏": "RIGHT-TO-LEFT MARK",
    "‪": "LEFT-TO-RIGHT EMBEDDING",
    "‫": "RIGHT-TO-LEFT EMBEDDING",
    "‬": "POP DIRECTIONAL FORMATTING",
    "‭": "LEFT-TO-RIGHT OVERRIDE",
    "‮": "RIGHT-TO-LEFT OVERRIDE",
    "⁦": "LEFT-TO-RIGHT ISOLATE",
    "⁧": "RIGHT-TO-LEFT ISOLATE",
    "⁨": "FIRST STRONG ISOLATE",
    "⁩": "POP DIRECTIONAL ISOLATE",
    "�": "REPLACEMENT CHARACTER",
}
PRIVATE_USE_RANGES = (
    (0xE000, 0xF8FF, "BMP 私用領域"),
    (0xF0000, 0xFFFFD, "補助私用領域A"),
    (0x100000, 0x10FFFD, "補助私用領域B"),
)
ALLOWED_CONTROL = frozenset("\n\r\t")


def _classify_invisible(char: str) -> str | None:
    if char in ALLOWED_CONTROL:
        return None
    if char in INVISIBLE_NAMES:
        return INVISIBLE_NAMES[char]
    code = ord(char)
    for low, high, label in PRIVATE_USE_RANGES:
        if low <= code <= high:
            return label
    if unicodedata.category(char) == "Cc":
        return "制御文字 (Cc)"
    return None


def rule_invisible_chars(lines: list[str], result: Result) -> list[str]:
    """制御文字・私用領域文字・不可視 format 文字の混入を検出する（修正しない）。"""
    for line_number, line in enumerate(lines, 1):
        body = split_eol(line)[0]
        for column, char in enumerate(body, 1):
            label = _classify_invisible(char)
            if label is None:
                continue
            name = unicodedata.name(char, "<名前なし>")
            result.add(
                line_number,
                "error",
                "invisible-chars",
                f"col {column}: {label} U+{ord(char):04X} ({name})",
            )
    return lines


# --------------------------------------------------------------------------
# rule: notation（旧 check_dialogue_constraints の表記検査 + normalize_financial_numbers）
# --------------------------------------------------------------------------

_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9}
_SMALL_UNITS = {"十": 10, "百": 100, "千": 1_000}
_LARGE_UNITS = (("兆", 1_000_000_000_000), ("億", 100_000_000), ("万", 10_000))
_CURRENCIES = "円|ドル|ユーロ|ポンド|元"

# 検出と修正で**同じ matcher** を使う。旧構成では checker が接尾辞 `[論性的化代方]`
# と接頭辞 `[何数]` を除外するのに normalizer が同じ除外を持たず、`一元化` を
# `1元化` へ、`何十兆円` を `何10兆円` へ壊し得た。
KANJI_MONEY_RE = re.compile(
    rf"(?<![0-9０-９何数])[〇一二三四五六七八九十百千]"
    rf"[〇一二三四五六七八九十百千万億兆・]*(?:{_CURRENCIES})(?![論性的化代方])"
)
KANJI_PERCENT_RE = re.compile(r"[〇一二三四五六七八九十百千万億兆・]+パーセント")
FULLWIDTH_NUMBER_RE = re.compile(rf"[０-９][０-９,.]*(?:{_CURRENCIES}|％)")
FULLWIDTH_PERCENT_RE = re.compile(r"(?:[0-9０-９]+(?:[.,．][0-9０-９]+)?)％")
_CURRENCY_TAIL_RE = re.compile(rf"({_CURRENCIES})$")


def _parse_small(text: str) -> int:
    if not text:
        return 0
    if all(char in _DIGITS for char in text):
        return int("".join(str(_DIGITS[char]) for char in text))
    total = 0
    pending: int | None = None
    for char in text:
        if char in _DIGITS:
            pending = _DIGITS[char]
        else:
            total += (1 if pending is None else pending) * _SMALL_UNITS[char]
            pending = None
    return total + (0 if pending is None else pending)


def _parse_integer(text: str) -> int:
    total = 0
    rest = text
    for marker, unit in _LARGE_UNITS:
        if marker in rest:
            high, rest = rest.split(marker, 1)
            total += (_parse_integer(high) if high else 1) * unit
    return total + _parse_small(rest)


def _parse_number(text: str) -> str:
    integer, separator, fraction = text.partition("・")
    value = f"{_parse_integer(integer):,}"
    if separator:
        value += "." + "".join(str(_DIGITS[char]) for char in fraction)
    return value


def _normalize_money(matched: str) -> str:
    tail = _CURRENCY_TAIL_RE.search(matched)
    currency = tail.group(1)
    number = matched[: tail.start()]
    for marker in ("兆", "億", "万"):
        if number.endswith(marker):
            prefix = number[:-1]
            if "・" in prefix:
                return f"{_parse_number(prefix)}{marker}{currency}"  # 十・五億円 → 10.5億円
            return f"{_parse_integer(prefix) if prefix else 1:,}{marker}{currency}"
    return f"{_parse_number(number)}{currency}"


def _normalize_line(body: str) -> tuple[str, list[str]]:
    """1行の金額・割合表記を正規化し、(修正後, 直した文字列一覧) を返す。"""
    fixed: list[str] = []

    def money(match: re.Match[str]) -> str:
        fixed.append(match.group(0))
        return _normalize_money(match.group(0))

    def percent(match: re.Match[str]) -> str:
        fixed.append(match.group(0))
        return _parse_number(match.group(0)[: -len("パーセント")]) + "%"

    def fullwidth(match: re.Match[str]) -> str:
        fixed.append(match.group(0))
        return unicodedata.normalize("NFKC", match.group(0))

    body = KANJI_MONEY_RE.sub(money, body)
    body = KANJI_PERCENT_RE.sub(percent, body)
    body = FULLWIDTH_NUMBER_RE.sub(fullwidth, body)
    body = FULLWIDTH_PERCENT_RE.sub(fullwidth, body)
    return body, fixed


def rule_notation(lines: list[str], result: Result) -> list[str]:
    """金額・割合を半角算用数字へ揃える。

    漢数字の金額、「パーセント」、全角数字・全角 `％` を対象にする。「何十兆円」の
    ような概数の慣用表現、`一元化`・`二元論` のような通貨でない語は除外する。
    """
    out: list[str] = []
    for line_number, line in enumerate(lines, 1):
        body, newline = split_eol(line)
        normalized, fixed = _normalize_line(body)
        for original in fixed:
            result.add(
                line_number, "error", "notation", f"半角算用数字へ直す: {original}"
            )
        out.append(normalized + newline)
    return out


# --------------------------------------------------------------------------
# rule: circled-numbers
# --------------------------------------------------------------------------

CIRCLED_NUMBER_RE = re.compile("[①-⑳]")
_CIRCLED_BASE = ord("①")


def _circled_to_paren(char: str) -> str:
    return f"({ord(char) - _CIRCLED_BASE + 1})"


def rule_circled_numbers(lines: list[str], result: Result) -> list[str]:
    """丸囲み数字（①②③…）を半角の `(1)(2)(3)…` へ書き換える。

    丸囲み数字はフォント・環境によって欠落・文字化けしやすく、Webでは表示
    されない場合がある。コードブロック・行内コード・TeX数式内は対象外。
    """
    protected = non_prose_lines(lines)
    out: list[str] = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if index in protected:
            out.append(line)
            continue
        body, newline = split_eol(line)
        masked = INLINE_SKIP_RE.sub(lambda m: "\x00" * len(m.group()), body)
        matches = list(CIRCLED_NUMBER_RE.finditer(masked))
        if not matches:
            out.append(line)
            continue
        parts: list[str] = []
        last = 0
        for m in matches:
            replacement = _circled_to_paren(m.group())
            result.add(
                line_number,
                "error",
                "circled-numbers",
                f"丸囲み数字を書き換える: {m.group()} → {replacement}",
            )
            parts.append(body[last:m.start()])
            parts.append(replacement)
            last = m.end()
        parts.append(body[last:])
        out.append("".join(parts) + newline)
    return out


# --------------------------------------------------------------------------
# rule: unit-notation
# --------------------------------------------------------------------------

# 長い（複合）語を先に置く。`メートル`・`グラム` 単体は複合語をすべて処理した
# 後に残ったものだけを対象にするため、この順序に依存する。
UNIT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile("立方メートル"), "m³"),
    (re.compile("平方センチメートル"), "cm²"),
    (re.compile("平方ミリメートル"), "mm²"),
    (re.compile("平方メートル"), "m²"),
    (re.compile("キロメートル"), "km"),
    (re.compile("センチメートル"), "cm"),
    (re.compile("ミリメートル"), "mm"),
    (re.compile("マイクロメートル"), "μm"),
    (re.compile("ピコメートル"), "pm"),
    (re.compile("メートル(?!法)"), "m"),
    (re.compile("キログラム"), "kg"),
    # `プログラム`・`ヒストグラム`・`エングラム`・`ダイヤグラム` のように
    # グラムを含むが単位ではない語を、直前がカタカナのときに限り除外する。
    (re.compile(r"(?<![゠-ヿ])グラム(?!染色|陽性|陰性)"), "g"),
)


def _masked_sub(
    body: str,
    pattern: re.Pattern[str],
    replacement: str,
    line_number: int,
    result: Result,
) -> str:
    masked = INLINE_SKIP_RE.sub(lambda m: "\x00" * len(m.group()), body)
    matches = list(pattern.finditer(masked))
    if not matches:
        return body
    parts: list[str] = []
    last = 0
    for m in matches:
        result.add(
            line_number,
            "error",
            "unit-notation",
            f"単位表記を書き換える: {m.group()} → {replacement}",
        )
        parts.append(body[last:m.start()])
        parts.append(replacement)
        last = m.end()
    parts.append(body[last:])
    return "".join(parts)


def rule_unit_notation(lines: list[str], result: Result) -> list[str]:
    """メートル・グラム系の単位のカタカナ表記を `m` `km` `g` `kg` 等へ揃える。

    コードブロック・行内コード・TeX数式内は対象外。
    """
    protected = non_prose_lines(lines)
    out: list[str] = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if index in protected:
            out.append(line)
            continue
        body, newline = split_eol(line)
        for pattern, replacement in UNIT_PATTERNS:
            body = _masked_sub(body, pattern, replacement, line_number, result)
        out.append(body + newline)
    return out


# --------------------------------------------------------------------------
# 節の解析（会話診断・構造検査の共通土台）
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*```")
# 節として切り出す見出しレベル。`####` は既定では節にしないが、見出しである以上
# 発言は終える（下記 parse_sections を参照）。
DEFAULT_SECTION_LEVELS = ("##", "###")
# 実効往復と会話量は主役2名だけで数える。これは解析ではなくルール側のフィルタ。
LEAD_SPEAKERS = ("やる夫", "やらない夫")


@dataclass
class Section:
    level: str
    title: str
    line: int
    speakers: list[str] = field(default_factory=list)
    speech_lines: list[int] = field(default_factory=list)
    speech_texts: list[str] = field(default_factory=list)
    # 各発言の話者行の行番号（1始まり）。集計で証拠位置を示すために持つ。
    speech_starts: list[int] = field(default_factory=list)

    def should_check(self) -> bool:
        if not self.speakers:
            return False
        return self.level == "###" or self.title.startswith(("幕間", "終幕", "演習"))

    @property
    def speech_chars(self) -> list[int]:
        return [len(text) for text in self.speech_texts]

    @property
    def turns(self) -> int:
        """同一話者の連続ブロックを畳み込んだ実効往復数。

        主役2名の往復だけを数える。脇役の割り込みは往復を切らない。
        """
        collapsed: list[str] = []
        for speaker in self.speakers:
            if speaker not in LEAD_SPEAKERS:
                continue
            if not collapsed or collapsed[-1] != speaker:
                collapsed.append(speaker)
        return len(collapsed) // 2

    @property
    def median_chars(self) -> float:
        return statistics.median(self.speech_chars) if self.speech_texts else 0.0

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
        """RAPID_MAX_CHARS 以下が連続する区間を、1始まりの閉区間で返す。"""
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
            f"発言字数 {min(self.speech_chars, default=0)}〜{self.median_chars:g}〜"
            f"{max(self.speech_chars, default=0)}、{bands}、計{self.total_chars}字"
        )


def parse_sections(
    lines: list[str],
    levels: tuple[str, ...] = DEFAULT_SECTION_LEVELS,
    names: set[str] | None = None,
) -> list[Section]:
    """見出しで区切った節を返す。`levels` に無い見出しは節を切らない。

    どのレベルであれ、見出し行は発言を終える。`####` を発言本文へ取り込むと、
    その見出しの字数が直前の発言へ加算され、発言長の診断が狂うため。

    **発言は全話者で切る。** 以前は主役2名の話者行でしか切らなかったため、
    脇役の話者行とその本文が直前の主役の発言へ加算され、4人以上を出す教材で
    「長大な発言」が実在しない件数だけ発火していた（57冊で1801件中177件）。
    `yaruo_markdown` の方針どおり、解析器は全話者を返し、「主役2名だけを
    数える」は `Section.turns` と `report_stats` のフィルタで表現する。
    """
    if names is None:
        names = speaker_names(lines)
    sections: list[Section] = []
    current: Section | None = None
    in_speech = False
    in_fence = False
    for line_no, line in enumerate(lines, 1):
        body = split_eol(line)[0]
        if FENCE_RE.match(body):
            in_fence = not in_fence
        heading = HEADING_RE.match(body) if not in_fence else None
        if heading:
            in_speech = False
            if heading.group(1) in levels:
                if current is not None:
                    sections.append(current)
                current = Section(heading.group(1), heading.group(2), line_no)
            continue
        if current is None:
            continue
        speaker = SPEAKER_LINE.match(body) if not in_fence else None
        if speaker and speaker.group(1) not in names:
            speaker = None
        if speaker:
            current.speakers.append(speaker.group(1))
            current.speech_lines.append(0)
            current.speech_texts.append("")
            current.speech_starts.append(line_no)
            in_speech = True
            continue
        if in_speech:
            if body.strip() == "":
                continue
            if body == "---":
                in_speech = False
                continue
            current.speech_lines[-1] += 1
            current.speech_texts[-1] += body
    if current is not None:
        sections.append(current)
    return sections


# --------------------------------------------------------------------------
# rule: structure（旧 check_dialogue_constraints の構造検査）
# --------------------------------------------------------------------------

END_MARKER = "**── 完 ──**"
# 終端マーカーの解析は1本。`**── I部 完 ──**` のような分冊の部完結も同じ形とみなし、
# 接頭辞を group(1) に取る。罫線・太字・空白は正規形へ厳密に統一する。
END_MARKER_RE = re.compile(
    r"^(?P<bold_open>\*{0,2})\s*(?P<rule_open>[─—―-]{0,4})\s*"
    r"(?:(?P<prefix>\S+)\s+)?完\s*"
    r"(?P<rule_close>[─—―-]{0,4})\s*(?P<bold_close>\*{0,2})$"
)


def _canonical_end_marker(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    return f"**── {prefix} 完 ──**" if prefix else END_MARKER


def _is_canonical_end_marker(match: re.Match[str]) -> bool:
    return match.group(0).strip() == _canonical_end_marker(match)


ACT_RE = re.compile(r"^第(\d+)幕")
SECTION_NO_RE = re.compile(r"^(\d+)-(\d+)(?=[　\s])")
FORBIDDEN_HEADINGS = (
    "はじめに", "この教材について", "本書の狙い", "対象読者", "扱う範囲", "学習の流れ",
)


def rule_structure(lines: list[str], result: Result) -> list[str]:
    """幕・節番号の連番、終端マーカー、見出しの揺れ、演習の形式を検査する。"""
    sections = parse_sections(lines)
    act: int | None = None
    previous_no: int | None = None
    for section in sections:
        title = section.title
        if section.level == "##":
            # 幕が変わると節番号は 1 から振り直す。終幕・幕間は幕番号を持たないが
            # 通し番号の節を抱えることがあるので、幕との一致は問わず連番だけを見る。
            act_match = ACT_RE.match(title)
            act = int(act_match.group(1)) if act_match else None
            previous_no = 0
            if "参考文献" in title and title != "参考文献":
                result.add(
                    section.line, "error", "structure",
                    f"参考文献の見出しが揺れている: 『{title}』（`## 参考文献` に統一する）",
                )
        if title in FORBIDDEN_HEADINGS or title.startswith(FORBIDDEN_HEADINGS):
            result.add(
                section.line, "error", "structure",
                f"全体説明の節: 『{title}』"
                "（冒頭説明は catalog.yml の question / plot が担う。第1幕の場面から始める）",
            )
        if section.level == "###":
            no_match = SECTION_NO_RE.match(title)
            if no_match:
                major, minor = int(no_match.group(1)), int(no_match.group(2))
                if act is not None and major != act:
                    result.add(
                        section.line, "error", "structure",
                        f"節番号が幕と不一致: 『{title}』（第{act}幕なので {act}-{minor} が期待値）",
                    )
                elif previous_no is not None and minor != previous_no + 1:
                    result.add(
                        section.line, "error", "structure",
                        f"節番号が連番でない: 『{title}』（直前が -{previous_no}）",
                    )
                previous_no = minor
        if title.startswith("演習") and not section.speakers:
            result.add(
                section.line, "warning", "structure",
                f"演習に会話が無い: 『{title}』"
                "（設問の箇条書きだけにせず、誤答→手掛かり→自己修正の対話にする）",
            )

    return lines


# --------------------------------------------------------------------------
# rule: end-marker（旧 check_dialogue_constraints の終端マーカー検査 + 正規化）
# --------------------------------------------------------------------------

def rule_end_marker(lines: list[str], result: Result) -> list[str]:
    """終端マーカーを `**── 完 ──**` へ揃える。分冊の部完結の接頭辞は保つ。"""
    out = list(lines)
    marker_lines: list[int] = []
    bodies = [split_eol(line)[0] for line in lines]

    for line_no, body in enumerate(bodies, 1):
        text = body.strip()
        if not text:
            continue
        match = END_MARKER_RE.match(text)
        if not match:
            continue
        if _is_canonical_end_marker(match):
            marker_lines.append(line_no)
            continue
        canonical = _canonical_end_marker(match)
        newline = split_eol(lines[line_no - 1])[1]
        out[line_no - 1] = canonical + newline
        marker_lines.append(line_no)
        result.add(
            line_no, "error", "end-marker",
            f"終端マーカーの表記揺れ: 『{text}』（`{canonical}` に統一する）",
        )

    if not marker_lines:
        reference_index = next(
            (i for i, body in enumerate(bodies) if body.strip() == "## 参考文献"),
            len(out),
        )
        newline = split_eol(out[reference_index - 1])[1] if reference_index else "\n"
        if not newline:
            newline = "\n"
        prefix = [] if _previous_nonempty(out, reference_index) == "---" else ["---" + newline]
        inserted = prefix + [END_MARKER + newline, "---" + newline]
        out[reference_index:reference_index] = inserted
        result.add(
            reference_index + len(prefix) + 1,
            "error",
            "end-marker",
            f"終端マーカー `{END_MARKER}` と前後の区切り行を追加",
        )
        return out

    previous = next(
        (bodies[i - 1] for i in range(marker_lines[0] - 1, 0, -1)
         if bodies[i - 1].strip()),
        "",
    )
    if previous != "---":
        result.add(
            marker_lines[0], "warning", "end-marker",
            f"終端マーカーの直前が `---` でない（現在は『{previous[:30]}』）",
        )
    return out


# --------------------------------------------------------------------------
# rule: structure-delimiter
# --------------------------------------------------------------------------

HEADING_DELIMITER_RE = re.compile(r"^#{1,6}\s+")


def _previous_nonempty(lines: list[str], index: int) -> str:
    for line in reversed(lines[:index]):
        body, _ = split_eol(line)
        if body.strip():
            return body.strip()
    return ""


def _next_nonempty(lines: list[str], index: int) -> str:
    for line in lines[index + 1 :]:
        body, _ = split_eol(line)
        if body.strip():
            return body.strip()
    return ""


def rule_structure_delimiter(lines: list[str], result: Result) -> list[str]:
    """見出しと終端マーカーの区切りを標準の境界へ揃える。

    見出しの直前は「空行、`---`、見出し」、直後は空行1行とする。見出し
    直後の `---` は、次の見出しの直前を兼ねる場合だけ残す。終端マーカー
    の直前も「空行、`---`、終端マーカー」とする。

    どの区切りにも属さない `---` が直前の空行なしで現れた場合、markdown は
    それを水平線ではなく直前行の setext 見出しとして解釈してしまう。タイトル
    直後と終端マーカー直後は区切り行の意図が明らかなので空行を補い、それ以外
    は空行の打ち間違いとみなして `---` を空行へ置き換える。
    """
    out = list(lines)

    # 終端マーカーの直前の区切り行は、本文から空行で分離する。end-marker
    # ルールが先に表記を正規化するため、ここでは正規形だけを対象にできる。
    marker_targets = [
        index for index, line in enumerate(out)
        if END_MARKER_RE.match(split_eol(line)[0].strip())
    ]
    for index in reversed(marker_targets):
        _, newline = split_eol(out[index])
        newline = newline or "\n"
        separator = index - 1
        while separator >= 0 and not split_eol(out[separator])[0].strip():
            separator -= 1
        if separator < 0 or split_eol(out[separator])[0].strip() != "---":
            continue
        before = separator - 1
        while before >= 0 and not split_eol(out[before])[0].strip():
            before -= 1
        if out[before + 1:separator] != [newline]:
            out[before + 1:separator] = [newline]
            result.add(separator + 1, "error", "structure-delimiter", "終端マーカー直前の区切り行の前に空行を1行挿入")

    targets = [
        index for index, line in enumerate(out)
        if split_eol(line)[0].startswith(("## ", "### "))
    ]

    for index in reversed(targets):
        _, newline = split_eol(out[index])
        newline = newline or "\n"

        next_nonempty = index + 1
        while next_nonempty < len(out) and not split_eol(out[next_nonempty])[0].strip():
            next_nonempty += 1
        if next_nonempty < len(out) and split_eol(out[next_nonempty])[0].strip() == "---":
            following = next_nonempty + 1
            while following < len(out) and not split_eol(out[following])[0].strip():
                following += 1
            keep = following < len(out) and split_eol(out[following])[0].startswith(("## ", "### "))
            if not keep:
                del out[next_nonempty]
                result.add(next_nonempty + 1, "error", "structure-delimiter", "見出し直後の不要な区切り行を除去")

        after_end = index + 1
        while after_end < len(out) and not split_eol(out[after_end])[0].strip():
            after_end += 1
        if out[index + 1:after_end] != [newline]:
            out[index + 1:after_end] = [newline]
            result.add(index + 2, "error", "structure-delimiter", "見出し直後の空行を1行に統一")

        previous = index - 1
        while previous >= 0 and not split_eol(out[previous])[0].strip():
            previous -= 1
        if previous >= 0 and split_eol(out[previous])[0].strip() == "---":
            separator = previous
            if split_eol(out[separator])[0] != "---":
                out[separator] = "---" + split_eol(out[separator])[1]
                result.add(separator + 1, "error", "structure-delimiter", "区切り行を `---` の完全一致へ正規化")
            if separator + 1 != index:
                del out[separator + 1:index]
                result.add(separator + 2, "error", "structure-delimiter", "区切り行と見出しの間の空行を除去")
                index = separator + 1
        else:
            separator = index
            out[separator:separator] = ["---" + newline]
            index += 1
            result.add(separator + 1, "error", "structure-delimiter", "見出し直前の区切り行を追加")

        before = separator - 1
        while before >= 0 and not split_eol(out[before])[0].strip():
            before -= 1
        if out[before + 1:separator] != [newline]:
            out[before + 1:separator] = [newline]
            result.add(separator, "error", "structure-delimiter", "区切り行直前の空行を1行に統一")

    # 上のパスで見出し・終端マーカーに付く区切り行は空行で分離済み。ここへ残る
    # のは、直前が本文のまま setext 見出しに化けている `---` だけ。
    protected = non_prose_lines(out)
    for index in reversed(range(1, len(out))):
        if index in protected or split_eol(out[index])[0].strip() != "---":
            continue
        previous = split_eol(out[index - 1])[0].strip()
        if not previous:
            continue
        newline = split_eol(out[index])[1] or "\n"
        if previous.startswith("# ") or END_MARKER_RE.match(previous):
            out.insert(index, newline)
            result.add(index + 1, "error", "structure-delimiter", "区切り行の直前に空行を1行挿入")
            continue
        following = split_eol(out[index + 1])[0].strip() if index + 1 < len(out) else ""
        if following:
            out[index] = newline
        else:
            del out[index]
        result.add(index + 1, "error", "structure-delimiter", "空行の代わりに置かれた `---` を空行へ置換")
    return out


# --------------------------------------------------------------------------
# rule: heading-level
# --------------------------------------------------------------------------

def rule_heading_level(lines: list[str], result: Result) -> list[str]:
    """教材本文の幕・節見出しを `##` と `###` に限定する。"""
    out = list(lines)
    in_fence = False
    for index, line in enumerate(out):
        body, newline = split_eol(line)
        if FENCE_RE.match(body):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = HEADING_RE.match(body)
        if not heading or len(heading.group(1)) < 4:
            continue
        out[index] = f"### {heading.group(2)}{newline}"
        result.add(
            index + 1,
            "error",
            "heading-level",
            f"節見出しのレベルが `{heading.group(1)}`（`###` に統一）",
        )
    return out


# --------------------------------------------------------------------------
# rule: footnotes（旧 check_dialogue_constraints の脚注検査）
# --------------------------------------------------------------------------

FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
FOOTNOTE_USE_RE = re.compile(r"\[\^([^\]]+)\](?!:)")
FOOTNOTE_BARE_RE = re.compile(r"参照[.。]?\s*$")


def rule_footnotes(lines: list[str], result: Result) -> list[str]:
    """脚注の未使用・未定義と、出典表記だけで解説が無い脚注を検査する。

    `## 参考文献` 内の未参照項目は、本文から脚注で呼ばれない番号付きの
    文献紹介として許可する。本文中・他の付録にある未使用定義は従来どおり
    取り残しとして error にする。
    """
    definitions: dict[str, int] = {}
    bibliography_definitions: set[str] = set()
    uses: dict[str, int] = {}
    bare: list[int] = []
    in_fence = False
    in_references = False
    for line_no, line in enumerate(lines, 1):
        body = split_eol(line)[0]
        if FENCE_RE.match(body):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if body.startswith("## "):
            in_references = body.strip() == "## 参考文献"
        definition = FOOTNOTE_DEF_RE.match(body)
        if definition:
            definitions.setdefault(definition.group(1), line_no)
            if in_references:
                bibliography_definitions.add(definition.group(1))
            if FOOTNOTE_BARE_RE.search(definition.group(2)):
                bare.append(line_no)
            continue
        for name in FOOTNOTE_USE_RE.findall(body):
            uses.setdefault(name, line_no)

    for name in sorted(definitions.keys() - uses.keys()):
        if name in bibliography_definitions:
            result.add(
                definitions[name], "info", "footnotes",
                f"本文未参照の文献紹介: [^{name}]",
            )
            continue
        result.add(
            definitions[name], "error", "footnotes",
            f"未使用の脚注定義: [^{name}]（節を削除・統合した際の取り残しでないか確認）",
        )
    for name in sorted(uses.keys() - definitions.keys()):
        result.add(uses[name], "error", "footnotes", f"未定義の脚注参照: [^{name}]")
    if bare:
        result.add(
            bare[0], "warning", "footnotes",
            f"出典表記だけで解説の無い脚注が{len(bare)}件"
            "（本文のどの主張を裏づけるか、要点の事実・数値・年号を一文添える）",
        )
    return lines


# --------------------------------------------------------------------------
# rule: term-english（専門用語の英語併記）
# --------------------------------------------------------------------------

# 全角括弧に収めた英語併記。`（long-term potentiation, LTP）` のように略語を
# 続けてよい。数式や単位の括弧を拾わないよう、先頭は英字に限る。
TERM_ENGLISH_RE = re.compile(r"（([A-Za-z][A-Za-z0-9 ,.'\-/&]*)）")
# 日本語の直後に半角括弧で英語を書いたもの。全角括弧へ揃える。
HALFWIDTH_ENGLISH_RE = re.compile(r"[ぁ-んァ-ヴー一-龥々]\(([A-Za-z][A-Za-z0-9 ,.'\-/&]*)\)")


# 用語の直前に来る1字の平仮名。これらは送り仮名でなく助詞と見なす（`現象をシナプス`
# の `を` を送り仮名と誤認すると、カタカナ語の初出判定が全部止まる）。
PARTICLES = frozenset("をのがはにでともやかへねよ")


def _script_of(char: str) -> str | None:
    if "一" <= char <= "鿿" or char == "々":
        return "kanji"
    if "ァ" <= char <= "ヴ" or char in "ー・":
        return "kata"
    if "ぁ" <= char <= "ん":
        return "hira"
    return None


def _annotated_term(body: str, paren: int) -> str | None:
    """`（English）` の直前にある用語を切り出す。切り出せなければ None。

    漢字だけ・カタカナだけの連なりを用語とみなす。`手続き記憶` のように送り仮名を
    挟む語は境界が決められないので、初出判定の対象から外す（検査しないだけで、
    併記そのものは正しい）。
    """
    if paren == 0:
        return None
    script = _script_of(body[paren - 1])
    if script not in ("kanji", "kata"):
        return None
    start = paren - 1
    while start > 0 and _script_of(body[start - 1]) == script:
        start -= 1
    if (
        start >= 2
        and _script_of(body[start - 1]) == "hira"
        and body[start - 1] not in PARTICLES
        and _script_of(body[start - 2]) in ("kanji", "kata")
    ):
        return None
    term = body[start:paren]
    return term if len(term) >= 2 else None


def rule_term_english(lines: list[str], result: Result) -> list[str]:
    """専門用語の英語併記を検査する。

    併記すべき語を決めるのは人間の仕事で、機械にはできない。ここが見るのは
    併記の**置き方**だけ——同じ英語を二度付けていないか、初出でない場所に
    付けていないか、括弧が全角か。
    """
    protected = non_prose_lines(lines)
    prose: list[tuple[int, str]] = []
    in_references = False
    for index, line in enumerate(lines):
        body = split_eol(line)[0]
        if body.startswith("## "):
            in_references = body.strip() == "## 参考文献"
        if index in protected or in_references:
            continue
        if body.startswith("#") or FOOTNOTE_DEF_RE.match(body):
            continue
        prose.append((index + 1, body))

    seen_english: dict[str, int] = {}
    annotations = 0
    for position, (line_no, body) in enumerate(prose):
        for match in HALFWIDTH_ENGLISH_RE.finditer(body):
            result.add(
                line_no, "warning", "term-english",
                f"英語併記の括弧が半角: ({match.group(1)})（全角の （） へ揃える）",
            )
        for match in TERM_ENGLISH_RE.finditer(body):
            annotations += 1
            english = match.group(1).strip().lower()
            first = seen_english.get(english)
            if first is None:
                seen_english[english] = line_no
            else:
                result.add(
                    line_no, "warning", "term-english",
                    f"同じ英語を再び併記: （{match.group(1)}）"
                    f"（L{first} が初出。併記は初出の1回だけ）",
                )
            term = _annotated_term(body, match.start())
            if term is None:
                continue
            earlier = None
            if term in body[: match.start() - len(term)]:
                earlier = line_no
            else:
                for previous_no, previous in prose[:position]:
                    if term in previous:
                        earlier = previous_no
                        break
            if earlier is not None:
                result.add(
                    line_no, "warning", "term-english",
                    f"初出でない位置に英語を併記: {term}"
                    f"（初出は L{earlier}。併記は初出へ移す）",
                )
    result.add(None, "info", "term-english", f"英語併記 {annotations}件")
    return lines


# --------------------------------------------------------------------------
# rule: dialogue-shape（旧 check_dialogue_constraints の会話診断）
# --------------------------------------------------------------------------

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

APPROVAL_RE = re.compile(r"鋭い|いい問いだ|良い言語化|完璧な直観")
BOILERPLATE_END_RE = re.compile(r"分かったのは|わかったのは|まとめると|要するに")


def rule_dialogue_shape(lines: list[str], result: Result) -> list[str]:
    """節ごとの会話量、実効往復、発言長の分布、節末の締め方を診断する。"""
    sections = parse_sections(lines)
    checked = [section for section in sections if section.should_check()]
    previous_boilerplate = False

    for section in checked:
        shape = section.shape()
        rapid = section.rapid_runs()
        rapid_text = (
            "、高速区間 " + "・".join(f"{start}〜{end}発言目" for start, end in rapid)
            if rapid
            else ""
        )
        result.add(
            section.line, "info", "dialogue-shape", f"{section.title} ({shape}{rapid_text})"
        )

        if section.turns < MIN_EFFECTIVE_TURNS:
            result.add(
                section.line, "warning", "dialogue-shape",
                f"{MIN_EFFECTIVE_TURNS}実効往復未満: {section.title}"
                f"（核心概念なら不足、{shape}）",
            )
        if section.turns > MANY_TURNS:
            result.add(
                section.line, "warning", "dialogue-shape",
                f"{MANY_TURNS}実効往復超: {section.title}"
                f"（核心概念が二つ競合していないか確認、{shape}）",
            )
        # 会話量は info。節の粒度は教材ごとに正当に異なり、既存56冊では
        # <1200字が全節の60%で発火して情報を持たなかった。合否に使わない。
        if section.total_chars < SECTION_CHAR_MIN:
            result.add(
                section.line, "info", "dialogue-shape",
                f"会話量が少ない: {section.title}"
                f" ({section.total_chars}字 < {SECTION_CHAR_MIN}字)",
            )
        elif section.total_chars > SECTION_CHAR_MAX:
            result.add(
                section.line, "info", "dialogue-shape",
                f"会話量が多い: {section.title}"
                f" ({section.total_chars}字 > {SECTION_CHAR_MAX}字)",
            )

        # 行数と字数は同じ「長すぎる発言」の2つの判定軸。1件として発火させ、
        # 診断には両方を書く（字数だけにすると行数のみ超過する節を見落とす）。
        over_lines = [
            index
            for index, count in enumerate(section.speech_lines, 1)
            if count > SPEECH_LINE_LIMIT
        ]
        over_chars = [
            index
            for index, count in enumerate(section.speech_chars, 1)
            if count > SPEECH_CHAR_REVIEW
        ]
        oversized = sorted(set(over_lines) | set(over_chars))
        if oversized:
            result.add(
                section.line, "warning", "dialogue-shape",
                f"長大な発言が{len(oversized)}件: {section.title}"
                f"（{SPEECH_LINE_LIMIT}行超 {len(over_lines)}件／"
                f"{SPEECH_CHAR_REVIEW}字超 {len(over_chars)}件、"
                f"{'・'.join(f'{i}発言目' for i in oversized)}。"
                "感情の頂点または不可分な導出か確認）",
            )

        band_counts = section.band_counts()
        if len(section.speech_texts) >= 8:
            dominant_label, dominant_count = max(band_counts, key=lambda item: item[1])
            if dominant_count / len(section.speech_texts) >= UNIFORM_BAND_RATIO:
                # テンポの偏りは yaruo-review が読む順序を決める材料であって合否ではない。
                result.add(
                    section.line, "info", "dialogue-shape",
                    f"発言長が「{dominant_label}」へ"
                    f"{dominant_count}/{len(section.speech_texts)}件集中: "
                    f"{section.title}（テンポ一定でないか確認）",
                )

        # 節末の理解の所有権。教師の長い発言で閉じていれば講義的総括の疑いがある。
        if (
            section.speakers[-1] == "やらない夫"
            and section.speech_chars[-1] > TEACHER_CLOSING_CHARS
        ):
            result.add(
                section.line, "warning", "dialogue-shape",
                f"節末が やらない夫 の{section.speech_chars[-1]}字の発言: {section.title}"
                "（講義的総括になっていないか、理解の所有権をやる夫へ返したか確認）",
            )

        boilerplate = bool(BOILERPLATE_END_RE.search(section.speech_texts[-1]))
        if boilerplate and previous_boilerplate:
            result.add(
                section.line, "warning", "dialogue-shape",
                f"節末の要約定型が連続: {section.title}"
                "（前節も同じ型で閉じている。発見・次の行動・感情的余波などへ散らす）",
            )
        previous_boilerplate = boilerplate

    approvals = sum(
        len(APPROVAL_RE.findall(text))
        for section in sections
        for text in section.speech_texts
    )
    if checked and approvals / len(checked) > APPROVAL_PER_SECTION:
        result.add(
            None, "warning", "dialogue-shape",
            f"承認語が{approvals}件／{len(checked)}節 "
            f"(={approvals / len(checked):.2f}件/節)"
            "（「鋭い」「いい問いだ」等のインフレ。重要な転換点へ絞る）",
        )
    return lines


# --------------------------------------------------------------------------
# --stats（受け入れレビューの横断表）
# --------------------------------------------------------------------------
#
# yaruo-review の Step 2 が要求する横断表を、レビュアーが毎回その場限りの
# スクリプトで出し直さないための集計。二者レビューで双方が同じ数字を見るための
# 共通の土台でもある。
#
# **ここに載せるのは、話者行から機械的に確定する量だけとする。** 「承認語」
# 「素朴案」のような語の一致で数えるものは、候補生成であって測定ではないので
# 載せない。件数を主張にするには全件の目視が要る（yaruo-review/SKILL.md）。


def _act_buckets(sections: list[Section]) -> list[tuple[str, list[Section]]]:
    """`##` 見出しごとに、その配下の節をまとめる。発言の無い幕は落とす。"""
    buckets: list[tuple[str, list[Section]]] = []
    for section in sections:
        if section.level == "##":
            buckets.append((section.title, []))
            continue
        if buckets and section.speech_texts:
            buckets[-1][1].append(section)
    return [(title, members) for title, members in buckets if members]


def _speaker_totals(members: list[Section]) -> dict[str, tuple[int, int]]:
    """話者ごとの (発言数, 総字数) を返す。"""
    totals: dict[str, tuple[int, int]] = {}
    for section in members:
        for speaker, text in zip(section.speakers, section.speech_texts):
            count, chars = totals.get(speaker, (0, 0))
            totals[speaker] = (count + 1, chars + len(text))
    return totals


def report_stats(path: Path, lines: list[str]) -> None:
    """幕別の話者バランスと見出し末の話者を出す。**診断であって合否に使わない。**"""
    sections = parse_sections(lines, levels=("##", "###"))
    print(f"{path}: 集計（診断。合否に使わない）")

    print(
        f"  [幕別の話者バランス] 主役2名 {'／'.join(LEAD_SPEAKERS)} のみ。"
        "比は脇役を含む幕の総字数に対する割合。発言字数は話者行・空行を除く本文のみ"
    )
    for title, members in _act_buckets(sections):
        totals = _speaker_totals(members)
        overall = sum(chars for _, chars in totals.values())
        columns = []
        for speaker in LEAD_SPEAKERS:
            count, chars = totals.get(speaker, (0, 0))
            average = chars // count if count else 0
            share = f"{chars * 100 // overall}%" if overall else "-"
            columns.append(f"{speaker} {count}発言/{chars}字/平均{average}/比{share}")
        print(f"    {title}")
        print(f"      {'  '.join(columns)}")

    closers = [
        (section.speech_starts[-1], section.speakers[-1], section.level, section.title)
        for section in sections
        if section.speech_texts and section.level in ("###", "####")
    ]
    tally: dict[str, int] = {}
    for _, speaker, _, _ in closers:
        tally[speaker] = tally.get(speaker, 0) + 1
    levels = {level: sum(1 for _, _, lv, _ in closers if lv == level) for level in ("###", "####")}
    print(
        f"  [見出し末の話者] 脇役を含む実際の最終話者。母数 {len(closers)}"
        f"（### {levels['###']} / #### {levels['####']}）"
        f" ── {'、'.join(f'{name} {count}' for name, count in sorted(tally.items()))}"
    )
    for line_no, speaker, level, title in closers:
        print(f"    L{line_no:<5} {speaker:<6} {level} {title}")


# --------------------------------------------------------------------------
# レジストリと CLI
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    id: str
    summary: str
    fixable: bool
    run: object


# 適用順は固定。会話表記を確定させてから強調・表・句点を直し、最後に検査だけの
# ルールを回す。
REGISTRY: tuple[Rule, ...] = (
    Rule("dialogue-frame", "発言外枠のカギカッコ・行頭全角空白", True, rule_dialogue_frame),
    Rule("emphasis-flanking", "約物に隣接して壊れた **", True, rule_emphasis_flanking),
    Rule("table-delimiter", "GFM 表の区切り行", True, rule_table_delimiter),
    Rule("dialogue-period", "発言末の句点", True, rule_dialogue_period),
    Rule("notation", "金額・割合の半角算用数字表記", True, rule_notation),
    Rule("circled-numbers", "丸囲み数字を (1)(2)(3) 等へ書き換え", True, rule_circled_numbers),
    Rule("unit-notation", "メートル・グラム系単位を m/km/g/kg 等へ書き換え", True, rule_unit_notation),
    Rule("end-marker", "終端マーカー `**── 完 ──**`", True, rule_end_marker),
    Rule("heading-level", "幕は ##、節は ###", True, rule_heading_level),
    Rule("structure-delimiter", "タイトル・見出し・完了マーカーの区切り行", True, rule_structure_delimiter),
    Rule("invisible-chars", "制御文字・私用領域文字の混入", False, rule_invisible_chars),
    Rule("structure", "幕・節番号、参考文献見出し、禁止見出し", False, rule_structure),
    Rule("footnotes", "脚注の未使用・未定義", False, rule_footnotes),
    Rule("term-english", "専門用語の英語併記の置き方", False, rule_term_english),
    Rule("dialogue-shape", "会話量・実効往復・発言長の診断", False, rule_dialogue_shape),
)


def selected_rules(spec: str | None) -> list[Rule]:
    if not spec:
        return list(REGISTRY)
    wanted = [name.strip() for name in spec.split(",") if name.strip()]
    known = {rule.id: rule for rule in REGISTRY}
    unknown = [name for name in wanted if name not in known]
    if unknown:
        raise SystemExit(f"未知のルール: {', '.join(unknown)}（--list-rules で一覧）")
    return [known[name] for name in wanted]


def lint_file(path: Path, rules: list[Rule], apply: bool) -> tuple[Result, bool]:
    with open(path, encoding="utf-8", newline="") as handle:
        lines = handle.readlines()
    original = list(lines)
    result = Result(lines)
    for rule in rules:
        if apply:
            # 適用時だけ連鎖させる。会話表記を確定させてから強調・表・句点を直す
            # という順序に意味があるため。
            result.lines = rule.run(result.lines, result)
        else:
            # 検査時は各ルールが原文を見る。前段の修正を織り込んだ本文に対して
            # 診断値を出すと、実ファイルと合わない字数を報告してしまう。
            rule.run(original, result)
    changed = result.lines != original
    if apply and changed:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.writelines(result.lines)
    return result, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="*")
    parser.add_argument("--fix", action="store_true", help="自動修正可能なものを適用する")
    parser.add_argument("--check", action="store_true", help="変更せず報告する（既定）")
    parser.add_argument("--rules", help="適用するルールIDをカンマ区切りで指定する")
    parser.add_argument("--verbose", action="store_true", help="info も表示する")
    parser.add_argument("--list-rules", action="store_true", help="ルール一覧を表示する")
    parser.add_argument(
        "--stats",
        action="store_true",
        help="受け入れレビュー用の横断表を出す（診断。合否に使わない）",
    )
    args = parser.parse_args()

    if args.stats:
        if not args.paths:
            parser.error("集計対象のパスを指定する")
        for path in args.paths:
            with open(path, encoding="utf-8", newline="") as handle:
                report_stats(path, handle.readlines())
        return 0
    if args.list_rules:
        for rule in REGISTRY:
            mark = "fix" if rule.fixable else "   "
            print(f"{mark}  {rule.id:<20} {rule.summary}")
        return 0
    if not args.paths:
        parser.error("検査対象のパスを指定する")

    rules = selected_rules(args.rules)
    exit_code = 0
    for path in args.paths:
        result, changed = lint_file(path, rules, args.fix)
        levels = {"error": 0, "warning": 0, "info": 0}
        for finding in result.findings:
            levels[finding.level] += 1
            if finding.level == "info" and not args.verbose:
                continue
            location = f"{path}:{finding.line}" if finding.line else f"{path}"
            print(f"{location}: {finding.level}: [{finding.rule}] {finding.message}")
        summary = "、".join(f"{level} {levels[level]}件" for level in LEVELS)
        if args.fix:
            print(f"{path}: {'修正した' if changed else '変更なし'}（{summary}）")
        else:
            print(f"{path}: {summary}")
        if levels["error"]:
            exit_code = 1
    return 0 if args.fix else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
