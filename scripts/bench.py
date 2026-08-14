#!/usr/bin/env python3
"""制作工程ベンチマークの土台。

一般ベンチマークではモデルを選べない。選びたいのは「この教材制作の6工程で
どのモデルがどれだけ効くか」なので、評価セットは実際の制作物から作る。

このスクリプトが持つのは**機械で確定する部分だけ**。

- `prompt`  : 事例の入力（本文の抜き出しを含む）を組み立てて標準出力へ出す
- `record`  : モデルの出力を規約どおりの名前で `bench/runs/` へ置く
- `blind`   : モデル名を伏せた対比較の袋を作る（対応表は袋の外へ隔離する）
- `reveal`  : judge の判定と対応表を突き合わせ、どのモデルが勝ったかへ戻す
- `report`  : タスク×モデルの能力プロファイル、judge 間の一致、再現性を出す

**単一スコアで順位を決めない。** 出るのは能力プロファイルであって総合点ではない。
評価の設計・軸・人手照合の手順は `bench/README.md` が正本。

    python3 scripts/bench.py check
    python3 scripts/bench.py prompt C-01
    python3 scripts/bench.py record C-01 --model opus --effort high --seq 1 --file out.md
    python3 scripts/bench.py blind --run 2026-08-12 --axis 物語性
    python3 scripts/bench.py reveal --judgments bench/judgments/<id>/judgments.yml
    python3 scripts/bench.py report --run 2026-08-12
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comments as C  # noqa: E402
import review_corpus as RC  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "bench"
CASES_DIR = BENCH_DIR / "cases"
RUNS_DIR = BENCH_DIR / "runs"
JUDGMENTS_DIR = BENCH_DIR / "judgments"

CASE_SCHEMA = "bench-case/v1"
TASKS = {
    "A": "問題発見",
    "B": "コメント対応",
    "C": "説明文→再発見教材",
    "D": "難所説明",
    "E": "構成改善",
    "F": "新規執筆",
}
AXES = ("正確性", "教育性", "物語性")
CASE_ID_RE = re.compile(r"^([A-F])-(\d{2})$")
OUTPUT_RE = re.compile(r"^(?P<model>.+)--(?P<effort>[^-]+)--(?P<seq>\d+)\.md$")

AXIS_INSTRUCTIONS = {
    "正確性": (
        "事実・数値・因果・用語・数式が正しいか、不確実な内容を断定していないかだけを見る。"
        "面白さと分かりやすさは見ない。"
    ),
    "教育性": (
        "読者が自分で推論する余地があるか、問いの前に答えを漏らしていないか、"
        "既知から未知へ到達できるか、説明後に類題を解ける理解になるかだけを見る。"
        "文章の巧みさは見ない。"
    ),
    "物語性": (
        "会話として自然か、展開に変化があるか、舞台・小道具・ボケが学習内容と因果でつながるか、"
        "同型の問答が反復していないかだけを見る。内容の正しさは見ない。"
    ),
}


class BenchError(ValueError):
    pass


# --------------------------------------------------------------------------
# 事例
# --------------------------------------------------------------------------


@dataclass
class Case:
    id: str
    path: Path
    meta: dict[str, Any]

    @property
    def task(self) -> str:
        return self.id.split("-", 1)[0]

    @property
    def input_path(self) -> Path:
        return self.path / "input.md"

    @property
    def reference_path(self) -> Path:
        return self.path / "reference.md"


def case_dir(case_id: str) -> Path:
    match = CASE_ID_RE.match(case_id)
    if not match:
        raise BenchError(f"事例IDは A-01 の形式: {case_id}")
    return CASES_DIR / match.group(1) / case_id


def load_case(case_id: str) -> Case:
    path = case_dir(case_id)
    meta_path = path / "case.yml"
    if not meta_path.exists():
        raise BenchError(f"事例が無い: {meta_path}")
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    return Case(case_id, path, meta)


def load_cases(task: str | None = None) -> list[Case]:
    cases: list[Case] = []
    if not CASES_DIR.exists():
        return cases
    for meta_path in sorted(CASES_DIR.glob("*/*/case.yml")):
        case_id = meta_path.parent.name
        if task and not case_id.startswith(f"{task}-"):
            continue
        cases.append(load_case(case_id))
    return cases


def section_text(source: Path, heading: str) -> str:
    """教材から節・幕を切り出す。素材を bench/ へ複製しないため。"""
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    span = C.section_range(lines, heading)
    if span is None:
        raise BenchError(f"見出しが見つからない: {heading}（{source}）")
    start, end = span
    return "".join(lines[start:end])


def material(case: Case) -> str:
    """case.yml の `source` が指す素材を取り出す。無ければ空。"""
    source = case.meta.get("source")
    if not source:
        return ""
    path = ROOT / str(source)
    if not path.exists():
        raise BenchError(f"素材が無い: {path}")
    heading = case.meta.get("section")
    return section_text(path, str(heading)) if heading else path.read_text(encoding="utf-8")


def source_digest(case: Case) -> str | None:
    text = material(case)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


def build_prompt(case: Case) -> str:
    parts = [case.input_path.read_text(encoding="utf-8").rstrip(), ""]
    body = material(case)
    if body:
        parts += ["---", "", "## 素材", "", body.rstrip(), ""]
    return "\n".join(parts).rstrip() + "\n"


# --------------------------------------------------------------------------
# 実行結果
# --------------------------------------------------------------------------


@dataclass
class Output:
    path: Path
    case_id: str
    model: str
    effort: str
    seq: int

    @property
    def label(self) -> str:
        return f"{self.model}/{self.effort}"


def load_outputs(run_id: str, case_id: str | None = None) -> list[Output]:
    outputs: list[Output] = []
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise BenchError(f"実行が無い: {run_dir}")
    for path in sorted(run_dir.glob("*/*.md")):
        match = OUTPUT_RE.match(path.name)
        if not match:
            continue
        if case_id and path.parent.name != case_id:
            continue
        outputs.append(
            Output(
                path,
                path.parent.name,
                match.group("model"),
                match.group("effort"),
                int(match.group("seq")),
            )
        )
    return outputs


def record(run_id: str, case_id: str, model: str, effort: str, seq: int, source: Path) -> Path:
    load_case(case_id)
    if "--" in model or "--" in effort:
        raise BenchError("モデル名と effort に `--` は使えない（区切りに使っている）")
    destination = RUNS_DIR / run_id / case_id / f"{model}--{effort}--{seq}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


# --------------------------------------------------------------------------
# blind 対比較
# --------------------------------------------------------------------------


PACKET_TEMPLATE = """\
# 対比較 {packet_id}

