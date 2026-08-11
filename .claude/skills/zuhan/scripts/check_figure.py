#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""図版の機械検査。内省では捕まらない事故だけを見る。

  python check_figure.py fig.svg [fig2.svg ...] [--png-dir DIR] [--labels]

検査項目
  1. 豆腐  … 指定フォントに存在しない文字（上付き・下付き・記号類）
  2. 交差  … <line> 同士が内部で交わっている（T字接合は正常なので除外）
  3. はみ出し … 要素が viewBox の外へ出ている
  4. 規模  … <text> の数・色数（1図1論点の目安を超えていないか）
必ず PNG も書き出す。最後は人間（またはモデル）が画像を見て確かめること。

ラベルの数え方は「2文字以上の <text> を、同一文字列は1個として数える」。
上限に当たったときにどれを削るか判断できるよう、超過時は数えたラベルを全部並べる。
設計中に見積もりたいときは `--labels` を付ければ、合格していても一覧が出る。
"""
import sys, re, os, glob
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]
# フォントを読めない環境でも最低限これは弾く（CJKフォントに無いことが多い）
FALLBACK_BAD = set("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻₀₁₂₃₄₅₆₇₈₉✓✔✕✖✗✘➜➔⟶⇒▲▼◀▶")


def font_charset():
    try:
        from fontTools.ttLib import TTFont, TTCollection
    except ImportError:
        return None
    for p in FONT_CANDIDATES:
        if not os.path.exists(p):
            continue
        try:
            fonts = TTCollection(p).fonts if p.endswith(".ttc") else [TTFont(p)]
            cs = set()
            for f in fonts:
                for t in f["cmap"].tables:
                    cs |= set(t.cmap.keys())
            return cs
        except Exception:
            continue
    return None


def seg_cross(a, b):
    """線分 a,b が内部で交わるなら交点を返す。端点接触・T字接合は None。"""
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-9:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    e = 0.02                      # 端点まわりの許容。T字接合を交差と呼ばないため
    if e < t < 1 - e and e < u < 1 - e:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def check(path, charset, png_dir=None, show_labels=False):
    tree = ET.parse(path)
    root = tree.getroot()
    vb = [float(v) for v in (root.get("viewBox") or "0 0 0 0").split()]
    issues, notes = [], []

    # 1. 豆腐
    texts = [(e.text or "") for e in root.iter(NS + "text")]
    bad = set()
    for t in texts:
        for ch in t:
            if ord(ch) < 32:
                continue
            if charset is not None:
                if ord(ch) not in charset:
                    bad.add(ch)
            elif ch in FALLBACK_BAD:
                bad.add(ch)
    if bad:
        issues.append(f"豆腐になる文字: {' '.join(sorted(bad))}"
                      "（上付き・下付き・装飾記号は使わない。n+ / SiO2 / × と書く）")

    # 2. 交差
    segs = []
    for e in root.iter(NS + "line"):
        role = e.get("data-role")
        if role == "glyph":
            continue
        try:
            segs.append(((float(e.get("x1")), float(e.get("y1")),
                          float(e.get("x2")), float(e.get("y2"))), role))
        except (TypeError, ValueError):
            pass
    hard, soft = [], []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            p = seg_cross(segs[i][0], segs[j][0])
            if not p:
                continue
            pt = (round(p[0], 1), round(p[1], 1))
            if segs[i][1] == segs[j][1] == "connector":
                hard.append(pt)
            else:
                soft.append(pt)
    if hard:
        issues.append(f"接続線どうしが交差 {len(hard)} 箇所: {hard[:6]}"
                      "（引き回しではなく配置を変えて直す。交差は要素過多の兆候）")
    if soft:
        notes.append(f"線の交差 {len(soft)} 箇所（参考）: {soft[:6]}"
                     " ← 経路の矢印が領域の境界を横切っているだけなら問題ない")

    # 3. はみ出し
    if len(vb) == 4:
        W, H = vb[2], vb[3]
        out = []
        for e in root.iter(NS + "rect"):
            try:
                x, y = float(e.get("x")), float(e.get("y"))
                w, h = float(e.get("width")), float(e.get("height"))
            except (TypeError, ValueError):
                continue
            if x < -1 or y < -1 or x + w > W + 1 or y + h > H + 1:
                out.append("rect")
        for e in root.iter(NS + "text"):
            try:
                x, y = float(e.get("x")), float(e.get("y"))
            except (TypeError, ValueError):
                continue
            if not (-1 <= x <= W + 1 and -1 <= y <= H + 1):
                out.append(f"text@{x},{y}")
        if out:
            issues.append(f"viewBox からはみ出し: {out[:6]}")

    # 4. 規模
    labels = {t.strip() for t in texts if len(t.strip()) >= 2}  # 同一文字列は1個と数える   # 1文字は記号なのでラベルに数えない
    cols = {e.get("stroke") for e in root.iter() if e.get("stroke")} | \
           {e.get("fill") for e in root.iter() if e.get("fill")}
    def dark(c):
        m = re.fullmatch(r"#([0-9a-fA-F]{6})", c or "")
        if not m:
            return False
        r_, g_, b_ = (int(m.group(1)[k:k + 2], 16) for k in (0, 2, 4))
        return (0.299 * r_ + 0.587 * g_ + 0.114 * b_) < 216   # 淡い地色は数えない
    cols = {c for c in cols if dark(c)}
    label_list = " / ".join(sorted(labels))
    if len(labels) > 22:
        issues.append(f"ラベル {len(labels)} 個。1図1論点を超えている。パネル分割を検討\n"
                      f"       数えたラベル: {label_list}")
    elif show_labels:
        notes.append(f"数えたラベル {len(labels)}/22: {label_list}")
    if len(cols) > 8:
        issues.append(f"意味のありそうな色 {len(cols)} 種。3系統までに抑える\n"
                      f"       数えた色: {' '.join(sorted(cols))}")

    png = None
    if png_dir:
        try:
            import cairosvg
            os.makedirs(png_dir, exist_ok=True)
            png = os.path.join(png_dir, os.path.basename(path)[:-4] + ".png")
            cairosvg.svg2png(url=path, write_to=png, scale=1.4,
                             background_color="white")
        except Exception as ex:
            issues.append(f"PNG 書き出し失敗: {ex}")
            png = None

    name = os.path.basename(path)
    if issues:
        print(f"[NG] {name}")
        for m in issues:
            print(f"     - {m}")
    else:
        print(f"[ok] {name}  ラベル{len(labels)} 色{len(cols)} 線{len(segs)}")
    for m in notes:
        print(f"     ? {m}")
    if png:
        print(f"     PNG: {png}  ← 必ず目視すること")
    return len(issues)


if __name__ == "__main__":
    argv, args, png_dir, show_labels = sys.argv[1:], [], None, False
    i = 0
    while i < len(argv):
        if argv[i] == "--png-dir" and i + 1 < len(argv):
            png_dir, i = argv[i + 1], i + 2
            continue
        if argv[i] == "--labels":
            show_labels, i = True, i + 1
            continue
        if not argv[i].startswith("--"):
            args.append(argv[i])
        i += 1
    files = []
    for a in args:
        files += sorted(glob.glob(a)) if any(c in a for c in "*?") else [a]
    cs = font_charset()
    if cs is None:
        print("※ フォントを読めないので豆腐検査は簡易版（fontTools 未導入）")
    n = sum(check(f, cs, png_dir, show_labels) for f in files)
    print(f"\n{len(files)} 枚中 指摘 {n} 件")
    sys.exit(1 if n else 0)
