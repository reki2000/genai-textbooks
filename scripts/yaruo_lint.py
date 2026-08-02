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
    if not runs:
        return body, False, []
    if any(len(m.group()) != 2 for m in runs):
        return body, False, ["長さ2以外の * の連続があるためスキップ"]

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
            if stop in speakers or SECTION_LINE.match(body):
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
# レジストリと CLI
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    id: str
    summary: str
    fixable: bool
    run: object


# 適用順は固定。会話表記を確定させてから強調・表・句点を直す。
REGISTRY: tuple[Rule, ...] = (
    Rule("dialogue-frame", "発言外枠のカギカッコ・行頭全角空白", True, rule_dialogue_frame),
    Rule("emphasis-flanking", "約物に隣接して壊れた **", True, rule_emphasis_flanking),
    Rule("table-delimiter", "GFM 表の区切り行", True, rule_table_delimiter),
    Rule("dialogue-period", "発言末の句点", True, rule_dialogue_period),
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
        result.lines = rule.run(result.lines, result)
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
    args = parser.parse_args()

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
