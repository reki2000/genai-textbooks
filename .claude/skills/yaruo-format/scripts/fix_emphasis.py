#!/usr/bin/env python3
"""やる夫式教材の強調記号 (**) の書式修正。

CommonMark の flanking 規則では、`**` の外側が文字（非空白・非約物）で
内側が約物（。、「」（）：など）に接していると、強調の開始／終了記号として
認識されず `**` がそのまま表示されてしまう。

  壊れる例: だお**「重要」**と言った   （** がそのまま見える）
  修正後:   だお **「重要」** と言った （外側に半角スペースを挿入）

修正は「壊れている側の外側に半角スペースを1つ挿入する」のみ。
正しくレンダリングされる箇所には触れない。冪等。

対象外（検出も修正もしない）:
  - フェンスコードブロック（```）の内部
  - インラインコード（`...`）の内部
  - 数式（$$ ブロック、行内の $...$ / $$...$$）の内部

自動修正できないパターンは警告として報告する:
  - `**` の内側が空白（例: ** 重要**）
  - 1行内の `**` が奇数個（対応が取れない）
  - 長さが2以外の * の連続（*italic* や ***both***）

usage: fix_emphasis.py <file.md> [--check]
  --check: 変更せず、修正が必要な行番号を表示して終了コード1を返す
"""
import re
import sys
import unicodedata

RUN_RE = re.compile(r"(?<!\*)\*+(?!\*)")
# インラインコード・行内数式（マスクして * の検出から除外する）
INLINE_SKIP_RE = re.compile(r"`[^`]*`|\$\$[^$]+\$\$|\$[^$\n]+\$")


def is_space(ch):
    # 行頭・行末（空文字）は CommonMark では空白扱い
    return ch == "" or ch.isspace()


def is_punct(ch):
    # CommonMark 0.30 の「Unicode punctuation」= P* および S* カテゴリ
    return ch != "" and unicodedata.category(ch)[0] in ("P", "S")


def left_flanking(before, after):
    if is_space(after):
        return False
    if not is_punct(after):
        return True
    return is_space(before) or is_punct(before)


def right_flanking(before, after):
    if is_space(before):
        return False
    if not is_punct(before):
        return True
    return is_space(after) or is_punct(after)


def process_line(body):
    """1行を処理し (修正後の行, 修正したか, 警告リスト) を返す。"""
    masked = INLINE_SKIP_RE.sub(lambda m: "\x00" * len(m.group()), body)
    runs = [
        m for m in RUN_RE.finditer(masked)
        if m.start() == 0 or masked[m.start() - 1] != "\\"
    ]
    if not runs:
        return body, False, []

    if any(len(m.group()) != 2 for m in runs):
        return body, False, ["長さ2以外の * の連続があるためスキップ"]
    if len(runs) % 2 == 1:
        return body, False, ["** が奇数個あり対応が取れないためスキップ"]

    inserts = []  # 半角スペースを挿入する位置
    warns = []
    for k in range(0, len(runs), 2):
        op, cl = runs[k], runs[k + 1]
        ob = masked[op.start() - 1] if op.start() > 0 else ""
        oa = masked[op.end()] if op.end() < len(masked) else ""
        cb = masked[cl.start() - 1] if cl.start() > 0 else ""
        ca = masked[cl.end()] if cl.end() < len(masked) else ""

        if not left_flanking(ob, oa):
            if is_space(oa):
                warns.append(f"col {op.start() + 1}: ** の直後が空白（手動修正が必要）")
            else:
                inserts.append(op.start())
        if not right_flanking(cb, ca):
            if is_space(cb):
                warns.append(f"col {cl.start() + 1}: ** の直前が空白（手動修正が必要）")
            else:
                inserts.append(cl.end())

    for pos in sorted(inserts, reverse=True):
        body = body[:pos] + " " + body[pos:]
    return body, bool(inserts), warns


def process(lines):
    out = []
    changed = []   # 1-indexed 修正行
    warnings = []  # (行番号, メッセージ)
    in_fence = False
    in_math = False

    for i, line in enumerate(lines, 1):
        body = line.rstrip("\n")
        stripped = body.lstrip("　 \t")

        if in_fence:
            if stripped.startswith("```"):
                in_fence = False
            out.append(line)
            continue
        if in_math:
            if body.count("$$") % 2 == 1:
                in_math = False
            out.append(line)
            continue
        if stripped.startswith("```"):
            in_fence = True
            out.append(line)
            continue
        if stripped.startswith("$$") and body.count("$$") % 2 == 1:
            in_math = True
            out.append(line)
            continue

        eol = line[len(body):]
        fixed, did, warns = process_line(body)
        if did:
            changed.append(i)
        for w in warns:
            warnings.append((i, w))
        out.append(fixed + eol)

    return out, changed, warnings


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out, changed, warnings = process(lines)
    for n, w in warnings:
        print(f"{path}:{n}: warning: {w}")
    if check:
        for n in changed:
            print(f"{path}:{n}: needs emphasis fix")
        print(f"{len(changed)} line(s) need emphasis fix")
        return 1 if changed else 0
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
    print(f"{path}: {len(changed)} line(s) fixed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
