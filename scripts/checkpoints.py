#!/usr/bin/env python3
"""Learning Checkpoint（教材の到達目標）の検査と想起練習の出題。

教材の本文は改訂され続けるので、「何幕まで読んだ」「何ページまで読んだ」は
学習成果の正本にならない。正本は**概念**にする。教材ごとに 5〜15 個の
Learning Checkpoint を `docs/books/{ID}/checkpoints.yml` へ置き、本文の版では
なく概念の理解を追う。

各 checkpoint は次の3つを同時に持つ。

- `statement`: 読者が到達したときにできること（「〜を説明できる」）
- `evidence`:  その概念が実際に本文で扱われている証拠（本文の引用断片）
- `probes`:    読了直後・翌日・数日後に出し直す想起練習（説明／予測／転移）

このスクリプトが見るのは**機械で確定することだけ**。checkpoint の粒度が
適切か、転移問題が本当に転移になっているかは人が見る。

    python3 scripts/checkpoints.py docs/books/<id>/checkpoints.yml --check
    python3 scripts/checkpoints.py --all --check
    python3 scripts/checkpoints.py docs/books/<id>/checkpoints.yml --quiz 翌日
    python3 scripts/checkpoints.py --scaffold <id>

error は必ず解消する（exit 1）。warning は人が内容を見て判断する。
info は診断であって合否に使わない。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comments import build_index, heading_path_at, normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = ROOT / "docs" / "books"

SCHEMA = "checkpoints/v1"
FILE_NAME = "checkpoints.yml"

MIN_CHECKPOINTS = 5
MAX_CHECKPOINTS = 15
MAX_STATEMENT_CHARS = 60
MIN_EVIDENCE_CHARS = 8

WHENS = ("直後", "翌日", "数日後")
KINDS = ("説明", "予測", "転移")
# 「できる」で閉じる到達行動だけを statement に置く。知識の名前
# （「DRAM のリフレッシュ」）は到達行動ではないので弾く。
STATEMENT_TAIL = "できる"

TOP_LEVEL_KEYS = {"schema", "book", "checkpoints"}
CHECKPOINT_KEYS = {
    "id",
    "statement",
    "concept",
    "depends_on",
    "evidence",
    "probes",
    "retired",
    "note",
}
PROBE_KEYS = {"when", "kind", "prompt", "expected"}

LEVELS = ("error", "warning", "info")


@dataclass
class Finding:
    level: str
    rule: str
    message: str
    where: str = ""


@dataclass
class Report:
    path: Path
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, rule: str, message: str, where: str = "") -> None:
        self.findings.append(Finding(level, rule, message, where))

    def counts(self) -> dict[str, int]:
        levels = {level: 0 for level in LEVELS}
        for finding in self.findings:
            levels[finding.level] += 1
        return levels


# --------------------------------------------------------------------------
# 読み込み
# --------------------------------------------------------------------------


def book_of(path: Path) -> str:
    return path.resolve().parent.name


def readme_of(path: Path) -> Path:
    return path.resolve().parent / "README.md"


def load(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError("空のファイル")
    if not isinstance(raw, dict):
        raise ValueError("トップレベルがマッピングではない")
    return raw


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# --------------------------------------------------------------------------
# 検査
# --------------------------------------------------------------------------


def check_structure(data: dict[str, Any], path: Path, report: Report) -> list[dict[str, Any]]:
    unknown = sorted(set(data) - TOP_LEVEL_KEYS)
    if unknown:
        report.add("error", "schema", f"未知のトップレベルキー: {'、'.join(unknown)}")
    if data.get("schema") != SCHEMA:
        report.add("error", "schema", f"schema は {SCHEMA} にする（現在: {data.get('schema')!r}）")

    expected_book = book_of(path)
    if data.get("book") != expected_book:
        report.add(
            "error",
            "schema",
            f"book がディレクトリ名と違う（book: {data.get('book')!r} / ディレクトリ: {expected_book}）",
        )

    entries = data.get("checkpoints")
    if not isinstance(entries, list) or not entries:
        report.add("error", "schema", "checkpoints が空、またはリストではない")
        return []
    valid: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            report.add("error", "schema", "checkpoint がマッピングではない", f"#{index}")
            continue
        unknown = sorted(set(entry) - CHECKPOINT_KEYS)
        if unknown:
            report.add(
                "error", "schema", f"未知のキー: {'、'.join(unknown)}", str(entry.get("id", f"#{index}"))
            )
        valid.append(entry)
    return valid


def check_ids(entries: list[dict[str, Any]], report: Report) -> None:
    seen: set[str] = set()
    for entry in entries:
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid.strip():
            report.add("error", "id", "id が無い")
            continue
        if cid in seen:
            report.add("error", "id", "id が重複している", cid)
        seen.add(cid)

    # 引退した checkpoint も id を残す（後から番号を詰め直すと、過去の
    # 学習記録が別の概念を指してしまう）。
    live = [entry for entry in entries if not entry.get("retired")]
    if len(live) < MIN_CHECKPOINTS:
        report.add(
            "error",
            "count",
            f"有効な checkpoint が {len(live)} 個しかない（下限 {MIN_CHECKPOINTS}）",
        )
    elif len(live) > MAX_CHECKPOINTS:
        report.add(
            "error",
            "count",
            f"有効な checkpoint が {len(live)} 個ある（上限 {MAX_CHECKPOINTS}）。"
            "上位概念へ統合するか、教材を分ける",
        )


def check_statements(entries: list[dict[str, Any]], report: Report) -> None:
    seen: dict[str, str] = {}
    for entry in entries:
        cid = str(entry.get("id", "?"))
        statement = entry.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            report.add("error", "statement", "statement が無い", cid)
            continue
        statement = statement.strip()
        if not statement.endswith(STATEMENT_TAIL):
            report.add(
                "error",
                "statement",
                f"到達行動で書く（「…{STATEMENT_TAIL}」で閉じる）: {statement}",
                cid,
            )
        if len(statement) > MAX_STATEMENT_CHARS:
            report.add(
                "warning",
                "statement",
                f"{len(statement)}字ある（目安 {MAX_STATEMENT_CHARS}字）。"
                "複数の到達点が混ざっていないか見る",
                cid,
            )
        key = normalize(statement)
        if key in seen:
            report.add("error", "statement", f"{seen[key]} と同じ到達点を二重に置いている", cid)
        else:
            seen[key] = cid

        if not str(entry.get("concept", "")).strip():
            report.add("error", "statement", "concept（概念名）が無い", cid)


def check_dependencies(entries: list[dict[str, Any]], report: Report) -> None:
    ids = {str(entry.get("id")) for entry in entries}
    graph: dict[str, list[str]] = {}
    for entry in entries:
        cid = str(entry.get("id", "?"))
        deps = [str(dep) for dep in _as_list(entry.get("depends_on"))]
        for dep in deps:
            if dep == cid:
                report.add("error", "depends", "自分自身に依存している", cid)
            elif dep not in ids:
                report.add("error", "depends", f"存在しない id に依存している: {dep}", cid)
        graph[cid] = [dep for dep in deps if dep in ids and dep != cid]

    # 依存の循環は「前提から未知へ到達する」順序が壊れている印。
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cycle = trail[trail.index(node) :] + [node]
            report.add("error", "depends", f"依存が循環している: {' → '.join(cycle)}", node)
            return
        state[node] = 1
        for dep in graph.get(node, []):
            visit(dep, trail + [node])
        state[node] = 2

    for node in graph:
        visit(node, [])


def check_evidence(
    entries: list[dict[str, Any]], readme: Path, report: Report
) -> dict[str, str]:
    """引用が本文に実在するか照合し、見つかった checkpoint の幕を返す。"""
    acts: dict[str, str] = {}
    if not readme.exists():
        report.add("error", "evidence", f"本文が無い: {readme}")
        return acts

    lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
    index = build_index(lines)

    for entry in entries:
        cid = str(entry.get("id", "?"))
        if entry.get("retired"):
            continue
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            report.add("error", "evidence", "evidence（本文の引用断片）が無い", cid)
            continue
        needle = normalize(evidence)
        if len(needle) < MIN_EVIDENCE_CHARS:
            report.add(
                "warning",
                "evidence",
                f"引用が短すぎて本文の別の場所にも当たる（{len(needle)}字）",
                cid,
            )
        position = index.text.find(needle)
        if position < 0:
            # 本文は改訂される。引用が消えたことは「概念が消えた」とは限らない
            # ので、error にはせず人へ回す。
            report.add(
                "warning",
                "evidence",
                f"引用が本文に見つからない: {evidence.strip()[:40]}。"
                "概念ごと消えたのか、言い回しが変わっただけかを人が判断して引き直す",
                cid,
            )
            continue
        if index.text.find(needle, position + 1) >= 0:
            report.add("warning", "evidence", "引用が本文の複数箇所に一致する", cid)
        line = index.line_at(position)
        # 経路は [題名, 幕, 節]。分布を見たいのは幕なので2段目を取る。
        path = heading_path_at(lines, line)
        acts[cid] = path[1] if len(path) > 1 else ""
    return acts


def check_probes(entries: list[dict[str, Any]], report: Report) -> None:
    whens: set[str] = set()
    kinds: set[str] = set()
    total = 0

    for entry in entries:
        cid = str(entry.get("id", "?"))
        if entry.get("retired"):
            continue
        probes = entry.get("probes")
        if not isinstance(probes, list) or not probes:
            report.add("error", "probe", "probes（想起練習）が1件も無い", cid)
            continue
        for order, probe in enumerate(probes, start=1):
            total += 1
            where = f"{cid}/probe{order}"
            if not isinstance(probe, dict):
                report.add("error", "probe", "probe がマッピングではない", where)
                continue
            unknown = sorted(set(probe) - PROBE_KEYS)
            if unknown:
                report.add("error", "probe", f"未知のキー: {'、'.join(unknown)}", where)

            when = probe.get("when")
            if when not in WHENS:
                report.add("error", "probe", f"when は {'／'.join(WHENS)} のいずれか（現在: {when!r}）", where)
            else:
                whens.add(when)

            kind = probe.get("kind")
            if kind not in KINDS:
                report.add("error", "probe", f"kind は {'／'.join(KINDS)} のいずれか（現在: {kind!r}）", where)
            else:
                kinds.add(kind)

            prompt = str(probe.get("prompt", "")).strip()
            expected = str(probe.get("expected", "")).strip()
            if not prompt:
                report.add("error", "probe", "prompt が無い", where)
            if not expected:
                report.add("error", "probe", "expected（採点用の要点）が無い", where)
            if prompt and expected and normalize(expected) in normalize(prompt):
                # 設問が答えを含んでいる。想起練習にならない。
                report.add("error", "probe", "prompt が expected をそのまま含んでいる（答えの先出し）", where)

    missing_when = [when for when in WHENS if when not in whens]
    if missing_when:
        report.add(
            "warning",
            "probe",
            f"間隔が偏っている（{'、'.join(missing_when)} の probe が無い）。"
            "読了直後だけでは定着を確かめられない",
        )
    if "転移" not in kinds:
        report.add(
            "error",
            "probe",
            "転移問題が1件も無い。教材の外の状況へ適用できるかを問う probe を置く",
        )
    if total:
        report.add("info", "probe", f"probe は合計 {total} 件")


def check_coverage(acts: dict[str, str], report: Report) -> None:
    if not acts:
        return
    distribution: dict[str, int] = {}
    for act in acts.values():
        distribution[act] = distribution.get(act, 0) + 1
    summary = "、".join(f"{act or '（見出し外）'}: {count}" for act, count in distribution.items())
    report.add("info", "coverage", f"引用位置の幕別分布 — {summary}")


def check_file(path: Path) -> Report:
    report = Report(path)
    try:
        data = load(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        report.add("error", "schema", f"読めない: {exc}")
        return report

    entries = check_structure(data, path, report)
    if not entries:
        return report
    check_ids(entries, report)
    check_statements(entries, report)
    check_dependencies(entries, report)
    acts = check_evidence(entries, readme_of(path), report)
    check_probes(entries, report)
    check_coverage(acts, report)
    return report


# --------------------------------------------------------------------------
# 出題と雛形
# --------------------------------------------------------------------------


def quiz(path: Path, when: str | None, with_expected: bool) -> str:
    data = load(path)
    lines: list[str] = [f"# 想起練習 — {data.get('book', '')}", ""]
    count = 0
    for entry in data.get("checkpoints") or []:
        if not isinstance(entry, dict) or entry.get("retired"):
            continue
        selected = [
            probe
            for probe in _as_list(entry.get("probes"))
            if isinstance(probe, dict) and (when is None or probe.get("when") == when)
        ]
        if not selected:
            continue
        lines.append(f"## {entry.get('id')} {entry.get('concept', '')}")
        lines.append("")
        for probe in selected:
            count += 1
            lines.append(f"{count}. [{probe.get('kind')}] {str(probe.get('prompt', '')).strip()}")
            if with_expected:
                lines.append(f"   - 要点: {str(probe.get('expected', '')).strip()}")
        lines.append("")
    if not count:
        lines.append("（該当する probe が無い）")
    return "\n".join(lines).rstrip() + "\n"


SCAFFOLD = """\
schema: {schema}
book: {book}
checkpoints:
  - id: cp-01
    concept: ここに概念名
    statement: ここに到達行動を「〜できる」で書く
    depends_on: []
    evidence: 本文からそのまま引く断片
    probes:
      - when: 直後
        kind: 説明
        prompt: 読者へ出す問い（答えを書かない）
        expected: 採点者が見る要点
      - when: 数日後
        kind: 転移
        prompt: 教材に出てこない状況へ当てる問い
        expected: 採点者が見る要点
