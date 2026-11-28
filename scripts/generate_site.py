#!/usr/bin/env python3
"""Generate the public docsify site (sidebar, top page, per-book pages,
sitemap) by merging catalog.yml files below docs/. Run automatically at build/deploy time;
nothing here is meant to be hand-edited or committed as generated output.
"""

from __future__ import annotations

import argparse
import difflib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is required. Install it with "
        "`python3 -m pip install -r requirements-dev.txt`."
    )

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit(
        "Pillow is required for public image optimization. Install it with "
        "`python3 -m pip install -r requirements-dev.txt`."
    )


def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "docs" / "README.md").is_file()
            and (candidate / "scripts" / "site_template.html").is_file()
        ):
            return candidate
    raise RuntimeError("could not find repository root")


ROOT = find_repo_root()
COUNT_SCRIPT_DIR = ROOT / ".claude" / "skills" / "yaruo-count" / "scripts"
sys.path.insert(0, str(COUNT_SCRIPT_DIR))
sys.dont_write_bytecode = True
from count_textbooks import count_document  # noqa: E402

DOCS_DIR = ROOT / "docs"
CATALOG_NAME = "catalog.yml"
TEMPLATE_PATH = ROOT / "scripts" / "site_template.html"
SIDEBAR_PATH = ROOT / "docs" / "_sidebar.md"
TOP_PAGE_PATH = ROOT / "docs" / "README.md"
INDEX_PATH = ROOT / "docs" / "index.html"
NOT_FOUND_PATH = ROOT / "docs" / "404.html"
SITEMAP_PATH = ROOT / "docs" / "sitemap.xml"
BOOKS_DIR = ROOT / "docs" / "books"
MARP_CLI = ("npx", "--yes", "@marp-team/marp-cli@4")
START_MARKER = "<!-- BEGIN GENERATED CATALOG -->"
END_MARKER = "<!-- END GENERATED CATALOG -->"
# Listing variants that include drafts. The browser picks between these and the
# public README.md/_sidebar.md at boot; see the draft-mode block in
# scripts/site_template.html.
DRAFT_TOP_PAGE_NAME = "README.draft.md"
DRAFT_SIDEBAR_NAME = "_sidebar.draft.md"
DRAFT_MARKER = "【下書き】"

# Editorial ratings carried in each book's catalog.yml under `ratings:` (see
# BUILD.md). Keys are stable identifiers; labels are the reader-facing axis
# names shown in the top-page listing, in display order. `overall` is not an
# axis: it is the mean of the three axes, and the listing rank is derived
# from it at build time rather than stored in the catalog. Knowledge amount /
# retention and domain coverage used to be separate axes; they overlapped
# enough that they are now a single `knowledge` axis (the mean of the two
# original scores, so it can land on quarter points such as 4.75).
RATING_AXES = (
    ("knowledge", "知識の充実"),
    ("appeal", "面白さ"),
    ("structure", "物語の構成"),
)
RATING_KEYS = tuple(key for key, _label in RATING_AXES) + ("overall",)

# Generated-image PNGs stay under docs/ as source assets, while the public
# build serves WebP derivatives. 1600 px covers the roughly 760 px article
# column at 2x density; 200 KiB leaves room for labels and thin lines.
PUBLIC_IMAGE_MAX_BYTES = 200 * 1024
PUBLIC_IMAGE_MAX_DIMENSION = 1600
PUBLIC_IMAGE_MIN_DIMENSION = 760
PUBLIC_IMAGE_MIN_QUALITY = 75
_PUBLIC_TEXT_SUFFIXES = {
    ".css", ".html", ".js", ".json", ".md", ".xml", ".yaml", ".yml"
}
_PNG_REFERENCE_RE = re.compile(
    r"(?P<path>(?:\.{0,2}/|/)?[A-Za-z0-9_./-]+\.png)"
    r"(?P<suffix>[?#][A-Za-z0-9_.~!$&'()*+,;=:@/?%-]*)?",
    re.IGNORECASE,
)

# Revision comparison: a catalog may carry `revision_of: <id>` naming the
# earlier version this document revises (see BUILD.md). The build then
# renders a line diff of the two README.md sources as the document's
# diff.md, linked from its page and from the top-page listing. Set it only
# for small revisions; a ground-up rewrite shares too little text for a
# line diff to mean anything. Differing lines are grouped into chunks of
# at most DIFF_CHUNK_MAX_LINES lines per side.
DIFF_CHUNK_MAX_LINES = 5
# A matched section pair whose identical-line ratio falls below this is a
# whole-section change: it is shown as one section unit (both sections in
# full, old above / new below) instead of line chunks, because pairing
# unrelated lines only produces highlight noise. Sections that exist on
# one side only are section units too. A section-unit side longer than
# DIFF_SECTION_FOLD_LINES is collapsed behind a <details> element.
DIFF_SECTION_REWRITE_RATIO = 0.2
DIFF_SECTION_FOLD_LINES = 50
# Character highlights inside a chunk are only computed between lines
# paired by similarity at this ratio or above; positional pairing paints
# highlights onto text that is not a difference.
DIFF_PAIR_MIN_RATIO = 0.55

# Each book is exactly one README.md. The former multi-part layout
# (README.2.md, README.3.md, ...) is rejected: a series is split into separate
# documents chained with `follows`; see BUILD.md.
LEGACY_PART_FILE_PATTERN = re.compile(r"^README\.[1-9][0-9]*\.md$")
DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SITE_ORIGIN = "https://reki2000.github.io"
SITE_BASE_PATH = "/genai-textbooks"
SITE_URL = SITE_ORIGIN + SITE_BASE_PATH
SITE_TITLE = "やる夫で学ぶ"
SITE_DESCRIPTION = "Short Textbooks on Various Topics Written by Generative AI"


def fail(message: str) -> None:
    raise ValueError(message)


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label} must be a mapping")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{label} must be a list")
    return value


def require_fields(item: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in item]
    if missing:
        fail(f"{label} is missing: {', '.join(missing)}")


