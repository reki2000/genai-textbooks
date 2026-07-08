#!/usr/bin/env python3
"""やる夫式教材の Markdown 表の修正。

GFM の表はヘッダ行の直後に区切り行（|---|---| 形式）が必須で、
これが無いと表としてレンダリングされず | がそのまま表示される。

  壊れる例: | 項目 | 値 |
            | 質量 | 80 GeV |
  修正後:   | 項目 | 値 |
            |---|---|
            | 質量 | 80 GeV |

`|` で始まる行が2行以上連続するブロックを表とみなし、
  (a) 各行の行頭の空白（台詞インデントの全角空白など）を除去する
      （GFM は行頭空白が ASCII 空白3個までしか表と認識しないため）
  (b) 2行目が区切り行でなければヘッダ行の列数に合わせた区切り行を挿入する
冪等。

対象外（検出も修正もしない）:
  - フェンスコードブロック（```）・複数行 $$ ブロックの内部
  - `|` で始まる行が1行だけの場合（表ではなく本文の可能性があるため）

自動修正できないパターンは警告として報告する:
  - 区切り行はあるが列数がヘッダ行と一致しない（GFM では表にならない）
  - 表ブロックの直前の行に | が含まれる（ヘッダ行が「 などと同一行に
    融合している可能性。ヘッダを誤認しないため、そのブロックは修正しない）
  - 表ブロックの直前が空行でも見出しでもない（段落の続きと解釈され
    表にならないことがある）

usage: fix_tables.py <file.md> [--check]
  --check: 変更せず、修正が必要な行番号を表示して終了コード1を返す
"""
import re
import sys

DELIM_CELL_RE = re.compile(r"^\s*:?-+:?\s*$")


def is_table_line(body):
    return body.lstrip().startswith("|")


def cells(body):
    s = body.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return re.split(r"(?<!\\)\|", s)


def is_delim_row(body):
    cs = cells(body)
    return len(cs) > 0 and all(DELIM_CELL_RE.match(c) for c in cs)


def make_delim(header_body):
    n = len(cells(header_body))
    return "|" + "|".join(["---"] * n) + "|"


def process(lines):
    out = []
    inserted = []   # 区切り行を挿入した位置（直前の1-indexed行番号）
    deindented = [] # 行頭空白を除去した1-indexed行番号
    warnings = []
    in_fence = False
    in_math = False
    prev_body = ""
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        body = line.rstrip("\n")
        stripped = body.lstrip("　 \t")

        if in_fence:
            if stripped.startswith("```"):
                in_fence = False
            out.append(line)
            prev_body = body
            i += 1
            continue
        if in_math:
            if body.count("$$") % 2 == 1:
                in_math = False
            out.append(line)
            prev_body = body
            i += 1
            continue
        if stripped.startswith("```"):
            in_fence = True
            out.append(line)
            prev_body = body
            i += 1
            continue
        if stripped.startswith("$$") and body.count("$$") % 2 == 1:
            in_math = True
            out.append(line)
            prev_body = body
            i += 1
            continue

        if not is_table_line(body):
            out.append(line)
            prev_body = body
            i += 1
            continue

        # ---- 表ブロックの先頭 ----
        start = i
        block = []
        while i < n:
            b = lines[i].rstrip("\n")
            if not is_table_line(b):
                break
            block.append(b)
            i += 1

        if len(block) < 2:
            out.extend(lines[start:i])
            prev_body = block[-1]
            continue

        if prev_body.strip() and prev_body.count("|") >= 2:
            warnings.append(
                (start + 1, "直前の行に | が含まれる（ヘッダ行が別の文と同一行に融合している可能性。手動修正が必要）"))
            out.extend(lines[start:i])
            prev_body = block[-1]
            continue
        if prev_body.strip() and not prev_body.lstrip().startswith("#"):
            warnings.append((start + 1, "表の直前が空行でない（段落の続きと解釈され表にならない可能性）"))

        eol = lines[start][len(block[0]):] or "\n"
        fixed = []
        for k, b in enumerate(block):
            s = b.lstrip("　 \t")
            if s != b:
                deindented.append(start + k + 1)
            fixed.append(s)

        header, second = fixed[0], fixed[1]
        if is_delim_row(second):
            if len(cells(second)) != len(cells(header)):
                warnings.append(
                    (start + 2, "区切り行の列数がヘッダ行と一致しない（手動修正が必要）"))
        else:
            inserted.append(start + 1)
            fixed = [header, make_delim(header)] + fixed[1:]

        out.extend(b + eol for b in fixed)
        prev_body = fixed[-1]

    return out, inserted, deindented, warnings


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out, inserted, deindented, warnings = process(lines)
    for ln, w in warnings:
        print(f"{path}:{ln}: warning: {w}")
    if check:
        for ln in inserted:
            print(f"{path}:{ln}: needs table delimiter row")
        for ln in deindented:
            print(f"{path}:{ln}: needs table de-indent")
        print(f"{len(inserted)} delimiter row(s), {len(deindented)} de-indent(s) needed")
        return 1 if (inserted or deindented) else 0
    if inserted or deindented:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
    print(f"{path}: {len(inserted)} delimiter row(s) inserted, {len(deindented)} line(s) de-indented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
