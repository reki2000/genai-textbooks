#!/usr/bin/env python3
"""Narrow やる夫式教材 down to the handful of places where an out-of-place
metaphor could be hiding, so the model never has to read a whole book.

The observation this rests on: a metaphor vehicle that feels abrupt is almost
always a word that belongs to no other book in the corpus. `封筒` and
`パスポート` in docs/books/asset-management both occur in that book and nowhere
else among the 30. Genuine domain terms share that property (`債券`, `証拠金`),
so the cross-book document frequency cannot separate the two on its own -- but
it does cut a book's vocabulary down to a list small enough to hand to a model
as a plain word list, with no body text attached.

Three subcommands, matching the three stages of the funnel:

    candidates  per-book word lists (stage 1, this script alone)
    context     body text around the words a model flagged (stage 3)
    markers     lines carrying an explicit simile marker (complementary pass)

Standard library only; PyYAML is used for book titles when available.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "docs" / "catalog.yaml").is_file():
            return candidate
    raise RuntimeError("could not find repository root containing docs/catalog.yaml")


ROOT = find_repo_root()
BOOKS_DIR = ROOT / "docs" / "books"
CATALOG_PATH = ROOT / "docs" / "catalog.yaml"

# Max-recall defaults: every term of the book, as long as it is near-absent
# from the rest of the corpus. Tightening these trades recall for tokens.
DEFAULT_MIN_COUNT = 1
DEFAULT_MAX_DF = 3

# Katakana runs of 3+, and kanji runs. Hiragana-only words are skipped: a
# metaphor vehicle is a concrete noun, and those are written in kanji or
# katakana. Kanji runs longer than 4 are emitted whole *and* chopped, so a long
# compound does not swallow a short word sitting inside it.
KATAKANA_RUN = re.compile(r"[ァ-ヴ][ァ-ヴー]{2,}")
KANJI_RUN = re.compile(r"[一-龥]{2,}")
KANJI_CHUNK = re.compile(r"[一-龥]{2,4}")

# Terms that are just a number and a counter carry no metaphor. Dropping them
# is the one place this script filters on meaning rather than distribution.
NUMERIC_CHARS = set("一二三四五六七八九十百千万億兆零半")
COUNTER_CHARS = set("年月日時分秒個人回目番号台本冊件割倍歩段層次代世紀間中前後")

# Speaker labels and the character roster are structure, not vocabulary.
SPEAKER_LINE = re.compile(r"^\*\*[^*]+\*\*(?:（[^）]*）)?：")

SIMILE_MARKER = re.compile(
    r"のようなもの|みたいなもの|のような話|に例え|にたとえ|例えると|喩え"
    r"|見立て|いわば|に似てい|と同じ(?:こと|だ|よう|で)|イメージすると"
    r"|置き換えると|に相当する|だと思え|と思えばいい"
)

# Used in stage 3 to tell "introduced properly" from "dropped in cold".
INTRO_MARKER = re.compile(
    r"とは|というのは|つまり|すなわち|に例え|にたとえ|例えると|見立て|いわば"
    r"|のようなもの|みたいなもの|と呼ぶ|と呼ぼう|名付け|定義"
)


def strip_noise(text: str) -> str:
    """Remove regions whose vocabulary says nothing about the prose.

    Bibliographies are the important one: 19 of the 30 books carry a 参考文献
    section, and its proper nouns are all corpus-unique, so leaving them in
    would bury the real candidates.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", "", text, flags=re.S)
    text = re.sub(r"\$[^$\n]*\$", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"^#{1,6}\s*参考文献.*", "", text, flags=re.S | re.M)
    text = re.sub(r"^#{1,6}\s*登場人物.*?(?=^#{1,6}\s)", "", text, flags=re.S | re.M)
    text = SPEAKER_LINE.sub("", text)
    return text


def is_numeric_noise(term: str) -> bool:
    if not any(c in NUMERIC_CHARS for c in term):
        return False
    return all(c in NUMERIC_CHARS or c in COUNTER_CHARS for c in term)


def extract_terms(text: str) -> list[str]:
    terms = KATAKANA_RUN.findall(text)
    for run in KANJI_RUN.findall(text):
        if len(run) <= 4:
            terms.append(run)
        else:
            terms.append(run)
            terms.extend(KANJI_CHUNK.findall(run))
    return [t for t in terms if not is_numeric_noise(t)]


def load_books() -> dict[str, str]:
    books = {}
    for path in sorted(BOOKS_DIR.glob("*/README.md")):
        books[path.parent.name] = path.read_text(encoding="utf-8")
    if not books:
        raise RuntimeError(f"no books found under {BOOKS_DIR}")
    return books


def load_titles() -> dict[str, str]:
    """Book titles and framing questions from the catalog, for stage 2 prompts.

    The catalog is the source of truth for what a book is *about*, which is
    exactly what a model needs in order to call a word off-topic.
    """
    try:
        import yaml
    except ImportError:
        return {}
    try:
        catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    titles = {}
    for doc in (catalog or {}).get("documents", []) or []:
        if isinstance(doc, dict) and doc.get("id"):
            titles[doc["id"]] = doc.get("title", "")
    return titles


