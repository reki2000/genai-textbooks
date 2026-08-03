#!/usr/bin/env python3
"""scripts/yaruo_review_eval.py のpilot回帰テスト。"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import yaruo_review_eval as review  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "review_eval_fixtures" / "sample.md"
SCHEMA = ROOT / ".claude" / "skills" / "yaruo-review" / "references" / "entertainment-learning.schema.json"


def presence(data: dict, line: int, quote: str, unit_id: str, region_kind: str = "prose") -> dict:
    unit = next(unit for unit in data["structure"]["units"] if unit["unit_id"] == unit_id)
    return {
        "claim_type": "presence",
        "line": line,
        "quote": quote,
        "region_kind": region_kind,
        "scope": {
            "start_line": unit["start_line"],
            "end_line": unit["end_line"],
            "unit_ids": [unit_id],
        },
        "compared_lines": [],
        "expected": None,
        "note": "fixture evidence",
    }


def complete_evaluation() -> dict:
    data = review.scaffold(FIXTURE)
    data["evaluator"].update(
        {"name": "human", "model": "fixture", "evaluated_at": "2026-08-03T00:00:00+00:00"}
    )
    first_unit = data["structure"]["units"][0]["unit_id"]
    ev = presence(data, 11, "最初の案を試すお。", first_unit)
    data["core_concepts"] = [
        {
            "concept_id": "concept-1",
            "label": "試行と修正",
            "description": "fixture",
            "evidence": [ev],
            "cycles": [
                {
                    "attempt": [ev],
                    "friction": [ev],
                    "diagnosis": [ev],
                    "revision": [ev],
                    "test": [ev],
                }
            ],
            "notes": [],
        }
    ]
    for ledger in data["unit_ledgers"]:
        ledger["section_role"] = "core_discovery"
    for score in data["book_scores"].values():
        score.update({"value": 3, "confidence": "high", "evidence": [ev], "rationale": "fixture"})
    for item in data["unit_scores"]:
        unit = next(unit for unit in data["structure"]["units"] if unit["unit_id"] == item["unit_id"])
        line = next(
            number
            for number in range(unit["start_line"], unit["end_line"] + 1)
            if review.line_region_kinds(FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True))[number - 1]
            == "prose"
        )
        quote = FIXTURE.read_text(encoding="utf-8").splitlines()[line - 1].strip()
        unit_ev = presence(data, line, quote, item["unit_id"])
        for score in item["scores"].values():
            score.update(
                {"value": 3, "confidence": "medium", "evidence": [unit_ev], "rationale": "fixture"}
            )
    data["gates"] = [
        {"axis": axis, "concept_id": "concept-1", "status": "pass", "evidence": [ev], "reason": "fixture"}
        for axis in ("L1", "L2")
    ]
    return data


def assert_has(errors: list[str], fragment: str) -> None:
    if not any(fragment in error for error in errors):
        raise AssertionError(f"{fragment!r} を含むエラーがない: {errors}")


def main() -> int:
    failures: list[str] = []
    cases = 0

    def case(name: str, function) -> None:
        nonlocal cases
        cases += 1
        try:
            function()
        except Exception as exc:  # test runner itself must list every failure
            failures.append(f"{name}: {exc}")

    case("schema-json", lambda: json.loads(SCHEMA.read_text(encoding="utf-8")))

    def structure_case() -> None:
        data = review.scaffold(FIXTURE)
        units = data["structure"]["units"]
        assert [unit["unit_kind"] for unit in units] == ["bare_act", "section", "section"]
        assert units[1]["start_line"] == 16, units[1]
        assert data["structure"]["act_count"] == 2
        assert data["structure"]["subdivided_act_count"] == 1
        assert len(data["structure"]["sampled_unit_ids"]) == 3
        assert any(item["reason"].startswith("meta-act:**――完") for item in data["structure"]["excluded_ranges"])
        assert any("索引" in item["reason"] for item in data["structure"]["excluded_ranges"])
        assert any("次に読む" in item["reason"] for item in data["structure"]["excluded_ranges"])
        assert any("対話演習" in item["reason"] for item in data["structure"]["excluded_ranges"])

    case("bare-act-and-section-scaffold", structure_case)

    def valid_case() -> None:
        errors = review.validate(FIXTURE, complete_evaluation())
        assert not errors, errors

    case("valid-evaluation", valid_case)

    def out_of_range_case() -> None:
        data = complete_evaluation()
        data["book_scores"]["E1"]["evidence"][0]["line"] = 999
        assert_has(review.validate(FIXTURE, data), "本文範囲外")

    case("line-out-of-range", out_of_range_case)

    def fabricated_quote_case() -> None:
        data = complete_evaluation()
        data["book_scores"]["E1"]["evidence"][0]["quote"] = "存在しない引用"
        assert_has(review.validate(FIXTURE, data), "引用が実在しない")

    case("fabricated-quote", fabricated_quote_case)

    def non_prose_case() -> None:
        data = complete_evaluation()
        unit_id = data["structure"]["units"][1]["unit_id"]
        data["book_scores"]["E1"]["evidence"] = [presence(data, 25, "x = 1", unit_id, "prose")]
        assert_has(review.validate(FIXTURE, data), "region_kind不一致")

    case("non-prose-region-mismatch", non_prose_case)

    def undefined_key_case() -> None:
        data = complete_evaluation()
        data["model_states"] = [
            {
                "model_id": "toy",
                "introduced_at": {"line": 11, "quote": "最初の案"},
                "state_version": 1,
                "derives_from": ["missing@1"],
                "adds": [],
                "limits_found": [],
                "uses": [{"line": 22, "quote": "修正する"}],
            }
        ]
        assert_has(review.validate(FIXTURE, data), "未定義model key参照")

    case("undefined-model-key", undefined_key_case)

    def cycle_case() -> None:
        data = complete_evaluation()
        data["model_states"] = [
            {
                "model_id": "a", "introduced_at": {"line": 11, "quote": "最初の案"},
                "state_version": 1, "derives_from": ["b@1"], "adds": [], "limits_found": [], "uses": []
            },
            {
                "model_id": "b", "introduced_at": {"line": 13, "quote": "反例"},
                "state_version": 1, "derives_from": ["a@1"], "adds": [], "limits_found": [], "uses": []
            },
        ]
        assert_has(review.validate(FIXTURE, data), "循環")

    case("model-cycle", cycle_case)

    def use_before_definition_case() -> None:
        data = complete_evaluation()
        data["model_states"] = [
            {
                "model_id": "toy",
                "introduced_at": {"line": 22, "quote": "修正する"},
                "state_version": 1,
                "derives_from": [],
                "adds": [],
                "limits_found": [],
                "uses": [{"line": 11, "quote": "最初の案"}],
            }
        ]
        assert_has(review.validate(FIXTURE, data), "導入前使用")

    case("use-before-definition", use_before_definition_case)

    def structure_tamper_case() -> None:
        data = complete_evaluation()
        data["structure"]["units"].pop()
        assert_has(review.validate(FIXTURE, data), "structureがscaffold再計算結果と一致しない")

    case("unit-coverage-tamper", structure_tamper_case)

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{cases - len(failures)}/{cases} 件が一致")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
