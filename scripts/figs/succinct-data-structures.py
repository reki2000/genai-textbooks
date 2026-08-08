#!/usr/bin/env python3
"""Generate explanatory SVG figures for succinct-data-structures."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "docs" / "books" / "succinct-data-structures" / "figs"

INK = "#24313a"
MUTED = "#60717d"
PAPER = "#fbfaf7"
PANEL = "#ffffff"
GRID = "#c9d2d8"
BLUE = "#2463a6"
BLUE_LIGHT = "#dcecf7"
ORANGE = "#d8612c"
ORANGE_LIGHT = "#fbe4d6"
GREEN = "#187c68"
GREEN_LIGHT = "#dcefe9"
PURPLE_LIGHT = "#ebe4f5"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(
    x: float,
    y: float,
    value: object,
    *,
    cls: str = "label",
    anchor: str = "start",
    fill: str | None = None,
) -> str:
    color = f' fill="{fill}"' if fill else ""
    return (
        f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"'
        f"{color}>{esc(value)}</text>"
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str = PANEL,
    stroke: str = GRID,
    radius: float = 12,
    sw: float = 2,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str = GRID,
    sw: float = 2,
    dash: str | None = None,
    marker: bool = False,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    marker_attr = ' marker-end="url(#arrow)"' if marker else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{sw}"{dash_attr}{marker_attr}/>'
    )


def svg_document(
    width: int, height: int, title_value: str, desc_value: str, body: str
) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(title_value)}</title>
  <desc id="desc">{esc(desc_value)}</desc>
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="{INK}"/>
    </marker>
    <style>
      text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif; fill: {INK}; dominant-baseline: middle; }}
      .title {{ font-size: 28px; font-weight: 700; }}
      .subtitle {{ font-size: 17px; fill: {MUTED}; }}
      .label {{ font-size: 18px; }}
      .small {{ font-size: 14px; fill: {MUTED}; }}
      .tiny {{ font-size: 12px; fill: {MUTED}; }}
      .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", "Noto Sans JP", monospace; font-size: 18px; font-weight: 650; }}
      .number {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", "Noto Sans JP", monospace; font-size: 22px; font-weight: 700; }}
      .result {{ font-size: 22px; font-weight: 700; }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="{PAPER}"/>
{body}
</svg>
'''


def bit_cells(
    bits: str,
    x: float,
    y: float,
    cell: float,
    *,
    fills: list[str] | None = None,
    labels: bool = True,
) -> str:
    out: list[str] = []
    for i, bit in enumerate(bits):
        fill = fills[i] if fills else PANEL
        out.append(
            rect(x + i * cell, y, cell, cell, fill=fill, radius=3, sw=1.5)
        )
        out.append(
            text(
                x + (i + 0.5) * cell,
                y + cell / 2 + 1,
                bit,
                cls="number",
                anchor="middle",
            )
        )
        if labels:
            out.append(
                text(
                    x + (i + 0.5) * cell,
                    y - 15,
                    i,
                    cls="tiny",
                    anchor="middle",
                )
            )
    return "\n".join(out)


def rank_figure() -> str:
    bits = "0010100110010100"
    x, y, cell = 128, 176, 58
    fills = []
    for i in range(len(bits)):
        if i < 8:
            fills.append(BLUE_LIGHT)
        elif i < 12:
            fills.append(GREEN_LIGHT)
        elif i < 14:
            fills.append(ORANGE_LIGHT)
        else:
            fills.append("#f1f3f4")

    body = [
        text(60, 48, "rank は三つの小さな答えを足す", cls="title"),
        text(
            60,
            82,
            "16ビットの縮小例：rank_1(14) は位置14より前にある1の個数",
            cls="subtitle",
        ),
        text(60, 128, "位置 i", cls="small"),
        bit_cells(bits, x, y, cell, fills=fills),
        line(
            x + 14 * cell,
            y - 40,
            x + 14 * cell,
            y + cell + 58,
            stroke=ORANGE,
            sw=4,
            dash="7 5",
        ),
        text(
            x + 14 * cell,
            y - 58,
            "問い合わせ境界 i=14",
            cls="label",
            anchor="middle",
            fill=ORANGE,
        ),
        rect(128, 300, 280, 96, fill=BLUE_LIGHT, stroke=BLUE),
        text(148, 326, "① 大区画の累積", cls="small"),
        text(268, 366, "S = 3", cls="result", anchor="middle", fill=BLUE),
        rect(460, 300, 280, 96, fill=GREEN_LIGHT, stroke=GREEN),
        text(480, 326, "② 小区画の累積", cls="small"),
        text(600, 366, "L = 2", cls="result", anchor="middle", fill=GREEN),
        rect(792, 300, 280, 96, fill=ORANGE_LIGHT, stroke=ORANGE),
        text(812, 326, "③ 残り2ビットを実測", cls="small"),
        text(
            932,
            366,
            "popcount = 1",
            cls="result",
            anchor="middle",
            fill=ORANGE,
        ),
        line(408, 348, 454, 348, stroke=INK, marker=True),
        line(740, 348, 786, 348, stroke=INK, marker=True),
        rect(250, 462, 700, 76, fill=PANEL, stroke=INK, radius=14, sw=2.5),
        text(
            600,
            500,
            "rank_1(14) = 3 + 2 + 1 = 6",
            cls="result",
            anchor="middle",
        ),
        text(
            1120,
            573,
            "大区画 + 小区画 + 短い実測",
            cls="small",
            anchor="end",
        ),
    ]
    return svg_document(
        1200,
        600,
        "二段階索引によるrank",
        "スーパーブロック累積3、ブロック内累積2、残り2ビットのpopcount 1を足し、rank 1 of 14 equals 6を得る。",
        "\n".join(body),
    )


def elias_fano_figure() -> str:
    values = [3, 8, 9, 21, 37]
    highs = [value >> 3 for value in values]
    lows = [value & 7 for value in values]
    positions = [high + i for i, high in enumerate(highs)]
    body = [
        text(
            55,
            46,
            "Elias–Fano：整数を上下に切り、上位部を位置へ変える",
            cls="title",
        ),
        text(
            55,
            80,
            "x = [3, 8, 9, 21, 37],  U = 64,  m = 5,  L = 3",
            cls="subtitle",
        ),
        rect(55, 112, 1090, 278, fill=PANEL),
    ]
    headers = [
        ("i", 105),
        ("x_i", 220),
        ("上位 h_i = x_i >> 3", 410),
        ("下位 l_i（3 bit）", 655),
        ("1を置く位置 h_i+i", 930),
    ]
    for label, xpos in headers:
        body.append(text(xpos, 142, label, cls="small", anchor="middle"))
    body.append(line(75, 166, 1125, 166, stroke=GRID))
    for row, (value, high, low, pos) in enumerate(
        zip(values, highs, lows, positions)
    ):
        yy = 198 + row * 38
        fill = ORANGE_LIGHT if row == 3 else PANEL
        body.append(
            rect(75, yy - 17, 1050, 34, fill=fill, stroke="none", radius=5, sw=0)
        )
        body.extend(
            [
                text(105, yy, row, cls="mono", anchor="middle"),
                text(220, yy, value, cls="mono", anchor="middle"),
                text(410, yy, high, cls="mono", anchor="middle"),
                text(655, yy, f"{low:03b}", cls="mono", anchor="middle"),
                text(930, yy, pos, cls="mono", anchor="middle"),
            ]
        )
    body.extend(
        [
            text(55, 426, "上位ビット列 H", cls="label"),
            text(55, 458, "位置", cls="small"),
        ]
    )
    bits = ["0"] * 9
    for pos in positions:
        bits[pos] = "1"
    body.append(
        bit_cells(
            "".join(bits),
            205,
            458,
            55,
            fills=[BLUE_LIGHT if bit == "1" else PANEL for bit in bits],
        )
    )
    body.extend(
        [
            text(730, 486, "1 の位置 = [0, 2, 3, 5, 8]", cls="small"),
            line(55, 548, 1145, 548, stroke=GRID),
            text(55, 580, "i = 3 の値をランダムアクセス", cls="label"),
            rect(55, 610, 1090, 74, fill=ORANGE_LIGHT, stroke=ORANGE),
            text(82, 647, "select_1(3)=5", cls="result", fill=ORANGE),
            text(315, 647, "→  h_3=5−3=2", cls="result"),
            text(590, 647, "→  l_3=101 (base 2)=5", cls="result"),
            text(
                865,
                647,
                "→  x_3=2×8+5=21",
                cls="result",
                fill=GREEN,
            ),
        ]
    )
    return svg_document(
        1200,
        720,
        "Elias–Fanoの分解と復元",
        "値列3、8、9、21、37を上位部と3ビットの下位部へ分解し、上位値と添字の和の位置に1を置く。添字3ではselect結果5から値21を復元する。",
        "\n".join(body),
    )


def louds_figure() -> str:
    nodes = {
        "0 日本": (230, 140),
        "1 東京都": (150, 245),
        "2 大阪府": (340, 245),
        "3 港区": (100, 350),
        "4 新宿区": (230, 350),
        "5 大阪市": (340, 350),
        "6 六本木": (55, 460),
        "7 芝浦": (165, 460),
    }
    edges = [
        ("0 日本", "1 東京都"),
        ("0 日本", "2 大阪府"),
        ("1 東京都", "3 港区"),
        ("1 東京都", "4 新宿区"),
        ("2 大阪府", "5 大阪市"),
        ("3 港区", "6 六本木"),
        ("3 港区", "7 芝浦"),
    ]
    body = [
        text(
            50,
            46,
            "LOUDS：幅優先番号の順に「子の数」を並べる",
            cls="title",
        ),
        text(
            50,
            80,
            "各ノードの次数 d を 1^d 0 に変換すると、ポインタ木が 2n−1 bit の列になる",
            cls="subtitle",
        ),
        rect(35, 105, 420, 430, fill=PANEL),
        text(55, 126, "住所木（丸内は幅優先番号）", cls="small"),
    ]
    for parent, child in edges:
        x1, y1 = nodes[parent]
        x2, y2 = nodes[child]
        body.append(line(x1, y1 + 22, x2, y2 - 22, stroke=INK, sw=2.2))
    highlighted = {"1 東京都", "3 港区", "4 新宿区"}
    for name, (xpos, ypos) in nodes.items():
        is_highlighted = name in highlighted
        body.append(
            rect(
                xpos - 50,
                ypos - 22,
                100,
                44,
                fill=ORANGE_LIGHT if is_highlighted else BLUE_LIGHT,
                stroke=ORANGE if is_highlighted else BLUE,
                radius=18,
                sw=2.2,
            )
        )
        body.append(
            text(xpos, ypos, name, cls="small", anchor="middle", fill=INK)
        )

    body.extend(
        [
            rect(485, 105, 680, 430, fill=PANEL),
            text(505, 130, "次数を単項符号へ", cls="small"),
        ]
    )
    segments = [
        ("0", "110", BLUE_LIGHT),
        ("1", "110", ORANGE_LIGHT),
        ("2", "10", GREEN_LIGHT),
        ("3", "110", PURPLE_LIGHT),
        ("4", "0", "#f1f3f4"),
        ("5", "0", "#f1f3f4"),
        ("6", "0", "#f1f3f4"),
        ("7", "0", "#f1f3f4"),
    ]
    sx, sy, cell = 515, 205, 40
    cursor = 0
    for name, bits, fill in segments:
        center = sx + (cursor + len(bits) / 2) * cell
        body.append(text(center, sy - 33, name, cls="tiny", anchor="middle"))
        for bit in bits:
            body.append(
                rect(
                    sx + cursor * cell,
                    sy,
                    cell,
                    cell,
                    fill=fill,
                    stroke=ORANGE if name == "1" else GRID,
                    radius=3,
                    sw=2 if name == "1" else 1.2,
                )
            )
            body.append(
                text(
                    sx + (cursor + 0.5) * cell,
                    sy + cell / 2 + 1,
                    bit,
                    cls="number",
                    anchor="middle",
                )
            )
            cursor += 1
    body.extend(
        [
            text(
                515,
                282,
                "110 | 110 | 10 | 110 | 0 | 0 | 0 | 0",
                cls="mono",
            ),
            rect(515, 326, 610, 90, fill=ORANGE_LIGHT, stroke=ORANGE),
            text(535, 350, "例：ノード1「東京都」", cls="small"),
            text(
                535,
                384,
                "子が2個 → 1^2 0 = 110 → 子は幅優先番号3・4",
                cls="label",
            ),
            line(745, 416, 745, 470, stroke=INK, marker=True),
            rect(610, 472, 270, 50, fill=GREEN_LIGHT, stroke=GREEN),
            text(
                745,
                497,
                "1 が7個 + 0 が8個 = 15 bit",
                cls="label",
                anchor="middle",
                fill=GREEN,
            ),
            rect(205, 574, 790, 82, fill=PANEL, stroke=INK, sw=2.5),
            text(
                600,
                604,
                "ポインタを保存しない",
                cls="result",
                anchor="middle",
            ),
            text(
                600,
                636,
                "親子関係は列中の rank / select で復元する",
                cls="label",
                anchor="middle",
            ),
        ]
    )
    return svg_document(
        1200,
        690,
        "LOUDSによる木の符号化",
        "8ノードの住所木を幅優先順に番号付けし、各ノードの子の数dを1のd乗と0へ変換する。連結結果は15ビットになる。",
        "\n".join(body),
    )


def wavelet_matrix_figure() -> str:
    rows = [
        (
            [3, 1, 3, 7, 2, 3, 1, 6, 4, 3, 2, 7],
            "000100011001",
            8,
            (0, 10),
            "上位 bit = 0",
        ),
        (
            [3, 1, 3, 2, 3, 1, 3, 2, 7, 6, 4, 7],
            "101110111101",
            3,
            (0, 7),
            "中位 bit = 1",
        ),
        (
            [1, 1, 4, 3, 3, 2, 3, 3, 2, 7, 6, 7],
            "110110110101",
            4,
            (3, 8),
            "下位 bit = 1",
        ),
    ]
    x, cell = 402, 56
    ys = [170, 350, 530]
    body = [
        text(
            45,
            44,
            "Wavelet Matrix：区間を保ったまま値域を半分ずつ絞る",
            cls="title",
        ),
        text(
            45,
            78,
            "具体例：S の先頭10件にある値3の個数 rank_3(10) を追う（3 = 011 base 2）",
            cls="subtitle",
        ),
    ]
    for level, ((values, bits, zeros, interval, decision), yy) in enumerate(
        zip(rows, ys)
    ):
        start, end = interval
        body.extend(
            [
                text(48, yy - 36, f"階層 {level}", cls="result"),
                text(48, yy - 2, decision, cls="label", fill=ORANGE),
                text(48, yy + 31, f"Z{level} = {zeros}", cls="small"),
                text(48, yy + 58, f"区間 [{start}, {end})", cls="small"),
            ]
        )
        for i, (value, bit) in enumerate(zip(values, bits)):
            xx = x + i * cell
            body.append(
                text(
                    xx + cell / 2,
                    yy - 29,
                    value,
                    cls="small",
                    anchor="middle",
                )
            )
            fill = BLUE_LIGHT if bit == "0" else PURPLE_LIGHT
            body.append(
                rect(xx, yy, cell, 48, fill=fill, stroke=GRID, radius=3, sw=1.3)
            )
            body.append(
                text(
                    xx + cell / 2,
                    yy + 25,
                    bit,
                    cls="number",
                    anchor="middle",
                )
            )
            if level == 0:
                body.append(
                    text(
                        xx + cell / 2,
                        yy - 53,
                        i,
                        cls="tiny",
                        anchor="middle",
                    )
                )
        body.append(
            rect(
                x + start * cell,
                yy - 8,
                (end - start) * cell,
                64,
                fill="none",
                stroke=ORANGE,
                radius=6,
                sw=4,
            )
        )
        if level < 2:
            body.extend(
                [
                    line(738, yy + 62, 738, yy + 121, stroke=INK, marker=True),
                    text(
                        758,
                        yy + 92,
                        "0を前、1を後へ安定分割",
                        cls="small",
                    ),
                ]
            )
    body.extend(
        [
            line(738, 594, 738, 635, stroke=INK, marker=True),
            rect(500, 638, 475, 76, fill=GREEN_LIGHT, stroke=GREEN, sw=2.5),
            text(
                738,
                663,
                "最終区間 [6, 10)",
                cls="label",
                anchor="middle",
            ),
            text(
                738,
                694,
                "幅 10−6 = 4  →  rank_3(10) = 4",
                cls="result",
                anchor="middle",
                fill=GREEN,
            ),
            text(
                1100,
                736,
                "青=0側 / 紫=1側 / 橙枠=追跡中の区間",
                cls="small",
                anchor="end",
            ),
        ]
    )
    return svg_document(
        1200,
        760,
        "Wavelet Matrixの区間遷移",
        "値3のビット011に沿って区間0から10を各階層で写す。区間は0から7、3から8、6から10へ変化し、最後の幅4がrankの答えになる。",
        "\n".join(body),
    )


FIGURES = {
    "rank-two-level.svg": rank_figure,
    "elias-fano-transform.svg": elias_fano_figure,
    "louds-encoding.svg": louds_figure,
    "wavelet-matrix-range.svg": wavelet_matrix_figure,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated figures differ from files on disk",
    )
    parser.add_argument(
        "--list", action="store_true", help="list generated figure paths"
    )
    args = parser.parse_args()

    expected = {name: render() for name, render in FIGURES.items()}
    if args.list:
        for name in expected:
            print((OUTPUT_DIR / name).relative_to(ROOT))
        return 0

    if args.check:
        stale: list[str] = []
        for name, content in expected.items():
            path = OUTPUT_DIR / name
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        if stale:
            print("stale or missing figures:", file=sys.stderr)
            for path in stale:
                print(f"  {path}", file=sys.stderr)
            return 1
        print(f"OK: {len(expected)} figures are up to date")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        path = OUTPUT_DIR / name
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
