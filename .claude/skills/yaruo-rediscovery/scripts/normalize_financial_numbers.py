#!/usr/bin/env python3
"""金額と割合の漢数字表記を半角算用数字へ直す。"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path


DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}
SMALL_UNITS = {"十": 10, "百": 100, "千": 1_000}
LARGE_UNITS = (("兆", 1_000_000_000_000), ("億", 100_000_000), ("万", 10_000))
NUM = "〇一二三四五六七八九十百千万億兆"
MONEY_RE = re.compile(
    rf"(?<![0-9０-９])([〇一二三四五六七八九十百千][{NUM}]*(?:・[〇一二三四五六七八九]+)?)(円|ドル|ユーロ|ポンド|元)"
)
DECIMAL_LARGE_MONEY_RE = re.compile(
    r"(?<![0-9０-９])([〇一二三四五六七八九十百千]+・[〇一二三四五六七八九]+)"
    r"([兆億万])(円|ドル|ユーロ|ポンド|元)"
)
PERCENT_RE = re.compile(rf"([{NUM}]+(?:・[〇一二三四五六七八九]+)?)パーセント")


def parse_small(text: str) -> int:
    if not text:
        return 0
    if all(char in DIGITS for char in text):
        return int("".join(str(DIGITS[char]) for char in text))
    total = 0
    pending: int | None = None
    for char in text:
        if char in DIGITS:
            pending = DIGITS[char]
        else:
            unit = SMALL_UNITS[char]
            total += (1 if pending is None else pending) * unit
            pending = None
    return total + (0 if pending is None else pending)


def parse_integer(text: str) -> int:
    total = 0
    rest = text
    for marker, unit in LARGE_UNITS:
        if marker in rest:
            high, rest = rest.split(marker, 1)
            total += (parse_integer(high) if high else 1) * unit
    return total + parse_small(rest)


def parse_number(text: str) -> str:
    integer, separator, fraction = text.partition("・")
    value = f"{parse_integer(integer):,}"
    if separator:
        value += "." + "".join(str(DIGITS[char]) for char in fraction)
    return value


def money_replacement(match: re.Match[str]) -> str:
    number, currency = match.groups()
    integer = number.split("・", 1)[0]
    for marker in ("兆", "億", "万"):
        if integer.endswith(marker) and "・" not in number:
            prefix = integer[:-1]
            return f"{parse_integer(prefix) if prefix else 1:,}{marker}{currency}"
    return f"{parse_number(number)}{currency}"


def normalize(text: str) -> str:
    text = DECIMAL_LARGE_MONEY_RE.sub(
        lambda match: f"{parse_number(match.group(1))}{match.group(2)}{match.group(3)}",
        text,
    )
    text = MONEY_RE.sub(money_replacement, text)
    text = PERCENT_RE.sub(lambda match: f"{parse_number(match.group(1))}%", text)
    normalized: list[str] = []
    for char in text:
        if "０" <= char <= "９" or char == "％":
            normalized.append(unicodedata.normalize("NFKC", char))
        else:
            normalized.append(char)
    return "".join(normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    before = args.path.read_text(encoding="utf-8")
    after = normalize(before)
    if before == after:
        print(f"変更なし: {args.path}")
        return 0
    if not args.apply:
        print(f"要修正: {args.path}（--apply で反映）")
        return 1
    args.path.write_text(after, encoding="utf-8")
    print(f"修正済み: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