評価軸は **{axis}** のみ。{instruction}

出力Aと出力Bを読み、どちらが優れるかを `A` / `B` / `tie` で答える。
根拠として**本文の位置と引用**を必ず添える。書いたモデルの推測は書かない。

## 課題

{task}

## 出力A

{left}

## 出力B

{right}
"""


def _order(packet_id: str, left: Output, right: Output) -> tuple[Output, Output]:
    """袋ごとに決定的に左右を入れ替える（提示順の偏りを消す）。"""
    digest = hashlib.sha256(packet_id.encode("utf-8")).digest()[0]
    return (left, right) if digest % 2 == 0 else (right, left)


def blind(run_id: str, axis: str, judge_id: str | None, max_pairs: int | None) -> Path:
    if axis not in AXES:
        raise BenchError(f"軸は {'／'.join(AXES)} のいずれか")
    outputs = load_outputs(run_id)
    if not outputs:
        raise BenchError(f"出力が1件も無い: {RUNS_DIR / run_id}")

    target = JUDGMENTS_DIR / (judge_id or f"{run_id}-{axis}")
    packets_dir = target / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    by_case: dict[str, list[Output]] = {}
    for output in outputs:
        by_case.setdefault(output.case_id, []).append(output)

    mapping: dict[str, dict[str, str]] = {}
    for case_id, case_outputs in sorted(by_case.items()):
        case = load_case(case_id)
        task_text = build_prompt(case).rstrip()
        pairs = list(itertools.combinations(sorted(case_outputs, key=lambda o: o.path.name), 2))
        if max_pairs is not None:
            pairs = pairs[:max_pairs]
        for index, (first, second) in enumerate(pairs, start=1):
            packet_id = f"{case_id}-{index:02d}"
            left, right = _order(packet_id, first, second)
            (packets_dir / f"{packet_id}.md").write_text(
                PACKET_TEMPLATE.format(
                    packet_id=packet_id,
                    axis=axis,
                    instruction=AXIS_INSTRUCTIONS[axis],
                    task=task_text,
                    left=left.path.read_text(encoding="utf-8").rstrip(),
                    right=right.path.read_text(encoding="utf-8").rstrip(),
                ),
                encoding="utf-8",
            )
            mapping[packet_id] = {
                "case": case_id,
                "A": str(left.path.relative_to(ROOT)),
                "B": str(right.path.relative_to(ROOT)),
            }

    # 対応表は袋と同じディレクトリへ置かない。judge へ渡すのは packets/ だけ。
    (target / "mapping.yml").write_text(
        yaml.safe_dump(
            {"run": run_id, "axis": axis, "packets": mapping},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (target / "judgments.yml").write_text(
        yaml.safe_dump(
            {
                "axis": axis,
                "judge": "（judge の名前。人なら人と書く）",
                "verdicts": {packet_id: {"winner": "", "reason": ""} for packet_id in mapping},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return target


def reveal(judgments_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(judgments_path.read_text(encoding="utf-8")) or {}
    mapping_path = judgments_path.parent / "mapping.yml"
    mapping = (yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}).get("packets", {})

    results: dict[str, Any] = {"axis": data.get("axis"), "judge": data.get("judge"), "verdicts": []}
    for packet_id, verdict in (data.get("verdicts") or {}).items():
        winner = str((verdict or {}).get("winner", "")).strip().upper()
        if winner not in {"A", "B", "TIE"}:
            continue
        slots = mapping.get(packet_id)
        if not slots:
            raise BenchError(f"対応表に無い袋: {packet_id}")
        left = Path(slots["A"]).name
        right = Path(slots["B"]).name
        results["verdicts"].append(
            {
                "packet": packet_id,
                "case": slots["case"],
                "winner": "tie" if winner == "TIE" else (left if winner == "A" else right),
                "loser": "" if winner == "TIE" else (right if winner == "A" else left),
                "reason": (verdict or {}).get("reason", ""),
            }
        )
    return results


def _model_of(filename: str) -> str:
    match = OUTPUT_RE.match(filename)
    return f"{match.group('model')}/{match.group('effort')}" if match else filename


# --------------------------------------------------------------------------
# 検査と集計
# --------------------------------------------------------------------------


def check() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for case in load_cases():
        where = f"cases/{case.task}/{case.id}"
        if case.meta.get("schema") != CASE_SCHEMA:
            findings.append(("error", f"{where}: schema が {CASE_SCHEMA} でない"))
        if case.meta.get("task") not in TASKS:
            findings.append(("error", f"{where}: task は {'／'.join(TASKS)} のいずれか"))
        elif case.meta.get("task") != case.task:
            findings.append(("error", f"{where}: task が事例IDと食い違う"))
        if not case.input_path.exists():
            findings.append(("error", f"{where}: input.md が無い"))
        if not str(case.meta.get("evaluates") or "").strip():
            findings.append(("error", f"{where}: evaluates（何を測る事例か）が空"))
        if case.task in {"A", "B"} and not case.reference_path.exists():
            # A は人間の主要指摘、B はコメントの解消条件が無いと採点できない。
            findings.append(("error", f"{where}: reference.md が無い（採点の基準）"))
        try:
            digest = source_digest(case)
        except BenchError as exc:
            findings.append(("error", f"{where}: {exc}"))
            continue
        recorded = case.meta.get("source_digest")
        if digest and not recorded:
            findings.append(("error", f"{where}: source_digest が無い（素材が動いても気づけない）"))
        elif digest and recorded != digest:
            findings.append(
                (
                    "warning",
                    f"{where}: 素材が変わった（記録 {recorded} → 現在 {digest}）。"
                    "過去の実行結果と横並びに比べられない",
                )
            )
    return findings


def report(run_id: str, judgments: Iterable[Path]) -> str:
    outputs = load_outputs(run_id)
    lines: list[str] = [f"# ベンチ結果 {run_id}", ""]

    models = sorted({output.label for output in outputs})
    cases = sorted({output.case_id for output in outputs})
    lines.append(f"事例 {len(cases)}件 × モデル {len(models)}種 ＝ 出力 {len(outputs)}件")
    repeats = {(output.case_id, output.label) for output in outputs}
    if len(outputs) > len(repeats):
        lines.append("同一条件の再生成あり（再現性を見られる）")
    else:
        lines.append("**同一条件の再生成が無い。1回の結果で順位を決めない。**")
    lines.append("")

    judgment_results = [reveal(path) for path in judgments]
    if not judgment_results:
        lines.append("judge の判定がまだ無い。`blind` で袋を作り、判定を集める。")
        return "\n".join(lines) + "\n"

    # タスク × モデルの勝率。総合点へ畳まない。
    tally: dict[tuple[str, str], list[int]] = {}
    for result in judgment_results:
        for verdict in result["verdicts"]:
            task = verdict["case"].split("-", 1)[0]
            if verdict["winner"] == "tie":
                continue
            for filename, delta in ((verdict["winner"], 1), (verdict["loser"], 0)):
                key = (task, _model_of(filename))
                tally.setdefault(key, []).append(delta)

    lines.append("## 能力プロファイル（軸別 blind 対比較の勝率）")
    lines.append("")
    header = "| タスク | " + " | ".join(models) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(models))
    for task in sorted({case_id.split("-", 1)[0] for case_id in cases}):
        cells = []
        for model in models:
            results = tally.get((task, model), [])
            cells.append(f"{sum(results)}/{len(results)}" if results else "—")
        lines.append(f"| {task} {TASKS.get(task, '')} | " + " | ".join(cells) + " |")
    lines.append("")

    if len(judgment_results) > 1:
        verdicts_by_judge = [
            {verdict["packet"]: verdict["winner"] for verdict in result["verdicts"]}
            for result in judgment_results
        ]
        shared = set(verdicts_by_judge[0])
        for verdicts in verdicts_by_judge[1:]:
            shared &= set(verdicts)
        agreed = [
            packet
            for packet in sorted(shared)
            if len({verdicts[packet] for verdicts in verdicts_by_judge}) == 1
        ]
        lines.append(f"## judge 間の一致：{len(agreed)}/{len(shared)}")
        lines.append("")
        split = [packet for packet in sorted(shared) if packet not in agreed]
        if split:
            lines.append("割れた袋（人が blind で確認する対象）：")
            lines.extend(f"- {packet}" for packet in split)
            lines.append("")

    lines.append("**この表は順位表ではない。** 工程ごとに使うモデルを決めるための材料。")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# 事例の作成
# --------------------------------------------------------------------------


CASE_TEMPLATE = """\
schema: {schema}
task: {task}
title: {title}
evaluates: （この事例で何を測るのか。1行）
origin: （どの制作物から作ったか）
"""

INPUT_A = """\
次の教材断片を読み、**問題のある箇所を最大3件**挙げよ。各件について、

