#!/usr/bin/env python3
"""`scripts/checkpoints.py` の検査規則の回帰。

見るのは「機械で確定することだけを error にしているか」と「本文が改訂されて
引用が消えたときに、error ではなく warning で人へ回すか」の二点。

    python3 scripts/tests/run_checkpoint_tests.py
"""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import checkpoints as C  # noqa: E402

README = """# やる夫で学ぶ何か

## 第1幕　入口

### 1-1　最初の問い

**やる夫**：
　電荷は漏れるお。だから **定期的に書き戻す** 必要があるお。

**やらない夫**：
　読み出すと電荷が消える。破壊読出しだ。

## 第2幕　密度

**やる夫**：
　一ビットあたりの部品数が違うんだお。
"""


def base_probe(**overrides: Any) -> dict[str, Any]:
    probe = {
        "when": "直後",
        "kind": "説明",
        "prompt": "なぜ書き戻しが要るのか。",
        "expected": "電荷が漏れるから。",
    }
    probe.update(overrides)
    return probe


def base_document() -> dict[str, Any]:
    checkpoints = []
    for index in range(1, 6):
        checkpoints.append(
            {
                "id": f"cp-0{index}",
                "concept": f"概念{index}",
                "statement": f"概念{index}の理由を説明できる",
                "depends_on": [],
                "evidence": "電荷は漏れるお",
                "probes": [base_probe()],
            }
        )
    checkpoints[0]["probes"].append(
        base_probe(when="翌日", kind="予測", prompt="翌日の問い。", expected="翌日の要点。")
    )
    checkpoints[1]["probes"].append(
        base_probe(when="数日後", kind="転移", prompt="別の状況では。", expected="別の要点。")
    )
    return {"schema": C.SCHEMA, "book": "sample-book", "checkpoints": checkpoints}


def run(document: dict[str, Any], *, readme: str = README, book: str = "sample-book") -> C.Report:
    with tempfile.TemporaryDirectory() as tmp:
        book_dir = Path(tmp) / book
        book_dir.mkdir()
        (book_dir / "README.md").write_text(readme, encoding="utf-8")
        path = book_dir / C.FILE_NAME
        path.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        return C.check_file(path)


def rules(report: C.Report, level: str) -> set[str]:
    return {finding.rule for finding in report.findings if finding.level == level}


def main() -> int:
    failures: list[str] = []
    cases = 0

    def case(name: str, document: dict[str, Any], *, errors: set[str], warnings: set[str] = frozenset(), readme: str = README) -> None:
        nonlocal cases
        cases += 1
        report = run(document, readme=readme)
        got_errors = rules(report, "error")
        got_warnings = rules(report, "warning")
        if got_errors != errors:
            failures.append(f"{name}: error 期待 {sorted(errors)} / 実際 {sorted(got_errors)}")
        elif warnings and not warnings <= got_warnings:
            failures.append(f"{name}: warning 期待 {sorted(warnings)} / 実際 {sorted(got_warnings)}")

    case("正常", base_document(), errors=set())

    document = base_document()
    document["schema"] = "checkpoints/v0"
    case("schema違い", document, errors={"schema"})

    document = base_document()
    document["book"] = "other-book"
    case("bookがディレクトリと不一致", document, errors={"schema"})

    document = base_document()
    document["checkpoints"] = document["checkpoints"][:3]
    case("下限割れ", document, errors={"count"})

    document = base_document()
    extra = copy.deepcopy(document["checkpoints"][0])
    document["checkpoints"] += [
        {**copy.deepcopy(extra), "id": f"cp-{index:02d}", "concept": f"概念{index}", "statement": f"概念{index}の理由を説明できる"}
        for index in range(6, 18)
    ]
    case("上限超え", document, errors={"count"})

    document = base_document()
    document["checkpoints"][1]["id"] = "cp-01"
    case("id重複", document, errors={"id"})

    document = base_document()
    document["checkpoints"][0]["statement"] = "DRAM のリフレッシュ"
    case("到達行動になっていない", document, errors={"statement"})

    document = base_document()
    document["checkpoints"][0]["depends_on"] = ["cp-02"]
    document["checkpoints"][1]["depends_on"] = ["cp-01"]
    case("依存の循環", document, errors={"depends"})

    document = base_document()
    document["checkpoints"][0]["depends_on"] = ["cp-99"]
    case("存在しない依存", document, errors={"depends"})

    document = base_document()
    document["checkpoints"][1]["probes"][1]["kind"] = "説明"
    case("転移問題が無い", document, errors={"probe"})

    document = base_document()
    document["checkpoints"][0]["probes"][0]["prompt"] = "電荷は漏れるので書き戻しが要る。理由は。"
    document["checkpoints"][0]["probes"][0]["expected"] = "電荷は漏れる"
    case("設問が答えを含む", document, errors={"probe"})

    document = base_document()
    document["checkpoints"][2]["probes"] = []
    case("probeが無い", document, errors={"probe"})

    # 本文の改訂で引用が消えるのは日常。error にせず人へ回す。
    document = base_document()
    document["checkpoints"][0]["evidence"] = "本文に存在しない一文である"
    case("引用が消えた", document, errors=set(), warnings={"evidence"})

    document = base_document()
    document["checkpoints"][0]["evidence"] = "漏れる"
    case("引用が短すぎる", document, errors=set(), warnings={"evidence"})

    # 引退した checkpoint は id を残したまま下限の数から外れる。
    cases += 1
    document = base_document()
    document["checkpoints"][0]["retired"] = True
    del document["checkpoints"][0]["probes"]
    del document["checkpoints"][0]["evidence"]
    report = run(document)
    if "count" not in rules(report, "error"):
        failures.append("引退: 有効な checkpoint が減ったのに count が出ていない")
    if "evidence" in rules(report, "error") or "probe" in rules(report, "error"):
        failures.append("引退: 引退分に evidence/probe を要求してしまった")

    # 出題は expected を伏せる。
    cases += 1
    with tempfile.TemporaryDirectory() as tmp:
        book_dir = Path(tmp) / "sample-book"
        book_dir.mkdir()
        (book_dir / "README.md").write_text(README, encoding="utf-8")
        path = book_dir / C.FILE_NAME
        path.write_text(
            yaml.safe_dump(base_document(), allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        quiz = C.quiz(path, "数日後", False)
        if "別の要点。" in quiz:
            failures.append("quiz: expected を読者向け出題へ漏らしている")
        if "別の状況では。" not in quiz:
            failures.append("quiz: 該当する probe を出していない")
        graded = C.quiz(path, "数日後", True)
        if "別の要点。" not in graded:
            failures.append("quiz --with-expected: 要点が出ていない")

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{cases} 件中 {cases - len(failures)} 件成功")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
