#!/usr/bin/env python3
"""やる夫式教材の台詞インデント整形。

複数行にまたがる「」台詞の継続行の冒頭に全角空白（U+3000）を挿入する。
以下の行は挿入対象外:
  - 台詞の最初の行（「 で始まる行）
  - 数式のみの行（$$...$$ および複数行 $$ ブロックの内部）
  - 空行
  - Markdown のブロック要素として解釈される行（箇条書き・表・見出し・引用）。
    行頭に全角空白を入れるとレンダリングが壊れるため。
冪等（既に全角空白で始まる行には二重に挿入しない）。

usage: indent_dialogue.py <file.md> [--check]
  --check: 変更せず、変更が必要な行番号を表示して終了コード1を返す
"""
import re
import sys

FWSP = "　"
SPEAKER_RE = re.compile(r"^\*\*.+\*\*：\s*$")
# 行頭に全角空白を入れると壊れる Markdown ブロック要素
BLOCK_RE = re.compile(r"^(?:[-*+] |\d+\. |\||>|#{1,6} |```)")


def process(lines):
    out = []
    changed = []  # 1-indexed line numbers that were modified
    depth = 0          # 「」の入れ子深さ（>0 なら台詞の内部）
    in_math = False    # 複数行 $$ ブロックの内部
    prev_nonblank = ""

    for i, line in enumerate(lines, 1):
        body = line.rstrip("\n")

        if depth == 0:
            # 台詞の開始判定: 直前の非空行が話者行で、この行が 「 で始まる
            if body.startswith("「") and SPEAKER_RE.match(prev_nonblank):
                depth = max(0, body.count("「") - body.count("」"))
            if body.strip():
                prev_nonblank = body
            out.append(line)
            continue

        # ---- 台詞の内部（継続行） ----
        if in_math:
            if body.count("$$") % 2 == 1:
                in_math = False
            out.append(line)
            continue

        if not body.strip():
            out.append(line)
            continue

        stripped = body.lstrip(FWSP + " \t")
        if stripped.startswith("$$"):
            if body.count("$$") % 2 == 1:
                in_math = True
            out.append(line)
            continue

        if BLOCK_RE.match(body):
            depth += body.count("「") - body.count("」")
            if depth <= 0:
                depth = 0
            out.append(line)
            continue

        if not body.startswith(FWSP):
            line = FWSP + line
            changed.append(i)

        depth += body.count("「") - body.count("」")
        if depth <= 0:
            depth = 0
        prev_nonblank = body
        out.append(line)

    return out, changed


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out, changed = process(lines)
    if check:
        for n in changed:
            print(f"{path}:{n}: needs indent")
        print(f"{len(changed)} line(s) need indent")
        return 1 if changed else 0
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
    print(f"{path}: {len(changed)} line(s) indented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