1. 問題箇所（引用）
2. なぜ学習上の問題なのか
3. どう直すか

を書く。3件に満たないと思えばそれより少なくてよい。**無理に3件へ埋めない。**
"""

INPUT_B = """\
次の教材断片へ、読者から下のコメントが付いた。**コメントが求める範囲だけ**を直し、
修正後の断片を出力せよ。

- コメントが求めていない箇所を直さない
- 語尾・一人称・キャラクターを変えない
- 意図された誤り（素朴案・誤答）を訂正しない

## コメント

（ここに人間のコメントを貼る）
"""


def from_record(record_name: str, case_id: str, task: str) -> Path:
    """review corpus の記録から A / B の事例を作る。"""
    if task not in {"A", "B"}:
        raise BenchError("記録から作れるのは A（問題発見）と B（コメント対応）だけ")
    corpus_record = RC.find_record(record_name)
    book = corpus_record.book
    heading_path = corpus_record.front.get("heading_path") or []
    source = ROOT / "docs" / "books" / book / "README.md"
    if not source.exists():
        raise BenchError(f"教材が無い: {source}")

    path = case_dir(case_id)
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "schema": CASE_SCHEMA,
        "task": task,
        "title": f"{book} {'/'.join(str(item) for item in heading_path)}",
        "evaluates": "（この事例で何を測るのか。1行）",
        "origin": f"review-corpus/records/{book}/{corpus_record.front.get('comment')}.md",
        "source": str(source.relative_to(ROOT)),
    }
    if heading_path:
        meta["section"] = str(heading_path[-1])
    case = Case(case_id, path, meta)
    meta["source_digest"] = source_digest(case)
    (path / "case.yml").write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (path / "input.md").write_text(INPUT_A if task == "A" else INPUT_B, encoding="utf-8")
    (path / "reference.md").write_text(
        f"# 人間の指摘（{record_name}）\n\n{corpus_record.body.strip()}\n", encoding="utf-8"
    )
    return path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="事例の必須欄と素材の同一性を検査する")

    cases_parser = sub.add_parser("cases", help="事例を一覧する")
    cases_parser.add_argument("--task", choices=sorted(TASKS))

    prompt_parser = sub.add_parser("prompt", help="事例の入力を組み立てる")
    prompt_parser.add_argument("case_id")

    digest_parser = sub.add_parser("digest", help="素材のダイジェストを出す／書き込む")
    digest_parser.add_argument("case_id")
    digest_parser.add_argument("--write", action="store_true", help="case.yml へ記録する")

    record_parser = sub.add_parser("record", help="モデルの出力を規約名で置く")
    record_parser.add_argument("case_id")
    record_parser.add_argument("--run", required=True)
    record_parser.add_argument("--model", required=True)
    record_parser.add_argument("--effort", required=True)
    record_parser.add_argument("--seq", type=int, default=1)
    record_parser.add_argument("--file", type=Path, required=True)

    blind_parser = sub.add_parser("blind", help="モデル名を伏せた対比較の袋を作る")
    blind_parser.add_argument("--run", required=True)
    blind_parser.add_argument("--axis", required=True, choices=AXES)
    blind_parser.add_argument("--judge-id")
    blind_parser.add_argument("--max-pairs", type=int)

    reveal_parser = sub.add_parser("reveal", help="判定を対応表と突き合わせる")
    reveal_parser.add_argument("--judgments", type=Path, required=True)

    report_parser = sub.add_parser("report", help="能力プロファイルを出す")
    report_parser.add_argument("--run", required=True)
    report_parser.add_argument("--judgments", type=Path, nargs="*", default=[])

    from_parser = sub.add_parser("from-record", help="review corpus の記録から事例を作る")
    from_parser.add_argument("record")
    from_parser.add_argument("--case-id", required=True)
    from_parser.add_argument("--task", required=True, choices=["A", "B"])

    args = parser.parse_args()

    try:
        if args.command == "check":
            findings = check()
            for level, message in findings:
                print(f"{level}: {message}")
            errors = sum(1 for level, _ in findings if level == "error")
            print(f"事例 {len(load_cases())}件、error {errors}件、warning {len(findings) - errors}件")
            return 1 if errors else 0

        if args.command == "cases":
            for case in load_cases(args.task):
                print(f"{case.id}\t{case.meta.get('title', '')}\t{case.meta.get('evaluates', '')}")
            return 0

        if args.command == "prompt":
            sys.stdout.write(build_prompt(load_case(args.case_id)))
            return 0

        if args.command == "digest":
            case = load_case(args.case_id)
            digest = source_digest(case)
            if digest is None:
                raise BenchError("この事例は素材を参照していない（source が無い）")
            if args.write:
                # 素材が動いたことに気づかないまま上書きしないよう、既存値との差を出す。
                previous = case.meta.get("source_digest")
                case.meta["source_digest"] = digest
                (case.path / "case.yml").write_text(
                    yaml.safe_dump(case.meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
                )
                print(f"{args.case_id}: {previous or '（未記録）'} → {digest}")
            else:
                print(digest)
            return 0

        if args.command == "record":
            destination = record(
                args.run, args.case_id, args.model, args.effort, args.seq, args.file
            )
            print(f"置いた: {destination.relative_to(ROOT)}")
            return 0

        if args.command == "blind":
            target = blind(args.run, args.axis, args.judge_id, args.max_pairs)
            print(f"袋: {(target / 'packets').relative_to(ROOT)}")
            print(f"対応表（judge へ渡さない）: {(target / 'mapping.yml').relative_to(ROOT)}")
            return 0

        if args.command == "reveal":
            sys.stdout.write(
                yaml.safe_dump(reveal(args.judgments), allow_unicode=True, sort_keys=False)
            )
            return 0

        if args.command == "report":
            sys.stdout.write(report(args.run, args.judgments))
            return 0

        if args.command == "from-record":
            path = from_record(args.record, args.case_id, args.task)
            print(f"作った: {path.relative_to(ROOT)}（input.md と evaluates を埋める）")
            return 0
    except (BenchError, RC.CorpusError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