def build_index(books: dict[str, str]) -> tuple[dict[str, Counter], Counter]:
    counts = {name: Counter(extract_terms(strip_noise(text))) for name, text in books.items()}
    document_frequency: Counter = Counter()
    for counter in counts.values():
        for term in counter:
            document_frequency[term] += 1
    return counts, document_frequency


def select_candidates(
    counter: Counter, document_frequency: Counter, min_count: int, max_df: int
) -> list[tuple[str, int]]:
    picked = [
        (term, n)
        for term, n in counter.items()
        if n >= min_count and document_frequency[term] <= max_df
    ]
    picked.sort(key=lambda item: (-item[1], item[0]))
    return picked


def cmd_candidates(args: argparse.Namespace) -> int:
    books = load_books()
    if args.book:
        missing = [b for b in args.book if b not in books]
        if missing:
            print(f"unknown book(s): {', '.join(missing)}", file=sys.stderr)
            return 2
    # The index is always built over every book: document frequency is only
    # meaningful against the whole corpus, even when reporting one book.
    counts, document_frequency = build_index(books)
    titles = load_titles()
    selected = args.book or sorted(books)

    report = []
    for name in selected:
        candidates = select_candidates(
            counts[name], document_frequency, args.min_count, args.max_df
        )
        report.append(
            {
                "book": name,
                "title": titles.get(name, ""),
                "vocabulary": len(counts[name]),
                "candidates": [{"term": t, "count": n} for t, n in candidates],
            }
        )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    total = 0
    for entry in report:
        total += len(entry["candidates"])
        header = entry["book"]
        if entry["title"]:
            header += f"  {entry['title']}"
        print(f"\n## {header}")
        print(f"語彙 {entry['vocabulary']} → 候補 {len(entry['candidates'])}")
        print(" ".join(f"{c['term']}({c['count']})" for c in entry["candidates"]))
    print(f"\n候補語 合計 {total}（count>={args.min_count}, df<={args.max_df}）")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    path = BOOKS_DIR / args.book / "README.md"
    if not path.is_file():
        print(f"no such book: {args.book}", file=sys.stderr)
        return 2
    lines = path.read_text(encoding="utf-8").split("\n")
    terms = [t for t in (t.strip() for t in args.terms.split(",")) if t]

    for term in terms:
        hits = [i for i, line in enumerate(lines) if term in line]
        if not hits:
            print(f"\n### {term}  — 出現なし")
            continue
        first = hits[0]
        lo = max(0, first - args.window)
        hi = min(len(lines), first + args.window + 1)
        introduced = any(INTRO_MARKER.search(lines[i]) for i in range(lo, hi))
        print(f"\n### {term}  出現{len(hits)}回  初出 L{first + 1}  "
              f"導入マーカー{'あり' if introduced else 'なし'}")
        print(f"--- 初出前後 L{lo + 1}-L{hi} ---")
        for i in range(lo, hi):
            mark = ">" if i == first else " "
            print(f"{mark}{i + 1:6d}| {lines[i]}")
        if len(hits) > 1:
            rest = ", ".join(f"L{i + 1}" for i in hits[1:])
            print(f"--- 他の出現行: {rest}")
    return 0


def cmd_markers(args: argparse.Namespace) -> int:
    books = load_books()
    if args.book:
        books = {k: v for k, v in books.items() if k in args.book}
    total = 0
    for name, text in sorted(books.items()):
        hits = [
            (i + 1, line)
            for i, line in enumerate(text.split("\n"))
            if SIMILE_MARKER.search(line)
        ]
        if not hits:
            continue
        total += len(hits)
        print(f"\n## {name}  ({len(hits)}行)")
        for lineno, line in hits:
            print(f"{lineno:6d}| {line.strip()}")
    print(f"\n比喩マーカー行 合計 {total}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_cand = sub.add_parser(
        "candidates", help="corpus-rare terms per book (stage 1)"
    )
    p_cand.add_argument("--book", action="append", help="book id; repeatable")
    p_cand.add_argument("--min-count", type=int, default=DEFAULT_MIN_COUNT)
    p_cand.add_argument("--max-df", type=int, default=DEFAULT_MAX_DF)
    p_cand.add_argument("--format", choices=("text", "json"), default="text")
    p_cand.set_defaults(func=cmd_candidates)

    p_ctx = sub.add_parser("context", help="body text around flagged terms (stage 3)")
    p_ctx.add_argument("--book", required=True)
    p_ctx.add_argument("--terms", required=True, help="comma-separated")
    p_ctx.add_argument("--window", type=int, default=12)
    p_ctx.set_defaults(func=cmd_context)

    p_mark = sub.add_parser("markers", help="explicit simile lines (complementary)")
    p_mark.add_argument("--book", action="append", help="book id; repeatable")
    p_mark.set_defaults(func=cmd_markers)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
