#!/usr/bin/env python3
"""やる夫式教材の同型反復（same-beat run）を語彙非依存で検出する。

固定の単語リストは一切使わない。発話ターンを

    役割ID（書内の総発話量順位） × 長さ級 × 終端型 × 非散文の有無

の1記号へ落とし、次の2指標で判定する。

* 単位内単調度 M : 記号列の周期反復がターン列をどれだけ占めるか
* 単位間新規性 N : 隣接単位の記号列の正規化編集距離

いずれも絶対閾値を置かず、その教材自身の分布で正規化する。教材ごとに地の
文体が違うため、書間で共通の閾値は意味を持たない。

使い方::

    python3 scripts/yaruo_beat_repetition.py docs/books/*/README.md
    python3 scripts/yaruo_beat_repetition.py docs/books/bureaucracy/README.md --show
    python3 scripts/yaruo_beat_repetition.py docs/books/*/README.md --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yaruo_markdown import SPEAKER_LINE, bodies_of, non_prose_lines, speaker_names
from yaruo_review_eval import build_structure

QUESTION_MARKS = "？?"
EXCLAIM_MARKS = "！!"

SHORT_TURN = 40
LONG_TURN = 120

ROLE_SLOTS = 4
LENGTH_SLOTS = 3
END_SLOTS = 3
NONPROSE_SLOTS = 2

LOW_RATIO = 0.85  # 書内中央値に対する「低新規性」の比
MIN_RUN_UNITS = 3  # ランとみなす最小単位数
MONOTONY_RATIO = 1.25  # 書内中央値に対する「高単調」の比


# --------------------------------------------------------------------------
# 層1 記号化
# --------------------------------------------------------------------------


def extract_turns(lines: list[str], start_line: int, end_line: int, names: set[str]) -> list[dict[str, Any]]:
    """[start_line, end_line]（1-indexed）の範囲を発話ターン列にする。"""
    bodies = bodies_of(lines)
    protected = non_prose_lines(lines)
    turns: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for index in range(start_line - 1, min(end_line, len(lines))):
        body = bodies[index]
        match = SPEAKER_LINE.match(body)
        if match and match.group(1) in names:
            current = {"who": match.group(1), "line": index + 1, "text": "", "nonprose": 0}
            turns.append(current)
            continue
        if current is None:
            continue
        if index in protected:
            current["nonprose"] += 1
            continue
        stripped = body.strip()
        if stripped.startswith("|") or re.match(r"^([-*+]|\d+\.)\s", stripped):
            current["nonprose"] += 1
            continue
        current["text"] += stripped
    return turns


def role_ranks(lines: list[str], names: set[str]) -> dict[str, int]:
    """話者を書内の総発話量で順位付けする。話者名そのものは判定に使わない。"""
    volume: dict[str, int] = {}
    for turn in extract_turns(lines, 1, len(lines), names):
        volume[turn["who"]] = volume.get(turn["who"], 0) + len(turn["text"])
    ordered = sorted(volume.items(), key=lambda item: (-item[1], item[0]))
    return {who: rank for rank, (who, _) in enumerate(ordered)}


def turn_symbol(turn: dict[str, Any], ranks: dict[str, int]) -> str:
    role = min(ranks.get(turn["who"], ROLE_SLOTS - 1), ROLE_SLOTS - 1)
    length = len(turn["text"])
    length_class = 0 if length < SHORT_TURN else (1 if length < LONG_TURN else 2)
    tail = turn["text"][-1:]
    end_class = 1 if tail in QUESTION_MARKS else (2 if tail in EXCLAIM_MARKS else 0)
    nonprose = 1 if turn["nonprose"] else 0
    code = ((role * LENGTH_SLOTS + length_class) * END_SLOTS + end_class) * NONPROSE_SLOTS + nonprose
    return chr(ord("A") + code)


def symbolize(turns: list[dict[str, Any]], ranks: dict[str, int]) -> str:
    return "".join(turn_symbol(turn, ranks) for turn in turns)


# --------------------------------------------------------------------------
# 層2 反復指標
# --------------------------------------------------------------------------


def monotony(symbols: str) -> float:
    """周期1〜3の反復が列をどれだけ占めるか。`ABABAB` を直接捉える。"""
    if len(symbols) < 4:
        return 0.0
    best = 0
    for period in (1, 2, 3):
        if len(symbols) <= period:
            continue
        streak = 0
        longest = 0
        for index in range(len(symbols) - period):
            if symbols[index] == symbols[index + period]:
                streak += 1
                longest = max(longest, streak)
            else:
                streak = 0
        best = max(best, longest + period if longest else 0)
    return min(best / len(symbols), 1.0)


def edit_ratio(left: str, right: str) -> float:
    """正規化編集距離。0 は完全同型、1 は共通部分なし。"""
    if not left or not right:
        return 1.0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, b in enumerate(right, start=1):
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b))
        previous = current
    return previous[-1] / max(len(left), len(right))


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


# --------------------------------------------------------------------------
# 検出
# --------------------------------------------------------------------------


def severity_of(run_units: int, depth: float, crosses_acts: bool) -> str:
    """ラン長と書内分位の深さから重みを決める。自動不合格には使わない。"""
    score = 0
    if run_units >= 4:
        score += 1
    if run_units >= 6:
        score += 1
    if depth <= 0.6:
        score += 1
    if depth <= 0.4:
        score += 1
    if crosses_acts:
        score += 1
    if score >= 4:
        return "critical"
    if score >= 2:
        return "major"
    return "minor"


# 層3のビートラベル。教師側と生徒側で別の集合を使う。
# 教師が「指示」で進め、生徒が「単純正答」で返す型が、最も避けたい形。
TEACHER_BEATS = {
    "指示": "I",  # 命令形で次の作業を与える
    "問い": "Q",  # 答えを生徒に探させる問いかけ
    "摩擦": "F",  # 反例・反証・失敗の提示
    "提示": "C",  # 正式名・整理・答え合わせ
}
STUDENT_BEATS = {
    "提案": "P",  # 自発的な素朴案
    "質問": "S",  # 生徒から教師への問い返し。主導権が生徒に渡る
    "誤答": "W",  # 素朴な誤答・的外れな断定
    "逡巡": "H",  # 迷い、言い淀み、保留、答えられない
    "単純正答": "A",  # 摩擦を経ずに正解を返す
    "検算": "T",  # 手計算・具体例での検査
    "診断": "D",  # なぜ失敗したかの言語化
    "修正": "R",  # 案の作り直し
}
COMMON_BEATS = {"情動": "E", "脱線": "X"}

BEAT_CODES = {**TEACHER_BEATS, **STUDENT_BEATS, **COMMON_BEATS}
BEAT_LABELS = {code: label for label, code in BEAT_CODES.items()}

STRUGGLE_CODES = "WHF"  # 苦労の実在を示すビート
PLAIN_CODES = "A"  # 摩擦なしの正答
DIRECTIVE_CODES = "I"
INQUIRY_CODES = "Q"
INITIATIVE_CODES = "PS"  # 生徒が会話を動かすビート


def beat_symbols(labels: list[str]) -> str:
    """層3のビートラベル列を1文字記号列にする。未知ラベルは脱線として扱う。"""
    return "".join(BEAT_CODES.get(label, "X") for label in labels)


def beat_metrics(symbols: str) -> dict[str, Any]:
    """ビート記号列から、指示偏重・単純正答・苦労の実在を測る。"""
    total = len(symbols) or 1
    directive = sum(symbols.count(code) for code in DIRECTIVE_CODES)
    inquiry = sum(symbols.count(code) for code in INQUIRY_CODES)
    plain = sum(symbols.count(code) for code in PLAIN_CODES)
    struggle = sum(symbols.count(code) for code in STRUGGLE_CODES)
    initiative = sum(symbols.count(code) for code in INITIATIVE_CODES)
    # 「指示 or 問い → 単純正答」の隣接ペア。最も避けたい型の直接計数。
    handover = sum(
        1
        for left, right in zip(symbols, symbols[1:])
        if left in DIRECTIVE_CODES + INQUIRY_CODES and right in PLAIN_CODES
    )
    directive_pairs = sum(
        1 for left, right in zip(symbols, symbols[1:]) if left in DIRECTIVE_CODES and right in PLAIN_CODES
    )
    return {
        "beats": total,
        "directive": directive,
        "inquiry": inquiry,
        "directive_share": round(directive / (directive + inquiry), 3) if directive + inquiry else None,
        "plain_answer": plain,
        "plain_answer_rate": round(plain / total, 3),
        "struggle": struggle,
        "struggle_rate": round(struggle / total, 3),
        "initiative": initiative,
        "initiative_rate": round(initiative / total, 3),
        "instruct_answer_pairs": handover,
        "directive_answer_pairs": directive_pairs,
    }


def analyze(path: Path, beats: dict[str, list[str]] | None = None) -> dict[str, Any]:
    lines = path.open(encoding="utf-8", newline="").read().splitlines(keepends=True)
    structure = build_structure(path, lines)
    names = speaker_names(lines)
    ranks = role_ranks(lines, names)

    # 層3を与えた場合はビート記号列だけで判定する。表層記号と混ぜて距離を取らない。
    target_units = (
        [unit for unit in structure["units"] if unit["unit_id"] in beats] if beats else structure["units"]
    )

    units: list[dict[str, Any]] = []
    for unit in target_units:
        turns = extract_turns(lines, unit["start_line"], unit["end_line"], names)
        symbols = beat_symbols(beats[unit["unit_id"]]) if beats else symbolize(turns, ranks)
        metrics = beat_metrics(symbols) if beats else None
        units.append(
            {
                "metrics": metrics,
                "unit_id": unit["unit_id"],
                "act_id": unit["act_id"],
                "title": unit["title"],
                "start_line": unit["start_line"],
                "end_line": unit["end_line"],
                "turn_count": len(turns),
                "symbols": symbols,
                "monotony": round(monotony(symbols), 3),
                "turns": turns,
            }
        )

    novelty: list[float | None] = [None]
    for previous, current in zip(units, units[1:]):
        novelty.append(round(edit_ratio(previous["symbols"], current["symbols"]), 3))
    for unit, value in zip(units, novelty):
        unit["novelty"] = value

    finite = [value for value in novelty if value is not None]
    novelty_median = median(finite)
    monotony_median = median([unit["monotony"] for unit in units])
    threshold = novelty_median * LOW_RATIO

    runs: list[dict[str, Any]] = []
    index = 1
    while index < len(units):
        if novelty[index] is not None and novelty[index] < threshold:
            end = index
            while end + 1 < len(units) and novelty[end + 1] is not None and novelty[end + 1] < threshold:
                end += 1
            members = units[index - 1 : end + 1]
            if len(members) >= MIN_RUN_UNITS:
                pair_values = [novelty[position] for position in range(index, end + 1)]
                depth = (median(pair_values) / novelty_median) if novelty_median else 1.0
                acts = {member["act_id"] for member in members}
                runs.append(
                    {
                        "unit_ids": [member["unit_id"] for member in members],
                        "axis": "E2" if len(acts) > 1 else "E3",
                        "defect_type": "same-beat-run",
                        "severity": severity_of(len(members), depth, len(acts) > 1),
                        "novelty": pair_values,
                        "depth": round(depth, 3),
                        "acts": sorted(acts),
                    }
                )
            index = end + 1
        else:
            index += 1

    # 層3を与えた場合だけ、指示偏重と単純正答のランを別立てで検出する。
    # これは同型反復とは独立の欠陥で、1単位でも成立しうるため run 検出に畳まない。
    beat_summary: dict[str, Any] | None = None
    marked_units: list[dict[str, Any]] = []
    if beats:
        joined = "".join(unit["symbols"] for unit in units)
        beat_summary = beat_metrics(joined)
        flat = []
        for unit in units:
            unit_metrics = unit["metrics"]
            marks = []
            if unit_metrics["struggle"] == 0:
                marks.append("no-struggle")
            if unit_metrics["plain_answer_rate"] >= 0.3:
                marks.append("plain-answer-heavy")
            # 指示率は分母が小さいと簡単に1.0へ振れる。教師の発話が4件以上ある単位だけ見る。
            if (
                unit_metrics["directive_share"] is not None
                and unit_metrics["directive"] + unit_metrics["inquiry"] >= 4
                and unit_metrics["directive_share"] >= 0.5
            ):
                marks.append("directive-led")
            unit["marks"] = marks
            flat.append(bool(marks))
            # ラン（3単位以上）に載らない単位も必ず報告する。
            # 指示→単純正答は1単位でも成立するため、ここが唯一の出口になる。
            if marks:
                marked_units.append(
                    {
                        "unit_id": unit["unit_id"],
                        "title": unit["title"],
                        "start_line": unit["start_line"],
                        "end_line": unit["end_line"],
                        "symbols": unit["symbols"],
                        "marks": marks,
                        "struggle": unit_metrics["struggle"],
                        "plain_answer": unit_metrics["plain_answer"],
                        "directive": unit_metrics["directive"],
                        "inquiry": unit_metrics["inquiry"],
                        "initiative": unit_metrics["initiative"],
                        "instruct_answer_pairs": unit_metrics["instruct_answer_pairs"],
                    }
                )
        index = 0
        while index < len(units):
            if flat[index]:
                end = index
                while end + 1 < len(units) and flat[end + 1]:
                    end += 1
                members = units[index : end + 1]
                if len(members) >= MIN_RUN_UNITS:
                    struggle = sum(member["metrics"]["struggle"] for member in members)
                    pairs = sum(member["metrics"]["instruct_answer_pairs"] for member in members)
                    runs.append(
                        {
                            "unit_ids": [member["unit_id"] for member in members],
                            "axis": "L2" if struggle == 0 else "E3",
                            "defect_type": "instruction-and-plain-answer",
                            "severity": "critical" if struggle == 0 and len(members) >= 4 else "major",
                            "struggle": struggle,
                            "instruct_answer_pairs": pairs,
                            "marks": sorted({mark for member in members for mark in member["marks"]}),
                        }
                    )
                index = end + 1
            else:
                index += 1

    monotone_units = [
        unit["unit_id"]
        for unit in units
        if monotony_median and unit["monotony"] >= monotony_median * MONOTONY_RATIO and unit["turn_count"] >= 8
    ]

    return {
        "book_id": path.parent.name,
        "layer": "beat" if beats else "surface",
        "source_path": str(path),
        "unit_count": len(units),
        "speaker_count": len(names),
        "novelty_median": round(novelty_median, 3),
        "monotony_median": round(monotony_median, 3),
        "threshold": round(threshold, 3),
        "runs": runs,
        "beat_summary": beat_summary,
        "marked_units": marked_units,
        "monotone_units": monotone_units,
        "units": units,
    }


# --------------------------------------------------------------------------
# 表示
# --------------------------------------------------------------------------


def clip(text: str, width: int = 46) -> str:
    text = text.strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def show_run(report: dict[str, Any], run: dict[str, Any], turn_limit: int) -> None:
    by_id = {unit["unit_id"]: unit for unit in report["units"]}
    print(f"\n  ── {run['severity']} / {run['axis']} / {run.get('defect_type')} / {' → '.join(run['unit_ids'])}")
    if "depth" in run:
        print(f"     深さ {run['depth']}（書内中央値比）　新規性 {run['novelty']}")
    else:
        print(f"     苦労ビート {run['struggle']}　指示→単純正答 {run['instruct_answer_pairs']}組　{run['marks']}")
    for unit_id in run["unit_ids"]:
        unit = by_id[unit_id]
        head = f"\n     [{unit_id}] {unit['title']}  L{unit['start_line']}-{unit['end_line']}  {unit['symbols']}"
        if unit.get("metrics"):
            metrics = unit["metrics"]
            head += (
                f"\n       指示{metrics['directive']}/問い{metrics['inquiry']}"
                f"　単純正答{metrics['plain_answer']}"
                f"　誤答・逡巡・摩擦{metrics['struggle']}"
            )
        print(head)
        beat_layer = report["layer"] == "beat"
        for turn, code in zip(unit["turns"][:turn_limit], unit["symbols"][:turn_limit]):
            if not turn["text"]:
                continue
            tag = f"{BEAT_LABELS.get(code, '?'):4s} " if beat_layer else ""
            print(f"       {tag}L{turn['line']:>5} {turn['who']}: {clip(turn['text'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--show", action="store_true", help="検出区間の会話の具体を表示する")
    parser.add_argument("--turns", type=int, default=6, help="--show で単位ごとに出す発話数")
    parser.add_argument("--json", type=Path, help="機械可読な結果の出力先")
    parser.add_argument("--units", action="store_true", help="全単位の指標を表示する")
    parser.add_argument(
        "--beats",
        type=Path,
        help="層3のビートラベル {unit_id: [提案, 摩擦, ...]} を読み、表層記号の代わりに使う",
    )
    args = parser.parse_args()

    beats = json.loads(args.beats.read_text(encoding="utf-8")) if args.beats else None

    reports = []
    for path in args.paths:
        report = analyze(path, beats)
        reports.append(report)
        flags = "".join(run["severity"][0].upper() for run in report["runs"]) or "-"
        print(
            f"{report['book_id']:22s} layer={report['layer']:7s} units={report['unit_count']:3d} "
            f"median_N={report['novelty_median']:.3f} median_M={report['monotony_median']:.3f} "
            f"runs={len(report['runs'])}[{flags}] monotone={len(report['monotone_units'])}"
        )
        if args.units:
            for unit in report["units"]:
                value = unit["novelty"]
                mark = ""
                if value is not None and value < report["threshold"]:
                    mark = "LOW"
                print(
                    f"    {unit['unit_id']:22s} N={('%.3f' % value) if value is not None else ' --- '} {mark:4s}"
                    f" M={unit['monotony']:.2f} turns={unit['turn_count']:3d} {unit['symbols'][:44]}"
                )
        if report["beat_summary"]:
            summary = report["beat_summary"]
            print(
                f"    beats={summary['beats']} 指示{summary['directive']}/問い{summary['inquiry']}"
                f"（指示率 {summary['directive_share']}）"
                f" 単純正答率 {summary['plain_answer_rate']} 苦労率 {summary['struggle_rate']}"
                f" 生徒主導率 {summary['initiative_rate']}"
                f" 指示→単純正答 {summary['instruct_answer_pairs']}組"
                f"（うち命令 {summary['directive_answer_pairs']}組）"
            )
            in_runs = {unit_id for run in report["runs"] for unit_id in run["unit_ids"]}
            for marked in report["marked_units"]:
                tail = "" if marked["unit_id"] in in_runs else "  ← ランに載らない単位"
                print(
                    f"    * {marked['unit_id']:22s} {marked['symbols'][:36]:38s}"
                    f" 指示{marked['directive']}/問{marked['inquiry']}"
                    f" 正答{marked['plain_answer']} 苦労{marked['struggle']}"
                    f" 生徒主導{marked['initiative']}"
                    f"  L{marked['start_line']}-{marked['end_line']}"
                    f"  {','.join(marked['marks'])}{tail}"
                )
        for run in report["runs"]:
            detail = (
                f"depth={run['depth']:.2f}"
                if "depth" in run
                else f"struggle={run['struggle']} pairs={run['instruct_answer_pairs']}"
            )
            print(
                f"    ! {run['severity']:8s} {run['axis']} {run['defect_type']:28s} "
                f"{len(run['unit_ids'])}単位 {detail} {run['unit_ids'][0]}…{run['unit_ids'][-1]}"
            )
            if args.show:
                show_run(report, run, args.turns)

    if args.json:
        payload = [
            {key: value for key, value in report.items() if key != "units"} for report in reports
        ]
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
