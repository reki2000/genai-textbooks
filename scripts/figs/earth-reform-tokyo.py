#!/usr/bin/env python3
"""earth-reform-tokyo の図。

地色（材料）：水=淡青、大陸地殻=淡黄、海洋地殻=灰の斜線、マントル=淡灰。
線の色：青=冷たく硬い板（スラブ）と現在の向きの磁化／橙=その図で見る1か所／
赤=やる夫の失敗案。灰は目盛と背景。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/earth-reform-tokyo/figs"

WATER, CONT, MANTLE = TINT[MAIN], TINT[FOCUS], TINT[MUTED]
RHO_C, RHO_OC, RHO_M = 2.8, 2.9, 3.3

# 1 km ごとの高度帯が地球表面に占める割合（%）。ETOPO1 の陸高海深曲線の概数。
HYPS = [(4, 6, 0.5), (3, 4, 1.1), (2, 3, 2.2), (1, 2, 4.5), (0, 1, 20.9),
        (-1, 0, 8.5), (-2, -1, 3.0), (-3, -2, 4.4), (-4, -3, 14.0), (-5, -4, 23.3),
        (-6, -5, 16.1), (-7, -6, 1.2)]


def hypsometry():
    """1-2 海面を1 km 下げても、出てくるのは二つのこぶの間の乏しい斜面だけ。縦長 M 520x620。

    y = 70 + (5 - 高度km)*40（+5 km → 70、0 → 270、-7 km → 550）
    x = 150 + 割合%*13（23.3% → 453）
    """
    total = sum(p for _, _, p in HYPS)
    land = sum(p for lo, _, p in HYPS if lo >= 0) / total * 100
    assert 28 < land < 30, land                      # 本文：海が約71%
    Y = lambda e: 70 + (5 - min(e, 5)) * 40
    X = lambda p: 150 + p / total * 100 * 13
    s = SVG(520, 620, "地球の高度分布は海面のすぐ上と水深4 km台の二つのこぶに分かれ、その間は面積が乏しい")
    for p in (10, 20):
        s.line(X(p), 60, X(p), 555, stroke="#e6e6e6")
        s.text(X(p), 576, f"{p}%", size=14, fill=SUB, anchor="middle")
    s.text(150, 576, "0", size=14, fill=SUB, anchor="middle")
    s.text(300, 604, "その高度帯が地表に占める面積", size=15, fill=SUB, anchor="middle")
    for lo, hi, p in HYPS:
        s.rect(150, Y(hi), X(p) - 150, Y(lo) - Y(hi), fill=CONT if lo >= 0 else WATER,
               stroke=INK, sw=1)
    s.line(150, 60, 150, 555, stroke=INK, sw=1.2)
    for e in (4, 2, 0, -2, -4, -6):
        s.text(140, Y(e) + 5, f"{e:+d} km" if e else "0", size=14, fill=SUB, anchor="end")
    s.line(40, Y(0), 500, Y(0), stroke=MAIN, sw=2)
    s.text(40, Y(0) - 8, "現在の海面", size=15, fill=MAIN, bold=True)
    s.text(X(20.9) + 10, Y(0.5) + 5, "大陸のこぶ", size=16, bold=True)
    s.text(X(23.3) - 8, Y(-4.5) + 6, "深海底のこぶ", size=16, bold=True, anchor="end", halo=True)
    s.line(40, Y(-1.08), 500, Y(-1.08), stroke=WARN, sw=2.4, dash="7 5")
    s.text(500, Y(-1.08) - 8, "やる夫の案：−1080 m", size=15, fill=WARN, anchor="end", bold=True)
    s.rect(152, Y(-1), 346, Y(-3) - Y(-1), fill="none", stroke=FOCUS, sw=2.4, dash="3 3")
    s.note(300, Y(-1.9) + 4, ["面積の乏しい斜面", "下げても陸は増えない"])
    return s


def column(s, x, w, layers, y0, k):
    """柱を上から積む。layers = [(厚さkm, 地色, ラベル)]。y0 が柱の上端、k は km→px。"""
    y = y0
    for t, fill, label in layers:
        s.rect(x, y, w, t * k, fill=fill, stroke=INK, sw=1.2,
               dash="5 4" if fill == "#ffffff" else None)
        if label:
            s.text(x + w / 2, y + t * k / 2 + 6, label, size=15, anchor="middle", halo=True)
        y += t * k
    return y


def isostasy():
    """2-1 同じ深さの面で上に載る重さが等しいとき、薄く重い床は 4.45 km 低くなる。縦長 M 520x560。

    深さ y = 60 + 深さkm*12（大陸の地表 0 → 60、基準面 35 km → 480）
    大陸の柱 x 40〜160 ／ 海側の柱 x 220〜340 ／ H の括弧 x 350、注記 x 366
    """
    H = (RHO_OC * 7 + RHO_M * 28 - RHO_C * 35) / RHO_M
    assert abs(H - 4.45) < 0.01, H
    assert abs(RHO_C * 35 - 98) < 1e-9
    k = 12
    s = SVG(520, 560, "同じ深さで上の重さが等しいとき、厚く軽い大陸の柱は薄く重い海の柱より4.45 km高い")
    oc = s.hatch(MUTED)
    column(s, 40, 120, [(35, CONT, "")], 60, k)
    s.text(100, 60 + 17.5 * k - 6, ["大陸地殻", "2.8", "35 km"], size=15, anchor="middle")
    column(s, 220, 120, [(H, "#ffffff", ""), (7, oc, ""), (28 - H, MANTLE, "")], 60, k)
    s.text(280, 60 + (H + 3.5) * k + 6, "海洋地殻 2.9", size=15, anchor="middle", halo=True)
    s.text(280, 60 + (H + 7 + (28 - H) / 2) * k + 6, ["マントル", "3.3"], size=15, anchor="middle")
    s.line(24, 480, 496, 480, stroke=MAIN, sw=2.4, dash="7 5")
    s.text(260, 506, "基準面：上に載る重さが等しい", size=15, fill=MAIN, anchor="middle", bold=True)
    s.text(100, 532, "2.8×35 = 98", size=15, anchor="middle")
    s.text(280, 532, "2.9×7 + 3.3×23.55 = 98", size=15, anchor="middle")
    s.line(350, 60, 350, 60 + H * k, stroke=FOCUS, sw=3)
    for yy in (60, 60 + H * k):
        s.line(344, yy, 356, yy, stroke=FOCUS, sw=3)
    s.text(362, 60 + H * k / 2 + 6, "H", size=18, fill=FOCUS, bold=True)
    s.line(24, 60, 220, 60, stroke=MUTED, dash="3 3")
    s.note(366, 150, ["H = 4.45 km", "水を入れない", "計算"])
    return s


# 日本海溝付近の学習用の震源（海溝軸からの水平距離 km, 深さ km）。本文 3-2 の表。
QUAKES = [(50, 30), (150, 55), (250, 95), (400, 170), (600, 300)]


def slab():
    """3-2 冷たい板が斜めに刺さり、その内部で深い地震が起きる。横長 L 760x440（縦横同じ縮尺）。

    x = 110 + 距離km*0.95（海溝 → 110、600 km → 680）、y = 60 + 深さkm*0.95
    板の厚さ 100 km、両面から温まった厚さ 13 km。
    """
    k = 0.95
    X = lambda d: 110 + d * k
    Y = lambda z: 60 + z * k
    angles = [math.degrees(math.atan((z2 - z1) / (d2 - d1)))
              for (d1, z1), (d2, z2) in zip(QUAKES, QUAKES[1:])]
    assert [round(a) for a in angles] == [14, 22, 27, 33], angles
    # 板の上面：海溝 (0,0) から、震源の 12 km 上を通る
    top = [(-120, 0), (0, 0)] + [(d, z - 12) for d, z in QUAKES] + [(640, 316)]
    def offset(pts, dist):
        out = []
        for i, (x, z) in enumerate(pts):
            a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            n = math.hypot(tx, tz)
            out.append((x - tz / n * dist, z + tx / n * dist))
        return out
    bot = offset(top, 100)
    P = lambda pts: [(X(x), Y(z)) for x, z in pts]
    s = SVG(760, 480, "海溝から陸側へ深くなる震源の並びは、厚さ100 kmの冷たい板が斜めに刺さった形をなぞる")
    s.poly(P(top) + P(bot)[::-1], fill=TINT[MAIN], stroke="none", closed=True)
    for d in (13, 87):
        s.poly(P(offset(top, d)), stroke=MAIN, sw=1, dash="4 3")
    s.poly(P(top), stroke=MAIN, sw=3.5)
    s.poly(P(bot), stroke=MAIN, sw=3.5)
    s.line(*P(top)[-1], *P(bot)[-1], stroke=MAIN, sw=3.5)
    s.line(24, Y(0), 740, Y(0), stroke=INK, sw=1.2)
    s.poly([(X(-10), Y(0)), (X(0), Y(0) + 10), (X(10), Y(0))], stroke=INK, sw=1.2)
    s.text(X(0), Y(0) - 10, "海溝", size=15, anchor="middle", bold=True)
    s.text(40, Y(0) - 10, "海洋側", size=15, fill=SUB)
    s.text(740, Y(0) - 10, "陸側", size=15, fill=SUB, anchor="end")
    for d, z in QUAKES:
        s.circle(X(d), Y(z), 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(X(50) + 12, Y(30) - 10, "震源", size=15, fill=FOCUS, bold=True)
    s.text(X(120), Y(90), "浅い所は 14°", size=14, fill=SUB, anchor="middle")
    s.text(X(470), Y(290), "深い所は 33°", size=14, fill=SUB, anchor="middle")
    s.text(X(-60), Y(52) + 5, "冷たい板", size=15, fill=MAIN, anchor="middle", bold=True, halo=True)
    s.text(X(340), Y(150), "温まるのは両面 13 km", size=14, fill=MAIN, anchor="middle", halo=True)
    for z in (200, 300):
        s.line(24, Y(z), 36, Y(z), stroke=MUTED)
        s.text(42, Y(z) + 5, f"深さ {z} km", size=14, fill=SUB)
    s.text(24, 460, "縦横同じ縮尺", size=14, fill=SUB)
    s.note(440, 110, ["深い地震は、冷たいまま", "刺さった板の中で起きる"])
    return s


# 地磁気の向き（現在と同じ向き=True）と、軸から縞の境界までの距離（本文 4-2）。
STRIPES = [(0, 16, True), (16, 52, False), (52, 72, True), (72, 90, False)]
AGES = {16: 0.78, 52: 2.58, 72: 3.6}


def stripes():
    """4-2 縞は軸をはさんで鏡写しで、どの境界も 距離÷年代 ≈ 20 km/100万年。横長 L 760x320。

    x = 380 ± 距離km*3.6（90 km → 56 / 704）。縞 y 96〜176。
    """
    rates = {d: d / a for d, a in AGES.items()}
    assert [round(r, 1) for r in rates.values()] == [20.5, 20.2, 20.0], rates
    X = lambda d, side: 380 + side * d * 3.6
    s = SVG(760, 320, "海嶺の両側に鏡写しの縞が並び、どの境界でも距離を年代で割ると約20 km/100万年になる")
    for side in (-1, 1):
        for a, b, normal in STRIPES:
            x1, x2 = sorted((X(a, side), X(b, side)))
            s.rect(x1, 96, x2 - x1, 80, fill=MAIN if normal else "#ffffff",
                   stroke=MAIN if b < 90 else MUTED, sw=1.4)
        s.arrow(X(8, side), 206, X(40, side), 206, stroke=INK, sw=2)
    s.line(380, 70, 380, 186, stroke=INK, sw=2.4)
    s.text(380, 58, "海嶺の軸", size=16, anchor="middle", bold=True)
    s.text(380, 234, "両側へ広がる", size=15, fill=SUB, anchor="middle")
    for d, a in AGES.items():
        x = X(d, 1)
        s.line(x, 180, x, 250, stroke=FOCUS, sw=1.6)
        s.text(x, 272, f"{d} km", size=15, anchor="middle", bold=True)
        s.text(x, 292, f"{round(a * 100)}万年", size=14, fill=SUB, anchor="middle")
        s.text(x, 86, f"{rates[d]:.1f}", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(704, 58, "距離÷年代", size=14, fill=FOCUS, anchor="end")
    s.rect(24, 260, 20, 14, fill=MAIN, stroke=MAIN)
    s.text(50, 272, "今と同じ向き", size=14)
    s.rect(24, 284, 20, 14, fill="#ffffff", stroke=MAIN)
    s.text(50, 296, "逆向き", size=14)
    s.note(440, 30, "どの境界も約20 km/100万年＝年2 cm")
    return s


def rebound():
    """6-2 地殻を Δ 削ると根が 0.85Δ 浮き、地表は 0.15Δ しか下がらない。小さな多数 M 600x470。

    Δ = 25 km、1 km = 4 px。柱の幅 110、中心 x 110 / 300 / 490。
    元の柱：上端 y 100、厚さ 70 km（下端 380）。点線 y 100 が元の地表。
    """
    rise = RHO_C / RHO_M
    assert round(rise, 2) == 0.85 and round(1 / (1 - rise), 1) == 6.6
    k, D, T = 4, 25, 70
    s = SVG(600, 470, "地殻を削ると軽くなった柱が浮き上がり、地表は削った厚さの0.15倍しか下がらない")
    s.rect(24, 250, 552, 190, fill=MANTLE, stroke="none")
    s.text(40, 428, "マントル 3.3", size=15, fill=SUB)
    s.line(24, 100, 576, 100, stroke=MUTED, dash="4 4")
    s.text(24, 92, "元の地表", size=14, fill=SUB)
    heads = ["元の柱", "上を Δ 削る", "根が浮く"]
    for i, cx in enumerate((110, 300, 490)):
        s.badge(cx - 8 * len(heads[i]) - 18, 38, i + 1)
        s.text(cx + 4, 44, heads[i], size=16, anchor="middle", bold=True)
        top, thick = 100, T
        if i >= 1:
            s.rect(cx - 55, 100, 110, D * k, fill="none", stroke=MUTED, dash="5 4")
            top, thick = 100 + D * k, T - D
        if i == 2:
            top -= D * rise * k
        s.rect(cx - 55, top, 110, thick * k, fill=CONT, stroke=INK, sw=1.6)
        if i == 0:
            s.text(cx, 250, ["大陸地殻", "2.8"], size=15, anchor="middle")
        if i == 1:
            s.text(cx, 100 + D * k / 2 + 6, "Δ", size=18, fill=SUB, anchor="middle", bold=True)
        if i == 2:
            s.arrow(cx, 100 + T * k - 4, cx, 100 + T * k - D * rise * k + 6, stroke=INK, sw=2.4)
            s.text(cx + 10, 100 + T * k + 30, "0.85Δ 浮く", size=15, anchor="middle")
            y1, y2 = 100, top
            s.line(cx + 70, y1, cx + 70, y2, stroke=FOCUS, sw=4)
            s.text(cx, 80, "地表は 0.15Δ 下がる", size=16, fill=FOCUS, anchor="middle", bold=True)
    s.note(210, 410, "6.6 削って 1 下がる")
    return s


# 東京低地の埋没谷（模式）。谷底の標高 m を横位置 x ごとに。本文の「深さ60 mの谷」に合わせる。
VALLEY = [(80, 20), (190, 20), (215, 2), (240, -8), (280, -30), (330, -55), (370, -64),
          (410, -60), (460, -44), (510, -20), (560, -4), (580, 2), (600, 20), (656, 20)]
LAYERS = [(-70, -52, "gravel", "谷底の礫"), (-52, -38, CONT, "三角州の堆積物"),
          (-38, -8, WATER, "内湾の泥（縄文海進）"), (-8, 2, "#ffffff", "高海面期以後の堆積物")]


def base(x):
    for (x1, e1), (x2, e2) in zip(VALLEY, VALLEY[1:]):
        if x1 <= x <= x2:
            return e1 + (e2 - e1) * (x - x1) / (x2 - x1)
    raise ValueError(x)


def buried_valley():
    """7-2 平らな低地の下に、1万年で埋まった深さ約60 mの谷がある。横長 M 680x420（模式）。

    y = 90 + (20 - 標高m)*3.6（+20 m → 90、0 → 162、-64 m → 392）
    ボーリング x = 240, 290, 340, 400, 460, 520。
    """
    Y = lambda e: 90 + (20 - e) * 3.6
    assert min(e for _, e in VALLEY) == -64
    s = SVG(680, 420, "平らな低地の下に深さ約60 mの谷が埋もれ、下から礫・三角州・内湾の泥・新しい堆積物で埋まっている")
    grav = s.hatch(MUTED)
    upl = [(x, e) for x, e in VALLEY]
    s.poly([(X, Y(e)) for X, e in upl] + [(656, Y(-72)), (80, Y(-72))], closed=True,
           fill=MANTLE, stroke="none")
    for lo, hi, fill, _ in LAYERS:
        xs = [x for x in range(190, 601, 2) if base(x) < hi]
        top = [(x, Y(hi)) for x in xs]
        bot = [(x, Y(max(base(x), lo))) for x in reversed(xs)]
        s.poly(top + bot, closed=True, fill=grav if fill == "gravel" else fill, stroke=INK, sw=0.8)
    for x in (240, 290, 340, 400, 460, 520):
        s.line(x, Y(2) - 8, x, Y(base(x)) + 14, stroke=SUB, sw=1.2)
        s.circle(x, Y(base(x)), 5, fill=FOCUS, stroke="#ffffff", sw=1.5)
    s.poly([(x, Y(base(x))) for x in range(190, 601, 2)], stroke=FOCUS, sw=3.5)
    s.text(135, Y(20) + 40, "台地", size=16, anchor="middle", bold=True)
    s.text(628, Y(20) + 40, "台地", size=16, anchor="middle", bold=True)
    s.text(400, Y(2) - 14, "低地（平ら）", size=16, anchor="middle", bold=True)
    s.text(240, Y(2) - 14, "ボーリング", size=14, fill=SUB, anchor="middle")
    s.text(370, Y(-60) + 5, "谷底の礫", size=14, anchor="middle", halo=True)
    s.text(370, Y(-45) + 5, "三角州の堆積物", size=15, anchor="middle", halo=True)
    s.text(390, Y(-23) + 5, "内湾の泥（縄文海進）", size=15, anchor="middle", halo=True)
    s.text(390, Y(-3) + 5, "高海面期以後", size=14, anchor="middle", halo=True)
    for e in (20, 0, -20, -40, -60):
        s.text(72, Y(e) + 5, f"{e:+d} m" if e else "0 m", size=14, fill=SUB, anchor="end")
    s.text(656, 410, "縦を横より大きく伸ばした模式図", size=14, fill=SUB, anchor="end")
    s.note(470, 52, ["平らな地面の下に", "深さ約60 mの谷"])
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig1-2-hypsometry.svg": hypsometry,
        OUT / "fig2-1-isostasy.svg": isostasy,
        OUT / "fig3-2-slab.svg": slab,
        OUT / "fig4-2-stripes.svg": stripes,
        OUT / "fig6-2-rebound.svg": rebound,
        OUT / "fig7-2-buried-valley.svg": buried_valley,
    }))
