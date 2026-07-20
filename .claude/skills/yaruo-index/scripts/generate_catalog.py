#!/usr/bin/env python3
"""Generate the public textbook indexes from docs/catalog.yaml."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
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
        if (candidate / "docs" / "catalog.yaml").is_file():
            return candidate
    raise RuntimeError("could not find repository root containing docs/catalog.yaml")


ROOT = find_repo_root()
COUNT_SCRIPT_DIR = ROOT / ".claude" / "skills" / "yaruo-count" / "scripts"
sys.path.insert(0, str(COUNT_SCRIPT_DIR))
sys.dont_write_bytecode = True
from count_textbooks import count_document  # noqa: E402

CATALOG_PATH = ROOT / "docs" / "catalog.yaml"
SIDEBAR_PATH = ROOT / "docs" / "_sidebar.md"
TOP_PAGE_PATH = ROOT / "docs" / "README.md"
START_MARKER = "<!-- BEGIN GENERATED CATALOG -->"
END_MARKER = "<!-- END GENERATED CATALOG -->"


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


def load_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog = require_mapping(raw, str(CATALOG_PATH.relative_to(ROOT)))
    categories = require_list(catalog.get("categories"), "categories")
    documents = require_list(catalog.get("documents"), "documents")

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
    document_paths: set[str] = set()
    document_orders: dict[str, set[int]] = defaultdict(set)
    registered_files: set[Path] = set()
    required_document_fields = (
        "id",
        "title",
        "path",
        "category",
        "order",
        "question",
        "plot",
    )
    for index, raw_document in enumerate(documents):
        document = require_mapping(raw_document, f"documents[{index}]")
        require_fields(document, required_document_fields, f"documents[{index}]")
        document_id = document["id"]
        path = document["path"]
        category_id = document["category"]
        order = document["order"]
        if not isinstance(document_id, str) or not document_id:
            fail(f"documents[{index}].id must be a non-empty string")
        for field in ("title", "question", "plot"):
            if not isinstance(document[field], str) or not document[field]:
                fail(f"document {document_id} has an invalid {field}")
        if document_id in document_ids:
            fail(f"duplicate document id: {document_id}")
        if not isinstance(path, str) or not path.startswith("/books/"):
            fail(f"document {document_id} has an invalid path: {path!r}")
        if path in document_paths:
            fail(f"duplicate document path: {path}")
        if category_id not in category_ids:
            fail(f"document {document_id} references unknown category: {category_id}")
        if not isinstance(order, int) or isinstance(order, bool):
            fail(f"document {document_id} has a non-integer order")
        if order in document_orders[category_id]:
            fail(f"duplicate order {order} in category {category_id}")
        relative_path = Path(path.removeprefix("/"))
        if ".." in relative_path.parts or relative_path.suffix:
            fail(f"document {document_id} has an unsafe path: {path!r}")
        source_path = (ROOT / "docs" / relative_path).with_suffix(".md")
        if not source_path.is_file():
            fail(f"document {document_id} points to missing file: {source_path}")
        document_ids.add(document_id)
        document_paths.add(path)
        document_orders[category_id].add(order)
        registered_files.add(source_path.resolve())

    actual_files = {path.resolve() for path in (ROOT / "docs" / "books").glob("*.md")}
    unregistered = sorted(actual_files - registered_files)
    if unregistered:
        names = ", ".join(path.name for path in unregistered)
        fail(f"unregistered files in docs/books: {names}")

    empty_categories = [category_id for category_id in category_ids if not document_orders[category_id]]
    if empty_categories:
        fail(f"categories without documents: {', '.join(sorted(empty_categories))}")

    categories.sort(key=lambda item: item["order"])
    documents.sort(key=lambda item: (item["category"], item["order"]))
    return categories, documents


def documents_by_category(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        grouped[document["category"]].append(document)
    return [(category, grouped[category["id"]]) for category in categories]


def reading_minutes(document: dict[str, Any]) -> int:
    source_path = (ROOT / "docs" / document["path"].removeprefix("/")).with_suffix(".md")
    return count_document(source_path)["reading_minutes"]


def render_sidebar(
    categories: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> str:
    lines = ["<!-- Generated from docs/catalog.yaml. Do not edit directly. -->", ""]
    for category, category_documents in documents_by_category(categories, documents):
        lines.append(f"- {category['title']}")
        for document in category_documents:
            minutes = reading_minutes(document)
            lines.append(
                f"  - [{document['title']}]({document['path']}) ({minutes}分)"
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
            minutes = reading_minutes(document)
            lines.extend(
                [
                    f"#### [{document['title']}]({document['path']}) ({minutes}分)",
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


def update_or_check(path: Path, expected: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == expected:
        return True
    if check:
        print(f"out of date: {path.relative_to(ROOT)}", file=sys.stderr)
        return False
    path.write_text(expected, encoding="utf-8")
    print(f"updated: {path.relative_to(ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated files differ instead of updating them",
    )
    args = parser.parse_args()

    try:
        categories, documents = load_catalog()
        sidebar = render_sidebar(categories, documents)
        current_top_page = TOP_PAGE_PATH.read_text(encoding="utf-8")
        top_page = replace_generated_catalog(
            current_top_page, render_top_page_catalog(categories, documents)
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"catalog error: {exc}", file=sys.stderr)
        return 1

    results = (
        update_or_check(SIDEBAR_PATH, sidebar, args.check),
        update_or_check(TOP_PAGE_PATH, top_page, args.check),
    )
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
