#!/usr/bin/env python3
"""`scripts/review_corpus.py` の凍結・分類・昇格ゲートの検査。

重点は「resolved だけを取り込むか」と「人の承認なしに昇格できないか」。

    python3 scripts/tests/run_corpus_tests.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import comments as C  # noqa: E402
import review_corpus as R  # noqa: E402

BOOK = """# やる夫で学ぶ何か

## 第1幕　入口

**やる夫**：
　電荷は漏れるお。

**やらない夫**：
　書き戻せばいい。
"""


def write_comment(book: str, comment_id: str, status: str, body: str) -> None:
    path = C.COMMENTS_DIR / book / f"{comment_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    comment = C.Comment(
        id=comment_id,
        book=book,
        part=0,
        kind="substance",
        unit="sentence",
        status=status,
        created="2026-08-01T00:00:00+00:00",
        anchor=C.Anchor(heading="第1幕　入口", heading_level=2, heading_path=["第1幕　入口"], quote="電荷は漏れるお"),
        body=body,
        answer="直した。",
        answered="2026-08-02T00:00:00+00:00",
    )
    path.write_text(comment.render(schema=C.COMMENT_SCHEMA, revision=1), encoding="utf-8")


def make_pattern(pattern_id: str, **front: str) -> None:
    R.PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    path = R.PATTERNS_DIR / f"{pattern_id}.md"
    path.write_text(
        R.PATTERN_TEMPLATE.format(schema=R.PATTERN_SCHEMA, pattern_id=pattern_id), encoding="utf-8"
    )
    if front:
        loaded = R.load_patterns()
        target = next(pattern for pattern in loaded if pattern.id == pattern_id)
        target.front.update(front)
        path.write_text(R._render(target.front, target.body), encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    cases = 0

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        C.COMMENTS_DIR = root / "comments"
        C.BOOKS_DIR = root / "docs" / "books"
        R.CORPUS_DIR = root / "review-corpus"
        R.RECORDS_DIR = R.CORPUS_DIR / "records"
        R.PATTERNS_DIR = R.CORPUS_DIR / "patterns"

        for book in ("book-a", "book-b"):
            (C.BOOKS_DIR / book).mkdir(parents=True, exist_ok=True)
            (C.BOOKS_DIR / book / "README.md").write_text(BOOK, encoding="utf-8")

        write_comment("book-a", "0001", "resolved", "教師が答えを先に言っている。")
        write_comment("book-a", "0002", "resolved", "ここも同じで、問いの前に答えが出ている。")
        write_comment("book-a", "0003", "answered", "まだ人が確認していない。")
        write_comment("book-a", "0004", "stale", "位置を見失った。")
        write_comment("book-b", "0001", "resolved", "問いの前に答えが漏れている。")

        cases += 1
        added, skipped = R.harvest(None, False)
        if added != 3 or skipped != 0:
            failures.append(f"harvest: resolved 3件のはずが added={added} skipped={skipped}")
        if (R.RECORDS_DIR / "book-a" / "0003.md").exists():
            failures.append("harvest: answered 止まりを取り込んでしまった")
        if (R.RECORDS_DIR / "book-a" / "0004.md").exists():
            failures.append("harvest: stale を取り込んでしまった")

        cases += 1
        added, skipped = R.harvest(None, False)
        if added != 0 or skipped != 3:
            failures.append(f"harvest 再実行: 冪等でない added={added} skipped={skipped}")

        cases += 1
        make_pattern("answer-before-question")
        R.label("book-a/0001", ["answer-before-question"], False)
        R.label("book-a/0002", ["answer-before-question"], False)
        # 分類は harvest --force で消えない（人の作業を上書きしない）。
        R.harvest(None, True)
        if R.find_record("book-a/0001").patterns != ["answer-before-question"]:
            failures.append("harvest --force: 付けたパターンを消してしまった")

        cases += 1
        report = R.check()
        warnings = [message for level, message in report.findings if level == "warning"]
        if report.errors():
            failures.append(f"ゲート未達で error が出た: {report.findings}")
        if warnings:
            failures.append(f"2件・1冊でゲート到達の warning が出た: {warnings}")

        cases += 1
        R.label("book-b/0001", ["answer-before-question"], False)
        report = R.check()
        warnings = [message for level, message in report.findings if level == "warning"]
        if report.errors():
            failures.append(f"ゲート到達で error が出た: {report.findings}")
        if not warnings:
            failures.append("3件・2冊でゲートに到達したのに、承認待ちの warning が出ない")

        cases += 1
        make_pattern(
            "answer-before-question",
            status="promoted",
            approved_by="",
            promoted_to="rediscovery",
        )
        R.label("book-a/0001", ["answer-before-question"], False)
        R.label("book-a/0002", ["answer-before-question"], False)
        R.label("book-b/0001", ["answer-before-question"], False)
        report = R.check()
        if not any("approved_by" in message for _, message in report.findings):
            failures.append("承認なしの昇格を通してしまった")

        cases += 1
        make_pattern(
            "answer-before-question",
            status="promoted",
            approved_by="reki",
            promoted_to="rediscovery",
        )
        R.label("book-a/0001", ["answer-before-question"], False)
        R.label("book-a/0002", ["answer-before-question"], False)
        R.label("book-b/0001", ["answer-before-question"], False)
        report = R.check()
        if report.errors():
            failures.append(f"正当な昇格が通らない: {report.findings}")

        cases += 1
        make_pattern("thin-pattern", status="promoted", approved_by="reki", promoted_to="lint:foo")
        R.label("book-a/0001", ["thin-pattern"], False)
        report = R.check()
        if not any("ゲートを満たしていない" in message for _, message in report.findings):
            failures.append("1件だけのパターンを昇格させてしまった")

        cases += 1
        R.label("book-a/0001", ["thin-pattern"], True)
        record = R.find_record("book-a/0001")
        if "thin-pattern" in record.patterns:
            failures.append("label --remove が効いていない")

        cases += 1
        R.label("book-a/0002", ["thin-pattern"], False)
        (R.PATTERNS_DIR / "thin-pattern.md").unlink()
        report = R.check()
        if not any("未定義のパターン" in message or "が無いのに" in message for _, message in report.findings):
            failures.append("パターン票が消えた参照を検出できていない")

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{cases} 件中 {cases - len(failures)} 件成功")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
