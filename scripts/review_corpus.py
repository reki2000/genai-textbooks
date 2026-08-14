#!/usr/bin/env python3
"""人間レビューを改善データとして蓄積し、再発防止ルールへ昇格させる。

`comments/` はローカルの作業用で `.gitignore` 済み、教材を直せば役目を終える。
そこで終わらせると、同じ指摘を何度でも受けることになる。

    人間コメント → AI修正 → 人間が resolved → review corpus
      → 類似のクラスタリング → 再発防止ルール候補 → 人間承認
      → lint / review skill / rediscovery skill へ昇格

このスクリプトが担うのは、**数えられる部分だけ**。

- `harvest`: `resolved` になったコメントだけを `review-corpus/records/` へ凍結する
- `label`:   記録へパターン名を付ける（クラスタリングの結果を書き戻す）
- `check`:   パターン票の必須欄と、昇格ゲートの成立を検査する
- `stats`:   未分類の件数、パターンごとの発生回数、昇格可能なパターンを出す

クラスタリングそのもの（どの指摘とどの指摘が同じ問題か）と、昇格先の判断は
人と `yaruo-retrospect` スキルが行う。**1件の指摘を直接スキルのルールへ
書き足さない。** 複数教材で繰り返し起きたものだけが一般則になる。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comments as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "review-corpus"
RECORDS_DIR = CORPUS_DIR / "records"
PATTERNS_DIR = CORPUS_DIR / "patterns"

RECORD_SCHEMA = "review-record/v1"
PATTERN_SCHEMA = "review-pattern/v1"

# 昇格ゲート。1教材で3回起きただけの問題は、その教材固有の癖かもしれない。
MIN_OCCURRENCES = 3
MIN_BOOKS = 2

PATTERN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PATTERN_STATUSES = ("candidate", "approved", "promoted", "rejected")
PROMOTION_TARGETS = ("lint", "review", "rediscovery", "checkpoint", "zuhan", "proofread")

REQUIRED_SECTIONS = ("症状", "なぜ学習上問題なのか", "推奨される修正")

_FRONTMATTER_RE = re.compile(r"\A---\n(?P<front>.*?)\n---\n?(?P<body>.*)\Z", re.DOTALL)


class CorpusError(ValueError):
    pass


# --------------------------------------------------------------------------
# 読み書き
# --------------------------------------------------------------------------


@dataclass
class Record:
    path: Path
    front: dict[str, Any]
    body: str

    @property
    def name(self) -> str:
        return f"{self.front.get('book')}/{self.front.get('comment')}"

    @property
    def book(self) -> str:
        return str(self.front.get("book", ""))

    @property
    def patterns(self) -> list[str]:
        return [str(item) for item in self.front.get("patterns") or []]


@dataclass
class Pattern:
    path: Path
    front: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return str(self.front.get("id", self.path.stem))

    @property
    def status(self) -> str:
        return str(self.front.get("status", "candidate"))


def _split(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise CorpusError("frontmatter が無い")
    front = yaml.safe_load(match.group("front")) or {}
    if not isinstance(front, dict):
        raise CorpusError("frontmatter がマッピングではない")
    return front, match.group("body")


def _render(front: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped}---\n\n{body.lstrip()}"


def load_records(book: str | None = None) -> list[Record]:
    records: list[Record] = []
    if not RECORDS_DIR.exists():
        return records
    for path in sorted(RECORDS_DIR.glob("*/*.md")):
        if path.name == "README.md":
            continue
        if book and path.parent.name != book:
            continue
        front, body = _split(path.read_text(encoding="utf-8"))
        records.append(Record(path, front, body))
    return records


def load_patterns() -> list[Pattern]:
    patterns: list[Pattern] = []
    if not PATTERNS_DIR.exists():
        return patterns
    for path in sorted(PATTERNS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        front, body = _split(path.read_text(encoding="utf-8"))
        patterns.append(Pattern(path, front, body))
    return patterns


def find_record(name: str) -> Record:
    if "/" not in name:
        raise CorpusError(f"記録は book/id で指定する: {name}")
    book, comment_id = name.split("/", 1)
    path = RECORDS_DIR / book / f"{comment_id}.md"
    if not path.exists():
        raise CorpusError(f"記録が無い: {path}")
    front, body = _split(path.read_text(encoding="utf-8"))
    return Record(path, front, body)


# --------------------------------------------------------------------------
# harvest
# --------------------------------------------------------------------------


def _thread_body(comment: C.Comment) -> str:
    parts: list[str] = []
    user_count = 0
    for message in comment.messages():
        if message.role == "user":
            user_count += 1
            label = "指摘" if user_count == 1 else "追加指摘"
        else:
            label = "対応"
        parts.append(f"## {label}\n\n{message.body.strip()}\n")
    return "\n".join(parts)


def harvest(book: str | None, force: bool) -> tuple[int, int]:
    """resolved のコメントだけを記録へ凍結する。戻り値は (新規, 既存)。"""
    added = 0
    skipped = 0
    for comment in C.load_comments(book):
        # 人が確認して閉じたものだけを高品質な改善データとみなす。
        # answered 止まりは「AI がそう主張している」に過ぎない。
        if comment.status != "resolved":
            continue
        path = RECORDS_DIR / comment.book / f"{comment.id}.md"
        if path.exists() and not force:
            skipped += 1
            continue
        existing_patterns: list[str] = []
        if path.exists():
            existing_patterns = Record(path, *_split(path.read_text(encoding="utf-8"))).patterns
        front = {
            "type": "review-record",
            "schema": RECORD_SCHEMA,
            "book": comment.book,
            "comment": comment.id,
            "kind": comment.kind,
            "unit": comment.unit,
            "created": comment.created,
            "answered": comment.answered,
            "heading_path": list(comment.anchor.heading_path or []),
            "quote": comment.anchor.quote,
            "patterns": existing_patterns,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(front, _thread_body(comment)), encoding="utf-8")
        added += 1
    return added, skipped


# --------------------------------------------------------------------------
# label
# --------------------------------------------------------------------------


def label(name: str, patterns: Iterable[str], remove: bool) -> list[str]:
    record = find_record(name)
    current = list(record.patterns)
    for pattern in patterns:
        if not PATTERN_ID_RE.match(pattern):
            raise CorpusError(f"パターン名は英小文字とハイフン: {pattern}")
        if remove:
            if pattern in current:
                current.remove(pattern)
        elif pattern not in current:
            current.append(pattern)
    record.front["patterns"] = current
    record.path.write_text(_render(record.front, record.body), encoding="utf-8")
    return current


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


@dataclass
class Report:
    findings: list[tuple[str, str]] = field(default_factory=list)

    def add(self, level: str, message: str) -> None:
        self.findings.append((level, message))

    def errors(self) -> int:
        return sum(1 for level, _ in self.findings if level == "error")


def occurrences(records: list[Record]) -> dict[str, list[Record]]:
    grouped: dict[str, list[Record]] = {}
    for record in records:
        for pattern in record.patterns:
            grouped.setdefault(pattern, []).append(record)
    return grouped


def gate(pattern_records: list[Record]) -> tuple[bool, str]:
    books = {record.book for record in pattern_records}
    if len(pattern_records) < MIN_OCCURRENCES:
        return False, f"発生 {len(pattern_records)}件（必要 {MIN_OCCURRENCES}件）"
    if len(books) < MIN_BOOKS:
        return False, f"教材 {len(books)}冊（必要 {MIN_BOOKS}冊）"
    return True, f"発生 {len(pattern_records)}件・教材 {len(books)}冊"


def check() -> Report:
    report = Report()
    records = load_records()
    patterns = load_patterns()
    known = {pattern.id for pattern in patterns}
    grouped = occurrences(records)

    for record in records:
        if record.front.get("schema") != RECORD_SCHEMA:
            report.add("error", f"{record.name}: schema が {RECORD_SCHEMA} でない")
        for pattern in record.patterns:
            if pattern not in known:
                report.add("error", f"{record.name}: 未定義のパターン {pattern}")

    for pattern in patterns:
        where = pattern.path.name
        if not PATTERN_ID_RE.match(pattern.id):
            report.add("error", f"{where}: パターン名は英小文字とハイフン")
        if pattern.id != pattern.path.stem:
            report.add("error", f"{where}: id とファイル名が違う")
        if pattern.front.get("schema") != PATTERN_SCHEMA:
            report.add("error", f"{where}: schema が {PATTERN_SCHEMA} でない")
        if pattern.status not in PATTERN_STATUSES:
            report.add("error", f"{where}: status は {'／'.join(PATTERN_STATUSES)} のいずれか")
        for section in REQUIRED_SECTIONS:
            if f"## {section}" not in pattern.body:
                report.add("error", f"{where}: 必須の節が無い（## {section}）")

        pattern_records = grouped.get(pattern.id, [])
        if not pattern_records and pattern.status != "rejected":
            report.add("error", f"{where}: 実例が1件も紐づいていない")

        approved = str(pattern.front.get("approved_by") or "").strip()
        passed, detail = gate(pattern_records)

        if pattern.status == "promoted":
            if not passed:
                report.add("error", f"{where}: 昇格済みだがゲートを満たしていない（{detail}）")
            if not approved:
                report.add("error", f"{where}: 昇格済みだが approved_by が空（人の承認が要る）")
            target = str(pattern.front.get("promoted_to") or "").strip()
            if not target:
                report.add("error", f"{where}: promoted_to が空")
            elif target.split(":", 1)[0] not in PROMOTION_TARGETS:
                report.add(
                    "error",
                    f"{where}: promoted_to の宛先が不正（{'／'.join(PROMOTION_TARGETS)}）",
                )
        elif pattern.status == "approved" and not approved:
            report.add("error", f"{where}: approved だが approved_by が空")
        elif pattern.status == "candidate" and passed and not approved:
            report.add("warning", f"{where}: ゲートを満たした（{detail}）。人の承認を待っている")

    for pattern_id, pattern_records in sorted(grouped.items()):
        if pattern_id not in known:
            report.add(
                "error",
                f"patterns/{pattern_id}.md が無いのに {len(pattern_records)}件が参照している",
            )
    return report


def stats() -> str:
    records = load_records()
    patterns = {pattern.id: pattern for pattern in load_patterns()}
    grouped = occurrences(records)
    unlabeled = [record for record in records if not record.patterns]

    lines = [f"記録 {len(records)}件（未分類 {len(unlabeled)}件）／パターン {len(patterns)}件", ""]
    if grouped:
        lines.append("パターン           状態        発生  教材  ゲート")
        for pattern_id, pattern_records in sorted(
            grouped.items(), key=lambda item: (-len(item[1]), item[0])
        ):
            books = {record.book for record in pattern_records}
            passed, _ = gate(pattern_records)
            status = patterns[pattern_id].status if pattern_id in patterns else "未定義"
            lines.append(
                f"{pattern_id:<18} {status:<10} {len(pattern_records):>4}  {len(books):>4}  "
                f"{'可' if passed else '—'}"
            )
        lines.append("")
    if unlabeled:
        lines.append("未分類の記録：")
        lines.extend(f"  {record.name}" for record in unlabeled)
    return "\n".join(lines).rstrip() + "\n"


PATTERN_TEMPLATE = """\
---
type: review-pattern
schema: {schema}
id: {pattern_id}
status: candidate
approved_by: ''
promoted_to: ''
---

