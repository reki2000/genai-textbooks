#!/usr/bin/env python3
"""Generate the public docsify site (sidebar, top page, per-book pages,
sitemap) by merging catalog.yml files below docs/. Run automatically at build/deploy time;
nothing here is meant to be hand-edited or committed as generated output.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
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
START_MARKER = "<!-- BEGIN GENERATED CATALOG -->"
END_MARKER = "<!-- END GENERATED CATALOG -->"

# Multi-part documents split their body across docs/books/{id}/README.md
# (part 1), README.2.md (part 2), README.3.md (part 3), ... Numbering must
# start at 1 and be contiguous; see docs/BUILD.md.
PART_FILE_PATTERN = re.compile(r"^README(?:\.(?P<n>[1-9][0-9]*))?\.md$")
DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_ROMAN_NUMERAL_TABLE: tuple[tuple[int, str], ...] = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def to_roman(number: int) -> str:
    symbols = []
    remainder = number
    for value, symbol in _ROMAN_NUMERAL_TABLE:
        while remainder >= value:
            symbols.append(symbol)
            remainder -= value
    return "".join(symbols)

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
    for index, (raw_document, catalog_path) in enumerate(
        zip(documents, document_sources, strict=True)
    ):
        document = require_mapping(raw_document, f"documents[{index}]")
        require_fields(document, required_document_fields, f"documents[{index}]")
        unknown_fields = sorted(set(document) - set(required_document_fields))
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

    categories.sort(key=lambda item: item["order"])
    documents.sort(
        key=lambda item: (
            item["category"],
            parse_created(item["created"], f"document {item['id']}.created"),
            item["id"],
        )
    )
    return categories, documents


def documents_by_category(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        grouped[document["category"]].append(document)
    return [(category, grouped[category["id"]]) for category in categories]


def document_path(document: dict[str, Any]) -> str:
    return f"/books/{document['id']}"


def discover_parts(document: dict[str, Any]) -> list[Path]:
    """Ordered part files for a document: README.md, README.2.md, README.3.md,
    ... Numbering must start at 1 and be contiguous."""
    directory = BOOKS_DIR / document["id"]
    numbered: dict[int, Path] = {}
    for candidate in directory.glob("README*.md"):
        match = PART_FILE_PATTERN.match(candidate.name)
        if not match:
            continue
        number = int(match["n"]) if match["n"] else 1
        numbered[number] = candidate
    expected = set(range(1, len(numbered) + 1))
    if set(numbered) != expected:
        fail(
            f"document {document['id']} has non-contiguous parts "
            f"{sorted(numbered)}, expected 1..{len(numbered)}"
        )
    return [numbered[number] for number in sorted(numbered)]


def parts_reading_minutes(document: dict[str, Any]) -> list[int]:
    return [count_document(path)["reading_minutes"] for path in discover_parts(document)]


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


def part_href(document: dict[str, Any], part_index: int) -> str:
    """Site-root-relative link to one part of a multi-part document. Part 1
    keeps the directory-style nav_href; later parts link straight to their
    README.N route, which docsify's history-mode router resolves to
    README.N.md the same way it already resolves any other clean route."""
    if part_index == 0:
        return nav_href(document)
    return f"{SITE_BASE_PATH}{document_path(document)}/README.{part_index + 1}"


def sidebar_title(document: dict[str, Any], multi_part: bool = False) -> str:
    title = re.split(r"[―─]", document["title"], maxsplit=1)[0].rstrip()
    if multi_part:
        title = re.sub(r"\s+[IVXLCDM]+$", "", title)
    return title


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
            parts = discover_parts(document)
            minutes = parts_reading_minutes(document)
            if len(parts) == 1:
                lines.append(
                    f"  - [{sidebar_title(document)} ({minutes[0]}分)]({nav_href(document)})"
                )
            else:
                for index in range(len(parts)):
                    roman = to_roman(index + 1)
                    lines.append(
                        f"  - [{sidebar_title(document, multi_part=True)} "
                        f"{roman}部({minutes[index]}分)]"
                        f"({part_href(document, index)})"
                    )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_top_page_catalog(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> str:
    lines = [START_MARKER, "", "## 教材一覧", ""]
    for category, category_documents in documents_by_category(categories, documents):
        lines.append(f"### {category['title']}")
        lines.append("")
        for document in category_documents:
            parts = discover_parts(document)
            minutes = parts_reading_minutes(document)
            heading = f"#### [{document['title']}]({nav_href(document)}) ({minutes[0]}分)"
            for index in range(1, len(parts)):
                roman = to_roman(index + 1)
                heading += (
                    f" ・ [{roman}部({minutes[index]}分)]({part_href(document, index)})"
                )
            lines.extend(
                [
                    heading,
                    f"問い：{document['question']}",
                    f"プロット：{document['plot']}",
                    "",
                ]
            )
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


def render_slide_deck(document: dict[str, Any], out_docs: Path) -> None:
    """Render docs/books/{id}/slide.md to build/books/{id}/slide.html via
    marp-cli, if a slide.md is present for the document."""
    source = BOOKS_DIR / document["id"] / "slide.md"
    if not source.is_file():
        return
    dest = out_docs / "books" / document["id"] / "slide.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "npx", "--yes", "@marp-team/marp-cli@4",
                str(source), "-o", str(dest), "--html", "--allow-local-files",
                "--template", "bare",
            ],
            check=True,
            cwd=ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        fail(f"document {document['id']} slide.md failed to render via marp-cli: {exc}")


def render_slide_decks(documents: list[dict[str, Any]], out_docs: Path) -> None:
    """Render all slide.md decks concurrently, since each invokes marp-cli as
    a separate subprocess and spends most of its time waiting on that
    process rather than on the Python interpreter."""
    targets = [document for document in documents if has_slide(document)]
    if not targets:
        return
    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        futures = {
            executor.submit(render_slide_deck, document, out_docs): document
            for document in targets
        }
        for future in as_completed(futures):
            future.result()


def render_book_extra_head(document: dict[str, Any]) -> str:
    url = page_url(document)
    return (
        f'  <link rel="canonical" href="{url}">\n'
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


def generate(categories: list[dict[str, Any]], documents: list[dict[str, Any]], out_docs: Path) -> None:
    # The generated HTML is only the docsify shell. The Markdown sources and
    # static assets must also be present in the deployed directory because
    # docsify fetches them in the browser at runtime.
    shutil.copytree(ROOT / "docs", out_docs, dirs_exist_ok=True)

    sidebar = render_sidebar(categories, documents)
    current_top_page = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    top_page = replace_generated_catalog(current_top_page, render_top_page_catalog(categories, documents))
    slide_doc_ids = [document["id"] for document in documents if has_slide(document)]

    write_file(out_docs / "_sidebar.md", sidebar)
    write_file(out_docs / "README.md", top_page)
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

    write_file(out_docs / "sitemap.xml", render_sitemap(documents))


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
        print("generated: build/_sidebar.md, build/README.md, build/index.html, build/404.html, "
              "build/books/*/index.html, build/books/*/slide.html, build/sitemap.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