"""


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def collect_paths(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted(BOOKS_DIR.glob(f"*/{FILE_NAME}"))
    return [Path(item) for item in args.paths]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", type=Path, nargs="*", help=f"docs/books/<id>/{FILE_NAME}")
    parser.add_argument("--all", action="store_true", help="docs/books/ 配下すべてを検査する")
    parser.add_argument("--check", action="store_true", help="検査する（既定）")
    parser.add_argument("--verbose", action="store_true", help="info も表示する")
    parser.add_argument("--quiz", metavar="TIMING", nargs="?", const="", help=f"想起練習を出題する（{'／'.join(WHENS)}）")
    parser.add_argument("--with-expected", action="store_true", help="--quiz に採点用の要点も出す")
    parser.add_argument("--scaffold", metavar="BOOK", help="雛形を標準出力へ書く")
    args = parser.parse_args()

    if args.scaffold:
        sys.stdout.write(SCAFFOLD.format(schema=SCHEMA, book=args.scaffold))
        return 0

    paths = collect_paths(args)
    if not paths:
        parser.error("検査対象のパスを指定する（または --all）")

    if args.quiz is not None:
        when = args.quiz or None
        if when is not None and when not in WHENS:
            parser.error(f"--quiz は {'／'.join(WHENS)} のいずれか")
        for path in paths:
            sys.stdout.write(quiz(path, when, args.with_expected))
        return 0

    exit_code = 0
    for path in paths:
        report = check_file(path)
        for finding in report.findings:
            if finding.level == "info" and not args.verbose:
                continue
            where = f" [{finding.where}]" if finding.where else ""
            print(f"{path}{where}: {finding.level}: [{finding.rule}] {finding.message}")
        levels = report.counts()
        print(f"{path}: " + "、".join(f"{level} {levels[level]}件" for level in LEVELS))
        if levels["error"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