# {pattern_id}

## 症状

（本文に何が起きているか。読者が何を見るか）

## なぜ学習上問題なのか

（面白くない、ではなく、どの理解が損なわれるか）

## 推奨される修正

（執筆時に何をすれば防げるか。修正時に何を足すか）

## 実例

（`review_corpus.py label` で記録へ紐づける。発生回数はそこから数える）
"""


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    harvest_parser = sub.add_parser("harvest", help="resolved のコメントを記録へ凍結する")
    harvest_parser.add_argument("--book", help="対象教材を絞る")
    harvest_parser.add_argument("--force", action="store_true", help="既存の記録を上書きする")

    label_parser = sub.add_parser("label", help="記録へパターン名を付ける")
    label_parser.add_argument("record", help="book/id")
    label_parser.add_argument("patterns", nargs="+")
    label_parser.add_argument("--remove", action="store_true", help="付け外す")

    new_parser = sub.add_parser("new-pattern", help="パターン票の雛形を作る")
    new_parser.add_argument("pattern_id")

    sub.add_parser("check", help="パターン票と昇格ゲートを検査する")
    sub.add_parser("stats", help="発生回数と昇格可能なパターンを出す")

    list_parser = sub.add_parser("list", help="記録を一覧する")
    list_parser.add_argument("--unlabeled", action="store_true", help="未分類だけ")
    list_parser.add_argument("--pattern", help="そのパターンが付いた記録だけ")

    args = parser.parse_args()

    try:
        if args.command == "harvest":
            added, skipped = harvest(args.book, args.force)
            print(f"記録 {added}件を追加、{skipped}件は既存のまま")
            return 0

        if args.command == "label":
            current = label(args.record, args.patterns, args.remove)
            print(f"{args.record}: {'、'.join(current) if current else '（未分類）'}")
            return 0

        if args.command == "new-pattern":
            if not PATTERN_ID_RE.match(args.pattern_id):
                raise CorpusError("パターン名は英小文字とハイフン")
            path = PATTERNS_DIR / f"{args.pattern_id}.md"
            if path.exists():
                raise CorpusError(f"すでにある: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                PATTERN_TEMPLATE.format(schema=PATTERN_SCHEMA, pattern_id=args.pattern_id),
                encoding="utf-8",
            )
            print(f"作成した: {path}")
            return 0

        if args.command == "check":
            report = check()
            for level, message in report.findings:
                print(f"{level}: {message}")
            print(f"error {report.errors()}件、warning {len(report.findings) - report.errors()}件")
            return 1 if report.errors() else 0

        if args.command == "stats":
            sys.stdout.write(stats())
            return 0

        if args.command == "list":
            for record in load_records():
                if args.unlabeled and record.patterns:
                    continue
                if args.pattern and args.pattern not in record.patterns:
                    continue
                labels = "、".join(record.patterns) or "（未分類）"
                print(f"{record.name}\t{labels}")
            return 0
    except CorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
