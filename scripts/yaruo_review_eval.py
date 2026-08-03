#!/usr/bin/env python3
"""エンタメ学習教材の評価票をscaffold・検証するpilot用CLI。

意味判断やLLM呼び出しは行わない。Markdown構造、引用の実在、評価単位の
カバレッジ、model_stateの参照順だけを機械的に確定する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from yaruo_markdown import (
    bodies_of,
    is_speaker_line,
    non_prose_lines,
    speaker_names,
)

SCHEMA_VERSION = "0.1.0-pilot"
UNIT_POLICY = "section-or-bare-act-v1"
BOOK_AXES = ("E1", "E2", "E3", "L1", "L2", "L3", "S1")
UNIT_AXES = ("E1", "E3", "L1", "L2", "L3", "S1")
META_ACT_PREFIXES = ("登場人物", "参考文献", "参考資料", "次に読む")
META_ACT_CONTAINS = ("索引",)
NARRATIVE_ACT = re.compile(
    r"^(?:第[0-9０-９]+幕|序幕|終幕|最終幕|幕間|プロローグ|エピローグ)"
)
H2 = re.compile(r"^##\s+(?!#)(.+?)\s*$")
H3 = re.compile(r"^###\s+(?!#)(.+?)\s*$")


def source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible_text(value: str) -> str:
    """引用照合用の保守的なMarkdown正規化。"""
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"(?<!\\)(?:\*\*|__|`)", "", value)
    value = re.sub(r"\\([\\`*_{}\[\]()#+.!|])", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def _protected_kinds(lines: list[str]) -> dict[int, str]:
    """non_prose_linesを正本として、保護行をmath/codeへ分類する。"""
    protected = non_prose_lines(lines)
    kinds: dict[int, str] = {}
    in_fence = False
    in_math = False
    for index, raw in enumerate(lines):
        if index not in protected:
            continue
        body = raw.rstrip("\r\n")
        stripped = body.lstrip("　 \t")
        if in_fence:
            kinds[index] = "code"
            if stripped.startswith("```"):
                in_fence = False
            continue
        if in_math:
            kinds[index] = "math"
            if body.count("$$") % 2 == 1:
                in_math = False
            continue
        if stripped.startswith("```"):
            kinds[index] = "code"
            in_fence = True
        else:
            kinds[index] = "math"
            if body.count("$$") % 2 == 1:
                in_math = True
    return kinds


def line_region_kinds(lines: list[str]) -> list[str]:
    names = speaker_names(lines)
    protected = _protected_kinds(lines)
    regions: list[str] = []
    for index, body in enumerate(bodies_of(lines)):
        if index in protected:
            regions.append(protected[index])
        elif is_speaker_line(body, names):
            regions.append("speaker_label")
        elif re.match(r"^#{1,6}\s+", body):
            regions.append("heading")
        elif body.lstrip().startswith("|"):
            regions.append("table")
        elif not body.strip() or body == "---":
            regions.append("other")
        else:
            regions.append("prose")
    return regions


def _is_meta_act(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title)
    if any(normalized.startswith(prefix) for prefix in META_ACT_PREFIXES):
        return True
    if any(fragment in normalized for fragment in META_ACT_CONTAINS):
        return True
    end_marker = re.sub(r"[*_`\-―—─ー]", "", normalized)
    return end_marker in {"完", "終", "おわり", "終わり"}


def _is_narrative_act(title: str) -> bool:
    normalized = re.sub(r"^[\s*_`\-―—─ー]+", "", title)
    return bool(NARRATIVE_ACT.match(normalized))


def _char_count(lines: list[str], start_line: int, end_line: int) -> int:
    return sum(len(line.rstrip("\r\n")) for line in lines[start_line - 1 : end_line])


def _sample_indices(book_id: str, count: int) -> list[int]:
    if count <= 4:
        return list(range(count))
    selected = {0, count // 2, count - 1}
    candidate = int(hashlib.sha256(book_id.encode("utf-8")).hexdigest(), 16) % count
    while candidate in selected:
        candidate = (candidate + 1) % count
    selected.add(candidate)
    return sorted(selected)


def build_structure(path: Path, lines: list[str]) -> dict[str, Any]:
    protected = non_prose_lines(lines)
    headings: list[tuple[int, str]] = []
    for index, raw in enumerate(lines, start=1):
        if index - 1 in protected:
            continue
        if match := H2.match(raw.rstrip("\r\n")):
            headings.append((index, match.group(1)))

    acts: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    evaluated_intervals: list[tuple[int, int]] = []
    meta_intervals: list[tuple[int, int, str]] = []
    act_number = 0

    for heading_index, (start, title) in enumerate(headings):
        end = headings[heading_index + 1][0] - 1 if heading_index + 1 < len(headings) else len(lines)
        if _is_meta_act(title) or not _is_narrative_act(title):
            reason = "meta-act" if _is_meta_act(title) else "non-act-h2"
            meta_intervals.append((start, end, f"{reason}:{title}"))
            continue

        act_number += 1
        act_id = f"act-{act_number:02d}"
        h3s: list[tuple[int, str]] = []
        for line_number in range(start + 1, end + 1):
            if line_number - 1 in protected:
                continue
            if match := H3.match(lines[line_number - 1].rstrip("\r\n")):
                h3s.append((line_number, match.group(1)))
        acts.append(
            {
                "act_id": act_id,
                "title": title,
                "start_line": start,
                "end_line": end,
                "section_count": len(h3s),
                "subdivided": bool(h3s),
            }
        )

        if not h3s:
            units.append(
                {
                    "unit_id": f"{act_id}.bare",
                    "unit_kind": "bare_act",
                    "act_id": act_id,
                    "act_title": title,
                    "title": title,
                    "start_line": start,
                    "end_line": end,
                    "char_count": _char_count(lines, start, end),
                    "sampled": False,
                }
            )
            evaluated_intervals.append((start, end))
            continue

        for section_index, (section_start, section_title) in enumerate(h3s):
            # 幕見出し直後の前置きも最初のsectionへ含め、本文行を取りこぼさない。
            unit_start = start if section_index == 0 else section_start
            unit_end = h3s[section_index + 1][0] - 1 if section_index + 1 < len(h3s) else end
            units.append(
                {
                    "unit_id": f"{act_id}.section-{section_index + 1:02d}",
                    "unit_kind": "section",
                    "act_id": act_id,
                    "act_title": title,
                    "title": section_title,
                    "start_line": unit_start,
                    "end_line": unit_end,
                    "char_count": _char_count(lines, unit_start, unit_end),
                    "sampled": False,
                }
            )
            evaluated_intervals.append((unit_start, unit_end))

    sample_indices = _sample_indices(path.parent.name, len(units))
    sampled_ids = [units[index]["unit_id"] for index in sample_indices]
    for index in sample_indices:
        units[index]["sampled"] = True

    ownership: list[str | None] = [None] * len(lines)
    for start, end in evaluated_intervals:
        for index in range(start - 1, end):
            if ownership[index] is not None:
                raise ValueError(f"評価単位が重複している: line {index + 1}")
            ownership[index] = "unit"

    meta_by_line: dict[int, str] = {}
    for start, end, reason in meta_intervals:
        for line_number in range(start, end + 1):
            meta_by_line[line_number] = reason

    excluded: list[dict[str, Any]] = []
    start: int | None = None
    reason: str | None = None
    for line_number, owner in enumerate(ownership, start=1):
        current = None if owner == "unit" else meta_by_line.get(line_number, "front-matter-or-unscoped")
        if current != reason:
            if reason is not None and start is not None:
                excluded.append({"start_line": start, "end_line": line_number - 1, "reason": reason})
            start = line_number if current is not None else None
            reason = current
    if reason is not None and start is not None:
        excluded.append({"start_line": start, "end_line": len(lines), "reason": reason})

    subdivided = sum(1 for act in acts if act["subdivided"])
    return {
        "unit_policy": UNIT_POLICY,
        "line_count": len(lines),
        "act_count": len(acts),
        "subdivided_act_count": subdivided,
        "subdivision_rate": subdivided / len(acts) if acts else 0.0,
        "acts": acts,
        "units": units,
        "excluded_ranges": excluded,
        "sampled_unit_ids": sampled_ids,
    }


def empty_score() -> dict[str, Any]:
    return {
        "value": None,
        "confidence": None,
        "evidence": [],
        "absence_evidence": [],
        "defect_types": [],
        "rationale": "",
    }


def empty_ledger(unit_id: str) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "section_role": None,
        "problem": [],
        "attempt": [],
        "friction": [],
        "diagnosis": [],
        "revision": [],
        "test": [],
        "affect": {"before": None, "after": None, "intensity_delta": None, "evidence": []},
        "initiative": {"opens": None, "turns": None, "closes": None, "evidence": []},
        "enrichment": [],
        "hook": {"next_question": None, "partial_disclosure": None, "evidence": []},
        "notes": [],
    }


def scaffold(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as source:
        lines = source.readlines()
    structure = build_structure(path, lines)
    return {
        "schema_version": SCHEMA_VERSION,
        "document_kind": "evaluation",
        "book_id": path.parent.name,
        "source_path": str(path),
        "source_sha256": source_sha256(path),
        "evaluator": {
            "name": "other",
            "model": "",
            "rubric_author": False,
            "evaluated_at": None,
            "mode": "pilot",
        },
        "structure": structure,
        "core_concepts": [],
        "book_scores": {axis: empty_score() for axis in BOOK_AXES},
        "unit_ledgers": [empty_ledger(unit["unit_id"]) for unit in structure["units"]],
        "unit_scores": [
            {
                "unit_id": unit_id,
                "scores": {axis: empty_score() for axis in UNIT_AXES},
                "notes": [],
            }
            for unit_id in structure["sampled_unit_ids"]
        ],
        "gates": [],
        "dull_runs": [],
        "model_states": [],
        "notes": [],
    }


def _iter_evidence(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if "claim_type" in value:
            yield value
        for child in value.values():
            yield from _iter_evidence(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_evidence(child)


def _validate_evidence(
    evidence: dict[str, Any], lines: list[str], regions: list[str], unit_ids: set[str], label: str
) -> list[str]:
    errors: list[str] = []
    required = {"claim_type", "line", "quote", "region_kind", "scope", "compared_lines", "expected", "note"}
    missing = required - evidence.keys()
    if missing:
        return [f"{label}: evidence必須項目がない: {sorted(missing)}"]
    claim_type = evidence["claim_type"]
    if claim_type not in {"presence", "absence", "comparison", "sequence"}:
        errors.append(f"{label}: 不明なclaim_type: {claim_type}")
        return errors

    line_number = evidence["line"]
    if claim_type == "presence":
        if not isinstance(line_number, int) or not 1 <= line_number <= len(lines):
            errors.append(f"{label}: presence.lineが本文範囲外: {line_number}")
        else:
            quote = evidence["quote"]
            if not isinstance(quote, str) or not visible_text(quote):
                errors.append(f"{label}: presence.quoteが空")
            elif visible_text(quote) not in visible_text(lines[line_number - 1]):
                errors.append(f"{label}: line {line_number} に引用が実在しない: {quote!r}")
            expected_region = evidence["region_kind"]
            actual_region = regions[line_number - 1]
            if expected_region != actual_region:
                errors.append(
                    f"{label}: line {line_number} のregion_kind不一致: "
                    f"票={expected_region!r}, 本文={actual_region!r}"
                )
    elif claim_type == "absence":
        if not evidence.get("scope") or not evidence.get("expected"):
            errors.append(f"{label}: absenceにはscopeとexpectedが必要")
    elif claim_type == "comparison":
        if not evidence.get("scope") or len(evidence.get("compared_lines", [])) < 2:
            errors.append(f"{label}: comparisonにはscopeと2行以上のcompared_linesが必要")
    elif claim_type == "sequence":
        scope = evidence.get("scope") or {}
        if len(scope.get("unit_ids", [])) < 2:
            errors.append(f"{label}: sequenceには2単位以上のscope.unit_idsが必要")

    scope = evidence.get("scope")
    if scope is not None:
        start = scope.get("start_line")
        end = scope.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int) or not (1 <= start <= end <= len(lines)):
            errors.append(f"{label}: scope行範囲が不正: {start}-{end}")
        for unit_id in scope.get("unit_ids", []):
            if unit_id not in unit_ids:
                errors.append(f"{label}: scopeが未定義unitを参照: {unit_id}")
        if isinstance(line_number, int) and isinstance(start, int) and isinstance(end, int):
            if not start <= line_number <= end:
                errors.append(f"{label}: evidence.lineがscope外: {line_number} not in {start}-{end}")
    for compared in evidence.get("compared_lines", []):
        if not isinstance(compared, int) or not 1 <= compared <= len(lines):
            errors.append(f"{label}: compared_linesが本文範囲外: {compared}")
    return errors


def _validate_model_states(data: dict[str, Any], lines: list[str]) -> list[str]:
    errors: list[str] = []
    states = data.get("model_states", [])
    nodes: dict[str, dict[str, Any]] = {}
    for index, state in enumerate(states):
        try:
            key = f"{state['model_id']}@{state['state_version']}"
        except KeyError as exc:
            errors.append(f"model_states[{index}]: 必須項目がない: {exc.args[0]}")
            continue
        if key in nodes:
            errors.append(f"model_stateが重複: {key}")
        nodes[key] = state

    graph: dict[str, list[str]] = {key: [] for key in nodes}
    for key, state in nodes.items():
        introduced = state.get("introduced_at", {})
        intro_line = introduced.get("line")
        intro_quote = introduced.get("quote")
        if not isinstance(intro_line, int) or not 1 <= intro_line <= len(lines):
            errors.append(f"{key}: introduced_at.lineが本文範囲外")
        elif not isinstance(intro_quote, str) or visible_text(intro_quote) not in visible_text(lines[intro_line - 1]):
            errors.append(f"{key}: introduced_at.quoteが本文に実在しない")
        for parent in state.get("derives_from", []):
            if parent not in nodes:
                errors.append(f"{key}: 未定義model key参照: {parent}")
            else:
                graph[key].append(parent)
        for use in state.get("uses", []):
            line_number = use.get("line")
            quote = use.get("quote")
            if not isinstance(line_number, int) or not 1 <= line_number <= len(lines):
                errors.append(f"{key}: uses.lineが本文範囲外: {line_number}")
            else:
                if isinstance(intro_line, int) and line_number < intro_line:
                    errors.append(f"{key}: 導入前使用: use={line_number}, introduced={intro_line}")
                if not isinstance(quote, str) or visible_text(quote) not in visible_text(lines[line_number - 1]):
                    errors.append(f"{key}: uses.quoteが本文に実在しない: line {line_number}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"model_stateに循環がある: {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, []):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)

    by_model: dict[str, list[int]] = {}
    for state in states:
        if "model_id" in state and isinstance(state.get("state_version"), int):
            by_model.setdefault(state["model_id"], []).append(state["state_version"])
    for model_id, versions in by_model.items():
        ordered = sorted(set(versions))
        if ordered != list(range(1, max(ordered) + 1)):
            errors.append(f"{model_id}: state_versionが非連続: {ordered}")
    return errors


def validate(path: Path, data: dict[str, Any], *, allow_incomplete: bool = False) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as source:
        lines = source.readlines()
    errors: list[str] = []
    for key in (
        "schema_version", "document_kind", "book_id", "source_path", "source_sha256",
        "evaluator", "structure", "core_concepts", "book_scores", "unit_ledgers", "unit_scores",
        "gates", "dull_runs", "model_states", "notes",
    ):
        if key not in data:
            errors.append(f"top-level必須項目がない: {key}")
    if errors:
        return errors
    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version不一致: {data['schema_version']!r}")
    if data["document_kind"] != "evaluation":
        errors.append(f"document_kind不一致: {data['document_kind']!r}")
    if data["book_id"] != path.parent.name:
        errors.append(f"book_id不一致: {data['book_id']!r} != {path.parent.name!r}")
    if data["source_sha256"] != source_sha256(path):
        errors.append("source_sha256が現在の本文と一致しない")

    expected_structure = build_structure(path, lines)
    if data["structure"] != expected_structure:
        errors.append("structureがscaffold再計算結果と一致しない（単位の欠落・重複・改変）")
    unit_ids = {unit["unit_id"] for unit in expected_structure["units"]}
    sampled_ids = set(expected_structure["sampled_unit_ids"])
    regions = line_region_kinds(lines)

    for index, evidence in enumerate(_iter_evidence(data)):
        errors.extend(_validate_evidence(evidence, lines, regions, unit_ids, f"evidence[{index}]"))

    if not allow_incomplete:
        evaluator = data["evaluator"]
        if not evaluator.get("model") or not evaluator.get("evaluated_at"):
            errors.append("completed票にはevaluator.model/evaluated_atが必要")
        if not data["core_concepts"]:
            errors.append("completed票には本文証拠付きcore_conceptsが必要")
        concept_ids: set[str] = set()
        for concept in data["core_concepts"]:
            concept_id = concept.get("concept_id")
            if not concept_id or concept_id in concept_ids:
                errors.append(f"core concept idが空または重複: {concept_id!r}")
            concept_ids.add(concept_id)
            if not concept.get("evidence"):
                errors.append(f"{concept_id}: inventory確定の本文証拠がない")
        actual_ledger_ids = [ledger.get("unit_id") for ledger in data["unit_ledgers"]]
        expected_ledger_ids = [unit["unit_id"] for unit in expected_structure["units"]]
        if actual_ledger_ids != expected_ledger_ids:
            errors.append(
                "unit_ledgersは全単位を本文順に1回ずつ含む必要がある: "
                f"expected={expected_ledger_ids}, actual={actual_ledger_ids}"
            )
        for ledger in data["unit_ledgers"]:
            if ledger.get("section_role") not in {
                "core_discovery", "setup", "test", "bridge", "reflection"
            }:
                errors.append(f"unit_ledgers[{ledger.get('unit_id')}]: section_roleが未確定")
        for axis in BOOK_AXES:
            score = data["book_scores"].get(axis)
            if not score or score.get("value") not in range(5):
                errors.append(f"book_scores.{axis}: 0..4の値が必要")
            elif not score.get("evidence") and not score.get("absence_evidence"):
                errors.append(f"book_scores.{axis}: 証拠がない")
        actual_unit_scores = {item.get("unit_id") for item in data["unit_scores"]}
        if actual_unit_scores != sampled_ids:
            errors.append(
                "unit_scoresはsampled_unit_idsと完全一致が必要: "
                f"expected={sorted(sampled_ids)}, actual={sorted(str(x) for x in actual_unit_scores)}"
            )
        for item in data["unit_scores"]:
            for axis in UNIT_AXES:
                score = item.get("scores", {}).get(axis)
                if not score or score.get("value") not in range(5):
                    errors.append(f"unit_scores[{item.get('unit_id')}].{axis}: 0..4の値が必要")
                elif not score.get("evidence") and not score.get("absence_evidence"):
                    errors.append(f"unit_scores[{item.get('unit_id')}].{axis}: 証拠がない")
        expected_gates = {(concept_id, axis) for concept_id in concept_ids for axis in ("L1", "L2")}
        actual_gates = {(gate.get("concept_id"), gate.get("axis")) for gate in data["gates"]}
        if actual_gates != expected_gates:
            errors.append(
                "gatesは各core conceptのL1/L2と完全一致が必要: "
                f"expected={sorted(expected_gates)}, actual={sorted(actual_gates)}"
            )

    errors.extend(_validate_model_states(data, lines))
    return errors


def _write_json(value: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        output.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold", help="評価JSONの雛形を生成")
    scaffold_parser.add_argument("source", type=Path)
    scaffold_parser.add_argument("--output", type=Path)

    validate_parser = subparsers.add_parser("validate", help="評価JSONを本文と照合")
    validate_parser.add_argument("source", type=Path)
    validate_parser.add_argument("evaluation", type=Path)
    validate_parser.add_argument("--allow-incomplete", action="store_true")

    args = parser.parse_args()
    if args.command == "scaffold":
        _write_json(scaffold(args.source), args.output)
        return 0

    data = json.loads(args.evaluation.read_text(encoding="utf-8"))
    errors = validate(args.source, data, allow_incomplete=args.allow_incomplete)
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"{len(errors)} error(s)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
