#!/usr/bin/env python3
"""docs/books/thermodynamics/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "thermodynamics" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


def fig_refrigerator_balance():
    s = Svg(760, 350, "図1　冷凍機は熱を消さず、仕事を足して外へ運ぶ",
            "倉庫から 92 kW を吸収し、電力 38 kW を加えるため、屋外側の放熱は 130 kW になる")
    s.box(34, 116, 170, 92, "冷凍倉庫 −20℃", "吸収される熱 92 kW", color=BLUE)
    s.box(292, 100, 176, 124, "冷凍機", "熱を低温側→高温側へ", color=AQUA)
    s.box(556, 116, 170, 92, "屋外側 35℃", "放熱 130 kW", color=ORANGE)
    s.arrow(208, 162, 284, 162, color=BLUE, sw=3)
    s.text(246, 149, "Q_C", size=12, fill=BLUE, anchor="middle", weight="700")
    s.arrow(472, 162, 548, 162, color=ORANGE, sw=3)
    s.text(510, 149, "Q_H", size=12, fill=ORANGE, anchor="middle", weight="700")
    s.box(306, 258, 148, 50, "電力 38 kW", "仕事 W", color=AQUA)
    s.arrow(380, 252, 380, 230, color=AQUA, sw=3)
    s.text(380, 81, "92 + 38 = 130 kW", size=22, fill=INK, anchor="middle", weight="700")
    s.text(380, 332, "屋外側の熱風には、倉庫から運んだ熱と圧縮機へ入れた電力の両方が含まれる", size=12, fill=INK2, anchor="middle")
    s.save("fig1-refrigerator-balance.svg")


def fig_heating_curve():
    s = Svg(760, 430, "図2　一定出力で加熱しても、温度は一直線に上がらない",
            "0℃と100℃の水平区間では、入力エネルギーが温度上昇ではなく相の変化に使われる")
    L, R, T, B = 84, 708, 88, 326
    s.line(L, T, L, B, stroke=INK3, sw=1.4)
    s.line(L, B, R, B, stroke=INK3, sw=1.4)
    s.text(28, 82, "温度", size=12, fill=INK2)
    s.text((L + R) / 2, B + 42, "投入エネルギー（時間）→", size=12, fill=INK2, anchor="middle")
    y_m20, y0, y100, y120 = 306, 266, 142, 104
    for y, lab in ((y_m20, "−20℃"), (y0, "0℃"), (y100, "100℃"), (y120, "120℃")):
        s.line(L, y, R, y, stroke=GRID, sw=1, dash="4 4")
        s.text(L - 10, y + 4, lab, size=11, fill=INK3, anchor="end")
    pts = [(96, y_m20), (170, y0), (314, y0), (426, y100), (626, y100), (690, y120)]
    s.path("M" + " L".join(f"{x},{y}" for x, y in pts), stroke=BLUE, sw=3.2)
    for x, y in pts:
        s.circle(x, y, 3.5, fill=BLUE)
    s.text(130, 286, "氷を昇温", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.text(242, 252, "融解", size=13, fill=ORANGE, anchor="middle", weight="700")
    s.text(242, 282, "334 kJ/kg", size=11.5, fill=ORANGE, anchor="middle")
    s.text(370, 202, "水を昇温", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.text(526, 128, "蒸発", size=13, fill=ORANGE, anchor="middle", weight="700")
    s.text(526, 158, "2257 kJ/kg", size=11.5, fill=ORANGE, anchor="middle")
    s.text(660, 124, "蒸気", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.arrow(242, 214, 242, 260, color=ORANGE)
    s.arrow(526, 90, 526, 136, color=ORANGE)
    s.text(380, 394, "水平でもエネルギー入力は継続：温度計では見えない分を、融けた／蒸発した質量が記録する", size=12, fill=INK2, anchor="middle")
    s.save("fig2-heating-curve.svg")


def fig_cycle():
    s = Svg(760, 420, "図3　膨張だけでは機関にならない ── 元へ戻る経路が正味仕事を決める",
            "P–V 図では膨張の下の面積から圧縮の下の面積を引いた、閉路の内側が一周の正味仕事")
    L, R, T, B = 96, 678, 90, 326
    s.line(L, T, L, B, stroke=INK3, sw=1.5)
    s.line(L, B, R, B, stroke=INK3, sw=1.5)
    s.text(45, 92, "圧力 P", size=12, fill=INK2)
    s.text((L + R) / 2, B + 36, "体積 V →", size=12, fill=INK2, anchor="middle")
    # clockwise closed path; area deliberately explicit rather than a thermodynamic model
    d_fill = "M170,136 C300,106 490,126 610,190 C500,248 316,270 170,226 Z"
    s.path(d_fill, fill=ORANGE, stroke="none", opacity=0.16)
    s.arrow_path("M170,136 C300,106 490,126 610,190", color=ORANGE, sw=3)
    s.arrow_path("M610,190 C500,248 316,270 170,226", color=BLUE, sw=3)
    s.arrow(170, 226, 170, 142, color=AQUA, sw=2.4)
    s.circle(170, 136, 5, fill="#ffffff", stroke=AQUA, sw=2)
    s.text(356, 119, "膨張：気体が仕事を出す", size=12, fill=ORANGE, anchor="middle", weight="700")
    s.text(380, 274, "圧縮：外から仕事を戻す", size=12, fill=BLUE, anchor="middle", weight="700")
    s.text(390, 196, "囲んだ面積", size=15, fill=INK, anchor="middle", weight="700")
    s.text(390, 217, "＝ W_net", size=13, fill=INK, anchor="middle")
    s.text(170, 120, "同じ状態へ戻る", size=11, fill=AQUA, anchor="middle", weight="700")
    s.text(380, 388, "一周すれば ΔU=0 なので Q_net=W_net。冷却・凝縮は、安い圧縮経路を作って閉路を成立させる。", size=12, fill=INK2, anchor="middle")
    s.save("fig3-cycle-net-work.svg")


def fig_exergy_ranking():
    s = Svg(760, 420, "図4　同じ1 MJでも、環境まで戻す間に取り出せる最大仕事は違う",
            "環境温度 35℃。電池は約1.00 MJ、圧縮空気は条件付きで0.82 MJ、500℃の熱は0.60 MJ、40℃の熱は0.016 MJ")
    x0, x1 = 184, 694
    rows = [
        ("電池", 1.00, AQUA, "≈ 1.00 MJ"),
        ("圧縮空気", 0.82, BLUE, "0.82 MJ（今回の状態）"),
        ("500℃の熱", 0.60, ORANGE, "0.60 MJ"),
        ("40℃の温水", 0.016, INK3, "0.016 MJ"),
    ]
    for i, (label, value, color, amount) in enumerate(rows):
        y = 100 + i * 68
        s.text(x0 - 16, y + 20, label, size=12.5, fill=INK, anchor="end", weight="700")
        s.rect(x0, y, x1 - x0, 34, fill="#ffffff", stroke=CARD_EDGE, rx=5)
        w = max(5, (x1 - x0) * value)
        s.rect(x0, y, w, 34, fill=color, stroke=color, rx=5, opacity=0.22)
        s.text(min(x0 + w + 10, x1 - 4), y + 22, amount, size=12, fill=color,
               anchor="start" if x0 + w + 130 < x1 else "end", weight="700")
    for v in (0, .25, .5, .75, 1):
        x = x0 + (x1 - x0) * v
        s.line(x, 82, x, 360, stroke=GRID, sw=1, dash="3 4")
        s.text(x, 378, f"{v:.2f}", size=10.5, fill=INK3, anchor="middle")
    s.text((x0 + x1) / 2, 402, "理想的に取り出せる最大仕事（MJ）", size=12, fill=INK2, anchor="middle")
    s.save("fig4-exergy-ranking.svg")


FIGURES = (fig_refrigerator_balance, fig_heating_curve, fig_cycle, fig_exergy_ranking)


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
    with tempfile.TemporaryDirectory(prefix="thermodynamics-figs-") as tmp:
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
