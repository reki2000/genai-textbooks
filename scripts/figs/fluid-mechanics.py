#!/usr/bin/env python3
"""docs/books/fluid-mechanics/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, SURFACE, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "fluid-mechanics" / "figs"


def figures(out_dir: Path) -> None:
    Svg = partial(SvgDocument, out_dir=out_dir)

    s = Svg(760, 350, "図1　連続体近似を支える中間尺度", "平均化箱は、分子を十分含みながら装置内の変化を潰さない：d ≪ ℓ ≪ L")
    y = 158
    s.arrow(72, y, 690, y, color=INK3, sw=1.5)
    points = [(112, "分子間隔 d", "数個では平均が揺れる", ORANGE), (370, "平均化箱 ℓ", "ρ・u・p を安定して測る", BLUE), (646, "装置長さ L", "場所による変化を残す", AQUA)]
    for x, label, sub, color in points:
        s.circle(x, y, 8, fill="#ffffff", stroke=color, sw=2.5)
        s.text(x, y - 28, label, size=13, fill=color, anchor="middle", weight="700")
        s.text(x, y + 35, sub, size=11, fill=INK2, anchor="middle")
    s.arrow(145, 238, 337, 238, color=BLUE, sw=2)
    s.arrow(403, 238, 612, 238, color=BLUE, sw=2)
    s.text(241, 226, "十分多くの分子", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.text(508, 226, "装置より十分小さい", size=11.5, fill=BLUE, anchor="middle", weight="700")
    s.rect(238, 274, 284, 48, fill="#ffffff", stroke=BLUE, rx=8, sw=1.6)
    s.text(380, 304, "中間尺度がなければ連続体近似は使えない", size=12.5, fill=INK, anchor="middle", weight="700")
    s.save("fig1-continuum-scale.svg")

    s = Svg(760, 390, "図2　ポンプ水頭18.0 mの行き先", "実測値で会計すると、速度へ残るのは2.5 mだけ：出口速度は14.7 m/sではなく7.0 m/s")
    x0, y0, total_w, h = 70, 130, 620, 70
    vals = [(7.0, "静水頭", AQUA), (5.4, "直管損失", ORANGE), (3.1, "局所損失", ORANGE), (2.5, "速度水頭", BLUE)]
    x = x0
    for value, label, color in vals:
        w = total_w * value / 18.0
        s.rect(x, y0, w, h, fill=color, stroke=SURFACE, sw=2, opacity=0.78)
        s.text(x + w / 2, y0 + 30, f"{value:.1f} m", size=14, fill="#ffffff", anchor="middle", weight="700")
        s.text(x + w / 2, y0 + 52, label, size=10.5, fill="#ffffff", anchor="middle", weight="700")
        x += w
    s.text(x0, 112, "ポンプが加える 18.0 m", size=12.5, fill=INK, weight="700")
    s.text(380, 230, "18.0 = 7.0 + 5.4 + 3.1 + 2.5 m", size=15, fill=INK, anchor="middle", weight="700")
    s.box(74, 270, 260, 70, "損失を無視した誤算", "√[2g(18−7)] = 14.7 m/s", color=RED)
    s.arrow(350, 305, 410, 305, color=INK2, sw=1.8)
    s.box(426, 270, 260, 70, "収支を閉じた実測", "√(2g×2.5) = 7.0 m/s", color=BLUE)
    s.save("fig2-head-budget.svg")

    s = Svg(760, 430, "図3　逆圧力勾配では壁近くから先に力尽きる", "外側の速い流れは進めても、運動量の小さい壁近傍は停止・逆流し、境界層が剥離する")
    panels = [(28, "順圧力勾配：付着", BLUE, False), (392, "逆圧力勾配：剥離", RED, True)]
    for px, title, color, separated in panels:
        s.rect(px, 82, 340, 288, fill="#ffffff", stroke=CARD_EDGE, rx=8)
        s.text(px + 170, 110, title, size=13, fill=color, anchor="middle", weight="700")
        wall_y = 308
        s.line(px + 25, wall_y, px + 315, wall_y, stroke=INK, sw=3)
        s.text(px + 28, 337, "壁：u = 0", size=10.5, fill=INK2)
        if not separated:
            for yy, length in [(274, 58), (242, 90), (204, 122), (160, 148)]:
                s.arrow(px + 52, yy, px + 52 + length, yy, color=BLUE, sw=2)
            s.path(f"M{px+45},295 C{px+110},285 {px+190},268 {px+300},248", stroke=BLUE, sw=2.2, dash="6 4")
            s.text(px + 180, 355, "下流ほど圧力低下 → 加速", size=11, fill=BLUE, anchor="middle", weight="700")
        else:
            for yy, length in [(274, 34), (242, 65), (204, 104), (160, 142)]:
                s.arrow(px + 52, yy, px + 52 + length, yy, color=BLUE, sw=2)
            s.arrow(px + 150, 286, px + 92, 286, color=RED, sw=2.5)
            s.path(f"M{px+45},296 C{px+120},278 {px+150},235 {px+180},214 C{px+215},188 {px+255},196 {px+306},222", stroke=RED, sw=2.6)
            s.text(px + 150, 265, "逆流", size=11, fill=RED, anchor="middle", weight="700")
            s.text(px + 196, 208, "剥離点", size=11, fill=RED, weight="700")
            s.text(px + 170, 355, "下流ほど圧力上昇 → 壁近傍が逆流", size=10.5, fill=RED, anchor="middle", weight="700")
    s.save("fig3-boundary-layer-separation.svg")

    s = Svg(760, 430, "図4　加速に必要な面積変化はMa=1で反転する", "亜音速は収縮で加速し、喉部で音速、超音速は拡大でさらに加速する")
    # ラバールノズル（上下壁）
    top = "M70,118 C190,118 255,164 370,176 C485,164 550,118 690,102"
    bot = "M70,292 C190,292 255,246 370,234 C485,246 550,292 690,308"
    interior = ("M70,118 C190,118 255,164 370,176 C485,164 550,118 690,102 "
                "L690,308 C550,292 485,246 370,234 C255,246 190,292 70,292 Z")
    s.path(interior, fill="#eef7ff", stroke="none")
    s.path(top, stroke=INK, sw=2.5); s.path(bot, stroke=INK, sw=2.5)
    s.line(370, 176, 370, 234, stroke=RED, sw=2, dash="5 4")
    s.text(370, 330, "喉部：Ma = 1", size=12, fill=RED, anchor="middle", weight="700")
    for x, yy, length in [(105,205,68),(210,205,82),(305,205,96),(430,205,108),(545,205,124)]:
        s.arrow(x, yy, x + length, yy, color=BLUE if x < 370 else AQUA, sw=2.3)
    s.text(190, 82, "亜音速 Ma < 1", size=14, fill=BLUE, anchor="middle", weight="700")
    s.text(190, 100, "dU > 0 なら dA < 0", size=11.5, fill=BLUE, anchor="middle")
    s.text(552, 64, "超音速 Ma > 1", size=14, fill=AQUA, anchor="middle", weight="700")
    s.text(552, 82, "dU > 0 なら dA > 0", size=11.5, fill=AQUA, anchor="middle")
    s.rect(150, 360, 460, 42, fill="#ffffff", stroke=INK2, rx=8)
    s.text(380, 386, "dA/A = (Ma² − 1) dU/U　→　符号がMa=1で逆転", size=13, fill=INK, anchor="middle", weight="700")
    s.save("fig4-laval-nozzle.svg")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    if not args.check:
        figures(OUT_DIR)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp)
        figures(candidate)
        expected = sorted(p.name for p in candidate.glob("*.svg"))
        actual = sorted(p.name for p in OUT_DIR.glob("*.svg")) if OUT_DIR.exists() else []
        if expected != actual:
            print(f"figure set differs: expected {expected}, actual {actual}", file=sys.stderr)
            return 1
        changed = [name for name in expected if not filecmp.cmp(candidate / name, OUT_DIR / name, shallow=False)]
        if changed:
            print("outdated figures: " + ", ".join(changed), file=sys.stderr)
            return 1
    print("all fluid-mechanics figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
