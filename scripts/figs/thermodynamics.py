#!/usr/bin/env python3
"""docs/books/thermodynamics/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import math
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


def fig_multistage_ceiling():
    s = Svg(760, 458, "図3　段を細かくしても、上がる高さは天井へ張りつく",
            "中間温度槽 0個で22段、1個で27段、3個で29段、7個で30段。1個で+5段だから増やすほど伸びる、という予想から離れていく")
    L, R, T, B = 118, 690, 108, 344
    y_max = 60.0

    def ypx(v):
        return B - (B - T) * v / y_max

    xs = [L + (R - L) * (i + 0.5) / 4 for i in range(4)]
    s.line(L, T - 10, L, B, stroke=INK3, sw=1.4)
    s.line(L, B, R, B, stroke=INK3, sw=1.4)
    for v in (0, 20, 40, 60):
        s.line(L, ypx(v), R, ypx(v), stroke=GRID, sw=1, dash="4 4")
        s.text(L - 10, ypx(v) + 4, f"{v:g}", size=11, fill=INK3, anchor="end")
    s.text(L - 10, T - 18, "段数", size=12, fill=INK2, anchor="end")
    for x, lab in zip(xs, ("0個", "1個", "3個", "7個")):
        s.line(x, B, x, B + 5, stroke=INK3, sw=1.2)
        s.text(x, B + 22, lab, size=12, fill=INK2, anchor="middle")
    s.text((L + R) / 2, B + 46, "中間温度槽の数", size=12, fill=INK2, anchor="middle")

    ceiling = 31.0
    s.line(L, ypx(ceiling), R, ypx(ceiling), stroke=INK3, sw=1.6, dash="7 5")
    s.text(L + 8, ypx(ceiling) - 9, "この高さへ張りつく（理由はまだ説明できない）",
           size=11.5, fill=INK2)

    predicted = [22, 27, 37, 57]
    measured = [22, 27, 29, 30]
    s.path("M" + " L".join(f"{x:.1f},{ypx(v):.1f}" for x, v in zip(xs, predicted)),
           stroke=RED, sw=2.4, dash="8 6")
    s.path("M" + " L".join(f"{x:.1f},{ypx(v):.1f}" for x, v in zip(xs, measured)),
           stroke=BLUE, sw=3.2)
    for x, v in zip(xs[2:], predicted[2:]):
        s.circle(x, ypx(v), 5, fill="#ffffff", stroke=RED, sw=2.4)
        s.text(x, ypx(v) - 14, f"予想 {v}段", size=12, fill=RED, anchor="middle", weight="700")
    for x, v in zip(xs, measured):
        s.circle(x, ypx(v), 5, fill=BLUE)
        dy = -14 if v == 22 else 22
        s.text(x, ypx(v) + dy, f"{v}段", size=12.5, fill=BLUE, anchor="middle", weight="700")

    s.circle(xs[0], ypx(14), 4.5, fill="#ffffff", stroke=INK3, sw=1.8)
    s.text(xs[0] + 12, ypx(14) + 5, "改良前 14段（1-2）。装置改良で22段へ", size=11.5, fill=INK2)
    s.text(xs[3], ypx(30) + 42, "運転時間は1個の約6倍", size=11, fill=INK3, anchor="middle")

    s.line(L + 14, 118, L + 46, 118, stroke=RED, sw=2.4, dash="8 6")
    s.text(L + 54, 122, "予想（このまま伸びる）", size=11.5, fill=INK2)
    s.line(L + 14, 138, L + 46, 138, stroke=BLUE, sw=3.2)
    s.text(L + 54, 142, "実測", size=11.5, fill=INK2)

    s.text(380, 418, "別方式の熱電素子は4段相当。第1法則が禁じるのははるか上なのに、実測は30段あたりで止まる。",
           size=12, fill=INK2, anchor="middle")
    s.text(380, 440, "止まる理由を、この時点の会計帳（エネルギーの列だけ）では書けない。",
           size=12, fill=INK2, anchor="middle")
    s.save("fig3-multistage-ceiling.svg")


def fig_cycle():
    s = Svg(760, 420, "図4　膨張だけでは機関にならない ── 元へ戻る経路が正味仕事を決める",
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
    s.save("fig4-cycle-net-work.svg")


def fig_carnot_contradiction():
    s = Svg(760, 476, "図5　可逆機関より高効率な機関があると仮定すると、低温源だけで動く機関になる",
            "仮の数値。高効率機関 X は Q_H=100 から W=40 を出し、可逆機関 R の逆運転は W=30 で Q_H=100 を戻す")
    panels = (
        (24, 226, "(1) 仮定：可逆機関より高効率な X", AQUA),
        (267, 226, "(2) 可逆機関 R を逆運転", BLUE),
        (510, 226, "(3) 2台を1台として外から見る", ORANGE),
    )
    for x, w, title, color in panels:
        cx = x + w / 2
        s.rect(x, 76, w, 336, fill="#ffffff", stroke=CARD_EDGE, rx=9)
        s.text(cx, 100, title, size=12.5, fill=INK, anchor="middle", weight="700")
        s.rect(x + 16, 116, w - 32, 30, fill=ORANGE, stroke=ORANGE, rx=6, sw=1.4, opacity=0.18)
        s.text(cx, 136, "高温側 T_H", size=12, fill=INK, anchor="middle", weight="700")
        s.rect(x + 16, 344, w - 32, 30, fill=BLUE, stroke=BLUE, rx=6, sw=1.4, opacity=0.18)
        s.text(cx, 364, "低温側 T_C", size=12, fill=INK, anchor="middle", weight="700")
        s.box(cx - 46, 214, 92, 74, "X" if x == 24 else ("R 逆転" if x == 267 else "X + R"),
              color=color, size=14)

    # (1) 高効率機関 X
    cx = 137
    s.arrow(cx - 26, 148, cx - 26, 210, color=ORANGE, sw=2.6)
    s.text(cx - 34, 182, "Q_H = 100", size=11.5, fill=ORANGE, anchor="end", weight="700")
    s.arrow(cx - 26, 292, cx - 26, 340, color=BLUE, sw=2.6)
    s.text(cx - 34, 320, "Q_C = 60", size=11.5, fill=BLUE, anchor="end", weight="700")
    s.arrow(cx + 48, 251, cx + 104, 251, color=INK, sw=2.6)
    s.text(cx + 76, 240, "W = 40", size=12, fill=INK, anchor="middle", weight="700")

    # (2) 逆運転した可逆機関 R
    cx = 380
    s.arrow(cx - 26, 210, cx - 26, 148, color=ORANGE, sw=2.6)
    s.text(cx - 34, 182, "Q_H = 100", size=11.5, fill=ORANGE, anchor="end", weight="700")
    s.arrow(cx - 26, 340, cx - 26, 292, color=BLUE, sw=2.6)
    s.text(cx - 34, 320, "Q_C = 70", size=11.5, fill=BLUE, anchor="end", weight="700")
    s.arrow(cx + 112, 251, cx + 60, 251, color=INK, sw=2.6)
    s.text(cx + 76, 240, "W = 30", size=12, fill=INK, anchor="middle", weight="700")

    # (3) 合成した装置
    cx = 623
    s.line(cx - 26, 152, cx - 26, 208, stroke=INK3, sw=2.2, dash="6 5")
    s.text(cx - 34, 176, "100 − 100", size=11.5, fill=INK3, anchor="end")
    s.text(cx - 34, 192, "= 0", size=11.5, fill=INK3, anchor="end", weight="700")
    s.arrow(cx - 26, 340, cx - 26, 292, color=RED, sw=2.8)
    s.text(cx - 34, 314, "70 − 60", size=11.5, fill=RED, anchor="end")
    s.text(cx - 34, 330, "= 10", size=11.5, fill=RED, anchor="end", weight="700")
    s.arrow(cx + 48, 251, cx + 104, 251, color=RED, sw=2.8)
    s.text(cx + 76, 240, "W = 10", size=12, fill=RED, anchor="middle", weight="700")
    s.text(cx, 396, "高温側は元通り、低温側だけが減る", size=11, fill=INK2, anchor="middle")

    s.text(380, 440, "一つの熱源から熱を奪い、ほかに変化を残さず全部を仕事にする機関ができてしまう。",
           size=13, fill=RED, anchor="middle", weight="700")
    s.text(380, 462, "これが認められないなら、「可逆機関より高効率」という最初の仮定が誤り。作動流体にはよらない。",
           size=12, fill=INK2, anchor="middle")
    s.save("fig5-carnot-contradiction.svg")


def fig_carnot_tiling():
    s = Svg(760, 492, "図6　任意の可逆サイクルを小さなカルノーサイクルで埋める",
            "隣り合うタイルが共有する辺では、一方の放熱が他方の受熱になって相殺し、外周だけが残る")
    GAMMA = 1.4
    L, R, T, B = 96, 430, 112, 340
    v0, v1, p0, p1 = 1.0, 3.2, 0.9, 3.1

    def X(v):
        return L + (R - L) * (v - v0) / (v1 - v0)

    def Y(p):
        return B - (B - T) * (p - p0) / (p1 - p0)

    s.line(L, T - 10, L, B, stroke=INK3, sw=1.4)
    s.line(L, B, R + 8, B, stroke=INK3, sw=1.4)
    s.text(L - 8, T - 18, "圧力 P", size=12, fill=INK2, anchor="end")
    s.text(R + 8, B + 22, "体積 V →", size=12, fill=INK2, anchor="end")

    # 外周：P–V 平面上の任意の可逆サイクル
    steps = 180
    loop = []
    for i in range(steps + 1):
        th = 2 * math.pi * i / steps
        loop.append((2.05 + 0.85 * math.cos(th),
                     2.00 + 0.72 * math.sin(th) + 0.14 * math.cos(2 * th)))
    loop_d = "M" + " L".join(f"{X(v):.1f},{Y(p):.1f}" for v, p in loop) + " Z"
    s.path(loop_d, fill=AQUA, stroke="none", opacity=0.07)

    def inside(v, p):
        """閉曲線 loop の内側かを交差数で判定する。"""
        hit = False
        for (va, pa), (vb, pb) in zip(loop, loop[1:]):
            if (pa > p) != (pb > p):
                if v < va + (p - pa) * (vb - va) / (pb - pa):
                    hit = not hit
        return hit

    def clipped_curve(fn):
        """曲線 P=fn(V) のうち、閉曲線の内側に入る区間だけを返す。"""
        n = 400
        vs = [v0 + (v1 - v0) * i / n for i in range(n + 1)]
        flags = [inside(v, fn(v)) for v in vs]

        def edge(v_in, v_out):  # 内外の境目を二分法で詰める
            for _ in range(24):
                mid = (v_in + v_out) / 2
                if inside(mid, fn(mid)):
                    v_in = mid
                else:
                    v_out = mid
            return v_in

        paths, span = [], []
        for i, v in enumerate(vs):
            if flags[i]:
                if not span and i > 0:
                    span.append(edge(v, vs[i - 1]))
                span.append(v)
                continue
            if span:
                span.append(edge(span[-1], v))
                paths.append(span)
                span = []
        if span:
            paths.append(span)
        return ["M" + " L".join(f"{X(v):.1f},{Y(fn(v)):.1f}" for v in sp)
                for sp in paths if len(sp) > 1]

    # 等温線 PV = c と断熱線 PV^γ = k（理想気体）。定数は等比で刻む
    for j in range(9):
        for d in clipped_curve(lambda v, c=2.0 * 1.16 ** j: c / v):
            s.path(d, stroke=ORANGE, sw=1.5, opacity=0.9)
    for j in range(11):
        for d in clipped_curve(lambda v, k=2.2 * 1.16 ** j: k / v ** GAMMA):
            s.path(d, stroke=AQUA, sw=1.5, dash="6 4", opacity=0.95)
    s.path(loop_d, stroke=INK, sw=3)

    # 進む向きを外周上に1か所だけ示す
    th = math.pi * 0.42
    va, pa = 2.05 + 0.85 * math.cos(th), 2.00 + 0.72 * math.sin(th) + 0.14 * math.cos(2 * th)
    th2 = math.pi * 0.30
    vb, pb = 2.05 + 0.85 * math.cos(th2), 2.00 + 0.72 * math.sin(th2) + 0.14 * math.cos(2 * th2)
    s.arrow(X(va), Y(pa), X(vb), Y(pb), color=INK, sw=3)

    s.line(L + 4, 368, L + 34, 368, stroke=ORANGE, sw=2)
    s.text(L + 42, 372, "等温線 PV = 一定", size=11.5, fill=INK2)
    s.line(L + 4, 390, L + 34, 390, stroke=AQUA, sw=2, dash="6 4")
    s.text(L + 42, 394, "断熱線 PV^1.4 = 一定（熱の出入りなし）", size=11.5, fill=INK2)
    s.text(L + 4, 416, "2本の傾きは近いので、タイルは細長い平行四辺形になる", size=11.5, fill=INK3)

    # 右：隣り合う2枚のタイルを取り出す
    ix, iy, iw, ih = 462, 96, 274, 208
    s.rect(ix, iy, iw, ih, fill="#ffffff", stroke=CARD_EDGE, rx=9)
    s.text(ix + iw / 2, iy + 24, "隣り合う2枚を取り出す", size=12.5, fill=INK,
           anchor="middle", weight="700")
    jv0, jv1, jp0, jp1 = 0.80, 1.62, 1.18, 2.82
    jl, jr, jt, jb = ix + 16, ix + iw - 16, iy + 40, iy + ih - 22

    def JX(v):
        return jl + (jr - jl) * (v - jv0) / (jv1 - jv0)

    def JY(p):
        return jb - (jb - jt) * (p - jp0) / (jp1 - jp0)

    def cross(c, k):  # 等温線 PV=c と断熱線 PV^γ=k の交点
        v = (k / c) ** (1 / (GAMMA - 1))
        return v, c / v

    def arc(fn, va_, vb_):
        pts = [va_ + (vb_ - va_) * i / 24 for i in range(25)]
        return "M" + " L".join(f"{JX(v):.1f},{JY(fn(v)):.1f}" for v in pts)

    def tile(c_lo, c_hi, k_lo, k_hi):
        v_ll, _ = cross(c_lo, k_lo)
        v_lh, _ = cross(c_lo, k_hi)
        v_hl, _ = cross(c_hi, k_lo)
        v_hh, _ = cross(c_hi, k_hi)
        return (
            (lambda v, c=c_lo: c / v, v_ll, v_lh),
            (lambda v, c=c_hi: c / v, v_hl, v_hh),
            (lambda v, k=k_lo: k / v ** GAMMA, v_ll, v_hl),
            (lambda v, k=k_hi: k / v ** GAMMA, v_lh, v_hh),
        )

    def boundary(c_lo, c_hi, k_lo, k_hi):
        """タイルの外周を、等温線・断熱線の実際の弧でつないだ閉路にする。"""
        v_ll, _ = cross(c_lo, k_lo)
        v_lh, _ = cross(c_lo, k_hi)
        v_hh, _ = cross(c_hi, k_hi)
        v_hl, _ = cross(c_hi, k_lo)
        segs = [
            arc(lambda v, c=c_lo: c / v, v_ll, v_lh),
            arc(lambda v, k=k_hi: k / v ** GAMMA, v_lh, v_hh),
            arc(lambda v, c=c_hi: c / v, v_hh, v_hl),
            arc(lambda v, k=k_lo: k / v ** GAMMA, v_hl, v_ll),
        ]
        return segs[0] + "".join(" L" + seg[1:] for seg in segs[1:]) + " Z"

    c1, c2, c3, k1, k2 = 2.00, 2.16, 2.33, 2.20, 2.38
    for c_lo, c_hi, color in ((c1, c2, ORANGE), (c2, c3, BLUE)):
        d = boundary(c_lo, c_hi, k1, k2)
        s.path(d, fill=color, stroke=color, sw=1.8, opacity=0.30)
        s.path(d, stroke=color, sw=1.8)
    s.path(arc(lambda v: c2 / v, *[cross(c2, k)[0] for k in (k1, k2)]), stroke=INK, sw=3.4)
    s.text(JX(1.45), JY(1.60), "A", size=13, fill=ORANGE, anchor="middle", weight="700")
    s.text(JX(0.96), JY(2.46), "B", size=13, fill=BLUE, anchor="middle", weight="700")
    s.line(JX(1.20), JY(1.94), JX(1.34), JY(2.34), stroke=INK, sw=1.2)
    s.text(JX(1.36), JY(2.42), "共有する辺", size=11.5, fill=INK, weight="700")
    s.text(ix + iw / 2, iy + ih - 6, "A が放熱する辺は、B が受熱する辺", size=11.5,
           fill=INK2, anchor="middle")

    s.lines_of_text(462, 332, (
        "・タイル1枚は等温線2本と断熱線2本で",
        "　囲まれた小さなカルノーサイクル",
        "・1枚だけなら Q_H / T_H = Q_C / T_C",
        "・共有する辺は2枚が逆向きにたどるので和は0",
        "・足し合わせると内部は消え、外周だけが残る",
    ), size=11.5, fill=INK2, lh=19)

    s.text(380, 452, "タイルを限りなく細かくすれば、外周の任意の可逆サイクルでも ∮ δQ_rev / T = 0。",
           size=12, fill=INK2, anchor="middle")
    s.text(380, 474, "閉じた経路で0なら2点間の Q/T の差は経路によらない。ここで初めて、状態量 S を置ける。",
           size=12, fill=INK2, anchor="middle")
    s.save("fig6-carnot-tiling.svg")


def fig_water_melting_line():
    s = Svg(760, 462, "図7　水の融解線は左へ傾く ── 加圧は氷を融かす向き",
            "0℃付近で dP/dT ≈ −13.5 MPa/K。−3℃の水を圧力だけで凍らせようとしても、向きが逆で桁も違う")
    L, R, T, B = 96, 430, 118, 340
    t0, t1, p1 = -4.2, 1.0, 55.0

    def X(t):
        return L + (R - L) * (t - t0) / (t1 - t0)

    def Y(p):
        return B - (B - T) * p / p1

    def melt_p(t):  # クラペイロンの式による融解線（0℃・0.1 MPa を通る直線近似）
        return 0.1 - 13.5 * t

    t_top = (0.1 - p1) / 13.5   # 上端 55 MPa と交わる温度
    t_bottom = 0.1 / 13.5       # 下端 0 MPa と交わる温度
    ice = (f"M{L:.1f},{T:.1f} L{X(t_top):.1f},{T:.1f} "
           f"L{X(t_bottom):.1f},{B:.1f} L{L:.1f},{B:.1f} Z")
    liquid = (f"M{X(t_top):.1f},{T:.1f} L{R:.1f},{T:.1f} L{R:.1f},{B:.1f} "
              f"L{X(t_bottom):.1f},{B:.1f} Z")
    s.path(ice, fill=BLUE, stroke="none", opacity=0.13)
    s.path(liquid, fill=AQUA, stroke="none", opacity=0.10)
    s.path(f"M{X(t_top):.1f},{T:.1f} L{X(t_bottom):.1f},{B:.1f}", stroke=INK, sw=3)

    s.line(L, T - 10, L, B, stroke=INK3, sw=1.4)
    s.line(L, B, R, B, stroke=INK3, sw=1.4)
    for t in (-4, -3, -2, -1, 0, 1):
        s.line(X(t), B, X(t), B + 5, stroke=INK3, sw=1.2)
        s.text(X(t), B + 20, f"{t}℃".replace("-", "−"), size=11, fill=INK3, anchor="middle")
    for p in (0, 10, 20, 30, 40, 50):
        s.line(L - 5, Y(p), L, Y(p), stroke=INK3, sw=1.2)
        s.text(L - 9, Y(p) + 4, f"{p:g}", size=11, fill=INK3, anchor="end")
    s.text(L - 9, T - 18, "圧力（MPa）", size=11.5, fill=INK2, anchor="end")
    s.text((L + R) / 2, B + 42, "温度 →", size=12, fill=INK2, anchor="middle")

    s.text(140, 300, "氷", size=17, fill=BLUE, anchor="middle", weight="700")
    s.text(368, 262, "液体（水）", size=15, fill=INK, anchor="middle", weight="700")
    s.line(244, 208, 224, 214, stroke=INK2, sw=1.2)
    s.text(250, 214, "dP/dT ≈ −13.5 MPa/K", size=11.5, fill=INK2)

    p_need = melt_p(-3.0)
    s.arrow(X(-3), Y(0.1), X(-3), Y(p_need), color=RED, sw=2.8)
    s.circle(X(-3), Y(p_need), 4.5, fill=RED)
    s.text(196, 140, "−3℃で融け始めるのは約40 MPa", size=11.5, fill=RED, weight="700")
    s.text(196, 158, "加圧すると、氷ではなく液体が有利になる", size=11.5, fill=RED)
    s.text(X(-3) + 10, Y(0.1) - 8, "常圧 0.1 MPa", size=11, fill=INK3)

    il, ir, it, ib = 500, 706, 158, 300
    s.rect(470, 118, 262, 222, fill="#ffffff", stroke=CARD_EDGE, rx=9)
    s.text(601, 142, "多くの物質（模式図）", size=12.5, fill=INK, anchor="middle", weight="700")
    s.line(il, it - 6, il, ib, stroke=INK3, sw=1.3)
    s.line(il, ib, ir, ib, stroke=INK3, sw=1.3)
    s.path(f"M{il + 16},{ib - 8} L{ir - 16},{it + 8}", stroke=INK, sw=2.6)
    s.text(il + 42, it + 30, "固体", size=12.5, fill=INK2, anchor="middle", weight="700")
    s.text(ir - 40, ib - 26, "液体", size=12.5, fill=INK2, anchor="middle", weight="700")
    s.text(601, 322, "ΔV > 0 なので dP/dT > 0。加圧で固体側が有利。", size=11.5,
           fill=INK2, anchor="middle")

    s.text(380, 406, "氷は液体より体積が大きく ΔV < 0。だから水の融解線だけが左へ傾き、加圧は融点を下げる。",
           size=12, fill=INK2, anchor="middle")
    s.text(380, 428, "1 K 動かすのに約13.5 MPa。減圧して凍らせても、潜熱 334 kJ/kg を捨てる先は消えない。",
           size=12, fill=INK2, anchor="middle")
    s.save("fig7-water-melting-line.svg")


def fig_exergy_ranking():
    s = Svg(760, 420, "図8　同じ1 MJでも、環境まで戻す間に取り出せる最大仕事は違う",
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
    s.save("fig8-exergy-ranking.svg")


def fig_lost_work_scale():
    s = Svg(760, 384, "図9　混ぜた瞬間に捨てた約11万段と、拾えた30段",
            "80℃と20℃の水を1 kgずつ直接混合：S_gen ≒ 36 J/K、W_lost = 293 × 36 ≒ 10.6 kJ ＝ 約11万段")
    x0, x1 = 60, 700
    s.rect(x0, 118, x1 - x0, 54, fill=ORANGE, stroke=ORANGE, rx=6, sw=1.6, opacity=0.20)
    s.text((x0 + x1) / 2, 151, "直接混合で失った最大仕事　10.6 kJ ＝ 約11万段", size=13.5,
           fill=INK, anchor="middle", weight="700")
    s.rect(x0, 118, 3, 54, fill=RED, stroke="none")
    s.text(x0 + 10, 110, "30段はこの左端（線の太さは実寸ではない）", size=11, fill=RED)

    zt, zh = 252, 48
    s.line(x0, 176, x0, zt, stroke=INK3, sw=1.2, dash="5 4")
    s.line(x0 + 3, 176, x1, zt, stroke=INK3, sw=1.2, dash="5 4")
    s.text(x0 + 18, 240, "左端の100段ぶんを拡大（全体の約0.09%）", size=11.5, fill=INK3)
    s.rect(x0, zt, x1 - x0, zh, fill="#ffffff", stroke=CARD_EDGE, rx=6)
    s.rect(x0, zt, (x1 - x0) * 0.30, zh, fill=RED, stroke=RED, rx=6, sw=1.6, opacity=0.22)
    s.text(x0 + (x1 - x0) * 0.15, zt + 30, "30段", size=14, fill=RED, anchor="middle", weight="700")
    s.text(x0 + (x1 - x0) * 0.30 + 14, zt + 30, "＝ 最高記録（約2.9 J）。11万段のうち 0.03%", size=12.5, fill=INK)

    s.text(380, 342, "エネルギーは1 Jも減っていない。減ったのは、そこから取り出せる仕事の上限だけ。",
           size=12, fill=INK2, anchor="middle")
    s.text(380, 364, "しかも熱の大部分は容器壁と配管を通り、エンジンを通らずに均されていた。",
           size=12, fill=INK2, anchor="middle")
    s.save("fig9-lost-work-scale.svg")


FIGURES = (fig_refrigerator_balance, fig_heating_curve, fig_multistage_ceiling, fig_cycle,
           fig_carnot_contradiction, fig_carnot_tiling, fig_water_melting_line,
           fig_exergy_ranking, fig_lost_work_scale)


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
