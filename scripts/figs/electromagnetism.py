#!/usr/bin/env python3
"""docs/books/electromagnetism/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, ORANGE, RED, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "electromagnetism" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


def fig_displacement_current() -> None:
    s = Svg(760, 430, "図1　同じ境界 C なら、どの面を張っても同じ磁場", "充電中のコンデンサ：導線では伝導電流 I、隙間では電束の変化が同じ役割を担う")

    def panel(x: float, corrected: bool) -> None:
        w = 336
        s.rect(x, 82, w, 266, fill="#ffffff", stroke=CARD_EDGE, rx=8)
        s.text(x + 16, 107, "修正後" if corrected else "元のアンペールの法則", size=13, weight="700", fill=AQUA if corrected else RED)
        # 導線とコンデンサ極板
        cx = x + 168
        s.line(cx, 122, cx, 188, stroke=INK, sw=3)
        s.line(cx, 238, cx, 313, stroke=INK, sw=3)
        s.rect(cx - 70, 188, 140, 7, fill=INK, rx=2)
        s.rect(cx - 70, 231, 140, 7, fill=INK, rx=2)
        s.arrow(cx, 142, cx, 178, color=ORANGE, sw=2.3)
        s.text(cx + 12, 158, "I", size=13, fill=ORANGE, weight="700")
        # 同一境界 C（楕円を path で表現）
        s.path(f"M{cx-102},166 C{cx-102},142 {cx+102},142 {cx+102},166 C{cx+102},190 {cx-102},190 {cx-102},166", stroke=BLUE, sw=2.2)
        s.text(cx - 112, 151, "C", size=13, fill=BLUE, weight="700")
        # 面A（導線を横切る）と面B（隙間へ膨らむ）
        s.path(f"M{cx-101},166 C{cx-72},123 {cx+72},123 {cx+101},166", stroke=ORANGE, sw=1.5, dash="5 4")
        s.text(x + 16, 137, "面A：導線を横切る", size=11, fill=ORANGE)
        s.path(f"M{cx-101},166 C{cx-82},278 {cx+82},278 {cx+101},166", stroke=AQUA, sw=1.7, dash="5 4")
        s.text(x + 16, 329, "面B：隙間を横切る", size=11, fill=AQUA)
        # 増加する電場（電子の移動と誤読させない破線矢印）
        for dx in (-42, 0, 42):
            s.arrow(cx + dx, 202, cx + dx, 225, color=AQUA, sw=1.5, dash="3 3")
        s.text(cx + 78, 218, "∂E/∂t", size=11, fill=AQUA, weight="700")

        if corrected:
            s.text(cx, 370, "面A：I　＝　面B：Id", size=14, fill=AQUA, anchor="middle", weight="700")
            s.text(cx, 394, "どちらも磁場の一周分は同じ", size=12, fill=INK2, anchor="middle")
        else:
            s.text(cx, 370, "面A：I　≠　面B：0", size=14, fill=RED, anchor="middle", weight="700")
            s.text(cx, 394, "同じ C なのに答えが割れる", size=12, fill=RED, anchor="middle")

    panel(24, False)
    panel(400, True)
    s.arrow(368, 211, 392, 211, color=INK2, sw=1.8)
    s.save("fig1-displacement-current.svg")


def fig_em_wave() -> None:
    s = Svg(760, 410, "図2　電磁波は、直交する E と B が同位相で進む", "波は x 方向へ進み、各点で E は y 方向、B は z 方向。E × B がエネルギーの進行方向を示す")
    left, right, axis_y = 78, 704, 226
    s.arrow(left, axis_y, right, axis_y, color=INK, sw=1.8)
    s.text(right, axis_y + 21, "+x（進行方向 S）", size=12, anchor="end", weight="700")
    # 同じ位相を、上下に分けた同形の正弦波で示す
    points_e, points_b = [], []
    for i in range(241):
        x = left + (right - left) * i / 240
        phase = 4 * math.pi * i / 240
        points_e.append((x, 146 - 50 * math.sin(phase)))
        points_b.append((x, 306 - 42 * math.sin(phase)))
    s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points_e), stroke=BLUE, sw=2.6)
    s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points_b), stroke=ORANGE, sw=2.6)
    s.line(left, 146, right, 146, stroke=GRID, sw=1)
    s.line(left, 306, right, 306, stroke=GRID, sw=1)
    s.text(28, 112, "E (y方向)", size=14, fill=BLUE, weight="700")
    s.text(28, 282, "B (z方向)", size=14, fill=ORANGE, weight="700")
    # 同位相の山を結ぶ
    crest_x = left + (right - left) / 8
    s.line(crest_x, 92, crest_x, 264, stroke=INK2, sw=1.2, dash="4 4")
    s.circle(crest_x, 96, 4, fill=BLUE)
    s.circle(crest_x, 264, 4, fill=ORANGE)
    s.text(crest_x + 9, 120, "山の位置が一致（同位相）", size=11.5, fill=INK2, weight="700")
    # 右下に局所的な右手系を明示
    ox, oy = 572, 354
    s.arrow(ox, oy, ox + 92, oy, color=INK, sw=2)
    s.arrow(ox, oy, ox, oy - 72, color=BLUE, sw=2)
    s.circle(ox, oy, 15, fill="#ffffff", stroke=ORANGE, sw=2)
    s.circle(ox, oy, 3.5, fill=ORANGE)
    s.text(ox + 98, oy + 4, "E × B", size=11.5, weight="700")
    s.text(ox - 8, oy - 79, "E (+y)", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.text(ox - 22, oy + 5, "B (+z)：手前", size=11, fill=ORANGE, anchor="end", weight="700")
    s.text(24, 392, "同じ位相で E = cB。2本が別々に追いかけるのではなく、1つの電磁波としてエネルギーを運ぶ。", size=11.5, fill=INK2)
    s.save("fig2-electromagnetic-wave.svg")


FIGURES = (fig_displacement_current, fig_em_wave)


def render_all(out_dir: Path) -> None:
    global Svg
    Svg = partial(SvgDocument, out_dir=out_dir)
    for render in FIGURES:
        render()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        render_all(OUT_DIR)
        return 0
    with tempfile.TemporaryDirectory(prefix="electromagnetism-figs-") as tmp:
        generated_dir = Path(tmp)
        render_all(generated_dir)
        generated = {p.name: p for p in generated_dir.glob("*.svg")}
        existing = {p.name: p for p in OUT_DIR.glob("*.svg")}
        stale = sorted(name for name in generated.keys() | existing.keys()
                       if name not in generated or name not in existing
                       or generated[name].read_bytes() != existing[name].read_bytes())
    if stale:
        print("stale, missing, or unexpected figures:", file=sys.stderr)
        for name in stale:
            print(f"  {OUT_DIR / name}", file=sys.stderr)
        return 1
    print(f"OK: {len(generated)} figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
