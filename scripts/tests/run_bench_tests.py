#!/usr/bin/env python3
"""`scripts/bench.py` の blind 対比較と集計の検査。

重点は「袋にモデル名が漏れていないか」「対応表を袋と一緒に渡していないか」
「判定を正しいモデルへ戻せるか」。

    python3 scripts/tests/run_bench_tests.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bench as B  # noqa: E402

CASE_META = """\
schema: bench-case/v1
task: F
title: 検査用
evaluates: 検査用の事例
origin: テスト
"""


def main() -> int:
    failures: list[str] = []
    cases = 0

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        B.ROOT = root
        B.BENCH_DIR = root / "bench"
        B.CASES_DIR = B.BENCH_DIR / "cases"
        B.RUNS_DIR = B.BENCH_DIR / "runs"
        B.JUDGMENTS_DIR = B.BENCH_DIR / "judgments"

        case_path = B.CASES_DIR / "F" / "F-01"
        case_path.mkdir(parents=True)
        (case_path / "case.yml").write_text(CASE_META, encoding="utf-8")
        (case_path / "input.md").write_text("# 課題\n\n書け。\n", encoding="utf-8")

        cases += 1
        findings = B.check()
        if findings:
            failures.append(f"正常な事例で findings が出た: {findings}")

        cases += 1
        for model, effort, text in (
            ("alpha", "high", "アルファの出力。"),
            ("beta", "medium", "ベータの出力。"),
            ("gamma", "xhigh", "ガンマの出力。"),
        ):
            source = root / f"{model}.md"
            source.write_text(text, encoding="utf-8")
            B.record("r1", "F-01", model, effort, 1, source)
        outputs = B.load_outputs("r1")
        if len(outputs) != 3:
            failures.append(f"record: 出力3件のはずが {len(outputs)}件")

        cases += 1
        target = B.blind("r1", "物語性", None, None)
        packets = sorted((target / "packets").glob("*.md"))
        if len(packets) != 3:  # 3モデルの総当たり
            failures.append(f"blind: 袋3個のはずが {len(packets)}個")
        for packet in packets:
            text = packet.read_text(encoding="utf-8")
            for name in ("alpha", "beta", "gamma", "high", "medium", "xhigh"):
                if name in text:
                    failures.append(f"blind: 袋へモデル情報が漏れた（{name}）: {packet.name}")
        if (target / "packets" / "mapping.yml").exists():
            failures.append("blind: 対応表を袋と同じディレクトリへ置いた")
        if not (target / "mapping.yml").exists():
            failures.append("blind: 対応表が無い")

        cases += 1
        # 提示順が袋ごとに入れ替わっている（常に左が同じモデルではない）。
        mapping = yaml.safe_load((target / "mapping.yml").read_text(encoding="utf-8"))["packets"]
        left_models = {Path(slots["A"]).name.split("--")[0] for slots in mapping.values()}
        if len(left_models) < 2:
            failures.append("blind: 左側が常に同じモデルになっている")

        cases += 1
        judgments = {
            "axis": "物語性",
            "judge": "judge-1",
            "verdicts": {packet_id: {"winner": "A", "reason": "根拠"} for packet_id in mapping},
        }
        judgments_path = target / "judgments.yml"
        judgments_path.write_text(yaml.safe_dump(judgments, allow_unicode=True), encoding="utf-8")
        revealed = B.reveal(judgments_path)
        for verdict in revealed["verdicts"]:
            expected = Path(mapping[verdict["packet"]]["A"]).name
            if verdict["winner"] != expected:
                failures.append(f"reveal: 勝者の戻し先が違う（{verdict['packet']}）")

        cases += 1
        text = B.report("r1", [judgments_path])
        if "同一条件の再生成が無い" not in text:
            failures.append("report: 再生成が無い実行にその注意が出ていない")
        if "順位表ではない" not in text:
            failures.append("report: 単一順位として読まれない注意が消えている")

        cases += 1
        # judge を2人にすると一致率が出る。
        second = target.parent / "judge-2"
        (second / "packets").mkdir(parents=True)
        (target / "mapping.yml").replace(second / "mapping.yml")
        (target / "mapping.yml").write_text(
            yaml.safe_dump({"packets": mapping}, allow_unicode=True), encoding="utf-8"
        )
        flipped = {
            "axis": "物語性",
            "judge": "judge-2",
            "verdicts": {
                packet_id: {"winner": "B" if index == 0 else "A", "reason": "根拠"}
                for index, packet_id in enumerate(mapping)
            },
        }
        second_path = second / "judgments.yml"
        second_path.write_text(yaml.safe_dump(flipped, allow_unicode=True), encoding="utf-8")
        text = B.report("r1", [judgments_path, second_path])
        if "judge 間の一致：2/3" not in text:
            failures.append(f"report: 一致率の集計が合わない\n{text}")
        if "割れた袋" not in text:
            failures.append("report: 割れた袋を人の確認対象として出していない")

        cases += 1
        source = root / "dup.md"
        source.write_text("アルファの2回目。", encoding="utf-8")
        B.record("r1", "F-01", "alpha", "high", 2, source)
        text = B.report("r1", [])
        if "同一条件の再生成あり" not in text:
            failures.append("report: 再生成を検出できていない")

        cases += 1
        try:
            B.record("r1", "F-01", "bad--name", "high", 1, source)
        except B.BenchError:
            pass
        else:
            failures.append("record: 区切りと衝突する名前を通してしまった")

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{cases} 件中 {cases - len(failures)} 件成功")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
