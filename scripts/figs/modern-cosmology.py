#!/usr/bin/env python3
"""docs/books/modern-cosmology/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, VIOLET, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "modern-cosmology" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


def fig_expansion() -> None:
    s = Svg(760, 400, "図1　中心から飛ぶのではない ── 格子そのものの一様膨張",
            "どの観測者を原点に選んでも、距離が大きい点ほど速く遠ざかる（v = HD）")

    def panel(x0: float, title: str, observer: tuple[int, int]) -> None:
        s.text(x0 + 150, 86, title, size=13, anchor="middle", weight="700")
        spacing, ox, oy = 52, x0 + 46, 116
        for j in range(4):
            s.line(ox, oy + j * spacing, ox + 5 * spacing, oy + j * spacing, stroke=GRID)
        for i in range(6):
            s.line(ox + i * spacing, oy, ox + i * spacing, oy + 3 * spacing, stroke=GRID)
        oi, oj = observer
        px, py = ox + oi * spacing, oy + oj * spacing
        for i, j in ((0, 0), (2, 0), (5, 0), (0, 3), (2, 2), (5, 3)):
            x, y = ox + i * spacing, oy + j * spacing
            if (i, j) != observer:
                dx, dy = x - px, y - py
                length = math.hypot(dx, dy)
                if length:
                    # 矢印長は観測者からの距離に比例（図示倍率 0.14）。
                    s.arrow(x, y, x + dx * 0.14, y + dy * 0.14, color=BLUE, sw=1.5)
            s.circle(x, y, 5, fill=ORANGE if (i, j) == observer else BLUE)
        s.circle(px, py, 11, fill="none", stroke=ORANGE, sw=2)
        s.text(px, py + 28, "観測者", size=10.5, fill=ORANGE, anchor="middle", weight="700")

    panel(36, "中央の点を原点にしても", (2, 2))
    panel(414, "端の点を原点にしても", (0, 3))
    s.arrow(356, 196, 404, 196, color=INK2, sw=1.8)
    s.lines_of_text(380, 224, ["原点を", "変更"], size=10.5, fill=INK2, anchor="middle", lh=14)
    s.rect(118, 330, 524, 42, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(380, 356, "観測者からの距離 D が 2 倍なら矢印も 2 倍 ── 中心は選び出されない",
           size=12.5, anchor="middle", weight="700")
    s.save("fig1-centerless-expansion.svg")


def fig_density_scaling() -> None:
    s = Svg(760, 450, "図2　膨張で宇宙の主役が交代する",
            "同じ尺度因子の増加でも、放射 a^-4・物質 a^-3・曲率 a^-2・宇宙定数 a^0 は異なる速さで薄まる")
    L, R, T, B = 92, 704, 92, 344
    xmin, xmax, ymin, ymax = -3.0, 1.0, -4.0, 9.0

    def x(v: float) -> float: return L + (v - xmin) / (xmax - xmin) * (R - L)
    def y(v: float) -> float: return B - (v - ymin) / (ymax - ymin) * (B - T)

    for v in range(-3, 2):
        s.line(x(v), T, x(v), B, stroke=GRID)
        s.text(x(v), B + 20, f"10^{v}", size=11, fill=INK3, anchor="middle")
    for v in (-4, 0, 4, 8):
        s.line(L, y(v), R, y(v), stroke=GRID)
        s.text(L - 10, y(v) + 4, f"10^{v}", size=10.5, fill=INK3, anchor="end")
    s.line(L, B, R, B, stroke=INK3)
    s.line(L, T, L, B, stroke=INK3)
    s.text((L + R) / 2, B + 43, "尺度因子 a（現在を 1）", size=12, fill=INK2, anchor="middle")
    s.text(24, 80, "相対密度（任意単位・対数）", size=11, fill=INK2)

    series = [("放射  a^-4", -4, 0.5, ORANGE, -1.58), ("物質  a^-3", -3, 0, BLUE, -1.76),
              ("曲率  a^-2（幾何項）", -2, -1.2, VIOLET, -1.68), ("宇宙定数  a^0", 0, -0.8, AQUA, -0.82)]
    for label, slope, intercept, color, label_x in series:
        pts = []
        for i in range(101):
            xv = xmin + (xmax - xmin) * i / 100
            yv = slope * xv + intercept
            if ymin <= yv <= ymax:
                pts.append((x(xv), y(yv)))
        s.path("M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts), stroke=color, sw=2.7,
               dash="7 4" if "曲率" in label else None)
        s.text(x(label_x) + 8, y(slope * label_x + intercept) - 8, label, size=11.5, fill=color, weight="700")
    s.arrow(190, 386, 570, 386, color=INK2, sw=1.5)
    s.text(380, 411, "時間の向き：小さい a（過去） → 大きい a（未来）", size=12, fill=INK2, anchor="middle")
    s.text(154, 112, "過去：放射が残りやすい", size=11.5, fill=ORANGE, weight="700")
    s.text(690, 327, "未来：定数項が残る", size=11.5, fill=AQUA, anchor="end", weight="700")
    s.save("fig2-density-scaling.svg")


def fig_horizon_exit() -> None:
    s = Svg(760, 430, "図3　同じ共動スケールが地平線を出て、後に戻る",
            "インフレーション中は c/(aH) が縮み、通常膨張では育つ。固定された波長との交差が地平線退出・再突入になる")
    L, R, T, B = 86, 704, 96, 316
    split = 326
    s.rect(L, T, split - L, B - T, fill="#f2f0ff", stroke="none", rx=5)
    s.rect(split, T, R - split, B - T, fill="#eef9f5", stroke="none", rx=5)
    for frac in (0.25, 0.5, 0.75):
        yy = T + frac * (B - T)
        s.line(L, yy, R, yy, stroke=GRID)
    s.line(L, B, R, B, stroke=INK3)
    s.line(split, T, split, B, stroke=INK3, dash="4 4")
    s.text((L + split) / 2, 84, "インフレーション（加速膨張）", size=12, fill=VIOLET, anchor="middle", weight="700")
    s.text((split + R) / 2, 84, "放射・物質優勢（減速膨張）", size=12, fill=AQUA, anchor="middle", weight="700")
    fixed_y = 204
    s.line(L, fixed_y, R, fixed_y, stroke=BLUE, sw=2.7)
    s.text(R - 4, fixed_y - 10, "固定した共動波長 λ", size=12, fill=BLUE, anchor="end", weight="700")
    # 左で減少、右で増加する連続曲線。交点は解析的に指定した2点。
    x_exit, x_re = 222, 548
    s.path(f"M{L},{T + 24} L{x_exit},{fixed_y} L{split},{B - 22} Q470,{B - 4} {x_re},{fixed_y} L{R},{T + 34}",
           stroke=ORANGE, sw=3)
    s.text(106, 130, "共動ハッブル半径 c/(aH)", size=12, fill=ORANGE, weight="700")
    for xx, label in ((x_exit, "退出"), (x_re, "再突入")):
        s.circle(xx, fixed_y, 6, fill="#ffffff", stroke=RED, sw=2.2)
        s.line(xx, fixed_y + 8, xx, B, stroke=RED, dash="3 3")
        s.text(xx, B + 22, label, size=12, fill=RED, anchor="middle", weight="700")
    s.text((x_exit + x_re) / 2, 178, "地平線の外：因果的な微視過程では届かない",
           size=11.5, fill=INK2, anchor="middle", weight="700")
    s.arrow(L + 28, 370, R - 28, 370, color=INK2, sw=1.5)
    s.text((L + R) / 2, 397, "宇宙の時間 →", size=12, fill=INK2, anchor="middle")
    s.save("fig3-horizon-exit-reentry.svg")


FIGURES = (fig_expansion, fig_density_scaling, fig_horizon_exit)


def generate(out_dir: Path) -> None:
    global Svg
    Svg = partial(SvgDocument, out_dir=out_dir)
    for fn in FIGURES:
        fn()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        generate(OUT_DIR)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        generated = Path(tmp)
        generate(generated)
        expected = sorted(p.name for p in OUT_DIR.glob("*.svg")) if OUT_DIR.exists() else []
        actual = sorted(p.name for p in generated.glob("*.svg"))
        if expected != actual:
            print(f"figure set differs: expected={expected}, generated={actual}", file=sys.stderr)
            return 1
        bad = [name for name in actual if (OUT_DIR / name).read_bytes() != (generated / name).read_bytes()]
        if bad:
            print("out of date: " + ", ".join(bad), file=sys.stderr)
            return 1
    print("all modern-cosmology figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
