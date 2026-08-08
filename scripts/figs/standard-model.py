#!/usr/bin/env python3
"""Generate explanatory SVG figures for the standard-model textbook."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from svgkit import AQUA, BLUE, GRID, INK, INK2, ORANGE, RED, VIOLET, Svg


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs" / "books" / "standard-model" / "figs"
NAMES = ("covariant-derivative-cancellation.svg", "electroweak-vacuum-split.svg")


def derivative_figure(out_dir: Path) -> None:
    s = Svg(760, 390, "局所位相変換：壊れる微分を接続で直す",
            "同じ余計な項が、ゲージ場 Aμ の変換から逆符号で現れて相殺する", out_dir)
    # before
    s.text(190, 88, "素の微分 ∂μ", size=14, weight="700", anchor="middle", fill=RED)
    s.box(35, 112, 145, 64, "φ", "局所位相変換", color=BLUE)
    s.arrow(190, 144, 246, 144, color=INK2)
    s.box(256, 105, 210, 78, "e^(iα)(∂μφ + i(∂μα)φ)", "余計な項が混ざる", color=RED, size=12)
    s.text(480, 149, "× 同じ顔で変換しない", size=13, weight="700", fill=RED)
    s.line(25, 205, 735, 205, stroke=GRID, sw=1.2)
    # after
    s.text(190, 240, "共変微分 Dμ = ∂μ − ieAμ", size=14, weight="700", anchor="middle", fill=AQUA)
    s.box(35, 266, 145, 68, "Dμφ", "局所位相変換", color=BLUE)
    s.arrow(190, 300, 246, 300, color=INK2)
    s.box(256, 253, 250, 94, "e^(iα) Dμφ", "余計な項は残らない", color=AQUA, size=14)
    s.text(520, 278, "+ i(∂μα)φ", size=12.5, fill=ORANGE)
    s.text(520, 302, "− i(∂μα)φ", size=12.5, fill=BLUE)
    s.line(515, 309, 635, 309, stroke=INK2)
    s.text(646, 303, "= 0", size=13, weight="700", fill=AQUA)
    s.text(520, 331, "Aμ の補正が打ち消す", size=11.5, fill=INK2)
    s.text(25, 374, "結論：場所ごとの位相基準を許すと、比較の換算規則 Aμ（接続）が必要になる。", size=13, weight="700")
    s.save(NAMES[0])


def electroweak_figure(out_dir: Path) -> None:
    s = Svg(760, 430, "真空が4方向を「重い3本＋光子1本」に分ける",
            "SU(2)×U(1) の生成子のうち、真空を動かさない Q=T³+Y/2 だけが残る", out_dir)
    s.box(25, 88, 160, 74, "SU(2) × U(1)", "生成子は4方向", color=VIOLET)
    s.arrow(194, 125, 254, 125, color=INK2)
    s.box(265, 82, 214, 86, "〈φ〉 = (0, v)/√2", "真空に作用させる", color=ORANGE)
    s.arrow(490, 125, 550, 125, color=INK2)
    s.box(560, 88, 175, 74, "動かす？", "T〈φ〉 = 0 か", color=BLUE)

    s.arrow_path("M648 172 C648 205 505 202 505 238", color=RED)
    s.arrow_path("M648 172 C648 210 666 211 666 238", color=AQUA)
    s.text(496, 218, "動かす：3方向", size=12.5, weight="700", anchor="middle", fill=RED)
    s.text(666, 218, "動かさない：1方向", size=12.5, weight="700", anchor="middle", fill=AQUA)

    s.box(255, 242, 250, 92, "T¹, T², T³−Y/2 側", "対称性が破れ、3自由度を食う", color=RED, size=12.5)
    s.box(548, 242, 187, 92, "Q = T³ + Y/2", "真空を不変に保つ", color=AQUA, size=13)
    s.arrow(380, 343, 380, 376, color=RED)
    s.arrow(642, 343, 642, 376, color=AQUA)
    s.box(255, 377, 250, 40, "W+・W−・Z：質量あり", color=RED, size=13)
    s.box(548, 377, 187, 40, "光子 A：質量ゼロ", color=AQUA, size=13)

    s.text(25, 268, "4 → 3 + 1", size=18, weight="700", fill=INK)
    s.lines_of_text(25, 296, ["破れた方向だけが", "ゴールドストーンを受け取り", "縦偏極を増やす"], size=11.5, lh=18)
    s.save(NAMES[1])


def generate(out_dir: Path) -> None:
    derivative_figure(out_dir)
    electroweak_figure(out_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        generate(OUTPUT_DIR)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        generated = Path(tmp)
        generate(generated)
        stale = [name for name in NAMES if not (OUTPUT_DIR / name).exists()
                 or (OUTPUT_DIR / name).read_bytes() != (generated / name).read_bytes()]
    if stale:
        print("stale or missing figures: " + ", ".join(stale))
        return 1
    print(f"OK: {len(NAMES)} figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
