#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""図版の機械検査と目視用 PNG の書き出し。

  python check_figure.py "docs/books/<id>/figs/*.svg" [--png-dir DIR]

NG（終了コード1）
  - 豆腐：日本語フォントに無い文字（上付き・下付き・装飾記号）
  - はみ出し：rect / text が viewBox の外
  - 文字が小さい：スマホ本文幅 340px へ縮めて実効 6px 未満
  - 多すぎる：2文字以上のラベルが 22 種を超える
注意（合否に使わない）
  - 4枚以上がすべて同じ幅・似た縦横比（形を内容から選んだか）

--png-dir を付けると、原寸（2倍密度）と 360px 幅の PNG を書き出す。必ず目で見ること。
"""
import glob
import os
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MOBILE, MIN_PX, MAX_LABELS = 340, 6.0, 22


def charset():
    try:
        from fontTools.ttLib import TTCollection
        return {c for f in TTCollection(FONT).fonts for t in f["cmap"].tables for c in t.cmap}
    except Exception:
        print(f"※ {FONT} を読めないので豆腐検査を省く（fonts-noto-cjk と fonttools を入れる）")
        return None


def check(path, cs):
    root = ET.parse(path).getroot()
    _, _, W, H = (float(v) for v in root.get("viewBox").split())
    texts = [(e, (e.text or "").strip()) for e in root.iter(NS + "text")]
    issues = []

    bad = {ch for _, t in texts for ch in t if cs is not None and ord(ch) not in cs}
    if bad:
        issues.append(f"豆腐になる文字: {' '.join(sorted(bad))}（n2 / SiO2 / × と書く）")

    out = []
    for e in root.iter(NS + "rect"):
        x, y = float(e.get("x", 0)), float(e.get("y", 0))
        if x < -1 or y < -1 or x + float(e.get("width", 0)) > W + 1 \
                or y + float(e.get("height", 0)) > H + 1:
            out.append(f"rect@{x:g},{y:g}")
    for e, t in texts:
        x, y = float(e.get("x")), float(e.get("y"))
        if not (0 <= x <= W and 0 <= y <= H):
            out.append(f"{t}@{x:g},{y:g}")
    if out:
        issues.append(f"viewBox からはみ出し: {out[:6]}")

    scale = min(1.0, MOBILE / W)
    small = sorted({(float(e.get("font-size")), t) for e, t in texts
                    if float(e.get("font-size")) * scale < MIN_PX})
    if small:
        issues.append(f"スマホ幅で {MIN_PX:g}px 未満の文字（幅 {W:g} なら {MIN_PX / scale:.1f} 以上）: "
                      + " / ".join(f"{t}({z:g})" for z, t in small[:8]))

    labels = {t for _, t in texts if len(t) >= 2}
    if len(labels) > MAX_LABELS:
        issues.append(f"ラベル {len(labels)} 種（上限 {MAX_LABELS}）。図を分ける: "
                      + " / ".join(sorted(labels)))

    print(f"[{'NG' if issues else 'ok'}] {os.path.basename(path)}  {W:g}x{H:g} ラベル{len(labels)}")
    for m in issues:
        print(f"     - {m}")
    return len(issues), (W, H / W)


def render(path, png_dir):
    import cairosvg
    os.makedirs(png_dir, exist_ok=True)
    stem = os.path.join(png_dir, os.path.basename(path)[:-4])
    cairosvg.svg2png(url=path, write_to=stem + ".png", scale=2)
    cairosvg.svg2png(url=path, write_to=stem + ".360.png", output_width=360)
    print(f"     PNG: {stem}.png / {stem}.360.png")


def main(argv):
    png_dir = argv[argv.index("--png-dir") + 1] if "--png-dir" in argv else None
    files = sorted(f for a in argv if a.endswith(".svg") for f in glob.glob(a))
    cs = charset()
    n, shapes = 0, []
    for f in files:
        k, shape = check(f, cs)
        n += k
        shapes.append(shape)
        if png_dir:
            render(f, png_dir)
    widths = {w for w, _ in shapes}
    ratios = [r for _, r in shapes]
    if len(shapes) >= 4 and len(widths) == 1 and max(ratios) - min(ratios) < 0.3:
        print(f"\n? 全 {len(shapes)} 枚が幅 {widths.pop():g}・縦横比 {min(ratios):.2f}〜"
              f"{max(ratios):.2f}。形を内容から選んだか layout.md で見直す")
    print(f"\n{len(files)} 枚中 指摘 {n} 件")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
