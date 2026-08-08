#!/usr/bin/env python3
"""topological-sensor-coverage 教材の説明図を決定的に生成する。"""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path

from svgkit import AQUA, BLUE, GRID, INK, INK2, ORANGE, RED, Svg

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/books/topological-sensor-coverage/figs"


def node(svg: Svg, x: float, y: float, label: str) -> None:
    svg.circle(x, y, 12, fill="#ffffff", stroke=BLUE, sw=2)
    svg.text(x, y + 4, label, size=11, weight="700", anchor="middle")


def simplex(svg: Svg, cx: float, filled: bool) -> None:
    pts = [(cx, 105), (cx - 72, 230), (cx + 72, 230)]
    fill = "#dff3ea" if filled else "#ffffff"
    svg.path("M " + " L ".join(f"{x},{y}" for x, y in pts) + " Z",
             fill=fill, stroke=AQUA if filled else BLUE, sw=3)
    for i, (x, y) in enumerate(pts, 1):
        node(svg, x, y, str(i))


def graph_vs_complex(out: Path) -> None:
    s = Svg(760, 340, "点と辺が同じでも、面の有無で穴は変わる",
            "1次元骨格だけでは「輪」と「埋まった面」を区別できない", out_dir=out)
    s.text(190, 84, "グラフ（1次元骨格）", size=14, weight="700", anchor="middle")
    simplex(s, 190, False)
    s.text(190, 267, "辺の閉路はある", size=12.5, anchor="middle", fill=INK2)
    s.text(190, 292, "面がない → H₁ ≅ F₂", size=14, anchor="middle", weight="700", fill=RED)
    s.arrow(345, 168, 415, 168, color=INK2, sw=2)
    s.text(380, 148, "2単体 [1,2,3]", size=11, anchor="middle", fill=INK2)
    s.text(570, 84, "単体複体（面を追加）", size=14, weight="700", anchor="middle")
    simplex(s, 570, True)
    s.text(570, 267, "同じ閉路が面の境界になる", size=12.5, anchor="middle", fill=INK2)
    s.text(570, 292, "面で埋まる → H₁ = 0", size=14, anchor="middle", weight="700", fill=AQUA)
    s.save("graph-vs-filled-simplex.svg")


def tri_points(cx: float, cy: float, side: float) -> list[tuple[float, float]]:
    h = side * math.sqrt(3) / 2
    return [(cx, cy - 2 * h / 3), (cx - side / 2, cy + h / 3), (cx + side / 2, cy + h / 3)]


def cech_vs_rips(out: Path) -> None:
    s = Svg(760, 400, "全ペアがつながっても、3重交差があるとは限らない",
            "同じペア情報からČechは枠、Ripsは面を作ることがある", out_dir=out)
    centers = tri_points(135, 220, 126)
    radius = 70  # 126/2 < 70 < 126/sqrt(3): pairwise overlap, empty triple intersection
    s.text(135, 85, "現実の検知円盤", size=14, weight="700", anchor="middle")
    for i, (x, y) in enumerate(centers, 1):
        s.circle(x, y, radius, fill=["#dcecff", "#ffe7dc", "#dff3ea"][i - 1],
                 stroke=[BLUE, ORANGE, AQUA][i - 1], sw=2, opacity=.62)
        node(s, x, y, str(i))
    s.circle(135, 220, 8, fill="#ffffff", stroke=RED, sw=2)
    s.text(135, 224, "×", size=12, fill=RED, weight="700", anchor="middle")
    s.text(135, 334, "各ペアは交差／中央は空", size=12, anchor="middle", weight="700", fill=RED)

    s.arrow(244, 220, 302, 220, color=INK2)
    s.text(273, 200, "3重交差を", size=10.5, anchor="middle", fill=INK2)
    s.text(273, 214, "確認", size=10.5, anchor="middle", fill=INK2)
    left = tri_points(390, 220, 118)
    s.text(390, 85, "Čech複体", size=14, weight="700", anchor="middle")
    s.path("M " + " L ".join(f"{x},{y}" for x, y in left) + " Z", stroke=BLUE, sw=3)
    for i, (x, y) in enumerate(left, 1): node(s, x, y, str(i))
    s.text(390, 334, "3重交差なし → 枠だけ", size=12, anchor="middle", weight="700", fill=RED)

    s.arrow(474, 220, 532, 220, color=INK2)
    s.text(503, 200, "全ペアの", size=10.5, anchor="middle", fill=INK2)
    s.text(503, 214, "辺だけ確認", size=10.5, anchor="middle", fill=INK2)
    right = tri_points(640, 220, 118)
    s.text(640, 85, "Rips複体", size=14, weight="700", anchor="middle")
    s.path("M " + " L ".join(f"{x},{y}" for x, y in right) + " Z",
           fill="#dff3ea", stroke=AQUA, sw=3)
    for i, (x, y) in enumerate(right, 1): node(s, x, y, str(i))
    s.text(640, 334, "3-clique → 面まで入る", size=12, anchor="middle", weight="700", fill=AQUA)
    s.text(380, 377, "通信は三角形でも、現実の検知領域には穴が残りうる", size=13.5,
           anchor="middle", weight="700", fill=INK)
    s.save("cech-vs-rips-triple-overlap.svg")


def build(out: Path) -> None:
    graph_vs_complex(out)
    cech_vs_rips(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        build(OUT)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp)
        build(expected)
        names = sorted(p.name for p in expected.glob("*.svg"))
        stale = [name for name in names if not (OUT / name).exists() or (OUT / name).read_bytes() != (expected / name).read_bytes()]
        extra = sorted(p.name for p in OUT.glob("*.svg") if p.name not in names)
        if stale or extra:
            if stale: print("outdated or missing:", ", ".join(stale))
            if extra: print("unexpected:", ", ".join(extra))
            return 1
    print("all generated figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
