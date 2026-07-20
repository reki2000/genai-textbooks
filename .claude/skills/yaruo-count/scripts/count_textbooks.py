#!/usr/bin/env python3
"""Count Unicode characters, lines, bytes, and reading time for Yaruo textbooks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


SPEAKER_LINE = re.compile(r"\*\*(?:やる夫|やらない夫)\*\*：\s*")
SPEECH_BOUNDARY = re.compile(r"(?:#{1,6}\s|---+\s*$)")


def normalized_content_lines(source_path: Path) -> list[str]:
    """Return countable lines after removing dialogue presentation characters."""
    lines = source_path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    speech: list[str] | None = None

    def flush_speech() -> None:
        nonlocal speech
        if speech is None:
            return
        speech = [line.lstrip("　") for line in speech]
        nonempty = [index for index, line in enumerate(speech) if line]
        if nonempty:
            first, last = nonempty[0], nonempty[-1]
            if speech[first].startswith("「"):
                speech[first] = speech[first][1:]
            if speech[last].endswith("」"):
                speech[last] = speech[last][:-1]
        kept.extend(speech)
        speech = None

    for line in lines:
        if SPEAKER_LINE.fullmatch(line):
            flush_speech()
            speech = []
        elif speech is not None and SPEECH_BOUNDARY.match(line):
            flush_speech()
            kept.append(line)
        elif speech is not None:
            speech.append(line)
        else:
            kept.append(line)
    flush_speech()
    return kept


def count_math_characters(lines: Iterable[str]) -> int:
    """Count code points in Markdown math, including dollar delimiters."""
    count = 0
    in_fence = False
    fence_character = ""
    in_block_math = False

    for line in lines:
        stripped = line.lstrip()
        if not in_block_math:
            fence = re.match(r"(```+|~~~+)", stripped)
            if fence:
                marker = fence.group(1)[0]
                if not in_fence:
                    in_fence = True
                    fence_character = marker
                elif marker == fence_character:
                    in_fence = False
                continue
            if in_fence:
                continue

        index = 0
        in_inline_code = False
        code_ticks = 0
        while index < len(line):
            if in_block_math:
                closing = line.find("$$", index)
                if closing < 0:
                    count += len(line) - index
                    break
                count += closing + 2 - index
                index = closing + 2
                in_block_math = False
                continue

            if line[index] == "`":
                end = index
                while end < len(line) and line[end] == "`":
                    end += 1
                run_length = end - index
                if not in_inline_code:
                    in_inline_code = True
                    code_ticks = run_length
                elif run_length == code_ticks:
                    in_inline_code = False
                index = end
                continue

            if not in_inline_code and line[index] == "$" and (
                index == 0 or line[index - 1] != "\\"
            ):
                delimiter = "$$" if line.startswith("$$", index) else "$"
                closing = index + len(delimiter)
                while True:
                    closing = line.find(delimiter, closing)
                    if closing < 0 or closing == 0 or line[closing - 1] != "\\":
                        break
                    closing += len(delimiter)
                if closing >= 0:
                    end = closing + len(delimiter)
                    count += end - index
                    index = end
                    continue
                if delimiter == "$$":
                    count += len(line) - index
                    in_block_math = True
                    break
            index += 1
    return count


def count_document(source_path: Path | str) -> dict[str, Any]:
    """Return all count and reading-time metrics for one textbook."""
    path = Path(source_path)
    raw_bytes = path.read_bytes()
    lines = normalized_content_lines(path)
    characters = sum(len(line) for line in lines)
    math_characters = count_math_characters(lines)
    other_characters = characters - math_characters
    math_seconds = math_characters / 10
    other_seconds = other_characters / 40
    total_seconds = math_seconds + other_seconds
    # Exact half-up rounding after combining both portions: 60 seconds per minute.
    weighted_characters = 4 * math_characters + other_characters
    reading_minutes = (weighted_characters + 1200) // 2400
    return {
        "path": path.as_posix(),
        "bytes": len(raw_bytes),
        "characters": characters,
        "lines": len(lines),
        "math_characters": math_characters,
        "other_characters": other_characters,
        "math_seconds": math_seconds,
        "other_seconds": other_seconds,
        "total_seconds": total_seconds,
        "reading_minutes": reading_minutes,
    }


def default_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[4]
    return sorted((repo_root / "docs" / "books").glob("*.md"))


def render_tsv(results: list[dict[str, Any]]) -> str:
    fields = (
        "path",
        "bytes",
        "characters",
        "lines",
        "math_characters",
        "other_characters",
        "math_seconds",
        "other_seconds",
        "total_seconds",
        "reading_minutes",
    )
    rows = ["\t".join(fields)]
    for result in results:
        rows.append("\t".join(str(result[field]) for field in fields))
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown files to count")
    parser.add_argument("--format", choices=("tsv", "json"), default="tsv")
    args = parser.parse_args()
    paths = args.paths or default_paths()
    results = [count_document(path) for path in paths]
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_tsv(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