def parse_created(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        fail(f"{label} must be an ISO 8601 string")
    try:
        created = datetime.fromisoformat(value)
    except ValueError:
        fail(f"{label} must be an ISO 8601 datetime")
    if created.tzinfo is None:
        fail(f"{label} must include a timezone")
    return created


def validate_ratings(value: Any, document_id: str) -> dict[str, float]:
    """Validate a catalog `ratings` block and return it as plain floats.

    All four keys (the three axes in RATING_AXES plus `overall`) are
    required, every value must lie within 1.0-5.0, and `overall` must be the
    mean of the three axes rounded to two decimals, so a catalog cannot
    drift away from the axis scores it claims to summarise.
    """
    label = f"document {document_id}.ratings"
    ratings = require_mapping(value, label)
    unknown = sorted(set(ratings) - set(RATING_KEYS))
    if unknown:
        fail(f"{label} has unknown fields: {', '.join(unknown)}")
    require_fields(ratings, RATING_KEYS, label)
    cleaned: dict[str, float] = {}
    for key in RATING_KEYS:
        score = ratings[key]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            fail(f"{label}.{key} must be a number")
        if not 1.0 <= float(score) <= 5.0:
            fail(f"{label}.{key} must be between 1.0 and 5.0")
        cleaned[key] = float(score)
    mean = sum(cleaned[key] for key, _label in RATING_AXES) / len(RATING_AXES)
    if abs(cleaned["overall"] - round(mean, 2)) > 0.011:
        fail(
            f"{label}.overall must be the mean of the axes "
            f"({round(mean, 2)}), not {cleaned['overall']}"
        )
    return cleaned


def assign_rating_ranks(documents: list[dict[str, Any]]) -> None:
    """Rank every rated document by its overall rating.

    The rank is derived here, over the full document set, instead of being
    stored in each catalog: adding or re-rating one book must not force an
    edit to every other book's catalog just to keep the ranks consistent.
    Ties on `overall` break by the axis scores in display order, then by id,
    so the ranking is total and stable. Each rated document gains
    `rating_rank` (1-based) and `rating_count` (how many documents are rated).
    """
    rated = [document for document in documents if "ratings" in document]

    def rank_key(document: dict[str, Any]) -> tuple:
        ratings = document["ratings"]
        return (
            -ratings["overall"],
            *(-ratings[key] for key, _label in RATING_AXES),
            document["id"],
        )

    for rank, document in enumerate(sorted(rated, key=rank_key), start=1):
        document["rating_rank"] = rank
        document["rating_count"] = len(rated)


def title_from_source(source_path: Path, document_id: str) -> str:
    """Return the title text from the first H1 line of a book source."""
    first_line = source_path.read_text(encoding="utf-8").split("\n", 1)[0]
    first_line = first_line.removeprefix("\ufeff")
    if not first_line.startswith("# ") or not first_line[2:].strip():
        fail(
            f"document {document_id} must start with a non-empty level-1 "
            f"heading: {source_path.relative_to(ROOT)}"
        )
    return first_line[2:].strip()


def load_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog_paths = sorted(DOCS_DIR.rglob(CATALOG_NAME))
    if not catalog_paths:
        fail(f"no {CATALOG_NAME} files found below docs/")

    categories: list[Any] = []
    documents: list[Any] = []
    document_sources: list[Path] = []
    for catalog_path in catalog_paths:
        label = str(catalog_path.relative_to(ROOT))
        raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        catalog = require_mapping(raw, label)
        unknown_fields = sorted(set(catalog) - {"categories", "documents"})
        if unknown_fields:
            fail(f"{label} has unknown fields: {', '.join(unknown_fields)}")
        if "categories" not in catalog and "documents" not in catalog:
            fail(f"{label} must contain categories or documents")
        if "categories" in catalog:
            categories.extend(require_list(catalog["categories"], f"{label}: categories"))
        if "documents" in catalog:
            fragment_documents = require_list(
                catalog["documents"], f"{label}: documents"
            )
            documents.extend(fragment_documents)
            document_sources.extend([catalog_path] * len(fragment_documents))

    if not categories:
        fail("merged catalog has no categories")
    if not documents:
        fail("merged catalog has no documents")

    category_ids: set[str] = set()
    category_orders: set[int] = set()
    for index, raw_category in enumerate(categories):
        category = require_mapping(raw_category, f"categories[{index}]")
        require_fields(category, ("id", "title", "order"), f"categories[{index}]")
        category_id = category["id"]
        order = category["order"]
        if not isinstance(category_id, str) or not category_id:
            fail(f"categories[{index}].id must be a non-empty string")
        if not isinstance(category["title"], str) or not category["title"]:
            fail(f"category {category_id} has an invalid title")
        if category_id in category_ids:
            fail(f"duplicate category id: {category_id}")
        if not isinstance(order, int) or isinstance(order, bool):
            fail(f"category {category_id} has a non-integer order")
        if order in category_orders:
            fail(f"duplicate category order: {order}")
        category_ids.add(category_id)
        category_orders.add(order)

    document_ids: set[str] = set()
    registered_files: set[Path] = set()
    required_document_fields = (
        "id",
        "category",
        "created",
        "question",
        "plot",
    )
    optional_document_fields = ("draft", "follows", "ratings", "revision_of")
    for index, (raw_document, catalog_path) in enumerate(
        zip(documents, document_sources, strict=True)
    ):
        document = require_mapping(raw_document, f"documents[{index}]")
        require_fields(document, required_document_fields, f"documents[{index}]")
        unknown_fields = sorted(
            set(document)
            - set(required_document_fields)
            - set(optional_document_fields)
        )
        if unknown_fields:
            fail(
                f"documents[{index}] has unknown fields: "
                f"{', '.join(unknown_fields)}"
            )
        document_id = document["id"]
        category_id = document["category"]
        if not isinstance(document_id, str) or not DOCUMENT_ID_PATTERN.fullmatch(
            document_id
        ):
            fail(
                f"documents[{index}].id must contain only lowercase ASCII "
                "letters, digits, and single hyphens"
            )
        for field in ("question", "plot"):
            if not isinstance(document[field], str) or not document[field]:
                fail(f"document {document_id} has an invalid {field}")
        if document_id in document_ids:
            fail(f"duplicate document id: {document_id}")
        if category_id not in category_ids:
            fail(f"document {document_id} references unknown category: {category_id}")
        parse_created(document["created"], f"document {document_id}.created")
        expected_catalog_path = BOOKS_DIR / document_id / CATALOG_NAME
        if catalog_path != expected_catalog_path:
            fail(
                f"document {document_id} must be defined in "
                f"{expected_catalog_path.relative_to(ROOT)}, not "
                f"{catalog_path.relative_to(ROOT)}"
            )
        source_path = expected_catalog_path.parent / "README.md"
        if not source_path.is_file():
            fail(f"document {document_id} points to missing file: {source_path}")
        draft = document.get("draft", False)
        if not isinstance(draft, bool):
            fail(f"document {document_id}.draft must be true or false")
        document["draft"] = draft
        if "ratings" in document:
            document["ratings"] = validate_ratings(document["ratings"], document_id)
        legacy_parts = sorted(
            path.name
            for path in source_path.parent.glob("README.*.md")
            if LEGACY_PART_FILE_PATTERN.fullmatch(path.name)
        )
        if legacy_parts:
            fail(
                f"document {document_id} has part files {', '.join(legacy_parts)}; "
                "split each part into its own document and chain them with "
                "`follows` (see BUILD.md)"
            )
        document["title"] = title_from_source(source_path, document_id)
        document_ids.add(document_id)
        registered_files.add(source_path.resolve())

    actual_files = {path.resolve() for path in (ROOT / "docs" / "books").glob("*/README.md")}
    unregistered = sorted(actual_files - registered_files)
    if unregistered:
        names = ", ".join(path.parent.name for path in unregistered)
        fail(f"unregistered folders in docs/books: {names}")

    populated_categories = {document["category"] for document in documents}
    empty_categories = category_ids - populated_categories
    if empty_categories:
        fail(f"categories without documents: {', '.join(sorted(empty_categories))}")

    for document in documents:
        source_id = document.get("revision_of")
        if source_id is None:
            continue
        if not isinstance(source_id, str) or not source_id:
            fail(f"document {document['id']}.revision_of must be a document id")
        if source_id == document["id"]:
            fail(f"document {document['id']}.revision_of points to itself")
        if source_id not in document_ids:
            fail(
                f"document {document['id']}.revision_of points to "
                f"unknown document: {source_id}"
            )

    categories.sort(key=lambda item: item["order"])
    assign_rating_ranks(documents)
    return categories, order_documents(documents)


def order_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by (category, created, id), except that a document carrying
    `follows: <id>` is placed right after the document it follows (its own
    followers right after it, and so on). `follows` only affects the order;
    each volume of a series is still an ordinary, independent document."""
    by_id = {document["id"]: document for document in documents}
    followers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    heads: list[dict[str, Any]] = []
    for document in documents:
        previous_id = document.get("follows")
        if previous_id is None:
            heads.append(document)
            continue
        label = f"document {document['id']}.follows"
        if not isinstance(previous_id, str) or not previous_id:
            fail(f"{label} must be a document id")
        if previous_id not in by_id:
            fail(f"{label} references unknown document: {previous_id}")
        if by_id[previous_id]["category"] != document["category"]:
            fail(
                f"{label} references {previous_id} in another category; "
                "a series must stay in one category"
            )
        followers[previous_id].append(document)

    def created_key(document: dict[str, Any]) -> tuple[datetime, str]:
        created = parse_created(
            document["created"], f"document {document['id']}.created"
        )
        return created, document["id"]

    ordered: list[dict[str, Any]] = []

    def place(document: dict[str, Any]) -> None:
        ordered.append(document)
        for follower in sorted(followers[document["id"]], key=created_key):
            place(follower)

    for head in sorted(heads, key=lambda item: (item["category"], *created_key(item))):
        place(head)
    if len(ordered) != len(documents):
        placed = {document["id"] for document in ordered}
        stuck = sorted(set(by_id) - placed)
        fail(f"follows forms a cycle among: {', '.join(stuck)}")
    return ordered


def public_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Documents that belong in the public listings. Drafts are still built and
    reachable by URL; they are only withheld from the top page, the sidebar and
    the sitemap until their catalog entry drops `draft: true`."""
    return [document for document in documents if not document.get("draft")]


def draft_marker(document: dict[str, Any]) -> str:
    """Listing prefix for a draft. Only the draft listings ever carry a draft,
    so this needs no separate flag to tell the two variants apart."""
    return DRAFT_MARKER if document.get("draft") else ""


def documents_by_category(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        grouped[document["category"]].append(document)
    # A category holding nothing but drafts disappears from the public listings
    # rather than leaving an empty heading behind. The build-time check that
    # every category has a document still runs against the full set.
    return [
        (category, grouped[category["id"]])
        for category in categories
        if grouped[category["id"]]
    ]


def document_path(document: dict[str, Any]) -> str:
    return f"/books/{document['id']}"


def reading_minutes(document: dict[str, Any]) -> int:
    return count_document(BOOKS_DIR / document["id"] / "README.md")["reading_minutes"]


def page_url(document: dict[str, Any]) -> str:
    """Absolute URL for a book page. Trailing slash matches the docs/books/<id>/
    directory + index.html layout, since GitHub Pages (no Jekyll pretty URLs)
    only resolves extensionless paths via directory + index.html, not via
    filename-without-extension lookup."""
    return f"{SITE_URL}{document_path(document)}/"


def nav_href(document: dict[str, Any]) -> str:
    """Site-root-relative link for sidebar/top-page navigation, including the
    project subpath. docsify history mode runs with no basePath, so links must
    carry the full subpath (/genai-textbooks/...); a bare /books/... link would
    drop the subpath on client-side navigation and 404. The trailing slash
    loads docs/books/<id>/README.md via docsify's directory convention."""
    return f"{SITE_BASE_PATH}{document_path(document)}/"


def sidebar_title(document: dict[str, Any]) -> str:
    return re.split(r"[―─]", document["title"], maxsplit=1)[0].rstrip()


def render_sidebar(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> str:
    lines = [
        "<!-- Generated from docs/**/catalog.yml. Do not edit directly. -->",
        "",
    ]
    for category, category_documents in documents_by_category(categories, documents):
        lines.append(f"- {category['title']}")
        for document in category_documents:
            lines.append(
                f"  - [{draft_marker(document)}{sidebar_title(document)} "
                f"({reading_minutes(document)}分)]({nav_href(document)})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_score(value: float) -> str:
    """Shortest plain form of a score: 5.0, 4.5 or 4.75 (quarter points
    occur on the merged knowledge axis)."""
    text = f"{value:.2f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def ratings_line(document: dict[str, Any]) -> str | None:
    """One-line rating summary for a listing entry, or None when unrated."""
    ratings = document.get("ratings")
    if not ratings:
        return None
    axes = "｜".join(
        f"{label} {format_score(ratings[key])}" for key, label in RATING_AXES
    )
    return (
        f"評価：総合評価 {ratings['overall']:.2f}"
        f"（{document['rating_count']}冊中{document['rating_rank']}位）｜{axes}"
    )


def _diff_highlight_pair(old_line: str, new_line: str) -> tuple[str, str]:
    """Markdown for one changed plain-line pair: the characters that
    actually differ are wrapped in a highlight span of the same colour
    family as the side (light red for old, light blue for new). The rest
    of the line is emitted raw, exactly as on the book page, so Markdown
    and math in it render through the normal docsify pipeline. Callers
    must not use this for lines containing math or for block units:
    a span inside a formula would break KaTeX."""
    matcher = difflib.SequenceMatcher(None, old_line, new_line, autojunk=False)
    old_parts: list[str] = []
    new_parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            old_parts.append(old_line[i1:i2])
            new_parts.append(new_line[j1:j2])
            continue
        if i2 > i1:
            old_parts.append(
                f'<span class="diff-hl-old">{old_line[i1:i2]}</span>'
            )
        if j2 > j1:
            new_parts.append(
                f'<span class="diff-hl-new">{new_line[j1:j2]}</span>'
            )
    return "".join(old_parts), "".join(new_parts)


def _diff_units(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Group lines into indivisible diff units. Display-math blocks
    ($$ ... $$, possibly multi-line), fenced code blocks and tables
    (consecutive lines starting with |) are single units: a formula is
    compared as a whole and is never split, re-wrapped or highlighted
    inside, so docsify + KaTeX receive it exactly as written. Everything
    else is a single line."""
    units: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            j = min(j + 1, len(lines))
            units.append(("code", lines[i:j]))
            i = j
            continue
        if "$$" in lines[i]:
            if lines[i].count("$$") % 2 == 0:
                units.append(("formula", [lines[i]]))
                i += 1
                continue
            j = i + 1
            while j < len(lines) and "$$" not in lines[j]:
                j += 1
            j = min(j + 1, len(lines))
            units.append(("formula", lines[i:j]))
            i = j
            continue
        if stripped.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            units.append(("table", lines[i:j]))
            i = j
            continue
        units.append(("line", [lines[i]]))
        i += 1
    return units


_SECTION_NUMBER_RE = re.compile(r"^第[0-9０-９一二三四五六七八九十百]+幕\s*")
_SUBSECTION_NUMBER_RE = re.compile(r"^[0-9０-９]+[-－―][0-9０-９]+\s*")
_SPEAKER_LABEL_RE = re.compile(r"^\*\*[^*]+\*\*[：:]?\s*$")
_SPEAKER_PREFIX_RE = re.compile(r"^\*\*[^*]+\*\*[：:]\s*")


def _is_weak_line(line: str) -> bool:
    """Lines that say almost nothing about which passage they belong to:
    blank lines, speaker labels on their own line (**やる夫**：), and
    lines whose content past the speaker label is a few characters.
    These repeat tens of thousands of times across the books, so if a
    match made only of such lines is allowed to anchor a diff, two
    completely different conversations get stitched together
    utterance by utterance just because the same speakers appear in
    both. A matching block therefore counts only when it contains a
    strong (non-weak) line, and weak lines never pair for highlights:
    a passage replaced across utterances stays one replaced span,
    while weak lines inside a genuinely unchanged stretch still
    match as part of that stretch's block."""
    stripped = line.strip()
    if not stripped or _SPEAKER_LABEL_RE.match(stripped):
        return True
    return len(_SPEAKER_PREFIX_RE.sub("", stripped)) <= 4


def _content_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if not _is_weak_line(line)]


def _split_sections(
    lines: list[str], heading_prefix: str = "## "
) -> list[tuple[str, int, int]]:
    """Split text into (heading, start, end) parts at headings of one
    level (`## ` acts by default, `### ` for the sections inside an
    act); the text before the first heading is a part with an empty
    heading."""
    starts = {i for i, line in enumerate(lines) if line.startswith(heading_prefix)}
    bounds = [0, *sorted(starts), len(lines)]
    return [
        (
            lines[start][len(heading_prefix):].strip() if start in starts else "",
            start,
            bounds[k + 1],
        )
        for k, start in enumerate(bounds[:-1])
    ]


def _match_sections(
    old_sections: list[tuple[str, int, int]],
    new_sections: list[tuple[str, int, int]],
    old_lines: list[str],
    new_lines: list[str],
    number_re: re.Pattern[str] = _SECTION_NUMBER_RE,
    pair_leftovers: bool = False,
) -> dict[int, int]:
    """Map new-section index -> old-section index. Sections pair up so
    that a section whose content changed completely can be recognised as
    one unit; whatever stays unpaired exists on one side only. Pairing is
    by heading first, ignoring the act/section number (a rewrite may
    renumber): exact, then character similarity at 0.8 or above.
    Retitled sections are then paired by content: the best remaining
    pair whose shared-line overlap (common lines over the shorter
    section) reaches 0.25. With pair_leftovers, sections still unpaired
    on both sides are paired in order -- used for the sections inside
    one act, where a leftover on each side is the same slot rewritten,
    and pairing them keeps the diff inside the section boundary."""

    def normalize(heading: str) -> str:
        return re.sub(r"\s+", "", number_re.sub("", heading))

    pairs: dict[int, int] = {}
    used_old: set[int] = set()
    for new_index, (heading, _s, _e) in enumerate(new_sections):
        for old_index, (old_heading, _os, _oe) in enumerate(old_sections):
            if old_index not in used_old and normalize(old_heading) == normalize(heading):
                pairs[new_index] = old_index
                used_old.add(old_index)
                break
    for new_index, (heading, _s, _e) in enumerate(new_sections):
        if new_index in pairs:
            continue
        best_index: int | None = None
        best_ratio = 0.8
        for old_index, (old_heading, _os, _oe) in enumerate(old_sections):
            if old_index in used_old:
                continue
            ratio = difflib.SequenceMatcher(
                None, normalize(old_heading), normalize(heading)
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = old_index
        if best_index is not None:
            pairs[new_index] = best_index
            used_old.add(best_index)

    def overlap(old_index: int, new_index: int) -> float:
        _h, os_, oe = old_sections[old_index]
        _h2, ns, ne = new_sections[new_index]
        old_content = _content_lines(old_lines[os_:oe])
        new_content = _content_lines(new_lines[ns:ne])
        old_counter = Counter(old_content)
        new_counter = Counter(new_content)
        common = sum((old_counter & new_counter).values())
        shorter = min(len(old_content), len(new_content))
        return common / shorter if shorter else 0.0

    candidates = sorted(
        (
            (overlap(old_index, new_index), new_index, old_index)
            for new_index in range(len(new_sections))
            if new_index not in pairs
            for old_index in range(len(old_sections))
            if old_index not in used_old
        ),
        reverse=True,
    )
    for score, new_index, old_index in candidates:
        if score < 0.25:
            break
        if new_index in pairs or old_index in used_old:
            continue
        pairs[new_index] = old_index
        used_old.add(old_index)
    if pair_leftovers:
        remaining_old = [
            index for index in range(len(old_sections)) if index not in used_old
        ]
        remaining_new = [
            index for index in range(len(new_sections)) if index not in pairs
        ]
        for new_index, old_index in zip(remaining_new, remaining_old):
            pairs[new_index] = old_index
            used_old.add(old_index)
    return pairs


def render_diff_page(document: dict[str, Any], source: dict[str, Any]) -> str:
    """Markdown page comparing this document (the revision) against its
    `revision_of` source. The page is ordinary Markdown throughout, so
    docsify and KaTeX render it exactly like a book page: the revision's
    full text is emitted verbatim, and only changed regions become
    two-pane rows (old on the left in red, new on the right in blue, in
    chunks of at most DIFF_CHUNK_MAX_LINES lines per side). No labels or
    explanations are attached to individual chunks -- the colour carries
    the meaning. Inside a plain line, the characters that differ are
    highlighted with a stronger tint of the same family; formulas,
    tables and code blocks are whole units and are never highlighted
    inside. Deleted lines appear in red where they used to be. The
    judgment is partitioned by act (`## ` headings) and, inside an act,
    by section (`### ` headings): units pair up by heading first within
    their parent only, line matching never crosses a section or act
    boundary, and a unit pair that shares almost no lines -- or a unit
    that exists on one side only -- is shown in place as one
    whole-section unit instead of line chunks."""
    old_lines = (BOOKS_DIR / source["id"] / "README.md").read_text(
        encoding="utf-8"
    ).splitlines()
    new_lines = (BOOKS_DIR / document["id"] / "README.md").read_text(
        encoding="utf-8"
    ).splitlines()

    blocks: list[str] = []
    changed_old = 0
    changed_new = 0
    chunk_count = 0
    section_blocks = 0

    def side_lines(
        units: list[tuple[str, list[str]]],
        counterparts: list[tuple[str, list[str]]],
        pair_map: dict[int, int],
        side: str,
    ) -> list[str]:
        """Markdown lines for one side of a chunk. A line gets character
        highlights only when pair_map links it to a genuinely similar
        line on the other side; everything else (unpaired lines,
        formulas, tables, code blocks, any line containing math) stays
        verbatim and is marked by the side's colour alone. Highlighting
        unpaired or merely positional lines would paint parts that are
        not differences at all."""
        rendered: list[str] = []
        for index, (kind, unit_lines) in enumerate(units):
            partner = pair_map.get(index)
            if kind == "line" and partner is not None:
                counterpart_line = counterparts[partner][1][0]
                old_line = unit_lines[0] if side == "old" else counterpart_line
                new_line = counterpart_line if side == "old" else unit_lines[0]
                pair = _diff_highlight_pair(old_line, new_line)
                rendered.append(pair[0] if side == "old" else pair[1])
            else:
                rendered.extend(unit_lines)
        return rendered

    def pair_chunk_lines(
        old_chunk: list[tuple[str, list[str]]],
        new_chunk: list[tuple[str, list[str]]],
    ) -> tuple[dict[int, int], dict[int, int]]:
        """Pair plain, math-free lines across a chunk by best character
        similarity (each line used once, best scores first), keeping
        only pairs at DIFF_PAIR_MIN_RATIO or above. Returns
        (old index -> new index, new index -> old index)."""

        def eligible(unit: tuple[str, list[str]]) -> bool:
            return (
                unit[0] == "line"
                and "$" not in unit[1][0]
                and not _is_weak_line(unit[1][0])
            )

        def pair_text(line: str) -> str:
            # A shared speaker prefix must not inflate the similarity of
            # two different utterances by the same speaker.
            return _SPEAKER_PREFIX_RE.sub("", line)

        candidates = sorted(
            (
                (
                    difflib.SequenceMatcher(
                        None,
                        pair_text(old_chunk[oi][1][0]),
                        pair_text(new_chunk[ni][1][0]),
                    ).ratio(),
                    oi,
                    ni,
                )
                for oi in range(len(old_chunk))
                if eligible(old_chunk[oi])
                for ni in range(len(new_chunk))
                if eligible(new_chunk[ni])
            ),
            reverse=True,
        )
        old_to_new: dict[int, int] = {}
        new_to_old: dict[int, int] = {}
        for ratio, oi, ni in candidates:
            if ratio < DIFF_PAIR_MIN_RATIO:
                break
            if oi in old_to_new or ni in new_to_old:
                continue
            old_to_new[oi] = ni
            new_to_old[ni] = oi
        return old_to_new, new_to_old

    def emit_changed(
        old_units: list[tuple[str, list[str]]],
        new_units: list[tuple[str, list[str]]],
    ) -> None:
        nonlocal changed_old, changed_new, chunk_count
        changed_old += sum(len(unit[1]) for unit in old_units)
        changed_new += sum(len(unit[1]) for unit in new_units)
        io = 0
        inew = 0
        while io < len(old_units) or inew < len(new_units):
            old_chunk: list[tuple[str, list[str]]] = []
            new_chunk: list[tuple[str, list[str]]] = []
            old_count = 0
            new_count = 0
            while io < len(old_units) and (
                not old_chunk or old_count + len(old_units[io][1]) <= DIFF_CHUNK_MAX_LINES
            ):
                old_count += len(old_units[io][1])
                old_chunk.append(old_units[io])
                io += 1
            while inew < len(new_units) and (
                not new_chunk or new_count + len(new_units[inew][1]) <= DIFF_CHUNK_MAX_LINES
            ):
                new_count += len(new_units[inew][1])
                new_chunk.append(new_units[inew])
                inew += 1
            if all(
                not line.strip()
                for unit in old_chunk + new_chunk
                for line in unit[1]
            ):
                # A sub-chunk made only of blank lines (an empty line
                # left over at a chunk boundary) is not a visible
                # change; showing it would produce an empty diff row.
                emit_same(new_chunk)
                continue
            chunk_count += 1
            old_to_new, new_to_old = pair_chunk_lines(old_chunk, new_chunk)
            parts = ['<div class="diff-row">']
            if old_chunk:
                parts.append('<div class="diff-pane diff-old">')
                parts.append("")
                parts.extend(side_lines(old_chunk, new_chunk, old_to_new, "old"))
                parts.append("")
                parts.append("</div>")
            else:
                parts.append('<div class="diff-pane diff-old"></div>')
            if new_chunk:
                parts.append('<div class="diff-pane diff-new">')
                parts.append("")
                parts.extend(side_lines(new_chunk, old_chunk, new_to_old, "new"))
                parts.append("")
                parts.append("</div>")
            else:
                parts.append('<div class="diff-pane diff-new"></div>')
            parts.append("</div>")
            blocks.append("\n".join(parts))

    def emit_same(units: list[tuple[str, list[str]]]) -> None:
        lines: list[str] = []
        for _kind, unit_lines in units:
            lines.extend(unit_lines)
        if lines:
            blocks.append("\n".join(lines))

    def emit_section(
        old_segment: list[str], new_segment: list[str]
    ) -> None:
        """One whole-section unit in place, as a two-pane row: both
        sections verbatim in their panes, no line pairing. Long sides
        are folded; a side that does not exist stays an empty pane."""
        nonlocal changed_old, changed_new, section_blocks
        changed_old += len(old_segment)
        changed_new += len(new_segment)
        section_blocks += 1

        def side(segment: list[str], side_class: str) -> list[str]:
            if not segment:
                return [f'<div class="diff-pane {side_class}"></div>']
            parts = [f'<div class="diff-pane {side_class}">', ""]
            if len(segment) > DIFF_SECTION_FOLD_LINES:
                parts.append(
                    '<details class="diff-fold">'
                    f"<summary>全文（{len(segment)} 行）を表示</summary>"
                )
                parts.append("")
                parts.extend(segment)
                parts.append("")
                parts.append("</details>")
            else:
                parts.extend(segment)
            parts.append("")
            parts.append("</div>")
            return parts

        parts = ['<div class="diff-row diff-row-section">']
        parts.extend(side(old_segment, "diff-old"))
        parts.extend(side(new_segment, "diff-new"))
        parts.append("</div>")
        blocks.append("\n".join(parts))

    old_sections = _split_sections(old_lines)
    new_sections = _split_sections(new_lines)
    section_pairs = _match_sections(old_sections, new_sections, old_lines, new_lines)
    old_only = [
        index
        for index in range(len(old_sections))
        if index not in set(section_pairs.values())
    ]
    old_only_ptr = 0

    def flush_old_only(before_old_index: int) -> None:
        nonlocal old_only_ptr
        while old_only_ptr < len(old_only) and old_only[old_only_ptr] < before_old_index:
            old_index = old_only[old_only_ptr]
            old_only_ptr += 1
            _heading, start, end = old_sections[old_index]
            emit_section(old_lines[start:end], [])

    def process_pair(old_slice: list[str], new_slice: list[str]) -> None:
        old_content = _content_lines(old_slice)
        new_content = _content_lines(new_slice)
        ratio = (
            difflib.SequenceMatcher(None, old_content, new_content, autojunk=False).ratio()
            if old_content or new_content
            else 1.0
        )
        if ratio < DIFF_SECTION_REWRITE_RATIO:
            emit_section(old_slice, new_slice)
            return
        old_units = _diff_units(old_slice)
        new_units = _diff_units(new_slice)

        def is_strong(unit: tuple[str, list[str]]) -> bool:
            return unit[0] != "line" or not _is_weak_line(unit[1][0])

        # Match on all units, then keep a matching block only if it
        # contains at least one strong unit. A block made solely of
        # weak lines (blanks and speaker labels) is exactly how two
        # different conversations get stitched together, so it is
        # dropped and the span stays one replacement; weak lines inside
        # a genuinely unchanged stretch still match, because their
        # block contains the surrounding strong lines.
        matcher = difflib.SequenceMatcher(
            None,
            ["\n".join(unit[1]) for unit in old_units],
            ["\n".join(unit[1]) for unit in new_units],
            autojunk=False,
        )
        kept: list[tuple[int, int]] = []
        for a, b, size in matcher.get_matching_blocks():
            if size and any(is_strong(old_units[a + k]) for k in range(size)):
                kept.extend((a + k, b + k) for k in range(size))
        kept_set = dict(kept)
        i = j = 0
        kept_index = 0
        while i < len(old_units) or j < len(new_units):
            if kept_set.get(i) == j and i < len(old_units):
                a1, b1 = i, j
                while kept_set.get(i) == j and i < len(old_units):
                    i += 1
                    j += 1
                emit_same(new_units[b1:j])
                continue
            a1, b1 = i, j
            while kept_index < len(kept) and (
                kept[kept_index][0] < i or kept[kept_index][1] < j
            ):
                kept_index += 1
            if kept_index < len(kept):
                i, j = kept[kept_index]
            else:
                i, j = len(old_units), len(new_units)
            if i > a1 or j > b1:
                emit_changed(old_units[a1:i], new_units[b1:j])
    def process_act_pair(old_slice: list[str], new_slice: list[str]) -> None:
        """Diff one paired act. When both versions of the act have
        `### ` sections, the diff is judged section by section inside
        the act: sections pair up within the act only, and line matching
        never crosses a section (or act) boundary. An act that has no
        sections on either side is judged as a whole."""
        if not (
            any(line.startswith("### ") for line in old_slice)
            and any(line.startswith("### ") for line in new_slice)
        ):
            process_pair(old_slice, new_slice)
            return
        old_subs = _split_sections(old_slice, "### ")
        new_subs = _split_sections(new_slice, "### ")
        sub_pairs = _match_sections(
            old_subs,
            new_subs,
            old_slice,
            new_slice,
            number_re=_SUBSECTION_NUMBER_RE,
            pair_leftovers=True,
        )
        sub_old_only = [
            index
            for index in range(len(old_subs))
            if index not in set(sub_pairs.values())
        ]
        ptr = 0
        for new_sub_index, (_h, sub_start, sub_end) in enumerate(new_subs):
            old_sub_index = sub_pairs.get(new_sub_index)
            if old_sub_index is None:
                emit_section([], new_slice[sub_start:sub_end])
                continue
            while ptr < len(sub_old_only) and sub_old_only[ptr] < old_sub_index:
                _oh, o_start, o_end = old_subs[sub_old_only[ptr]]
                ptr += 1
                emit_section(old_slice[o_start:o_end], [])
            _oh, o_start, o_end = old_subs[old_sub_index]
            process_pair(old_slice[o_start:o_end], new_slice[sub_start:sub_end])
        while ptr < len(sub_old_only):
            _oh, o_start, o_end = old_subs[sub_old_only[ptr]]
            ptr += 1
            emit_section(old_slice[o_start:o_end], [])

    for new_index, (heading, start, end) in enumerate(new_sections):
        old_index = section_pairs.get(new_index)
        if old_index is None:
            emit_section([], new_lines[start:end])
            continue
        flush_old_only(old_index)
        _old_heading, old_start, old_end = old_sections[old_index]
        process_act_pair(old_lines[old_start:old_end], new_lines[start:end])
    flush_old_only(len(old_sections))

    lines = [
        f"# 差分：{document['title']}",
        "",
        f"こちらは改訂版で、比較元は [{source['title']}](../{source['id']}/README.md) です。"
        f"[こちら（改訂版）の本文](README.md) に戻る。",
        "",
        "こちら（改訂版）の全文をそのまま表示し、変わった所は左右2ペインで示しています。"
        "左の<span class=\"diff-old\">旧（比較元）</span> は赤、"
        "右の<span class=\"diff-new\">新（こちら）</span> は青、"
        "行の中で実際に異なる部分は同系の薄い色でハイライトします。"
        "式は丸ごと1つの差分単位として扱います。",
        "",
        f"全文 {len(new_lines)} 行（比較元 {len(old_lines)} 行）。"
        f"変更は {chunk_count} 塊（うち節単位 {section_blocks} 件）で、"
        f"比較元 {changed_old} 行 → こちら {changed_new} 行が変わっています。",
        "",
    ]
    if blocks:
        lines.append("\n\n".join(blocks))
    else:
        lines.append("差分はありません。")
    return "\n".join(lines) + "\n"


def write_diff_pages(
    documents: list[dict[str, Any]], out_docs: Path
) -> None:
    """Write diff.md for every document carrying `revision_of`, and add a
    link to it at the top of the document's built README.md copy (the
    source README.md itself is left untouched)."""
    by_id = {document["id"]: document for document in documents}
    for document in documents:
        source_id = document.get("revision_of")
        if not source_id:
            continue
        source = by_id[source_id]
        book_dir = out_docs / "books" / document["id"]
        write_file(book_dir / "diff.md", render_diff_page(document, source))
        readme_path = book_dir / "README.md"
        readme = readme_path.read_text(encoding="utf-8")
        title, _, rest = readme.partition("\n")
        link = (
            f"> こちらは改訂版です。比較元「{source['title']}」との"
            "[差分を見る](diff.md)"
        )
        readme_path.write_text(f"{title}\n\n{link}\n{rest}", encoding="utf-8")


def render_top_page_catalog(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> str:
    by_id = {document["id"]: document for document in documents}
    lines = [
        START_MARKER,
        "",
        "## 教材一覧",
        "",
        "各教材には、エンタメ学習コンテンツとしての評価（各5点満点）を付けている。"
        "**知識の充実**＝具体的な知識の量と、その分野の主要テーマの網羅、定着のしやすさ、"
        "**面白さ**＝読ませる力、"
        "**物語の構成**＝プロットと構成。"
        "**総合評価**は3つの評価の平均で、順位は全教材の総合評価順。",
        "",
    ]
    for category, category_documents in documents_by_category(categories, documents):
        lines.append(f"### {category['title']}")
        lines.append("")
        for document in category_documents:
            lines.extend(
                [
                    f"#### [{draft_marker(document)}{document['title']}]"
                    f"({nav_href(document)}) ({reading_minutes(document)}分)",
                    f"問い：{document['question']}",
                    f"プロット：{document['plot']}",
                ]
            )
            rating = ratings_line(document)
            if rating is not None:
                lines.append(rating)
            if document.get("revision_of"):
                source = by_id[document["revision_of"]]
                lines.append(
                    f"差分：改訂版です。比較元「{source['title']}」との"
                    f"[差分を見る]({nav_href(document)}diff)"
                )
            lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def replace_generated_catalog(current: str, generated: str) -> str:
    if START_MARKER not in current or END_MARKER not in current:
        fail(f"{TOP_PAGE_PATH.relative_to(ROOT)} does not contain catalog markers")
    before, remainder = current.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    return before + generated + after.lstrip("\n")


def render_shell(
    title: str, description: str, extra_head: str = "", slide_doc_ids: list[str] | None = None
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("@@TITLE@@", title)
        .replace("@@DESCRIPTION@@", description)
        .replace("@@BASE_PATH@@", SITE_BASE_PATH)
        .replace("@@SITE_TITLE@@", SITE_TITLE)
        .replace("@@EXTRA_HEAD@@", extra_head)
        .replace("@@SLIDE_DOC_IDS@@", json.dumps(sorted(slide_doc_ids or [])))
    )


def has_slide(document: dict[str, Any]) -> bool:
    return (BOOKS_DIR / document["id"] / "slide.md").is_file()


def slide_needs_render(document: dict[str, Any], out_docs: Path) -> bool:
    source = BOOKS_DIR / document["id"] / "slide.md"
    if not source.is_file():
        return False
    dest = out_docs / "books" / document["id"] / "slide.html"
    return not (
        dest.is_file() and dest.stat().st_mtime_ns >= source.stat().st_mtime_ns
    )


def render_slide_deck(document: dict[str, Any], out_docs: Path) -> None:
    """Render docs/books/{id}/slide.md to build/books/{id}/slide.html via
    marp-cli, if a slide.md is present for the document."""
    # Render the copied source: raster references there may have been changed
    # from source PNGs to public WebP derivatives.
    source = out_docs / "books" / document["id"] / "slide.md"
    dest = out_docs / "books" / document["id"] / "slide.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                *MARP_CLI,
                str(source), "-o", str(dest), "--html", "--allow-local-files",
                "--template", "bare",
            ],
            check=True,
            cwd=ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        fail(f"document {document['id']} slide.md failed to render via marp-cli: {exc}")


def warm_marp_cli() -> None:
    """Populate the npx cache for marp-cli with a single throwaway run.

    Every `npx --yes @marp-team/marp-cli@4` resolves to the same cache
    directory under ~/.npm/_npx, so starting several of them at once on a
    cold cache lets one process read a half-installed node_modules that
    another is still writing (`Cannot find module 'cssfilter'`). Installing
    once, serially, leaves the concurrent renders with nothing to race over."""
    try:
        subprocess.run(
            [*MARP_CLI, "--version"],
            check=True,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        fail(f"marp-cli is unavailable: {exc}")


def render_slide_decks(documents: list[dict[str, Any]], out_docs: Path) -> None:
    """Render all slide.md decks concurrently, since each invokes marp-cli as
    a separate subprocess and spends most of its time waiting on that
    process rather than on the Python interpreter."""
    targets = [
        document for document in documents
        if slide_needs_render(document, out_docs)
    ]
    if not targets:
        return
    warm_marp_cli()
    # marp-cli is heavier than a plain I/O wait, so keep the fan-out near the
    # core count instead of starting one process per deck.
    workers = min(len(targets), max(os.cpu_count() or 1, 2))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(render_slide_deck, document, out_docs): document
            for document in targets
        }
        for future in as_completed(futures):
            future.result()


def render_book_extra_head(document: dict[str, Any]) -> str:
    url = page_url(document)
    # A draft page is reachable by URL on purpose, but nothing should index it
    # while it is still withheld from the listings and the sitemap.
    robots = '  <meta name="robots" content="noindex">\n' if document.get("draft") else ""
    return (
        robots
        + f'  <link rel="canonical" href="{url}">\n'
        f'  <meta property="og:type" content="article">\n'
        f'  <meta property="og:site_name" content="{SITE_TITLE}">\n'
        f'  <meta property="og:title" content="{document["title"]}">\n'
        f'  <meta property="og:description" content="{document["question"]}">\n'
        f'  <meta property="og:url" content="{url}">\n'
        f'  <meta name="twitter:card" content="summary">\n'
    )


def render_site_extra_head() -> str:
    url = SITE_URL + "/"
    return (
        f'  <link rel="canonical" href="{url}">\n'
        f'  <meta name="keywords" content="やる夫,教科書,生成AI,対話形式,再発見学習">\n'
        f'  <meta property="og:type" content="website">\n'
        f'  <meta property="og:site_name" content="{SITE_TITLE}">\n'
        f'  <meta property="og:title" content="{SITE_TITLE}">\n'
        f'  <meta property="og:description" content="{SITE_DESCRIPTION}">\n'
        f'  <meta property="og:url" content="{url}">\n'
        f'  <meta name="twitter:card" content="summary">\n'
    )


def render_not_found_extra_head() -> str:
    return '  <meta name="robots" content="noindex">\n'


def render_sitemap(documents: list[dict[str, Any]]) -> str:
    urls = [SITE_URL + "/"] + [page_url(document) for document in documents]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.append(f"  <url><loc>{url}</loc></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _webp_bytes(image: Image.Image, quality: int) -> bytes:
    output = io.BytesIO()
    image.save(output, "WEBP", quality=quality, method=6)
    return output.getvalue()


def render_public_webp(source: Path) -> bytes:
    """Render one source image within the public byte budget.

    Prefer compression over downscaling because textbook figures contain
    small labels and thin lines. If quality 75 cannot meet the budget, reduce
    dimensions in 10% steps, but never below the article width.
    """
    with Image.open(source) as opened:
        opened.load()
        image = ImageOps.exif_transpose(opened)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert(
                "RGBA" if "transparency" in image.info else "RGB"
            )

    longest = max(image.size)
    if longest > PUBLIC_IMAGE_MAX_DIMENSION:
        scale = PUBLIC_IMAGE_MAX_DIMENSION / longest
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )

    while True:
        for quality in range(100, PUBLIC_IMAGE_MIN_QUALITY - 1, -1):
            payload = _webp_bytes(image, quality)
            if len(payload) <= PUBLIC_IMAGE_MAX_BYTES:
                return payload

        longest = max(image.size)
        if longest <= PUBLIC_IMAGE_MIN_DIMENSION:
            raise ValueError(
                f"cannot optimize {source.relative_to(ROOT)} below "
                f"{PUBLIC_IMAGE_MAX_BYTES} bytes without making it narrower "
                f"than {PUBLIC_IMAGE_MIN_DIMENSION}px"
            )
        next_longest = max(PUBLIC_IMAGE_MIN_DIMENSION, int(longest * 0.9))
        scale = next_longest / longest
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )


def _reference_target(reference: str, referring_file: Path, out_docs: Path) -> Path:
    if reference.startswith(SITE_BASE_PATH + "/"):
        return (out_docs / reference.removeprefix(SITE_BASE_PATH + "/")).resolve()
    if reference.startswith("/"):
        return (out_docs / reference.lstrip("/")).resolve()
    return (referring_file.parent / reference).resolve()


def rewrite_public_png_references_in_text(
    text: str,
    referring_file: Path,
    out_docs: Path,
    conversions: dict[Path, Path],
) -> str:
    """Point one copied text file at its generated WebP delivery assets."""
    def replace(match: re.Match[str]) -> str:
        reference = match.group("path")
        target = _reference_target(reference, referring_file, out_docs)
        if target not in conversions:
            return match.group(0)
        return reference[:-4] + ".webp" + (match.group("suffix") or "")

    return _PNG_REFERENCE_RE.sub(replace, text)


def rewrite_public_png_references(
    out_docs: Path, conversions: dict[Path, Path]
) -> None:
    """Point copied site text at generated WebP files, preserving URL style."""
    for text_path in out_docs.rglob("*"):
        if (
            not text_path.is_file()
            or text_path.suffix.lower() not in _PUBLIC_TEXT_SUFFIXES
        ):
            continue
        text = text_path.read_text(encoding="utf-8")
        rewritten = rewrite_public_png_references_in_text(
            text, text_path, out_docs, conversions
        )
        if rewritten != text:
            text_path.write_text(rewritten, encoding="utf-8")


def public_image_conversions(out_docs: Path) -> dict[Path, Path]:
    """Map copied PNG paths to their WebP delivery paths."""
    source_books_dir = DOCS_DIR / "books"
    books_dir = out_docs / "books"
    return {
        (books_dir / source.relative_to(source_books_dir)).resolve():
        (books_dir / source.relative_to(source_books_dir)).with_suffix(".webp").resolve()
        for source in source_books_dir.rglob("*.png")
    }


def public_image_needs_render(source: Path, destination: Path) -> bool:
    """Return whether a public WebP is absent, stale, or over budget.

    The generator source is itself an input: changing compression constants or
    conversion code must invalidate every existing derivative. copytree uses
    copy2, so copied PNG mtimes still match their originals.
    """
    if not destination.is_file() or destination.stat().st_size > PUBLIC_IMAGE_MAX_BYTES:
        return True
    newest_input = max(source.stat().st_mtime_ns, Path(__file__).stat().st_mtime_ns)
    return destination.stat().st_mtime_ns < newest_input


def optimize_public_images(out_docs: Path) -> list[tuple[Path, Path]]:
    """Replace copied book PNGs with <=200 KiB WebP delivery assets.

    The source PNGs in docs/ remain untouched. UI assets such as favicon.png
    are outside books/ and deliberately keep their original format.
    """
    source_books_dir = DOCS_DIR / "books"
    books_dir = out_docs / "books"
    # Remove the cache file used by an earlier implementation. Derivative
    # freshness is now carried by each WebP's own mtime, so this must not be
    # deployed as a public asset from an existing local build directory.
    (out_docs / ".public-image-cache.json").unlink(missing_ok=True)
    source_pngs = {
        source.relative_to(source_books_dir): source
        for source in source_books_dir.rglob("*.png")
    }
    source_webps = {
        source.relative_to(source_books_dir)
        for source in source_books_dir.rglob("*.webp")
    }

    # copytree(..., dirs_exist_ok=True) intentionally preserves most build
    # output for fast slide rebuilds. Remove only obsolete raster derivatives
    # so a deleted source image cannot remain publicly reachable after the
    # next local build.
    for stale in books_dir.rglob("*.png"):
        if stale.relative_to(books_dir) not in source_pngs:
            stale.unlink()
    for stale in books_dir.rglob("*.webp"):
        relative = stale.relative_to(books_dir)
        if relative not in source_webps and relative.with_suffix(".png") not in source_pngs:
            stale.unlink()

    conversions = public_image_conversions(out_docs)
    for relative, original in sorted(source_pngs.items()):
        copied_source = books_dir / relative
        destination = copied_source.with_suffix(".webp")
        if public_image_needs_render(original, destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(render_public_webp(original))
            os.replace(temporary, destination)

    rewrite_public_png_references(out_docs, conversions)
    for source in conversions:
        source.unlink(missing_ok=True)
    return list(conversions.items())


# Aozora-style ruby (｜基底《よみ》, see AGENTS.md) is converted straight to
# <ruby> HTML here at build time rather than by a docsify plugin in the
# browser. ｜《》 (and the < of a raw <ruby> tag) are Unicode punctuation, so
# **｜台詞《せりふ》** would fail CommonMark's emphasis-flanking rule once
# docsify's markdown-it parses the page, silently dropping the bold -- the
# same reason a literal ｜ next to ** breaks. A zero-width non-joiner
# (U+200C, general category Cf: neither punctuation nor whitespace) around
# each <ruby> span keeps ** flanking intact without changing anything
# visible.
RUBY_GUARD = "\u200c"

_RUBY_PROTECTED_PATTERN = (
    r"```[\s\S]*?(?:```|$)"
    r"|~~~[\s\S]*?(?:~~~|$)"
    r"|`[^`\n]*`"
    r"|\$\$[\s\S]*?\$\$"
    r"|\$[^$\n]*\$"
)
_RUBY_PATTERN = r"｜([^｜《》\n]{1,40})《([^｜《》\n]{1,40})》"
_RUBY_TOKEN_RE = re.compile(f"(?:{_RUBY_PROTECTED_PATTERN})|(?:{_RUBY_PATTERN})")


def convert_ruby_to_html(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        base = match.group(1)
        if base is None:
            return match.group(0)
        reading = match.group(2)
        ruby = f"<ruby>{base}<rp>（</rp><rt>{reading}</rt><rp>）</rp></ruby>"
        return f"{RUBY_GUARD}{ruby}{RUBY_GUARD}"

    return _RUBY_TOKEN_RE.sub(replace, text)


def apply_ruby_conversion(out_docs: Path) -> None:
    # slide.md (marp) doesn't render through docsify/markdown-it, so ruby
    # notation isn't used there (see AGENTS.md).
    for md_path in out_docs.rglob("*.md"):
        if md_path.name == "slide.md":
            continue
        text = md_path.read_text(encoding="utf-8")
        if "｜" not in text:
            continue
        converted = convert_ruby_to_html(text)
        if converted != text:
            md_path.write_text(converted, encoding="utf-8")


# docsify-footnote (see site_template.html) parses footnote definitions in
# document order: for each `[^N]:` block it deletes the block's own raw text
# out of the page source once it has located and replaced every `[^N]`
# reference elsewhere. If a *later* footnote's definition text itself cites
# an *earlier* footnote (e.g. `[^30]: ... [^29] と同じ...`), that citation is
# still raw, undeleted text when footnote 29 is processed, so 29's reference
# scan matches it too and rewrites it in place -- after which footnote 30's
# own definition block no longer matches the string the plugin captured at
# the start, so the deletion silently fails and the whole `[^30]: ...` line
# leaks into the page as plain body text instead of becoming a footnote.
# Reference: docsify-footnote@1.0.8 dist/docsify-footnote.min.js.
#
# Fixed by pre-rewriting, at build time only, any `[^M]` that appears inside
# another footnote's own definition body into a plain link pointing at that
# footnote's entry (`#ftref-M`, the id docsify-footnote assigns to its list
# item). Two things about the replacement matter:
#
# - It must not itself contain the literal substring `[^M]` -- the plugin's
#   `\[\^M\]` regex would still find and mangle it inside the replacement,
#   reproducing the exact same bug one level in (tried and confirmed broken:
#   the plugin renumbered the still-live `[^M]` text to a suffixed label
#   like "29-1" and the surrounding block deletion failed again). Dropping
#   the caret (`[M]` instead of `[^M]`) makes it inert to that regex.
# - It must be Markdown link syntax, not a raw HTML `<a href="#...">` tag.
#   docsify's history-mode router only rewrites in-page hash links that go
#   through its own Markdown-link compiler; a passthrough HTML anchor
#   bypasses that and gets mis-resolved into a `?id=...`-suffixed URL that
#   doesn't scroll anywhere (tried and confirmed broken). Mirroring the
#   `[\[N\]](#ftref-N)` form docsify-footnote itself emits for its back-links
#   keeps it on the path that already works.
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:(.*)$", re.MULTILINE)
_FOOTNOTE_REF_RE = re.compile(r"\[\^(\d+)\](?!:)")


def convert_footnote_backrefs(text: str) -> str:
    def guard_refs(body: str) -> str:
        return _FOOTNOTE_REF_RE.sub(
            lambda m: f'[\\[{m.group(1)}\\]](#ftref-{m.group(1)})', body
        )

    def replace(match: re.Match[str]) -> str:
        number, body = match.group(1), match.group(2)
        return f"[^{number}]:{guard_refs(body)}"

    return _FOOTNOTE_DEF_RE.sub(replace, text)


def apply_footnote_backref_guard(out_docs: Path) -> None:
    for md_path in out_docs.rglob("*.md"):
        if md_path.name == "slide.md":
            continue
        text = md_path.read_text(encoding="utf-8")
        if "[^" not in text:
            continue
        converted = convert_footnote_backrefs(text)
        if converted != text:
            md_path.write_text(converted, encoding="utf-8")


def generate(categories: list[dict[str, Any]], documents: list[dict[str, Any]], out_docs: Path) -> None:
    # The generated HTML is only the docsify shell. The Markdown sources and
    # static assets must also be present in the deployed directory because
    # docsify fetches them in the browser at runtime.
    shutil.copytree(ROOT / "docs", out_docs, dirs_exist_ok=True)
    optimize_public_images(out_docs)

    # Two listing variants: the public one, and the draft one the browser loads
    # instead when draft mode is on. Everything else below is built from the
    # full document set, so a draft gets the same page, figures and slides as a
    # published book and only its listing entries differ.
    published = public_documents(documents)
    current_top_page = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    def top_page_for(subset: list[dict[str, Any]]) -> str:
        return replace_generated_catalog(
            current_top_page, render_top_page_catalog(categories, subset)
        )

    slide_doc_ids = [document["id"] for document in documents if has_slide(document)]

    write_file(out_docs / "_sidebar.md", render_sidebar(categories, published))
    write_file(out_docs / "README.md", top_page_for(published))
    write_file(out_docs / DRAFT_SIDEBAR_NAME, render_sidebar(categories, documents))
    write_file(out_docs / DRAFT_TOP_PAGE_NAME, top_page_for(documents))
    write_file(
        out_docs / "index.html",
        render_shell(SITE_TITLE, SITE_DESCRIPTION, render_site_extra_head(), slide_doc_ids),
    )
    write_file(
        out_docs / "404.html",
        render_shell(SITE_TITLE, SITE_DESCRIPTION, render_not_found_extra_head(), slide_doc_ids),
    )

    for document in documents:
        relative_path = Path(document_path(document).removeprefix("/")) / "index.html"
        page_title = f"{document['title']} - {SITE_TITLE}"
        page = render_shell(page_title, document["question"], render_book_extra_head(document), slide_doc_ids)
        write_file(out_docs / relative_path, page)

    render_slide_decks(documents, out_docs)

    apply_ruby_conversion(out_docs)
    apply_footnote_backref_guard(out_docs)

    # Diff pages are written last on purpose: they quote both sources raw,
    # so the ruby and footnote rewrites above must not run over them.
    write_diff_pages(documents, out_docs)

    write_file(out_docs / "sitemap.xml", render_sitemap(published))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="only validate merged docs/**/catalog.yml and a trial build, without touching build/",
    )
    args = parser.parse_args()

    try:
        categories, documents = load_catalog()
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                generate(categories, documents, Path(tmp))
        else:
            generate(categories, documents, ROOT / "build")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"catalog error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print("catalog OK")
    else:
        print("generated: build/_sidebar.md, build/README.md, build/_sidebar.draft.md, "
              "build/README.draft.md, build/index.html, build/404.html, "
              "build/books/*/index.html, build/books/*/slide.html, "
              "build/books/*/diff.md (only for books with revision_of), build/sitemap.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
