#!/usr/bin/env python3
"""docs/books/nature-of-time/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "nature-of-time" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


def fig_relativity_of_simultaneity() -> None:
    s = Svg(760, 430, "図1　列車内の「同時」は、地上では同時でない", "同じ三つの出来事でも、列車系では両端へ同時到着、地上系では後端へ先に到着する")
    panels = [(24, "列車内の座標", False), (392, "地上の座標（列車は右へ）", True)]
    for px, label, ground in panels:
        s.rect(px, 82, 344, 284, fill="#ffffff", stroke=CARD_EDGE, rx=8)
        s.text(px + 172, 108, label, size=13, anchor="middle", weight="700", fill=BLUE)
        y = 220
        if ground:
            # 地上系では発光後に列車全体が右へ進む。到着時の端を実線で示す。
            s.rect(px + 88, y - 45, 214, 90, fill="#f3f8ff", stroke=BLUE, rx=8, sw=1.8)
            rear, front, flash = px + 88, px + 302, px + 174
            s.arrow(px + 120, 142, px + 225, 142, color=INK2, sw=1.8)
            s.text(px + 238, 146, "v", size=13, fill=INK2, weight="700")
            s.circle(flash, y, 7, fill=ORANGE)
            s.arrow(flash - 8, y, rear + 4, y, color=ORANGE, sw=2.2)
            # 後端へ到着した同じ瞬間、右向き光はまだ逃げる前端へ届いていない。
            s.arrow(flash + 8, y, front - 28, y, color=ORANGE, sw=2.2)
            s.circle(rear, y, 6, fill=RED)
            s.circle(front, y, 6, fill="#ffffff", stroke=INK3, sw=2)
            s.text(rear, 292, "後端：先に到着", size=12, fill=RED, anchor="middle", weight="700")
            s.text(front, 292, "前端：後で到着", size=12, fill=INK2, anchor="middle", weight="700")
        else:
            s.rect(px + 65, y - 45, 214, 90, fill="#f3f8ff", stroke=BLUE, rx=8, sw=1.8)
            rear, front, flash = px + 65, px + 279, px + 172
            s.circle(flash, y, 7, fill=ORANGE)
            s.arrow(flash - 8, y, rear + 4, y, color=ORANGE, sw=2.2)
            s.arrow(flash + 8, y, front - 4, y, color=ORANGE, sw=2.2)
            s.circle(rear, y, 6, fill=AQUA)
            s.circle(front, y, 6, fill=AQUA)
            s.text(px + 172, 292, "両端：同時に到着", size=12, fill=AQUA, anchor="middle", weight="700")
        s.text(rear, 247, "後端", size=10.5, fill=INK2, anchor="middle")
        s.text(front, 247, "前端", size=10.5, fill=INK2, anchor="middle")
        s.text(flash, 202, "発光", size=10.5, fill=ORANGE, anchor="middle", weight="700")
    s.text(380, 402, "光速はどちらの座標でも c。それでも離れた出来事の同時性は運動状態に依存する。", size=12, anchor="middle", weight="700")
    s.save("fig1-relativity-of-simultaneity.svg")


def fig_gps_clock_budget() -> None:
    s = Svg(760, 390, "図2　GPS時計のずれは、速度と重力の差し引き", "1日あたり：速度で −7.2 μs、弱い重力で +46 μs、合計は約 +38 μs")
    cx = 380
    s.line(90, 220, 670, 220, stroke=INK3, sw=1.5)
    s.line(cx, 126, cx, 308, stroke=INK, sw=1.8)
    s.text(cx, 333, "地上時計との差 0", size=11.5, anchor="middle", fill=INK2)
    scale = 4.0
    # 0 を共通起点にした符号付き棒。本文の丸め値をそのまま使う。
    s.rect(cx - 7.2 * scale, 150, 7.2 * scale, 45, fill=ORANGE, stroke=ORANGE, rx=5, opacity=.85)
    s.text(cx - 7.2 * scale - 10, 178, "速度  −7.2 μs", size=13, fill=ORANGE, anchor="end", weight="700")
    s.rect(cx, 225, 46 * scale, 45, fill=BLUE, stroke=BLUE, rx=5, opacity=.85)
    s.text(cx + 46 * scale + 10, 253, "重力  +46 μs", size=13, fill=BLUE, weight="700")
    net_x = cx + 38 * scale
    s.line(net_x, 113, net_x, 294, stroke=AQUA, sw=2.4, dash="5 4")
    s.text(net_x, 103, "差し引き 約 +38 μs/日", size=13, fill=AQUA, anchor="middle", weight="700")
    s.box(205, 344, 350, 36, "未補正なら測位誤差は約11 km/日", color=RED, size=12.5)
    s.save("fig2-gps-clock-budget.svg")


def fig_causal_record() -> None:
    s = Svg(760, 430, "図3　記録できるのは、現在 P へ因果信号が届く側", "過去の出来事は P に痕跡を作れるが、未来の出来事から通常の信号は P へ戻れない")
    px, py = 380, 236
    # 光円錐の境界と領域
    s.path(f"M{px},{py} L205,70 L555,70 Z", fill="#edf9f4", stroke=AQUA, sw=1.8, opacity=.9)
    s.path(f"M{px},{py} L205,398 L555,398 Z", fill="#eef6ff", stroke=BLUE, sw=1.8, opacity=.9)
    s.circle(px, py, 8, fill=INK)
    s.text(px + 14, py + 5, "現在の出来事 P", size=13, weight="700")
    s.text(px, 94, "未来光円錐", size=13, fill=AQUA, anchor="middle", weight="700")
    s.text(px, 386, "過去光円錐", size=13, fill=BLUE, anchor="middle", weight="700")
    past = (300, 336)
    future = (470, 126)
    s.circle(*past, 7, fill=BLUE)
    s.text(past[0] - 12, past[1] + 5, "過去の出来事", size=11.5, fill=BLUE, anchor="end", weight="700")
    s.arrow(past[0] + 7, past[1] - 7, px - 8, py + 8, color=BLUE, sw=2.3)
    s.text(286, 275, "信号 → 現在の痕跡", size=11.5, fill=BLUE, anchor="middle")
    s.circle(*future, 7, fill=AQUA)
    s.text(future[0] + 12, future[1] + 5, "未来の出来事", size=11.5, fill=AQUA, weight="700")
    s.arrow(px + 8, py - 8, future[0] - 7, future[1] + 7, color=AQUA, sw=2.3)
    s.arrow(future[0] - 12, future[1] + 12, px + 18, py - 18, color=RED, sw=1.8, dash="5 4")
    s.line(418, 177, 442, 201, stroke=RED, sw=3)
    s.line(442, 177, 418, 201, stroke=RED, sw=3)
    s.text(534, 195, "未来 → P は不可", size=11.5, fill=RED, anchor="middle", weight="700")
    s.text(380, 419, "「未来が存在するか」と「未来から情報を読めるか」は別の問い。", size=12, anchor="middle", weight="700")
    s.save("fig3-causal-record.svg")


def fig_branch_point() -> None:
    s = Svg(760, 390, "図4　点を除くと、直線は2成分・分岐点は3成分", "分岐点の近傍は開区間と同相でないため、通常の1次元多様体にはならない")
    panels = [(28, "実数直線の内部点", False), (392, "樹の分岐点", True)]
    for px, title, branched in panels:
        s.rect(px, 82, 340, 242, fill="#ffffff", stroke=CARD_EDGE, rx=8)
        s.text(px + 170, 110, title, size=13, anchor="middle", weight="700", fill=BLUE if not branched else ORANGE)
        cx, cy = px + 170, 190
        s.line(px + 55, cy, cx - 12, cy, stroke=BLUE, sw=4)
        if branched:
            s.line(cx + 12, cy - 8, px + 285, 140, stroke=ORANGE, sw=4)
            s.line(cx + 12, cy + 8, px + 285, 240, stroke=AQUA, sw=4)
        else:
            s.line(cx + 12, cy, px + 285, cy, stroke=AQUA, sw=4)
        s.circle(cx, cy, 10, fill="#ffffff", stroke=RED, sw=2.5, dash="3 3")
        s.text(cx, cy + 4, "×", size=14, fill=RED, anchor="middle", weight="700")
        s.text(px + 170, 286, "点を除く → 3成分" if branched else "点を除く → 2成分", size=14, anchor="middle", weight="700", fill=RED if branched else INK)
    s.text(380, 359, "成分数は同相写像で変わらない：3成分の近傍を開区間へ変形できない。", size=12, anchor="middle", weight="700")
    s.save("fig4-branch-point.svg")


FIGURES = (fig_relativity_of_simultaneity, fig_gps_clock_budget, fig_causal_record, fig_branch_point)


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
    with tempfile.TemporaryDirectory(prefix="nature-of-time-figs-") as tmp:
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
