#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/statistics/figs/*.svg を決定的に生成する。

配色の割り当て（この教材での意味づけ。作図規約の3系統に対応させる）
  青 #1f6fd0 : いま推定・比較したい量、正しく作った比較、残っている情報
  橙 #e07b1f : いま条件を絞った場所、注目する一点、問い合わせ
  赤 #cf3b2d : 誤った読み方、失われた比較、破綻する案
  灰 #8d8d8d : 目盛り、母集団や背景の構造、動かないもの
形でも必ず区別する（塗り／白抜き、実線／破線、○／△／×）。

本文の数値は各関数の冒頭で assert して突き合わせてから描く。
"""
import filecmp
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (  # noqa: E402
    SVG, INK, SUB, MAIN, FOCUS, WARN, MUTED,
    TINT_MAIN, TINT_FOCUS, TINT_WARN, TINT_MUTED,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "statistics" / "figs"


# ---------------------------------------------------------------- 共通ヘルパ
def lin(p0, p1, v0, v1):
    """値 v を座標へ写す一次関数。丸めて決定的な出力にする。"""
    def f(v):
        return round(p0 + (v - v0) * (p1 - p0) / float(v1 - v0), 2)
    return f


def xaxis(s, x0, x1, y, ticks, tx, labels=None, color=SUB, size=10, sw=1.2):
    """水平の目盛り軸。ticks は値のリスト、labels は同じ長さの文字列。"""
    s.line(x0, y, x1, y, stroke=color, sw=sw, cap="butt")
    for i, v in enumerate(ticks):
        px = tx(v)
        s.line(px, y, px, y + 5, stroke=color, sw=sw, cap="butt")
        if labels is not None:
            s.text(px, y + 18, labels[i], size=size, fill=color, anchor="middle")


def yaxis(s, y0, y1, x, ticks, ty, labels=None, color=SUB, size=10, sw=1.2):
    """垂直の目盛り軸。y0 が下端、y1 が上端。"""
    s.line(x, y0, x, y1, stroke=color, sw=sw, cap="butt")
    for i, v in enumerate(ticks):
        py = ty(v)
        s.line(x - 5, py, x, py, stroke=color, sw=sw, cap="butt")
        if labels is not None:
            s.text(x - 9, py + 4, labels[i], size=size, fill=color, anchor="end")


def polyline(s, pts, stroke=MAIN, sw=2.0, dash=None):
    d = "M " + " L ".join("%g %g" % (round(x, 2), round(y, 2)) for x, y in pts)
    s.path(d, stroke=stroke, sw=sw, dash=dash)


def tri_up(s, cx, cy, r=6, fill=FOCUS, stroke=None, sw=1.2):
    """上向き三角。色だけでなく形でも区別するための印。"""
    d = "M %g %g L %g %g L %g %g Z" % (
        round(cx, 2), round(cy - r, 2),
        round(cx + r * 0.9, 2), round(cy + r * 0.7, 2),
        round(cx - r * 0.9, 2), round(cy + r * 0.7, 2))
    s.path(d, stroke=stroke or fill, sw=sw, fill=fill)


def tri_down(s, cx, cy, r=6, fill=FOCUS, stroke=None, sw=1.2):
    d = "M %g %g L %g %g L %g %g Z" % (
        round(cx, 2), round(cy + r, 2),
        round(cx + r * 0.9, 2), round(cy - r * 0.7, 2),
        round(cx - r * 0.9, 2), round(cy - r * 0.7, 2))
    s.path(d, stroke=stroke or fill, sw=sw, fill=fill)


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def binom_pmf(k, n, p):
    c = math.factorial(n) // (math.factorial(k) * math.factorial(n - k))
    return c * p ** k * (1 - p) ** (n - k)


def normal_pdf(x, mu, sd):
    return math.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))


def lcg(seed):
    """決定的な擬似乱数（線形合同法）。Date/Random を使わずに図を再現可能にする。"""
    state = [seed]

    def nxt():
        state[0] = (1103515245 * state[0] + 12345) % (2 ** 31)
        return state[0] / float(2 ** 31)
    return nxt


def std_normal_pair(u1, u2):
    """Box-Muller。u1, u2 は (0,1) の一様乱数。"""
    r = math.sqrt(-2.0 * math.log(max(u1, 1e-12)))
    return r * math.cos(2 * math.pi * u2), r * math.sin(2 * math.pi * u2)


# ---------------------------------------------------------------- 1-2
def fig1_2():
    """1-2 同じ平均3,000円でも、並べると形が違う。

    本文の二市場 A=2800,2900,3000,3100,3200 / B=0,0,1000,4000,10000。
    どちらも合計15,000円・平均3,000円。中央値は3,000円と1,000円。

    グリッド（先に宣言し、この座標だけを使う）
      価格軸  px(v) = 80 + v*0.061   (0円 → 80 / 10,000円 → 690)
      y  40 タイトル / 92 A の帯ラベル / 120 A の点列 / 150 A の中央値印
         190 B の帯ラベル / 218 B の点列 / 248 B の中央値印
         276 価格目盛り軸 / 300 目盛りラベル
      色  青＝観測した回答（塗り丸） / 橙＝中央値（三角） / 灰＝平均3,000円の縦線
    """
    a = [2800, 2900, 3000, 3100, 3200]
    b = [0, 0, 1000, 4000, 10000]
    assert sum(a) == 15000 and sum(b) == 15000
    assert sum(a) / 5 == 3000 and sum(b) / 5 == 3000
    assert sorted(a)[2] == 3000 and sorted(b)[2] == 1000
    assert max(a) - min(a) == 400 and max(b) - min(b) == 10000

    s = SVG(760, 366,
            "同じ平均3,000円でも、Aは中心に固まりBは両端へ割れる")
    px = lin(96, 690, 0, 10000)

    s.text(52, 32, "平均はどちらも 3,000 円。同じ物差しへ並べると別の市場になる",
           size=14, weight="700")

    # 平均3,000円の縦線（両方の帯を貫く、動かない基準）
    s.line(px(3000), 118, px(3000), 296, stroke=MUTED, sw=1.6, dash="6 4")

    # 商品A：主軸の上ではひと塊にしか見えない
    s.text(52, 126, "商品A", size=13, weight="700", fill=INK)
    s.text(52, 144, "2,800〜3,200 円", size=10, fill=SUB)
    s.rect(px(2800) - 9, 124, px(3200) - px(2800) + 18, 26,
           fill=TINT_MAIN, stroke=MAIN, sw=1.6, rx=13)
    for v in a:
        s.circle(px(v), 137, 4, fill=MAIN, stroke=MAIN, sw=1.0)
    s.line(px(3200) + 12, 140, 374, 152, stroke=MUTED, sw=1.0, dash="4 3")

    # 商品A の拡大パネル
    s.rect(378, 62, 322, 108, fill="#ffffff", stroke=MUTED, sw=1.2, rx=4)
    s.text(392, 80, "商品A の拡大", size=11, fill=SUB, weight="700")
    zx = lin(408, 674, 2750, 3250)
    s.dim(zx(2800), zx(3200), 98, "範囲 400 円", up=True)
    for v in a:
        s.circle(zx(v), 122, 6.5, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
    tri_up(s, zx(3000), 138, 6, fill=FOCUS)
    s.text(zx(3000), 160, "中央値 3,000 円", size=10, fill=FOCUS, anchor="middle")

    # 二つの市場で共通の平均
    s.dim(px(0), px(10000), 186, "範囲 10,000 円", up=True)
    s.text(px(3000) + 10, 208, "平均 3,000 円", size=11, fill=SUB, weight="700")
    s.text(px(3000) + 10, 224, "← 二つの市場で共通", size=10, fill=SUB)

    # 商品B
    s.text(52, 230, "商品B", size=13, weight="700", fill=INK)
    seen = {}
    for v in b:
        n = seen.get(v, 0)
        seen[v] = n + 1
        s.circle(px(v), 256 - n * 17, 6.5, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
    tri_up(s, px(1000), 278, 6.5, fill=FOCUS)
    s.text(px(1000), 300, "中央値 1,000 円", size=10, fill=FOCUS, anchor="middle")

    xaxis(s, 76, 706, 322,
          [0, 2000, 4000, 6000, 8000, 10000], px,
          ["0", "2,000", "4,000", "6,000", "8,000", "10,000 円"])
    s.text(391, 358, "希望価格", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 1-3
def fig1_3():
    """1-3 各列の分布は同じまま、組み方だけで向きが逆になる。

    本文の二調査。時間 5,10,15,20,25 分と価格 1,000〜3,000 円は共通で、
    調査1は小さい順どうし、調査2は価格だけ逆順で組む。

    グリッド
      調査1 作図領域 x 118..330 / 調査2 x 458..670（同一スケール）
      tx(分) = lin(118,330,5,25)（調査2は +340）
      ty(円) = lin(232,72,1000,3000)
      y  36 タイトル / 60 パネル名 / 72..232 作図領域 / 252 時間の周辺
         x  100（調査2は 440）価格の周辺
      色  青＝同じ人の時間と価格の組（塗り丸） / 灰＝周辺（列ごとの分布、白抜き丸）
    """
    times = [5, 10, 15, 20, 25]
    up = [1000, 1500, 2000, 2500, 3000]
    down = [3000, 2500, 2000, 1500, 1000]
    assert sorted(up) == sorted(down)
    assert sum(up) == sum(down)

    s = SVG(760, 312,
            "列ごとの分布が同じでも、組を替えると散布図は逆向きになる")
    s.text(40, 32, "同じ二つの列。組を切り替えると、点の向きだけが反転する",
           size=14, weight="700")
    s.text(40, 50, "縦＝希望価格 1,000〜3,000 円　／　横＝遊んだ時間 5〜25 分",
           size=10, fill=SUB)

    def panel(x0, prices, name, arrow_up):
        tx = lin(x0, x0 + 212, 5, 25)
        ty = lin(248, 88, 1000, 3000)
        s.text(x0 - 18, 74, name, size=12, weight="700", fill=INK)
        s.rect(x0 - 14, 82, 240, 172, fill="#ffffff", stroke=MUTED, sw=1.0)
        # 周辺（列ごとの分布）は両パネルで同一
        for t in times:
            s.circle(tx(t), 268, 4.5, fill="#ffffff", stroke=MUTED, sw=1.4)
        for p in [1000, 1500, 2000, 2500, 3000]:
            s.circle(x0 - 32, ty(p), 4.5, fill="#ffffff", stroke=MUTED, sw=1.4)
        pts = [(tx(t), ty(p)) for t, p in zip(times, prices)]
        polyline(s, pts, stroke=MAIN, sw=1.4, dash="5 4")
        for cx, cy in pts:
            s.circle(cx, cy, 6, fill=TINT_MAIN, stroke=MAIN, sw=1.9)
        lab = "長く遊ぶほど高い" if arrow_up else "長く遊ぶほど安い"
        s.text(x0 + 106, 294, lab, size=11, fill=MAIN,
               anchor="middle", weight="700")

    panel(118, up, "調査1", True)
    panel(458, down, "調査2", False)

    s.text(40, 272, "時間の分布", size=10, fill=SUB)
    s.text(78, 100, "価格の", size=10, fill=SUB, anchor="end")
    s.text(78, 113, "分布", size=10, fill=SUB, anchor="end")
    s.text(702, 272, "どちらも同じ", size=10, fill=SUB)
    s.text(702, 285, "白丸の並び", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 2-1
def fig2_1():
    """2-1 幅が人口比、高さが購入希望率。面積の合計が34%。

    本文の設定。一般家庭30%が市場の90%、ファンクラブ会員70%が10%。
    0.1*0.7 + 0.9*0.3 = 0.34。二率の単純平均50%とは別の量。

    グリッド
      x  幅 = 市場に占める割合。sx(w) = lin(90,690,0,1)
         会員 0..0.10 → 90..150 / 一般 0.10..1.00 → 150..690
      y  高さ = 購入希望率。sy(p) = lin(286,66,0,1)
         70% → 132 / 30% → 220 / 34% → 211.2 / 50% → 176
      y  34 タイトル / 300 目盛り軸 / 318 目盛りラベル
      色  青＝人口比で重み付けした34% / 赤＝重みを捨てた50%（誤り） / 橙＝会員の柱
    """
    p_member, p_general, share_member = 0.70, 0.30, 0.10
    weighted = share_member * p_member + (1 - share_member) * p_general
    assert abs(weighted - 0.34) < 1e-12
    assert abs((p_member + p_general) / 2 - 0.50) < 1e-12

    s = SVG(760, 344,
            "幅を人口比、高さを購入希望率にすると、市場全体は34%になる")
    sx = lin(90, 690, 0, 1)
    sy = lin(286, 66, 0, 1)
    s.text(60, 32, "会員を1万人集めても、届くのは左の細い柱の高さだけ",
           size=14, weight="700")
    s.text(90, 52, "縦＝購入希望率　／　横＝市場に占める割合（面積が人数）",
           size=10, fill=SUB)

    # 一般家庭（背景の構造）
    s.rect(sx(0.10), sy(p_general), sx(1.0) - sx(0.10), 286 - sy(p_general),
           fill=TINT_MUTED, stroke=MUTED, sw=1.4)
    s.text((sx(0.10) + sx(1.0)) / 2, sy(p_general) + 34,
           "一般家庭　市場の90%・購入希望30%", size=12, fill=INK, anchor="middle")

    # 会員（いま注目している柱）
    s.rect(sx(0), sy(p_member), sx(0.10) - sx(0), 286 - sy(p_member),
           fill=TINT_FOCUS, stroke=FOCUS, sw=2.0)
    s.text(sx(0.05), sy(p_member) - 26, "会員", size=12, fill=FOCUS,
           anchor="middle", weight="700")
    s.text(sx(0.05), sy(p_member) - 12, "市場の10%", size=10, fill=FOCUS,
           anchor="middle")
    s.text(sx(0.10) + 8, sy(p_member) + 14, "購入希望 70%", size=11, fill=FOCUS)

    # 重みを捨てた単純平均（誤り）
    s.line(sx(0), sy(0.50), sx(1.0), sy(0.50), stroke=WARN, sw=1.8, dash="7 4")
    s.text(sx(1.0) + 6, sy(0.50) + 4, "50%", size=11, fill=WARN, weight="700")
    s.text(sx(0.36), sy(0.50) - 8, "二つの率を同じ重さで平均した 50%（誤り）",
           size=11, fill=WARN)

    # 人口比で重み付けした値
    s.line(sx(0), sy(weighted), sx(1.0), sy(weighted), stroke=MAIN, sw=2.4)
    s.text(sx(1.0) + 6, sy(weighted) + 4, "34%", size=11, fill=MAIN, weight="700")
    s.text(sx(0.32), sy(weighted) - 8,
           "0.1×0.7 ＋ 0.9×0.3 ＝ 34%（この線より下の面積 ＝ 二本の柱の面積）",
           size=11, fill=MAIN)

    xaxis(s, 90, 700, 300, [0, 0.10, 0.5, 1.0], sx,
          ["0", "10%", "50%", "100%"])
    yaxis(s, 286, 66, 90, [0, 0.5, 1.0], sy, ["0", "50%", "100%"])
    return s


# ---------------------------------------------------------------- 3-2
def fig3_2():
    """3-2 同じ検査機でも、入口の故障率で警報の意味が変わる。

    本文の二場面。工場（1,000台中10台が故障＝1%）と修理工場（故障率50%）。
    感度90%・誤警報5%は共通。警報後の故障確率は 9/58.5≒15% と 45/47.5≒95%。

    グリッド（二パネルで座標を固定し、変えるのは入口の故障率だけ）
      パネル左 x 70..360 / 右 x 430..720
      幅 = 母集団に占める割合、高さ = 警報が出る確率
      sy(p) = lin(268,74,0,1)  （0% → 268 / 90% → 93.4 / 5% → 258.3）
      y  34 タイトル / 60 パネル名 / 268 底辺 / 286 幅ラベル / 312 結論
      色  青＝故障から出た警報（実線・塗り） / 赤＝正常から出た誤警報（破線・淡塗り）
          灰＝警報が出なかった部分
    """
    sens, fpr = 0.90, 0.05
    cases = []
    for n, rate in ((1000, 0.01), (100, 0.50)):
        tp = n * rate * sens
        fp = n * (1 - rate) * fpr
        cases.append((n, rate, tp, fp, tp / (tp + fp)))
    assert abs(cases[0][2] - 9.0) < 1e-9 and abs(cases[0][3] - 49.5) < 1e-9
    assert abs(cases[0][4] - 0.1538461538) < 1e-9
    assert abs(cases[1][2] - 45.0) < 1e-9 and abs(cases[1][3] - 2.5) < 1e-9
    assert abs(cases[1][4] - 0.9473684210) < 1e-9

    s = SVG(760, 330,
            "感度90%・誤警報5%は同じでも、故障率1%と50%では警報の意味が変わる")
    s.text(46, 32, "同じ検査機。入口の故障率だけを替えると、警報の中身が入れ替わる",
           size=14, weight="700")
    s.text(46, 50, "縦＝警報が出る確率（感度90% と 誤警報5%）　／　横＝母集団に占める割合",
           size=10, fill=SUB)
    sy = lin(268, 78, 0, 1)

    def panel(x0, title, n, rate, tp, fp, ppv):
        x1 = x0 + 288
        sx = lin(x0, x1, 0, 1)
        s.text(x0, 76, title, size=13, weight="700", fill=INK)
        s.text(x0 + 74, 76, "全%d台のうち故障 %d%%"
               % (n, round(rate * 100)), size=11, fill=SUB)
        # 全体の枠（白抜きにして、中のラベルが読めるようにする）
        s.rect(x0, sy(1.0), x1 - x0, 268 - sy(1.0),
               fill="#ffffff", stroke=MUTED, sw=1.2)
        xb = sx(rate)
        s.line(xb, sy(1.0), xb, 268, stroke=MUTED, sw=1.2)
        # 故障から出た警報（実線・塗り）
        s.rect(x0, sy(sens), xb - x0, 268 - sy(sens),
               fill=TINT_MAIN, stroke=MAIN, sw=2.0)
        # 正常から出た誤警報（破線・淡塗り）
        s.rect(xb, sy(fpr), x1 - xb, 268 - sy(fpr),
               fill=TINT_WARN, stroke=WARN, sw=1.8, dash="5 3")
        s.text(max(x0 + 8, xb + 6), sy(sens) - 9,
               "故障→警報 %s台" % ("%g" % tp),
               size=11, fill=MAIN, weight="700")
        s.text(x1 - 4, sy(fpr) - 9, "正常→誤警報 %s台" % ("%g" % fp),
               size=11, fill=WARN, weight="700", anchor="end")
        s.text(x0, 288, "← 故障", size=10, fill=SUB)
        s.text(x1, 288, "正常 →", size=10, fill=SUB, anchor="end")
        s.text(x0 + 144, 314,
               "警報のうち本当の故障は %.0f%%" % round(ppv * 100),
               size=13, fill=FOCUS, anchor="middle", weight="700")

    panel(72, "工場", *cases[0])
    panel(432, "修理工場", *cases[1])
    yaxis(s, 268, 78, 72, [0, 0.5, 1.0], sy, ["0", "50%", "100%"])
    return s


# ---------------------------------------------------------------- 3-3
def fig3_3():
    """3-3 重りの置き方が違っても、支点（期待値）は同じ800円。

    本文の見積もり 0円80% / 2,000円15% / 10,000円5% は期待値800円。
    案B 0円92% / 10,000円8% も期待値800円で、分散だけが違う。
    重りの面積を確率へ比例させる（半径 ∝ √p）。

    グリッド
      費用軸 px(v) = lin(96, 690, 0, 10000)  （800円 → 143.5 / 2,000円 → 214.8）
      y  34 タイトル / 108 見積もりの梁 / 148 支点 / 228 案Bの梁 / 268 支点
         296 費用目盛り / 314 目盛りラベル
      色  青＝重り（確率） / 橙＝支点＝期待値800円 / 灰＝目盛り
    """
    est = [(0, 0.80), (2000, 0.15), (10000, 0.05)]
    alt = [(0, 0.92), (10000, 0.08)]
    ev_est = sum(v * p for v, p in est)
    ev_alt = sum(v * p for v, p in alt)
    var_alt = sum(v ** 2 * p for v, p in alt) - ev_alt ** 2
    var_est = sum(v ** 2 * p for v, p in est) - ev_est ** 2
    assert ev_est == 800 and ev_alt == 800
    assert abs(var_alt / 1e6 - 7.36) < 1e-9          # 本文の 7.36（千円単位）
    assert abs(math.sqrt(var_alt) / 1000 - 2.7129) < 1e-3

    s = SVG(760, 356,
            "重りの置き方が違っても、期待値という支点は同じ800円に来る")
    px = lin(96, 690, 0, 10000)
    s.text(60, 32, "期待値800円は、一度も起こらない値。重りを支える点として決まる",
           size=14, weight="700")
    s.text(60, 50, "丸の面積が確率、支点が期待値", size=10, fill=SUB)

    def beam(y, items, name, name_y, sd_yen):
        s.text(60, name_y, name, size=12, weight="700", fill=INK)
        s.line(px(0) - 20, y, px(10000) + 20, y, stroke=INK, sw=2.2, cap="butt")
        for v, p in items:
            r = round(26 * math.sqrt(p), 2)
            s.circle(px(v), y - r - 2, r, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
            s.text(px(v), y - r * 2 - 10, "%d%%" % round(p * 100),
                   size=11, fill=MAIN, anchor="middle", weight="700")
        tri_up(s, px(800), y + 12, 9, fill=FOCUS)
        s.text(px(800) + 14, y + 32, "期待値 800 円", size=11, fill=FOCUS,
               weight="700")
        s.text(px(10000) + 20, y + 26,
               "標準偏差 約 %s 円" % format(sd_yen, ","),
               size=10, fill=SUB, anchor="end", weight="700")

    beam(152, est, "品質部の見積もり　0円80% ／ 2,000円15% ／ 10,000円5%", 78,
         int(round(math.sqrt(var_est) / 10) * 10))
    beam(272, alt, "案B　0円92% ／ 10,000円8%", 200,
         int(round(math.sqrt(var_alt) / 10) * 10))

    xaxis(s, 76, 706, 316, [0, 2000, 4000, 6000, 8000, 10000], px,
          ["0", "2,000", "4,000", "6,000", "8,000", "10,000 円"])
    s.text(391, 350, "一台あたりの保証費用", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 4-1
def fig4_1():
    """4-1 十時間の実測と、平均2のポアソン分布。

    本文の実測 0,1,2,5,1,3,0,2,4,2（合計20、平均2）。
    P(N=0)=e^-2≒0.135 に対し、十時間の実測では0回が2つで20%。

    グリッド
      左パネル  時刻軸 tx(i) = lin(96, 336, 0, 9) / 件数軸 ly(c) = lin(232, 82, 0, 5)
      右パネル  回数軸 kx(k) = lin(444, 690, 0, 6) / 確率軸 ry(p) = lin(232, 82, 0, 0.3)
      y  34 タイトル / 60 パネル名 / 232 底辺 / 250 目盛りラベル / 276 注記
      色  青＝実測 / 橙＝0回のところ（理論13.5%対実測20%） / 灰＝ポアソンの理論値
    """
    obs = [0, 1, 2, 5, 1, 3, 0, 2, 4, 2]
    assert sum(obs) == 20 and sum(obs) / len(obs) == 2
    assert abs(poisson_pmf(0, 2) - 0.1353352832) < 1e-9
    assert obs.count(0) / len(obs) == 0.2

    s = SVG(760, 302, "十時間の実測と、平均2のポアソン分布を並べる")
    s.text(60, 32, "平均2でも、黙る時間と五回鳴く時間が同じ模型から出る",
           size=14, weight="700")

    # 左：時間順の実測
    tx = lin(96, 336, 0, 9)
    ly = lin(232, 82, 0, 5)
    s.text(74, 60, "十時間の実測（件／時）", size=12, weight="700", fill=INK)
    for i, c in enumerate(obs):
        col = FOCUS if c == 0 else MAIN
        s.rect(tx(i) - 8, ly(c), 16, 232 - ly(c),
               fill=TINT_FOCUS if c == 0 else TINT_MAIN, stroke=col, sw=1.6)
        s.text(tx(i), ly(c) - 6, str(c), size=10, fill=col, anchor="middle")
    s.line(74, ly(2), 352, ly(2), stroke=MUTED, sw=1.6, dash="6 4")
    s.text(354, ly(2) + 4, "平均2", size=10, fill=SUB)
    xaxis(s, 74, 352, 232, [0, 2, 4, 6, 8], tx, ["1", "3", "5", "7", "9"])
    s.text(205, 268, "何時間目", size=10, fill=SUB, anchor="middle")

    # 右：理論分布と実測割合
    kx = lin(486, 700, 0, 6)
    ry = lin(232, 82, 0, 0.30)
    s.text(422, 60, "平均2のポアソンと、十時間の割合", size=12, weight="700", fill=INK)
    for k in range(7):
        th = poisson_pmf(k, 2)
        s.rect(kx(k) - 12, ry(th), 24, 232 - ry(th),
               fill=TINT_MUTED, stroke=MUTED, sw=1.4)
        emp = obs.count(k) / 10.0
        if emp > 0:
            col = FOCUS if k == 0 else MAIN
            s.line(kx(k) - 14, ry(emp), kx(k) + 14, ry(emp), stroke=col, sw=2.8)
    s.text(468, ry(0.20) + 4, "0回の実測 20%", size=10, fill=FOCUS,
           anchor="end", weight="700")
    s.text(468, ry(0.1353) + 4, "0回の理論 13.5%", size=10, fill=SUB,
           anchor="end")
    xaxis(s, 464, 716, 232, [0, 1, 2, 3, 4, 5, 6], kx,
          ["0", "1", "2", "3", "4", "5", "6"])
    s.text(590, 268, "一時間あたりの件数", size=10, fill=SUB, anchor="middle")
    s.text(422, 292, "灰の柱＝ポアソンの確率、横棒＝十時間での割合",
           size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 5-1
def fig5_1():
    """5-1 個体の散らばり（標準偏差）と、推定値の散らばり（標準誤差）は階層が違う。

    本文の三回の100人調査（62人・57人・66人）。
    Var(p^)=p(1-p)/n なので標準誤差は sqrt(0.62*0.38/100)≒0.0485＝約4.9ポイント。

    グリッド
      上段（推定値の階層）  px(p) = lin(150, 660, 0.44, 0.80)
        曲線 y 84..194（正規近似、頂点の高さ110）/ 底辺 194
        62/57/66 の印 y 194 / 標準誤差の寸法線 y 218
      下段（個体の階層）  帯 x 150..660、y 268..296 を100分割
      y  32 タイトル / 68 上段ラベル / 250 下段ラベル / 314 注記
      色  青＝標本ごとに動く推定値の分布 / 橙＝実際に得た三つの値 / 灰＝個体
    """
    p, n = 0.62, 100
    se = math.sqrt(p * (1 - p) / n)
    assert abs(se - 0.048538) < 1e-6
    assert round(se * 100, 1) == 4.9

    s = SVG(760, 340,
            "標本比率が揺れる。個体の散らばりと推定値の散らばりは階層が違う")
    px = lin(150, 660, 0.44, 0.80)
    s.text(52, 32, "同じ手順で選び直すたび、標本比率は別の値になる", size=14, weight="700")

    # 上段：推定値の標本分布
    s.text(52, 68, "調査を繰り返したときの標本比率（中心 62%）", size=12,
           weight="700", fill=INK)
    peak = normal_pdf(p, p, se)
    pts = []
    v = 0.44
    while v <= 0.8001:
        pts.append((px(v), 194 - 110 * normal_pdf(v, p, se) / peak))
        v += 0.002
    polyline(s, pts, stroke=MAIN, sw=2.2)
    s.line(150, 194, 660, 194, stroke=SUB, sw=1.2, cap="butt")
    for val, lab in ((0.62, "62人"), (0.57, "57人"), (0.66, "66人")):
        top = 194 - 110 * normal_pdf(val, p, se) / peak
        s.line(px(val), 194, px(val), top, stroke=FOCUS, sw=1.6, dash="4 3")
        s.circle(px(val), top, 4.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
        s.text(px(val), top - 10, lab, size=11, fill=FOCUS, anchor="middle",
               weight="700")
    s.dim(px(p - se), px(p + se), 176, "")
    s.text(px(p + se) + 12, 180, "標準誤差 約4.9ポイント", size=10, fill=SUB)
    xaxis(s, 140, 670, 194, [0.45, 0.55, 0.65, 0.75], px,
          ["45%", "55%", "65%", "75%"])
    s.text(680, 198, "推定値の散らばり", size=10, fill=MAIN, weight="700")

    # 下段：一回の調査の中身
    s.text(52, 268, "一回の調査：100人の回答（この中の違いが標準偏差）",
           size=12, weight="700", fill=INK)
    for i in range(100):
        cx = 150 + i * 5.1
        filled = i < 62
        s.rect(cx, 286, 4.0, 24, fill=TINT_MAIN if filled else "#ffffff",
               stroke=MAIN if filled else MUTED, sw=0.9)
    s.text(52, 302, "個体の散らばり", size=10, fill=SUB)
    s.text(664, 302, "62人が「買いたい」", size=10, fill=SUB)
    s.arrow(px(p), 282, px(p), 232, stroke=MUTED, sw=1.4)
    s.text(px(p) + 10, 254, "この一回が、上の分布から引いた一点", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 6-2
def fig6_2():
    """6-2 動くのは網（区間）で、杭（真値）は固定されている。

    真の率0.62・n=100 から同じ手順で20回作った95%信頼区間。
    seed 6 の擬似乱数では20本のうち1本だけが真値を外す。

    グリッド
      px(p) = lin(150, 700, 0.42, 0.84)
      i 本目の区間  y = 78 + i*14   （i = 0..19）
      y  32 タイトル / 58 真値ラベル / 348 凡例 / 360 目盛り軸 / 378 ラベル
      色  青＝真値を覆った区間 / 赤＝外した区間（×印つき） / 灰＝固定した真値の縦線
    """
    p, n, seed = 0.62, 100, 6
    se_true = math.sqrt(p * (1 - p) / n)
    r = lcg(seed)
    zs = []
    while len(zs) < 20:
        z1, z2 = std_normal_pair(r(), r())
        zs += [z1, z2]
    rows = []
    for z in zs[:20]:
        ph = p + z * se_true
        half = 1.96 * math.sqrt(ph * (1 - ph) / n)
        rows.append((ph, ph - half, ph + half))
    misses = [i for i, (_, lo, hi) in enumerate(rows) if not lo <= p <= hi]
    assert len(misses) == 1

    s = SVG(760, 392,
            "同じ手順で作り直した20本の区間。19本が固定した真値を覆う")
    px = lin(150, 700, 0.42, 0.84)
    s.text(52, 32, "真値は固定した杭。投げ直すのは網のほうで、その95%が杭を囲む",
           size=14, weight="700")
    s.line(px(p), 62, px(p), 356, stroke=MUTED, sw=2.0, dash="7 4")
    s.text(px(p), 56, "真の率 62%（固定）", size=11, fill=SUB, anchor="middle")

    for i, (ph, lo, hi) in enumerate(rows):
        y = 78 + i * 14
        col = WARN if i in misses else MAIN
        s.line(px(lo), y, px(hi), y, stroke=col, sw=2.2)
        s.line(px(lo), y - 4, px(lo), y + 4, stroke=col, sw=1.6)
        s.line(px(hi), y - 4, px(hi), y + 4, stroke=col, sw=1.6)
        s.circle(px(ph), y, 3.0, fill=col, stroke=col, sw=1.0)
        if i in misses:
            s.cross(px(p), y, 5, stroke=WARN, sw=2.0)
            s.text(px(lo) - 10, y + 4, "外した1本", size=10, fill=WARN,
                   weight="700", anchor="end")
    s.text(52, 84, "1回目", size=10, fill=SUB)
    s.text(52, 350, "20回目", size=10, fill=SUB)

    xaxis(s, 140, 712, 360, [0.45, 0.55, 0.65, 0.75], px,
          ["45%", "55%", "65%", "75%"])
    s.text(426, 386, "調査ごとの95%信頼区間", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 7-1
def fig7_1():
    """7-1 標本数を変えずに閾値だけ動かすと、二つの誤りが綱引きになる。

    基準 p=0.5（n=100、標準誤差0.05）と、真の率0.62（標準誤差0.0485）。
    有意水準5%の閾値 0.5+1.645*0.05=0.582 で検出力78%、
    1%の閾値 0.5+2.326*0.05=0.616 で検出力53%。

    グリッド（二パネルで座標を固定し、変えるのは閾値だけ）
      左 x 70..368 / 右 x 402..700、px(p) = lin(x0, x0+298, 0.34, 0.80)
      曲線 y 96..214（頂点の高さ118）/ 底辺 214
      y  32 タイトル / 54 副題 / 78 パネル名 / 234 閾値ラベル / 268 面積の内訳
      色  赤＝誤って発売する確率（第一種） / 青＝見逃す確率（第二種） / 灰＝分布の輪郭
    """
    p0, p1, n = 0.5, 0.62, 100
    se0 = math.sqrt(p0 * (1 - p0) / n)
    se1 = math.sqrt(p1 * (1 - p1) / n)
    assert abs(se0 - 0.05) < 1e-12
    cases = []
    for z, alpha in ((1.645, 0.05), (2.326, 0.01)):
        thr = p0 + z * se0
        beta = 0.5 * (1 + math.erf((thr - p1) / (se1 * math.sqrt(2))))
        cases.append((thr, alpha, 1 - beta))
    assert abs(cases[0][0] - 0.58225) < 1e-6
    assert abs(cases[0][2] - 0.7816) < 1e-3
    assert abs(cases[1][2] - 0.5304) < 1e-3

    s = SVG(760, 328,
            "閾値を厳しくすると誤発売は減るが、見逃しが増える")
    s.text(52, 32, "標本数を変えずに閾値だけ動かすと、二つの誤りは綱引きになる",
           size=14, weight="700")
    s.text(52, 52, "灰＝基準50%が正しい世界　／　青＝真の率が62%の世界",
           size=10, fill=SUB)

    def panel(x0, title, thr, alpha, power):
        px = lin(x0, x0 + 298, 0.34, 0.80)
        s.text(x0, 78, title, size=12, weight="700", fill=INK)
        peak = normal_pdf(p0, p0, se0)
        for mu, sd, col, tint in ((p0, se0, MUTED, TINT_MUTED),
                                  (p1, se1, MAIN, TINT_MAIN)):
            pts, area = [], []
            v = 0.34
            while v <= 0.8001:
                y = 218 - 118 * normal_pdf(v, mu, sd) / peak
                pts.append((px(v), y))
                inside = v >= thr if mu == p0 else v <= thr
                if inside:
                    area.append((px(v), y))
                v += 0.002
            if area:
                d = ("M %g %g L " % (area[0][0], 218)
                     + " L ".join("%g %g" % (round(x, 2), round(y, 2))
                                  for x, y in area)
                     + " L %g %g Z" % (area[-1][0], 218))
                s.path(d, stroke="none", sw=0,
                       fill=TINT_WARN if mu == p0 else tint, op=0.95)
            polyline(s, pts, stroke=col, sw=2.0)
        s.line(x0, 218, x0 + 298, 218, stroke=SUB, sw=1.2, cap="butt")
        s.line(px(thr), 100, px(thr), 232, stroke=FOCUS, sw=2.2)
        tri_up(s, px(thr), 240, 6, fill=FOCUS)
        s.text(px(thr), 262, "境界", size=11, fill=FOCUS,
               anchor="middle", weight="700")
        s.text(x0 + 149, 288,
               "誤って発売 %d%%　／　売れるのに見逃し %d%%"
               % (round(alpha * 100), round((1 - power) * 100)),
               size=11, anchor="middle", fill=INK)
        s.text(x0 + 149, 308, "検出力 %d%%" % round(power * 100),
               size=12, anchor="middle", fill=FOCUS, weight="700")
        for val, lab in ((0.4, "40%"), (0.5, "50%"), (0.7, "70%")):
            s.text(px(val), 234, lab, size=9, fill=SUB, anchor="middle")

    panel(70, "有意水準 5%（緩い境界）", *cases[0])
    panel(402, "有意水準 1%（厳しい境界）", *cases[1])
    s.text(380, 322, "赤い面積＝誤って発売する確率、青い面積＝見逃す確率",
           size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 8-1
def fig8_1():
    """8-1 残差が大きい点と、傾きを回す点は別物。

    直線 y=x+1 にちょうど乗る5点 (1,2)(2,3)(3,4)(4,5)(5,6) へ一点を足す。
    (3,8) を足すと残差3.33だが傾きは1のまま。
    (12,9) を足すと残差-0.43しかないのに傾きは1から0.613へ回る。

    グリッド（二パネルで座標を固定し、変えるのは足した一点だけ）
      左 x 96..368 / 右 x 428..700、tx = lin(x0, x0+272, 0, 13)
      ty = lin(252, 88, 0, 14)
      y  32 タイトル / 76 パネル名 / 252 底辺 / 270 目盛り / 292 結論
      色  青＝もとの5点と、それだけで引いた線 / 橙＝足した一点と、足した後の線
    """
    base = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]

    def fit(pts):
        k = len(pts)
        mx = sum(x for x, _ in pts) / k
        my = sum(y for _, y in pts) / k
        sxy = sum((x - mx) * (y - my) for x, y in pts)
        sxx = sum((x - mx) ** 2 for x, _ in pts)
        b = sxy / sxx
        return b, my - b * mx

    b0, a0 = fit(base)
    assert abs(b0 - 1.0) < 1e-12 and abs(a0 - 1.0) < 1e-12
    b_far, a_far = fit(base + [(3, 8)])
    b_lev, a_lev = fit(base + [(12, 9)])
    assert abs(b_far - 1.0) < 1e-9
    assert abs(b_lev - 0.612903) < 1e-6
    assert abs((8 - (a_far + b_far * 3)) - 3.3333) < 1e-3
    assert abs((9 - (a_lev + b_lev * 12)) + 0.4301) < 1e-3

    s = SVG(760, 320, "残差の大きさと、傾きを回す力は別の診断")
    ty = lin(252, 88, 0, 14)
    s.text(52, 32, "線から遠い点と、線に近いのに傾きを回す点を分けて探す",
           size=14, weight="700")
    s.text(52, 52, "破線＝もとの5点だけで引いた線　／　実線＝一点を足した後の線",
           size=10, fill=SUB)

    def panel(x0, title, extra, b, a, resid, note):
        tx = lin(x0, x0 + 272, 0, 13)
        s.text(x0 - 24, 76, title, size=12, weight="700", fill=INK)
        s.rect(x0 - 20, 84, 300, 172, fill="#ffffff", stroke=MUTED, sw=1.0)
        # もとの5点だけで引いた線
        s.line(tx(0), ty(a0), tx(13), ty(a0 + b0 * 13),
               stroke=MAIN, sw=1.8, dash="6 4")
        # 一点を足した後の線
        s.line(tx(0), ty(a), tx(13), ty(a + b * 13), stroke=FOCUS, sw=2.4)
        for cx, cy in base:
            s.circle(tx(cx), ty(cy), 5.5, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
        s.line(tx(extra[0]), ty(extra[1]), tx(extra[0]),
               ty(a + b * extra[0]), stroke=FOCUS, sw=1.4, dash="3 3")
        s.circle(tx(extra[0]), ty(extra[1]), 7, fill=FOCUS, stroke=FOCUS, sw=1.8)
        s.text(x0 + 126, 274, "足した点の残差 %.2f　傾き %.2f" % (resid, b),
               size=11, anchor="middle", fill=INK)
        s.text(x0 + 126, 296, note, size=12, anchor="middle",
               fill=FOCUS, weight="700")

    panel(96, "線から遠い点（3, 8）", (3, 8), b_far, a_far,
          8 - (a_far + b_far * 3), "傾きは 1 のまま動かない")
    panel(428, "端にある点（12, 9）", (12, 9), b_lev, a_lev,
          9 - (a_lev + b_lev * 12), "残差は小さいのに傾きが回る")
    return s


# ---------------------------------------------------------------- 8-2
def fig8_2():
    """8-2 「人口をそろえて広告費だけ違う地域」がデータに無い。

    12地域の人口と広告費が細い帯へ乗ると、帯に直交する向きの比較が作れない。
    座標は人口 10,15,…,65 万人、広告費 = 人口*0.5 + 決められたずれ。

    グリッド
      tx(人口) = lin(150, 640, 5, 70) / ty(広告費) = lin(268, 84, 0, 40)
      照会する縦帯  人口 35〜40万人（tx で 414..452）
      y  32 タイトル / 58 副題 / 288 目盛り / 312 注記
      色  青＝観測した地域 / 橙＝答えたい比較（人口を固定して広告費だけ動かす）
          赤＝その比較にデータが無い区間
    """
    pops = [10, 15, 20, 25, 30, 36, 38, 44, 49, 54, 60, 65]
    offs = [0.8, -0.6, 1.0, -0.9, 0.5, -0.4, 0.4, -1.0, 0.6, -0.7, 1.1, -0.5]
    ads = [round(p * 0.5 + o, 2) for p, o in zip(pops, offs)]
    in_band = [a for p, a in zip(pops, ads) if 35 <= p <= 39]
    assert len(in_band) == 2
    # 帯の中で広告費が動く幅は、全体の広がりの1割ほどしかない
    assert max(in_band) - min(in_band) < 2.0
    assert max(ads) - min(ads) > 20.0

    s = SVG(760, 330,
            "人口をそろえると広告費がほとんど動かず、二本の坂を分けられない")
    tx = lin(150, 640, 5, 70)
    ty = lin(268, 84, 0, 40)
    s.text(52, 32, "係数を分けるには、片方だけ動いた地域が要る", size=14, weight="700")
    s.text(52, 52, "点はどれも一本の帯に乗り、帯に直交する向きの比較が作れない",
           size=10, fill=SUB)

    s.rect(tx(35), 84, tx(39) - tx(35), 184, fill=TINT_FOCUS, stroke=FOCUS,
           sw=1.6, dash="5 3")
    s.text(tx(37), 78, "人口をそろえた地域", size=10, fill=FOCUS,
           anchor="middle", weight="700")
    for p, a in zip(pops, ads):
        s.circle(tx(p), ty(a), 6, fill=TINT_MAIN, stroke=MAIN, sw=1.9)
    # 広告費は縦軸なので、その幅も縦方向へ比例させて描く。
    dim_x = tx(39) + 18
    dim_y1, dim_y2 = ty(max(in_band)), ty(min(in_band))
    s.line(dim_x, dim_y1, dim_x, dim_y2, stroke=FOCUS, sw=1.6)
    s.line(dim_x - 5, dim_y1, dim_x + 5, dim_y1, stroke=FOCUS, sw=1.4)
    s.line(dim_x - 5, dim_y2, dim_x + 5, dim_y2, stroke=FOCUS, sw=1.4)
    s.text(dim_x + 9, (dim_y1 + dim_y2) / 2 + 4,
           "幅 %.1f" % (max(in_band) - min(in_band)), size=10,
           fill=FOCUS, weight="700")
    s.text(tx(43), ty(8), "全体の幅 %.1f" % (max(ads) - min(ads)),
           size=10, fill=SUB)
    s.arrow(tx(52), ty(32), tx(41), ty(25), stroke=WARN, sw=2.0)
    s.text(tx(52) + 6, ty(32) - 2, "この向きの観測が無い", size=11, fill=WARN,
           weight="700")

    xaxis(s, 130, 660, 288, [10, 25, 40, 55, 70], tx,
          ["10", "25", "40", "55", "70"])
    s.text(395, 322, "人口（万人）", size=10, fill=SUB, anchor="middle")
    yaxis(s, 268, 84, 150, [0, 10, 20, 30, 40], ty,
          ["0", "10", "20", "30", "40"])
    s.text(150, 68, "広告費（百万円）", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 9-2
def fig9_2():
    """9-2 混同したまま人数を増やすか、同じ引き出しへ両方を入れるか。

    できる子の指摘（Aは午前・新品電池、Bは午後・再利用電池）を配置表にする。
    左は対角の二マスしか埋まらず、機種差と時間帯・電池差を分けられない。
    右は時間帯×電池の四マスすべてでA/Bを無作為割付する。

    グリッド（二パネルで座標を固定し、変えるのは各マスの中身だけ）
      左 表 x 150..368 / 右 x 470..688、行高 46、列幅 109
      行  午前（y 118..164）／ 午後（y 164..210）
      列  新品電池 ／ 再利用電池
      y  32 タイトル / 76 パネル名 / 100 列見出し / 232 結論
      色  青＝比較が成立するマス / 赤＝比較相手がいない空マス / 灰＝表の罫線
    """
    s = SVG(760, 268, "同じ引き出しの中にA/Bが両方あるかを、人数より先に見る")
    s.text(52, 32, "人数を増やしても、機種と時間帯が重なったままなら比較は生まれない",
           size=14, weight="700")

    def table(x0, title, cells, note, note_col):
        s.text(x0 - 8, 76, title, size=12, weight="700", fill=INK)
        s.text(x0 + 54, 100, "新品電池", size=11, fill=SUB, anchor="middle")
        s.text(x0 + 163, 100, "再利用電池", size=11, fill=SUB, anchor="middle")
        for i, row in enumerate(("午前", "午後")):
            s.text(x0 - 12, 147 + i * 46, row, size=11, fill=SUB, anchor="end")
            for j in range(2):
                cx, cy = x0 + j * 109, 118 + i * 46
                body = cells[i][j]
                filled = body != ""
                s.rect(cx, cy, 109, 46,
                       fill=TINT_MAIN if filled else TINT_WARN,
                       stroke=MAIN if filled else WARN,
                       sw=1.6, dash=None if filled else "5 3")
                if filled:
                    s.text(cx + 54, cy + 29, body, size=13,
                           fill=MAIN, anchor="middle", weight="700")
                else:
                    s.cross(cx + 54, cy + 23, 9, stroke=WARN, sw=2.2)
        s.text(x0 + 109, 232, note, size=12, anchor="middle",
               fill=note_col, weight="700")

    table(150, "できる子が見つけた配置",
          [["A のみ", ""], ["", "B のみ"]],
          "空きマスに比較相手がいない", WARN)
    table(470, "ブロック内で無作為割付",
          [["A と B", "A と B"], ["A と B", "A と B"]],
          "どのマスでも機種差を比べられる", MAIN)
    return s


# ---------------------------------------------------------------- 10-1
def fig10_1():
    """10-1 周辺が同じでも、同時の四箱は一つに決まらない。

    本文の店舗A（会員返品20・会員非返品30・非会員返品0・非会員非返品50）と
    店舗B（10・40・10・40）。行和も列和も同じで、中身だけが違う。

    グリッド（二表で座標を固定し、変えるのは四箱の中身だけ）
      表A 左上 (150,116) / 表B 左上 (470,116)、セル 96×52
      周辺の列 セルの右 x+192..x+250、周辺の行 y 220..252
      y  32 タイトル / 96 列見出し / 116..220 四箱 / 240 行和 / 268 列和
         292 条件付き返品率
      色  青＝同時分布の四箱 / 橙＝会員を知ったときの返品率 / 灰＝周辺（行和・列和）
    """
    a = [[20, 30], [0, 50]]
    b = [[10, 40], [10, 40]]
    for t in (a, b):
        assert [r[0] + r[1] for r in t] == [50, 50]
        assert [t[0][j] + t[1][j] for j in (0, 1)] == [20, 80]
    assert a[0][0] / 50 == 0.4 and a[1][0] / 50 == 0.0
    assert b[0][0] / 50 == 0.2 and b[1][0] / 50 == 0.2

    s = SVG(760, 320, "行和も列和も同じ二店舗が、まったく違う四箱を持つ")
    s.text(52, 32, "周辺を二枚そろえても、同時の四箱は一つに決まらない",
           size=14, weight="700")

    def table(x0, name, t, hi):
        s.text(x0, 74, name, size=13, weight="700", fill=INK)
        s.text(x0 + 48, 100, "返品", size=10, fill=SUB, anchor="middle")
        s.text(x0 + 144, 100, "返品なし", size=10, fill=SUB, anchor="middle")
        s.text(x0 + 220, 100, "行和", size=10, fill=SUB, anchor="middle")
        for i, rname in enumerate(("会員", "非会員")):
            s.text(x0 - 10, 148 + i * 52, rname, size=11, fill=SUB, anchor="end")
            for j in range(2):
                cx, cy = x0 + j * 96, 116 + i * 52
                mark = (i, j) == hi
                s.rect(cx, cy, 96, 52,
                       fill=TINT_FOCUS if mark else TINT_MAIN,
                       stroke=FOCUS if mark else MAIN, sw=2.0 if mark else 1.4)
                s.text(cx + 48, cy + 32, str(t[i][j]), size=15,
                       fill=FOCUS if mark else MAIN, anchor="middle",
                       weight="700")
            s.rect(x0 + 192, 116 + i * 52, 56, 52,
                   fill=TINT_MUTED, stroke=MUTED, sw=1.2)
            s.text(x0 + 220, 148 + i * 52, "50", size=13, fill=SUB,
                   anchor="middle")
        for j in range(2):
            s.rect(x0 + j * 96, 220, 96, 32, fill=TINT_MUTED, stroke=MUTED,
                   sw=1.2)
            s.text(x0 + j * 96 + 48, 241, str([20, 80][j]), size=13, fill=SUB,
                   anchor="middle")
        s.text(x0 + 220, 241, "列和", size=10, fill=SUB, anchor="middle")
        s.text(x0 + 96, 282,
               "会員の返品率 %d%% ／ 非会員 %d%%"
               % (round(t[0][0] / 50 * 100), round(t[1][0] / 50 * 100)),
               size=11, fill=FOCUS, anchor="middle", weight="700")

    table(150, "店舗A", a, (0, 0))
    table(470, "店舗B", b, (0, 0))
    s.text(380, 308, "灰のマスは二店舗で同じ。青と橙のマスだけが違う",
           size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 10-3
def fig10_3():
    """10-3 一マスが6倍へ伸びたら、密度は1/6へ薄める。

    本文の U=2X, V=3Y。元の単位正方形（面積1・密度1）が
    0<U<2, 0<V<3 の長方形（面積6）へ伸びる。密度を据え置くと総量が6になる。
    左半分の確率1/2も、密度1/6なら保たれる（面積3×1/6）。

    グリッド（1単位 = 70px）
      元  x 150..220 / y 250..180   （4×4 の方眼、一マス 17.5×17.5）
      先  x 420..560 / y 250..40    （同じ方眼、一マス 35×52.5）
      y  32 タイトル / 60 副題 / 268 面積の注記 / 292 密度の注記 / 312 結論
      色  青＝確率が保たれている領域（左半分） / 橙＝伸びた一マス / 赤＝密度を据え置いた誤り
    """
    jac = 2 * 3
    assert jac == 6
    assert abs(1.0 / jac * (2 * 3) - 1.0) < 1e-12          # 総量1
    assert abs(1.0 / jac * (1 * 3) - 0.5) < 1e-12          # 左半分も1/2

    s = SVG(760, 330, "座標を伸ばした分だけ密度を薄めないと、確率が6倍に増える")
    s.text(52, 32, "ゴム方眼の一マスが何倍になったかが、掛けるべき領収書",
           size=14, weight="700")
    s.text(52, 54, "U = 2X, V = 3Y", size=11, fill=SUB)

    def grid(x0, y0, w, h, name, note, tint_left):
        s.rect(x0, y0 - h, w, h, fill="#ffffff", stroke=INK, sw=1.8)
        s.rect(x0, y0 - h, w / 2.0, h, fill=TINT_MAIN, stroke="none", sw=0)
        for i in range(1, 4):
            s.line(x0 + w * i / 4.0, y0 - h, x0 + w * i / 4.0, y0,
                   stroke=MUTED, sw=0.9)
            s.line(x0, y0 - h * i / 4.0, x0 + w, y0 - h * i / 4.0,
                   stroke=MUTED, sw=0.9)
        s.rect(x0, y0 - h / 4.0, w / 4.0, h / 4.0,
               fill=TINT_FOCUS, stroke=FOCUS, sw=2.0)
        s.text(x0, y0 + 22, name, size=12, weight="700", fill=INK)
        s.text(x0, y0 + 40, note, size=10, fill=SUB)
        s.text(x0 + w / 4.0, y0 - h - 10, tint_left, size=10, fill=MAIN,
               anchor="middle", weight="700")

    grid(150, 258, 56, 56, "もとの正方形",
         "面積1・密度1・総量1", "左半分 1/2")
    grid(430, 258, 112, 168, "変換後の長方形",
         "面積6・密度1/6・総量1", "左半分 1/2")
    s.arrow(236, 226, 406, 226, stroke=INK, sw=2.0)
    s.text(321, 218, "横2倍・縦3倍", size=11, anchor="middle", weight="700")
    s.text(321, 244, "一マスの面積が6倍", size=11, fill=FOCUS,
           anchor="middle", weight="700")
    s.text(52, 322, "密度1のまま塗ると総量が 2×3×1 ＝ 6 になる（確率にならない）",
           size=11, fill=WARN, weight="700")
    return s


# ---------------------------------------------------------------- 11-2
def fig11_2():
    """11-2 台数を増やすと、最小値だけが早い側へ動く。

    本文の耐久試験（平均寿命1,000時間、各台が210時間以内に壊れる確率2%）。
    この二条件を満たすWeibull（形状 k、尺度 eta）を数値的に決めてから描く。
    最小値が210時間以内である確率は 1-0.98^n で、n=1/10/100 が 2%/18%/87%。

    グリッド
      tx(時間) = lin(140, 690, 0, 2500) / 密度は各曲線の最大値で正規化
      曲線の底辺 y 262、高さ 150（n ごとに同じ倍率で描く）
      y  32 タイトル / 56 副題 / 262 底辺 / 280 目盛り / 306 注記
      色  青＝一台の寿命 / 橙＝100台の最小値 / 灰＝10台の最小値 / 赤＝210時間の線
    """
    lo, hi = 1.0, 6.0
    for _ in range(200):
        k = (lo + hi) / 2
        eta = 210.0 / (0.020202707 ** (1.0 / k))
        mean = eta * math.gamma(1 + 1.0 / k)
        if mean > 1000.0:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    eta = 210.0 / (0.020202707 ** (1.0 / k))
    assert abs(eta * math.gamma(1 + 1.0 / k) - 1000.0) < 0.5
    assert abs((1 - math.exp(-(210.0 / eta) ** k)) - 0.02) < 1e-4
    probs = [1 - 0.98 ** n for n in (1, 10, 100)]
    assert abs(probs[0] - 0.02) < 1e-9
    assert abs(probs[2] - 0.8674) < 1e-3

    def cdf(t, n):
        return 1 - math.exp(-n * (t / eta) ** k)

    s = SVG(760, 330, "台数を増やすほど、最初の故障は早い側へ動く")
    tx = lin(150, 640, 0, 2000)
    ty = lin(268, 84, 0, 1)
    s.text(52, 32, "一位のタイムは、走者の速さだけでなく参加人数も背負う",
           size=14, weight="700")
    s.text(52, 54, "平均寿命1,000時間・210時間以内に壊れる確率2%の分布から",
           size=10, fill=SUB)

    for n, col in ((1, MAIN), (10, MUTED), (100, FOCUS)):
        pts = []
        t = 0.0
        while t <= 2000:
            pts.append((tx(t), ty(cdf(t, n))))
            t += 8
        polyline(s, pts, stroke=col, sw=2.4)
    s.line(tx(210), 76, tx(210), 278, stroke=WARN, sw=2.0, dash="6 4")
    s.text(tx(210) + 8, 72, "210時間（実際に出た最初の故障）", size=11,
           fill=WARN, weight="700")
    for n, col, lab, dy in ((1, MAIN, "1台なら 2%", 20),
                            (10, MUTED, "10台の最小値なら 18%", -8),
                            (100, FOCUS, "100台の最小値なら 87%", -8)):
        v = cdf(210, n)
        s.circle(tx(210), ty(v), 5.5, fill=col, stroke=col, sw=1.0)
        s.text(tx(210) + 12, ty(v) + dy, lab, size=12, fill=col, weight="700")

    xaxis(s, 140, 660, 268, [0, 500, 1000, 1500, 2000], tx,
          ["0", "500", "1,000", "1,500", "2,000"])
    s.text(395, 320, "故障までの時間（時間）", size=10, fill=SUB, anchor="middle")
    yaxis(s, 268, 84, 150, [0, 0.5, 1.0], ty, ["0", "50%", "100%"])
    s.text(60, 76, "その時間までに壊れている確率", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 12-1
def fig12_1():
    """12-1 分布のカメラが同じでも、一本の軌跡は別物になる。

    左は X_n = Z_n/sqrt(n)（0へ確率収束し、山も0へ潰れる）。
    右は Z_n がいつも標準正規（山は変わらないが、一本の軌跡は落ち着かない）。
    乱数は seed 11 の線形合同法から決定的に作る。

    グリッド（左右で座標を固定し、変えるのは列の作り方だけ）
      軌跡  x 120..370（右は +320）、n = 1..60、y 190（0）を中心に ±86
      分布  同じパネル幅、底辺 y 306、高さ 76、横軸は軌跡と同じ値域 -3.2..3.2
      y  32 タイトル / 74 パネル名 / 190 0 の線 / 226 分布ラベル / 320 目盛り
      色  青＝観測した一本の軌跡 / 橙＝n=60 での分布 / 灰＝0 の基準線
    """
    r = lcg(11)
    zs = []
    while len(zs) < 120:
        z1, z2 = std_normal_pair(r(), r())
        zs += [z1, z2]
    shrink = [zs[i] / math.sqrt(i + 1) for i in range(60)]
    stay = zs[60:120]
    assert abs(shrink[59]) < 0.5          # 終盤は0の近くへ縮む
    assert max(abs(v) for v in stay[40:]) > 0.8   # 終盤も同じ幅で暴れる

    s = SVG(760, 348, "山が0へ潰れる収束と、山が変わらない収束を分ける")
    s.text(52, 32, "「近づく」の主語を、一本の軌跡と分布の山へ分ける",
           size=14, weight="700")

    def panel(x0, series, sd, title, note, note_col):
        tx = lin(x0, x0 + 250, 1, 60)

        def yv(v):
            return round(145 - v / 3.2 * 55, 2)
        s.text(x0 - 12, 74, title, size=12, weight="700", fill=INK)
        s.line(x0 - 8, 145, x0 + 258, 145, stroke=MUTED, sw=1.4)
        s.text(x0 - 14, 149, "0", size=10, fill=SUB, anchor="end")
        polyline(s, [(tx(i + 1), yv(v)) for i, v in enumerate(series)],
                 stroke=MAIN, sw=1.6)
        s.text(x0 + 262, 149, "n=60", size=9, fill=SUB)
        # n=60 での分布
        base, hgt = 302, 82
        peak = normal_pdf(0, 0, sd)
        pts = []
        v = -3.2
        while v <= 3.201:
            pts.append((tx(1) + (v + 3.2) / 6.4 * 250,
                        base - hgt * normal_pdf(v, 0, sd) / peak))
            v += 0.02
        polyline(s, pts, stroke=FOCUS, sw=2.2)
        s.line(x0, base, x0 + 250, base, stroke=SUB, sw=1.2, cap="butt")
        s.text(x0 - 12, 236, "n=60 での分布", size=11, fill=FOCUS, weight="700")
        s.text(x0 - 12, 336, note, size=11, fill=note_col, weight="700")

    panel(120, shrink, 1 / math.sqrt(60),
          "① 各回の値を sqrt(n) で割る",
          "軌跡も山も 0 へ寄る（確率収束）", MAIN)
    panel(440, stay, 1.0,
          "② 毎回あらためて引き直す",
          "山は同じでも軌跡は落ち着かない", WARN)
    return s


# ---------------------------------------------------------------- 12-3
def fig12_3():
    """12-3 同じ0.01の揺れが、坂の急さで別の幅になる。

    本文の値。p=0.50→0.51 でオッズは 1.000→1.041（+0.041）、
    p=0.90→0.91 では 9.000→10.111（+1.111）。接線の傾き 1/(1-p)^2 は 4 と 100。

    橙の箱は本文どおり入力幅0.01で、縦幅は接線近似の 0.01*g'(p)。

    グリッド
      tx(p) = lin(140, 660, 0.30, 0.92) / ty(odds) = lin(272, 76, 0, 12)
      注目点  p=0.50 → (313.4, 252.7) / p=0.90 → (648.6, 125.0)
      y  32 タイトル / 56 副題 / 272 底辺 / 290 目盛り / 314 軸ラベル
      色  青＝オッズ曲線 / 橙＝入力の揺れ0.01と、その出力幅 / 灰＝目盛り
    """
    def odds(p):
        return p / (1 - p)
    d1 = odds(0.51) - odds(0.50)
    d2 = odds(0.91) - odds(0.90)
    assert abs(d1 - 0.040816) < 1e-6
    assert abs(d2 - 1.111111) < 1e-6
    assert abs(1 / (1 - 0.5) ** 2 - 4.0) < 1e-12
    assert abs(1 / (1 - 0.9) ** 2 - 100.0) < 1e-9

    s = SVG(760, 330, "同じ入力の揺れでも、曲線の急な場所では出力が大きく伸びる")
    tx = lin(140, 660, 0.30, 0.92)
    ty = lin(272, 76, 0, 12)
    s.text(52, 32, "揺れの大きさは、入力の揺れ × 足元の傾きで決まる",
           size=14, weight="700")
    s.text(52, 54, "オッズ p /（1 − p）", size=11, fill=SUB)

    pts = []
    v = 0.30
    while v <= 0.9201:
        pts.append((tx(v), ty(odds(v))))
        v += 0.002
    polyline(s, pts, stroke=MAIN, sw=2.4)

    for p, dd, slope, lab_dy in ((0.50, d1, 4, 34), (0.90, d2, 100, -60)):
        x1, x2 = tx(p), tx(p + 0.01)
        y1, y2 = ty(odds(p)), ty(odds(p) + 0.01 * slope)
        s.rect(x1, min(y1, y2), x2 - x1, abs(y2 - y1),
               fill=TINT_FOCUS, stroke=FOCUS, sw=1.8)
        s.circle(x1, y1, 5.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
        s.text(x1 + 10, y1 + lab_dy,
               "p = %.2f　傾き %d 倍" % (p, slope), size=11, fill=FOCUS,
               weight="700")
        s.text(x1 + 10, y1 + lab_dy + 16,
               "0.01 の揺れ → オッズ %+.3f" % dd, size=10, fill=SUB)

    xaxis(s, 130, 670, 272, [0.3, 0.5, 0.7, 0.9], tx,
          ["0.30", "0.50", "0.70", "0.90"])
    s.text(400, 314, "推定した割合 p", size=10, fill=SUB, anchor="middle")
    yaxis(s, 272, 76, 140, [0, 4, 8, 12], ty, ["0", "4", "8", "12"])
    s.text(112, 68, "オッズ", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 13-2
def fig13_2():
    """13-2 尤度の最大は、滑らかな山頂ではなく崖の縁に来る。

    本文の一様(0, θ) と観測 2, 4, 6。θ<6 では尤度0、θ>=6 では θ^-3。
    最大は境界の θ=6。モーメント法の答え 8 は同じ図の別の場所にある。

    グリッド
      tx(θ) = lin(150, 680, 3.5, 14) / 尤度は最大値で正規化して 高さ160
      y  32 タイトル / 56 副題 / 262 底辺 / 280 目盛り / 306 軸ラベル
      色  橙＝最尤の崖（θ=6） / 青＝尤度曲線 / 赤＝観測を出せない範囲（θ<6）
    """
    obs = [2, 4, 6]
    m = max(obs)
    mom = 2 * (sum(obs) / len(obs))
    assert m == 6 and mom == 8

    def lik(th):
        return 0.0 if th < m else th ** (-len(obs))

    s = SVG(760, 330, "一様分布の尤度は境界で最大になり、微分0では拾えない")
    tx = lin(150, 680, 1.5, 14)
    s.text(52, 32, "観測 2・4・6 を全部収める、いちばん狭い箱が最尤",
           size=14, weight="700")
    s.text(52, 54, "尤度 L(θ) は θ < 6 で 0、θ ≧ 6 で θ の3乗に反比例",
           size=10, fill=SUB)

    peak = lik(m)
    s.line(tx(1.5), 262, tx(m), 262, stroke=WARN, sw=3.4)
    s.text(tx(m) - 12, 240, "この範囲の箱からは 6 が出ない（尤度 0）", size=11,
           fill=WARN, weight="700", anchor="end")
    pts = []
    th = m
    while th <= 14.001:
        pts.append((tx(th), 262 - 160 * lik(th) / peak))
        th += 0.02
    s.line(tx(m), 262, tx(m), 102, stroke=MAIN, sw=2.4)
    polyline(s, pts, stroke=MAIN, sw=2.4)
    s.circle(tx(m), 102, 6.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(tx(m) + 12, 96, "最尤推定 θ = 6（崖の縁）", size=12, fill=FOCUS,
           weight="700")
    s.text(tx(m) + 12, 114, "微分 0 の内点を探すソフトは、ここを見落とす",
           size=10, fill=SUB)

    s.line(tx(mom), 262 - 160 * lik(mom) / peak, tx(mom), 262,
           stroke=MUTED, sw=1.8, dash="5 3")
    s.circle(tx(mom), 262 - 160 * lik(mom) / peak, 5.5,
             fill="#ffffff", stroke=MUTED, sw=2.0)
    s.text(tx(mom) + 10, 262 - 160 * lik(mom) / peak - 8,
           "モーメント法 θ = 8", size=11, fill=SUB, weight="700")

    for v in obs:
        tri_up(s, tx(v), 278, 5.5, fill=INK)
    s.text(tx(2), 302, "観測 2", size=10, fill=SUB, anchor="middle")
    s.text(tx(4), 302, "4", size=10, fill=SUB, anchor="middle")
    s.text(tx(6), 302, "6", size=10, fill=SUB, anchor="middle")
    s.line(140, 262, 692, 262, stroke=SUB, sw=1.2, cap="butt")
    for v in (2, 4, 6, 8, 10, 12, 14):
        s.line(tx(v), 262, tx(v), 267, stroke=SUB, sw=1.2)
    s.text(700, 266, "θ", size=12, fill=SUB, style="italic")
    s.text(395, 324, "未知の上限 θ の候補", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 15-2
def fig15_2():
    """15-2 誤報予算を守るには、二仮説を強く見分ける入口から配る。

    本文の設定。二人中の購入者数について H0:p=0.1、H1:p=0.6。
    尤度比は 0人 0.20 / 1人 2.67 / 2人 36。1人・2人を棄却域にすると
    誤報19%・検出力84%。0人・2人という左右対称形は誤報82%で、同じ予算ではない。

    グリッド
      三つの結果を x 中心 210 / 400 / 590 に置く。柱の幅 42、対で並べる
      柱の底辺 y 246、高さ = 確率 × 150
      y  32 タイトル / 58 副題 / 88 尤度比 / 246 底辺 / 266 結果ラベル
         292 棄却域の帯 / 316 まとめ
      色  灰＝H0（正常）で出る確率 / 青＝H1（売れる）で出る確率 / 橙＝尤度比
          赤＝左右対称にした棄却域（予算超過）
    """
    p0, p1 = 0.1, 0.6
    h0 = [binom_pmf(k, 2, p0) for k in range(3)]
    h1 = [binom_pmf(k, 2, p1) for k in range(3)]
    lr = [h1[k] / h0[k] for k in range(3)]
    assert abs(lr[0] - 0.19753) < 1e-4
    assert abs(lr[1] - 2.66667) < 1e-4
    assert abs(lr[2] - 36.0) < 1e-9
    good = h0[2] + h0[1]
    bad = h0[2] + h0[0]
    assert abs(good - 0.19) < 1e-9 and abs(bad - 0.82) < 1e-9

    s = SVG(760, 368, "尤度比順なら誤報19%、左右対称形は誤報82%で予算を超える")
    s.text(52, 32, "「珍しい順」ではなく「二つの世界を見分ける倍率順」に配る",
           size=14, weight="700")
    s.text(52, 56, "灰＝基準 p=0.1 の世界　／　青＝p=0.6 の世界（二人中の購入者数）",
           size=10, fill=SUB)

    centers = (210, 400, 590)
    for k, cx in enumerate(centers):
        s.text(cx, 88, "尤度比 %.2f" % lr[k], size=12, fill=FOCUS,
               anchor="middle", weight="700")
        for j, (v, col, tint) in enumerate(((h0[k], MUTED, TINT_MUTED),
                                            (h1[k], MAIN, TINT_MAIN))):
            bx = cx - 44 + j * 46
            s.rect(bx, 246 - 150 * v, 42, 150 * v, fill=tint, stroke=col,
                   sw=1.6)
            s.text(bx + 21, 246 - 150 * v - 7, "%.2f" % v, size=10, fill=col,
                   anchor="middle")
        s.text(cx, 268, "%d人が購入" % k, size=11, anchor="middle", fill=INK)
    s.line(150, 246, 660, 246, stroke=SUB, sw=1.2, cap="butt")

    s.text(52, 308, "尤度比順に配る", size=11, fill=MAIN, weight="700")
    s.rect(centers[1] - 52, 294, 210, 22, fill=TINT_MAIN, stroke=MAIN, sw=1.6)
    s.text(centers[1] + 53, 309, "誤報 19% ／ 検出力 84%", size=11, fill=MAIN,
           anchor="middle", weight="700")
    s.text(52, 356, "左右対称に配る", size=11, fill=WARN, weight="700")
    s.rect(centers[0] - 52, 342, 104, 22, fill=TINT_WARN, stroke=WARN,
           sw=1.6, dash="5 3")
    s.rect(centers[2] - 52, 342, 104, 22, fill=TINT_WARN, stroke=WARN,
           sw=1.6, dash="5 3")
    s.text(centers[1], 357, "誤報 82%（予算を大きく超える）", size=11,
           fill=WARN, anchor="middle", weight="700")
    return s


# ---------------------------------------------------------------- 15-3
def fig15_3():
    """15-3 同じ尤度の山を、高さ・距離・傾きの三方向から測る。

    二項 n=20・購入13人、帰無仮説 p=0.5 の対数尤度で三統計量を計算する。
    尤度比 2*(logL(0.65)-logL(0.5))=1.83、Wald 1.98、score 1.80。

    グリッド
      tx(p) = lin(150, 680, 0.30, 0.92) / 対数尤度は最大値からの差で 高さ200
      旗 p=0.5 → 268.6 / 星 p=0.65 → 397.0
      y  32 タイトル / 56 副題 / 262 底辺 / 284 目盛り / 312 三つの数値
      色  青＝対数尤度の山 / 橙＝帰無仮説の点（旗）と傾き / 灰＝頂上（星）
    """
    n, x0_, p_null = 20, 13, 0.5
    phat = x0_ / n

    def ll(p):
        return x0_ * math.log(p) + (n - x0_) * math.log(1 - p)

    lr = 2 * (ll(phat) - ll(p_null))
    score_stat = (x0_ / p_null - (n - x0_) / (1 - p_null)) ** 2 / (n / (p_null * (1 - p_null)))
    wald = (phat - p_null) ** 2 / (phat * (1 - phat) / n)
    assert abs(phat - 0.65) < 1e-12
    assert abs(lr - 1.8280) < 1e-3
    assert abs(score_stat - 1.8) < 1e-9
    assert abs(wald - 1.9780) < 1e-3

    s = SVG(760, 340, "同じ尤度の山を、高さ・距離・出発点の傾きで測る三方式")
    tx = lin(150, 680, 0.38, 0.88)
    s.text(52, 32, "三つの検定は別の道具ではなく、一つの山の測り方が違う",
           size=14, weight="700")
    s.text(52, 54, "20人中13人が購入、帰無仮説は p = 0.5", size=10, fill=SUB)

    sc = 45.0

    def ly(p):
        return round(96 + (ll(phat) - ll(p)) * sc, 2)
    pts = []
    v = 0.38
    while v <= 0.8801:
        pts.append((tx(v), ly(v)))
        v += 0.002
    polyline(s, pts, stroke=MAIN, sw=2.4)
    s.line(150, 262, 690, 262, stroke=SUB, sw=1.2, cap="butt")

    # 頂上（灰）と帰無点（橙の旗）
    s.line(tx(phat), ly(phat), tx(phat), 262, stroke=MUTED, sw=1.4, dash="5 3")
    s.circle(tx(phat), ly(phat), 6.5, fill=MUTED, stroke=MUTED, sw=1.0)
    s.text(tx(phat) + 12, ly(phat) - 4, "頂上 p = 0.65", size=11, fill=SUB,
           weight="700")
    s.line(tx(p_null), ly(p_null), tx(p_null), 262, stroke=FOCUS, sw=2.0)
    s.circle(tx(p_null), ly(p_null), 6.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(tx(p_null) + 12, ly(p_null) + 34, "帰無 p = 0.5", size=11,
           fill=FOCUS, weight="700")

    # 高さの差／頂上までの距離／旗での傾き
    s.line(tx(p_null) - 46, ly(phat), tx(p_null) - 46, ly(p_null),
           stroke=INK, sw=2.0)
    s.text(tx(p_null) - 54, (ly(phat) + ly(p_null)) / 2 + 4, "高さの差",
           size=11, anchor="end", weight="700")
    s.dim(tx(p_null), tx(phat), 246, "頂上までの距離", up=True)
    slope = (x0_ / p_null - (n - x0_) / (1 - p_null))
    dx = 0.055
    s.line(tx(p_null - dx), ly(p_null) + slope * dx * sc,
           tx(p_null + dx), ly(p_null) - slope * dx * sc,
           stroke=FOCUS, sw=2.6)
    s.text(tx(p_null + dx) + 8, ly(p_null) - slope * dx * sc - 4,
           "旗での傾き", size=11, fill=FOCUS, weight="700")

    xaxis(s, 140, 690, 262, [0.4, 0.5, 0.65, 0.8], tx,
          ["0.40", "0.50", "0.65", "0.80"])
    s.text(415, 302, "購入率 p の候補", size=10, fill=SUB, anchor="middle")
    s.text(415, 328,
           "尤度比 %.2f　／　Wald %.2f　／　score %.2f　（大標本では近づく）"
           % (lr, wald, score_stat),
           size=12, anchor="middle", weight="700", fill=INK)
    return s


# ---------------------------------------------------------------- 16-4
def fig16_4():
    """16-4 罰則は係数を一意にしても、識別不能な比較を観測済みにはしない。

    総広告費が常にテレビ広告費の2倍（X2 = 2X1）なら、予測は b1 + 2b2 だけで決まる。
    b1 + 2b2 = 2 を満たす係数の組はすべて同じ無罰則予測を返す（尾根）。
    目的関数を (b1+2b2-2)^2 + lambda*penalty、lambda=1 とすると、
    ridge は (1/3, 2/3)、lasso は (0, 7/8) を選ぶ。どちらも縮小により
    無罰則の尾根から原点側へ動くが、データが見分けられる方向は増えていない。

    グリッド
      bx(b1) = lin(150, 620, -0.6, 2.6) / by(b2) = lin(276, 76, -0.3, 1.3)
      尾根の直線  b1 = 2 - 2*b2
      y  32 タイトル / 56 副題 / 300 軸ラベル / 322 結論
      色  赤＝無罰則で同じ予測を返す尾根（識別不能） / 青＝ridgeの選ぶ点
          橙＝lassoの選ぶ点 / 灰＝罰則の等高線
    """
    c = 2.0
    lam = 1.0
    ridge = (c / (5.0 + lam), 2 * c / (5.0 + lam))
    lasso = (0.0, (4 * c - lam) / 8.0)
    assert abs(ridge[0] - 1.0 / 3.0) < 1e-12
    assert abs(ridge[1] - 2.0 / 3.0) < 1e-12
    assert abs(lasso[1] - 7.0 / 8.0) < 1e-12
    assert ridge[0] + 2 * ridge[1] < c
    assert lasso[0] + 2 * lasso[1] < c

    s = SVG(760, 358, "罰則で解が一意になっても、未観測の比較が識別されたわけではない")
    # 縦横で1単位の長さをそろえる（等高線の接し方が意味を持つため）
    bx = lin(240, 700, -0.3, 2.6)
    by = lin(300, 80, -0.3, 1.087)
    s.text(52, 32, "一意な答えが出たことと、データが答えを見分けたことは別",
           size=14, weight="700")
    s.text(52, 54, "総広告費がテレビ広告費のちょうど2倍なら、予測は b1 + 2b2 だけで決まる",
           size=10, fill=SUB)

    # 罰則の等高線（見えている範囲だけ描く）
    r = math.sqrt(ridge[0] ** 2 + ridge[1] ** 2)
    arc = []
    a = 0.0
    while a <= math.pi / 2 + 1e-9:
        arc.append((bx(r * math.cos(a)), by(r * math.sin(a))))
        a += math.pi / 120
    polyline(s, arc, stroke=MUTED, sw=1.4, dash="5 3")
    l1 = abs(lasso[0]) + abs(lasso[1])
    s.line(bx(l1), by(0.0), bx(0.0), by(l1), stroke=MUTED, sw=1.4, dash="4 3")
    s.text(bx(0.72), by(0.50), "ridge の輪", size=10, fill=SUB)
    s.text(bx(0.36), by(0.26), "lasso の輪", size=10, fill=SUB)

    # 尾根
    s.line(bx(-0.3), by((c + 0.3) / 2), bx(2.6), by((c - 2.6) / 2),
           stroke=WARN, sw=3.0)
    s.text(bx(1.35), by(0.42), "無罰則の尾根  b1 + 2b2 = 2", size=12, fill=WARN,
           weight="700")
    s.text(bx(1.35), by(0.30), "この線上はどれも同じ当てはまり", size=11,
           fill=WARN, weight="700")

    s.circle(bx(ridge[0]), by(ridge[1]), 7, fill=MAIN, stroke=MAIN, sw=1.0)
    s.text(bx(ridge[0]) + 14, by(ridge[1]) + 4, "ridge lambda=1  (0.33, 0.67)",
           size=11, fill=MAIN, weight="700")
    s.circle(bx(lasso[0]), by(lasso[1]), 7, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(bx(lasso[0]) + 14, by(lasso[1]) - 14, "lasso lambda=1  (0, 0.875)",
           size=11, fill=FOCUS, weight="700")
    s.circle(bx(2.0), by(0.0), 5, fill="#ffffff", stroke=WARN, sw=1.8)
    s.text(bx(2.0) + 14, by(0.0) - 12, "(2, 0) も同じ予測", size=10, fill=WARN)

    xaxis(s, 230, 712, by(0), [0, 1, 2], bx, ["0", "1", "2"])
    s.text(716, by(0) + 4, "b1", size=11, fill=SUB)
    yaxis(s, 300, 80, bx(0), [0, 1], by, ["0", "1"])
    s.text(bx(0), 72, "b2", size=11, fill=SUB, anchor="middle")
    s.text(52, 340,
           "lambda=1 の一例。解が一意でも、片方だけ動かす観測は増えていない",
           size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 17-1
def fig17_1():
    """17-1 直線は控室に置き、応答の部屋に合う扉を通す。

    左は件数の部屋。恒等リンクの直線は広告費0で −3件を返し、
    log リンクなら同じ増え方でも正の範囲に留まる。
    右は確率の部屋。恒等リンクは1を越え、logit リンクは0と1の間に収まる。

    グリッド（二パネルで縦軸の意味だけが変わる）
      左 tx = lin(96, 356, 0, 9) / ly = lin(250, 90, -5, 20)
      右 tx = lin(456, 716, 0, 12) / ry = lin(250, 90, -0.1, 1.3)
      y  32 タイトル / 56 副題 / 74 パネル名 / 250 底辺 / 268 目盛り / 300 結論
      色  赤＝範囲を飛び出す直線 / 青＝範囲を守る扉つきの曲線 / 灰＝範囲の外
    """
    lin_a, lin_b = -3.0, 2.5
    assert lin_a == -3.0
    log_d = (math.log(17.0) - math.log(2.0)) / 6.0
    log_c = math.log(2.0) - 2 * log_d
    assert abs(math.exp(log_c) - 0.98) < 0.02          # 広告費0でも正

    s = SVG(760, 322, "応答の取り得る範囲に合う扉を、直線と平均の間へ挟む")
    s.text(52, 32, "直線を捨てるのではなく、平均の出口を範囲へ戻す",
           size=14, weight="700")
    s.text(52, 54, "赤＝恒等リンク（範囲を飛び出す）　／　青＝log・logit の扉",
           size=10, fill=SUB)

    # 左：件数の部屋
    tx = lin(96, 356, 0, 9)
    ly = lin(250, 90, -5, 20)
    s.text(72, 74, "件数の平均（0以上）", size=12, weight="700", fill=INK)
    s.rect(96, ly(0), 260, 250 - ly(0), fill=TINT_MUTED, stroke="none", sw=0)
    s.text(350, ly(-2.4), "件数にならない範囲", size=10, fill=SUB, anchor="end")
    polyline(s, [(tx(v), ly(lin_a + lin_b * v)) for v in (0, 9)],
             stroke=WARN, sw=2.4)
    pts = []
    v = 0.0
    while v <= 9.001:
        mu_v = math.exp(log_c + log_d * v)
        if mu_v <= 20.0:
            pts.append((tx(v), ly(mu_v)))
        v += 0.05
    polyline(s, pts, stroke=MAIN, sw=2.4)
    s.circle(tx(0), ly(lin_a), 5.5, fill=WARN, stroke=WARN, sw=1.0)
    s.text(tx(0) + 12, ly(lin_a) + 24, "広告費0で −3件", size=11, fill=WARN,
           weight="700")
    yaxis(s, 250, 90, 96, [-5, 0, 10, 20], ly, ["−5", "0", "10", "20"])
    s.line(96, ly(0), 356, ly(0), stroke=SUB, sw=1.2, cap="butt")
    xaxis(s, 88, 366, 250, [0, 3, 6, 9], tx, ["0", "3", "6", "9"])
    s.text(226, 292, "広告費", size=10, fill=SUB, anchor="middle")

    # 右：確率の部屋
    tx2 = lin(456, 716, 0, 12)
    ry = lin(250, 90, -0.1, 1.3)
    s.text(432, 74, "確率の部屋（0から1）", size=12, weight="700", fill=INK)
    s.rect(456, 90, 260, ry(1.0) - 90, fill=TINT_MUTED, stroke="none", sw=0)
    s.rect(456, ry(0.0), 260, 250 - ry(0.0), fill=TINT_MUTED, stroke="none", sw=0)
    s.text(462, ry(1.16), "確率にならない範囲", size=10, fill=SUB)
    polyline(s, [(tx2(v), ry(0.10 + 0.10 * v)) for v in (0, 12)],
             stroke=WARN, sw=2.4)
    pts = []
    v = 0.0
    while v <= 12.001:
        pts.append((tx2(v), ry(1.0 / (1 + math.exp(-(-2.2 + 0.55 * v))))))
        v += 0.05
    polyline(s, pts, stroke=MAIN, sw=2.4)
    s.circle(tx2(11), ry(1.20), 5.5, fill=WARN, stroke=WARN, sw=1.0)
    s.text(tx2(11) - 10, ry(1.20) - 8, "予測 120%", size=11, fill=WARN,
           weight="700", anchor="end")
    yaxis(s, 250, 90, 456, [0, 0.5, 1.0], ry, ["0", "50%", "100%"])
    s.line(456, ry(0), 716, ry(0), stroke=SUB, sw=1.2, cap="butt")
    s.line(456, ry(1), 716, ry(1), stroke=SUB, sw=1.2, cap="butt")
    xaxis(s, 448, 726, 250, [0, 4, 8, 12], tx2, ["0", "4", "8", "12"])
    s.text(586, 292, "広告費", size=10, fill=SUB, anchor="middle")

    s.text(380, 314, "応答の部屋 → 確率の間取り → リンクの扉、の順で組む",
           size=11, anchor="middle", weight="700", fill=INK)
    return s


# ---------------------------------------------------------------- 17-3
def fig17_3():
    """17-3 平均が同じでも、混雑の幅が違えば人員配置は変わる。

    本文の「平均10件・分散50」。Poisson は平均＝分散なので分散10しか作れない。
    分散50を許す負の二項（r = mu^2/(var-mu) = 2.5）と並べ、95%上側点を比べる。

    グリッド
      kx(件数) = lin(150, 690, 0, 32) / 確率は Poisson の最大値で正規化して 高さ160
      y  32 タイトル / 56 副題 / 254 底辺 / 272 目盛り / 300 上側点の注記
      色  灰＝平均も分散も10のPoisson / 青＝平均10・分散50の分布 / 橙＝95%上側点
    """
    mu, var = 10.0, 50.0
    r = mu ** 2 / (var - mu)
    assert abs(r - 2.5) < 1e-12
    pp = r / (r + mu)

    def nb(k):
        lg = (math.lgamma(k + r) - math.lgamma(k + 1) - math.lgamma(r)
              + r * math.log(pp) + k * math.log(1 - pp))
        return math.exp(lg)
    assert abs(sum(nb(k) for k in range(0, 400)) - 1.0) < 1e-6
    assert abs(sum(k * nb(k) for k in range(0, 900)) - mu) < 1e-2

    def upper95(f):
        acc = 0.0
        for k in range(0, 400):
            acc += f(k)
            if acc >= 0.95:
                return k
        return 400
    up_p = upper95(lambda k: poisson_pmf(k, mu))
    up_n = upper95(nb)
    assert up_p == 15 and up_n == 24

    s = SVG(760, 330, "平均が同じでも、分散が広がれば必要な人員は変わる")
    kx = lin(150, 690, 0, 32)
    s.text(52, 32, "平均10件だけ合っていても、日ごとの山の幅は決まらない",
           size=14, weight="700")
    s.text(52, 54, "灰＝Poisson（平均＝分散＝10）　／　青＝平均10・分散50",
           size=10, fill=SUB)

    peak = poisson_pmf(int(mu), mu)
    for k in range(33):
        w = 12
        s.rect(kx(k) - w, 254 - 160 * poisson_pmf(k, mu) / peak, w,
               160 * poisson_pmf(k, mu) / peak,
               fill=TINT_MUTED, stroke=MUTED, sw=1.0)
        s.rect(kx(k), 254 - 160 * nb(k) / peak, w, 160 * nb(k) / peak,
               fill=TINT_MAIN, stroke=MAIN, sw=1.0)
    s.line(150, 254, 700, 254, stroke=SUB, sw=1.2, cap="butt")

    for val, col, lab, dy in (
            (up_p, MUTED, "Poissonの95%%上側 %d件" % up_p, 36),
            (up_n, FOCUS, "分散50なら95%%上側 %d件" % up_n, 12)):
        s.line(kx(val), 96, kx(val), 262, stroke=col, sw=2.0, dash="6 4")
        s.text(kx(val) + 8, 96 + dy, lab, size=11, fill=col, weight="700")

    xaxis(s, 140, 700, 254, [0, 5, 10, 15, 20, 25, 30], kx,
          ["0", "5", "10", "15", "20", "25", "30"])
    s.text(420, 296, "一日の問い合わせ件数", size=10, fill=SUB, anchor="middle")
    s.text(52, 320, "平均だけ合わせて上側を読むと、必要な人員を小さく見積もる",
           size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 19-1
def fig19_1():
    """19-1 点は動いていないのに、単位を替えると第一軸が倒れる。

    顧客8人の（価格, 満足度）＝(1,2)(2,1)(2,3)(3,2)(3,4)(4,3)(4,5)(5,4)。
    1,000円単位なら共分散行列は [[1.5,1.0],[1.0,1.5]] で第一軸は45度。
    価格を円単位（1,000倍）にすると第一軸は価格方向へ倒れ、角度はほぼ0度。

    グリッド
      tx(価格) = lin(180, 560, 0.4, 5.6) / ty(満足度) = lin(276, 84, 0.4, 5.6)
      （縦横で1目盛りの長さを同じにした等方の図）
      y  32 タイトル / 56 副題 / 296 目盛り / 320 結論
      色  青＝千円単位での第一軸（45度） / 赤＝円単位での第一軸（ほぼ水平）
          灰＝観測した顧客
    """
    pts = [(1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 3), (4, 5), (5, 4)]
    n = len(pts)
    mx = sum(p for p, _ in pts) / n
    my = sum(q for _, q in pts) / n
    vxx = sum((p - mx) ** 2 for p, _ in pts) / n
    vyy = sum((q - my) ** 2 for _, q in pts) / n
    vxy = sum((p - mx) * (q - my) for p, q in pts) / n
    assert abs(vxx - 1.5) < 1e-12 and abs(vyy - 1.5) < 1e-12
    assert abs(vxy - 1.0) < 1e-12
    ang_k = math.degrees(math.atan2(1.0, 1.0))
    # 価格を1,000倍すると共分散は1,000倍、価格の分散は百万倍。
    ang_y = 0.5 * math.degrees(math.atan2(2 * 1000 * vxy,
                                          vxx * 1e6 - vyy))
    assert abs(ang_k - 45.0) < 1e-9
    assert ang_y < 0.04

    s = SVG(760, 342, "同じ点群でも、単位を替えると第一主成分の向きが変わる")
    tx = lin(180, 560, 0.4, 5.6)
    ty = lin(276, 84, 0.4, 5.6)
    s.text(52, 32, "分散最大の向きは、顧客の中身ではなく目盛りの大きさにも引かれる",
           size=14, weight="700")
    s.text(52, 54, "縦横で1目盛りの長さをそろえた図（主成分はこの空間で決まる）",
           size=10, fill=SUB)

    s.rect(170, 78, 400, 204, fill="#ffffff", stroke=MUTED, sw=1.0)
    for p, q in pts:
        s.circle(tx(p), ty(q), 6.5, fill=TINT_MUTED, stroke=MUTED, sw=1.8)
    cx, cy = tx(mx), ty(my)
    s.circle(cx, cy, 4, fill=INK, stroke=INK, sw=1.0)
    s.arrow(cx, cy, tx(mx + 1.8), ty(my + 1.8), stroke=MAIN, sw=2.8)
    s.arrow(cx, cy, tx(mx - 1.8), ty(my - 1.8), stroke=MAIN, sw=2.8)
    s.arrow(cx, cy, tx(mx + 2.2), cy, stroke=WARN, sw=2.8)
    s.arrow(cx, cy, tx(mx - 2.2), cy, stroke=WARN, sw=2.8)
    s.text(tx(mx + 1.9), ty(my + 1.9) - 10, "1,000円単位の第一軸（45度）",
           size=11, fill=MAIN, weight="700")
    s.text(tx(mx + 2.3) + 4, cy + 20, "円単位の第一軸", size=11, fill=WARN,
           weight="700")
    s.text(tx(mx + 2.3) + 4, cy + 36, "（ほぼ0度）", size=11, fill=WARN,
           weight="700")

    xaxis(s, 170, 578, 282, [1, 2, 3, 4, 5], tx, ["1", "2", "3", "4", "5"])
    s.text(375, 314, "希望価格（1,000円）", size=10, fill=SUB, anchor="middle")
    yaxis(s, 276, 84, 170, [1, 3, 5], ty, ["1", "3", "5"])
    s.text(132, 74, "満足度", size=10, fill=SUB)
    s.text(52, 336,
           "価格を1,000倍すると分散は百万倍。相関行列を使うか、"
           "単位の意味を残すかは問いで決める", size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 20-1
def fig20_1():
    """20-1 全体10%という集合写真が、二つの扉を隠している。

    本文の夜間監視。全100時間のうち障害は10時間で全体10%だが、
    正常の次の一時間が障害になるのは5%、障害の次は55%。
    障害が2時間続く構造を、時系列の帯として示す。

    グリッド
      帯 x 150..690 を40コマ（1コマ 13.5px）、y 96..126
      柱 三本 中心 x 240 / 420 / 600、底辺 y 288、高さ = 率 × 150
      y  32 タイトル / 56 副題 / 88 帯ラベル / 140 注記 / 288 底辺 / 308 柱ラベル
      色  赤＝障害の時間 / 灰＝全体をならした率 / 橙＝いまいる部屋から出る率
    """
    overall, from_ok, from_ng = 0.10, 0.05, 0.55
    strip = [0] * 40
    for start in (9, 26):
        strip[start] = strip[start + 1] = 1
    assert sum(strip) / len(strip) == 0.10

    s = SVG(760, 340, "全体の障害率10%が、正常の次と障害の次という二つの扉を隠す")
    s.text(52, 32, "必要な過去を「現在」という部屋へ畳んでから、出る扉の率を見る",
           size=14, weight="700")
    s.text(52, 54, "一度落ちると復旧まで二時間かかるので、障害は固まって起きる",
           size=10, fill=SUB)

    s.text(52, 88, "直近40時間", size=11, fill=SUB, weight="700")
    for i, v in enumerate(strip):
        s.rect(150 + i * 13.5, 96, 13.5, 30,
               fill=TINT_WARN if v else "#ffffff",
               stroke=WARN if v else MUTED, sw=1.2)
    s.text(694, 116, "→ 時間", size=10, fill=SUB)
    s.text(150, 148, "赤＝障害。ならせば10%でも、赤の隣は赤になりやすい",
           size=11, fill=SUB)

    for cx, val, col, lab in ((240, overall, MUTED, "全100時間をならした率"),
                              (420, from_ok, MAIN, "正常だった次の一時間"),
                              (600, from_ng, FOCUS, "障害だった次の一時間")):
        s.rect(cx - 46, 288 - 150 * val, 92, 150 * val,
               fill=TINT_MUTED if col is MUTED else
               (TINT_MAIN if col is MAIN else TINT_FOCUS),
               stroke=col, sw=2.0)
        s.text(cx, 288 - 150 * val - 10, "%d%%" % round(val * 100), size=14,
               fill=col, anchor="middle", weight="700")
        s.text(cx, 308, lab, size=11, anchor="middle", fill=INK)
    s.line(150, 288, 690, 288, stroke=SUB, sw=1.2, cap="butt")
    s.text(52, 330, "同じログでも、どの部屋にいるかを条件にすると次の予報が変わる",
           size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 20-3
def fig20_3():
    """20-3 揺れの大きい証言は軽く、安定した証言は重くする。

    本文の午前3時06分。第一センサーが5.0度、第二センサーが0.4度、
    手持ち計が0.5度の上昇を示し、直前までの足取りからの予測はほぼ0度。
    更新後は0.6度で、幅は通常より広い。

    グリッド
      tx(度) = lin(150, 660, -0.8, 7.2)
      行 y  110 予測 / 152 第一センサー / 194 第二センサー / 236 手持ち計
           284 更新後
      誤差棒の長さは校正試験での揺れの大小だけを表す（本文に数値は無い）
      y  32 タイトル / 56 副題 / 316 目盛り / 336 軸ラベル
      色  灰＝直前までの予測 / 青＝観測した三つの値 / 橙＝更新後の推定
    """
    obs = [("第一センサー", 5.0, 1.9), ("第二センサー", 0.4, 0.7),
           ("手持ち計", 0.5, 0.35)]
    pred = 0.05
    updated = 0.6
    assert obs[0][1] == 5.0 and obs[2][1] == 0.5 and updated == 0.6

    s = SVG(760, 352, "揺れの大きい証言を軽く、安定した証言を重くして更新する")
    tx = lin(150, 660, -0.8, 7.2)
    s.text(52, 32, "五度を真実とせず、全部ノイズともせず、途中の像を更新する",
           size=14, weight="700")
    s.text(52, 54, "横棒は校正試験で分かった相対的な揺れ（数値区間ではない）",
           size=10, fill=SUB)

    s.line(tx(pred), 96, tx(pred), 300, stroke=MUTED, sw=1.4, dash="5 3")
    rows = [("直前までの予測", pred, 0.5, MUTED, 110)]
    rows += [(n, v, e, MAIN, y) for (n, v, e), y in
             zip(obs, (152, 194, 236))]
    for name, val, err, col, y in rows:
        s.text(150, y + 4, name, size=11, fill=INK, anchor="end")
        s.line(tx(val - err), y, tx(val + err), y, stroke=col, sw=2.0)
        s.line(tx(val - err), y - 5, tx(val - err), y + 5, stroke=col, sw=1.6)
        s.line(tx(val + err), y - 5, tx(val + err), y + 5, stroke=col, sw=1.6)
        s.circle(tx(val), y, 6, fill=col, stroke=col, sw=1.0)
        s.text(tx(val), y - 14, "%.1f 度" % val, size=10, fill=col,
               anchor="middle", weight="700")
    s.text(150, 288, "更新後の推定", size=12, fill=FOCUS, anchor="end",
           weight="700")
    s.line(tx(updated - 0.9), 284, tx(updated + 0.9), 284, stroke=FOCUS, sw=2.6)
    s.line(tx(updated - 0.9), 278, tx(updated - 0.9), 290, stroke=FOCUS, sw=1.8)
    s.line(tx(updated + 0.9), 278, tx(updated + 0.9), 290, stroke=FOCUS, sw=1.8)
    s.circle(tx(updated), 284, 7.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(tx(updated), 268, "0.6 度（幅は通常より広い）", size=11, fill=FOCUS,
           anchor="middle", weight="700")

    xaxis(s, 140, 680, 316, [0, 1, 2, 3, 4, 5, 6, 7], tx,
          ["0", "1", "2", "3", "4", "5", "6", "7"])
    s.text(410, 344, "内部温度の上昇量（度）", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 21-1
def fig21_1():
    """21-1 同じ8個の空欄でも、どこが抜けるかで結論が変わる。

    本文の三つのログ。甲は校正係がくじで抜き、乙は旧型中継器の夜勤（前半）が抜け、
    丙は真の温度が高いところで温度計が記録を止める。
    温度列は seed 23 の擬似乱数で決定的に作り、抜けた後の平均を比べる。

    グリッド
      tx(枠) = lin(160, 680, 0, 39)、点は真の温度、ty(度) = lin(y0, y0-58, 35, 43)
      行 y0  132（甲）/ 216（乙）/ 300（丙）
      y  32 タイトル / 56 副題 / 各行 −70 見出し / 各行 +18 平均
      色  青＝観測できた枠 / 赤＝欠測した枠（×印） / 灰＝真の平均
    """
    r = lcg(23)
    temps = []
    for i in range(40):
        base = 38.0 + 2.2 * math.sin(i * 0.42)
        temps.append(round(base + (r() - 0.5) * 1.4, 3))
    true_mean = sum(temps) / len(temps)
    miss_a = [2, 7, 12, 18, 23, 29, 33, 38]
    # 観測済みの時刻・機種に依存する欠測。夜勤に当たる前半20枠だけから選び、
    # この具体例では観測平均をほぼ変えない配置にする。
    miss_b = [0, 4, 6, 8, 10, 12, 15, 18]
    miss_c = sorted(range(40), key=lambda i: -temps[i])[:8]
    assert len(set(miss_a)) == len(set(miss_b)) == len(set(miss_c)) == 8
    assert len(miss_b) == 8
    assert max(miss_b) < 20                     # 乙は夜勤（前半）だけが欠測

    def kept_mean(miss):
        keep = [t for i, t in enumerate(temps) if i not in miss]
        return sum(keep) / len(keep)
    assert kept_mean(miss_c) < true_mean - 0.4      # 丙だけ平均が下へずれる
    assert abs(kept_mean(miss_a) - true_mean) < 0.25
    assert abs(kept_mean(miss_b) - true_mean) < 0.05

    s = SVG(760, 356, "空欄の数ではなく、どこが空欄になったかが推測を左右する")
    tx = lin(160, 680, 0, 39)
    s.text(52, 32, "穴の大きさより、大きな魚だけ抜ける形の穴かを見る",
           size=14, weight="700")
    s.text(52, 54, "同じ温度記録40枠から、8枠が欠ける三つの仕組み", size=10, fill=SUB)

    for y0, miss, name, note in ((132, miss_a, "甲：くじで抜いた",
                                  "値にも札にも関係なく抜ける"),
                                 (216, miss_b, "乙：旧型中継器の夜勤",
                                  "観測済みの札（時刻・機種）で説明できる"),
                                 (300, miss_c, "丙：高温で記録が止まる",
                                  "抜けた値そのものが抜ける理由")):
        ty = lin(y0, y0 - 58, 35, 43)
        s.text(52, y0 - 46, name, size=12, weight="700", fill=INK)
        s.text(198, y0 - 46, note, size=9, fill=SUB)
        s.line(160, y0 + 2, 680, y0 + 2, stroke=MUTED, sw=1.0)
        for i, t in enumerate(temps):
            if i in miss:
                s.cross(tx(i), ty(t), 4.5, stroke=WARN, sw=1.8)
            else:
                s.circle(tx(i), ty(t), 3.2, fill=MAIN, stroke=MAIN, sw=0.8)
        km = kept_mean(miss)
        s.line(160, ty(km), 680, ty(km), stroke=FOCUS, sw=1.8, dash="5 3")
        s.text(686, ty(km) + 4, "観測平均 %.1f 度" % km, size=10, fill=FOCUS,
               weight="700")
    s.text(52, 348, "真の平均は %.1f 度。丙だけ、平均も分散も低く見える"
           % true_mean, size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 21-3
def fig21_3():
    """21-3 故障で階段が下がり、打切りでは下げずに次の段の人数だけ減る。

    本文の五台。2日目に一台故障、3日目に一台が追跡終了、5日目に一台故障、
    残る二台は6日目まで稼働。生存率は 1 → 0.8 → 0.8 → 0.533。

    グリッド
      tx(日) = lin(160, 620, 0, 6.6)
      上段 五台の追跡線 y 100 + i*26（i = 0..4）
      下段 生存曲線 ty(率) = lin(320, 200, 0, 1)、底辺 320
      y  32 タイトル / 76 上段見出し / 240 下段見出し / 336 目盛り / 356 軸ラベル
      色  赤＝故障（×） / 灰＝追跡終了（縦棒） / 青＝生存曲線 / 橙＝危険集合の人数
    """
    tracks = [(2.0, "fail"), (3.0, "censor"), (5.0, "fail"),
              (6.0, "alive"), (6.0, "alive")]
    steps = []
    surv, at_risk = 1.0, 5
    for t in (2.0, 5.0):
        d = 1
        surv *= (1 - d / at_risk)
        steps.append((t, surv, at_risk))
        at_risk -= d
        if t == 2.0:
            at_risk -= 1          # 3日目の追跡終了
    assert abs(steps[0][1] - 0.8) < 1e-12
    assert abs(steps[1][1] - 0.5333333) < 1e-6
    assert steps[1][2] == 3

    s = SVG(760, 400, "打切りは階段を下げず、次の段の人数だけを減らす")
    tx = lin(160, 620, 0, 6.6)
    ty = lin(330, 234, 0, 1)
    s.text(52, 32, "途中まで走った時間を捨てず、観察の終わりと寿命の終わりを分ける",
           size=14, weight="700")

    s.text(52, 74, "五台の追跡", size=12, weight="700", fill=INK)
    for i, (t, kind) in enumerate(tracks):
        y = 96 + i * 22
        s.text(150, y + 4, "%d号機" % (i + 1), size=10, fill=SUB, anchor="end")
        s.line(tx(0), y, tx(t), y, stroke=MAIN, sw=2.2)
        if kind == "fail":
            s.cross(tx(t), y, 6, stroke=WARN, sw=2.4)
            s.text(tx(t) + 12, y + 4, "故障", size=10, fill=WARN, weight="700")
        elif kind == "censor":
            s.line(tx(t), y - 7, tx(t), y + 7, stroke=MUTED, sw=2.6)
            s.text(tx(t) + 12, y + 4, "追跡終了", size=10, fill=SUB,
                   weight="700")
        else:
            s.arrow(tx(t), y, tx(t) + 14, y, stroke=MAIN, sw=2.0)

    s.text(52, 220, "そこから作る生存曲線", size=12, weight="700", fill=INK)
    path = [(tx(0), ty(1.0))]
    prev = 1.0
    for t, sv, risk in steps:
        path += [(tx(t), ty(prev)), (tx(t), ty(sv))]
        prev = sv
    path.append((tx(6.6), ty(prev)))
    polyline(s, path, stroke=MAIN, sw=2.6)
    for t, sv, risk in steps:
        s.circle(tx(t), ty(sv), 5.5, fill=MAIN, stroke=MAIN, sw=1.0)
        s.text(tx(t) + 10, ty(sv) - 8, "%.3f" % sv, size=11, fill=MAIN,
               weight="700")
        s.text(tx(t), 376, "危険集合 %d台" % risk, size=10, fill=FOCUS,
               anchor="middle", weight="700")
    s.line(tx(3.0), ty(0.8), tx(3.0), 330, stroke=MUTED, sw=1.6, dash="5 3")
    s.text(tx(3.0) + 8, 306, "打切りでは下げない", size=10, fill=SUB,
           weight="700")

    xaxis(s, 150, 640, 330, [0, 1, 2, 3, 4, 5, 6], tx,
          ["0", "1", "2", "3", "4", "5", "6"])
    s.text(390, 394, "追跡日数（日）", size=10, fill=SUB, anchor="middle")
    yaxis(s, 330, 234, 160, [0, 0.5, 1.0], ty, ["0", "0.5", "1.0"])
    return s


# ---------------------------------------------------------------- 22-1
def fig22_1():
    """22-1 適合の改善に、部品数の請求書を足して順位を付け直す。

    本文の二模型。小 k=2・−2logL=100、大 k=10・−2logL=90。
    AIC は 104 対 110、n=100 の BIC は 109.22 対 136.10 で、どちらも小模型が勝つ。
    kを1増やすとき同点を保つのに必要な適合改善が、AICは2、BICは4.61になる。

    グリッド
      dx(−2logL) = lin(180, 620, 84, 116) / dy(k) = lin(292, 92, 0, 13)
      小模型 (100, 2) → (455.0, 261.2) / 大模型 (90, 10) → (317.5, 138.5)
      y  32 タイトル / 56 副題 / 312 目盛り / 336 軸ラベル
      色  青＝小模型を通る等AIC線 / 橙＝等BIC線（n=100） / 灰＝二つの候補
    """
    small, large = (100.0, 2), (90.0, 10)
    aic = [d + 2 * k for d, k in (small, large)]
    pen = math.log(100)
    bic = [d + pen * k for d, k in (small, large)]
    assert aic == [104.0, 110.0]
    assert abs(bic[0] - 109.21) < 0.02 and abs(bic[1] - 136.05) < 0.02
    assert abs(math.log(10) - 2.3026) < 1e-3
    assert abs(math.log(10000) - 9.2103) < 1e-3

    s = SVG(760, 348, "適合の改善へ部品代を足すと、二模型の順位が入れ替わる")
    dx = lin(180, 620, 84, 116)
    dy = lin(292, 92, 0, 13)
    s.text(52, 32, "尤度だけなら大模型。部品代を足すと小模型が勝つ",
           size=14, weight="700")
    s.text(52, 54, "線が左下にあるほど良い。傾きの絶対値が罰の重さ", size=10, fill=SUB)

    for c, col, lab, slope in ((aic[0], MAIN, "等AIC線（罰 2k）", 2.0),
                               (bic[0], FOCUS, "等BIC線（n=100、罰 4.61k）", pen)):
        # 見えている k の範囲だけで端点を作る（y を切り詰めると傾きが崩れる）
        k_hi = min(13.0, (c - 84.0) / slope)
        polyline(s, [(dx(c), dy(0)), (dx(c - slope * k_hi), dy(k_hi))],
                 stroke=col, sw=2.4, dash="7 4")
        s.text(dx(c - slope * k_hi) + 8, dy(k_hi) - 8, lab, size=11, fill=col,
               weight="700")

    for (d, k), name, col, dyy in ((small, "小模型 k=2", MAIN, 22),
                                   (large, "大模型 k=10", WARN, -16)):
        s.circle(dx(d), dy(k), 8, fill=col, stroke=col, sw=1.0)
        s.text(dx(d) + 14, dy(k) + dyy, name, size=12, fill=col, weight="700")
    s.text(dx(small[0]) + 14, dy(small[1]) + 38, "AIC 104 ／ BIC 109.2",
           size=10, fill=SUB)
    s.text(dx(large[0]) + 14, dy(large[1]) + 2, "AIC 110 ／ BIC 136.1",
           size=10, fill=SUB)

    xaxis(s, 170, 632, 292, [90, 100, 110], dx, ["90", "100", "110"])
    s.text(400, 336, "−2 log L（小さいほど当てはまりが良い）", size=10,
           fill=SUB, anchor="middle")
    yaxis(s, 292, 92, 180, [0, 5, 10], dy, ["0", "5", "10"])
    s.text(140, 84, "部品数 k", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 22-2
def fig22_2():
    """22-2 セルをばらばらに隠すか、人を隠すか、未来を隠すか。

    本文の予測大会。同じ顧客の月〜木で学び金曜を当てると95%、
    顧客ごとに分けると72%。運用でまだ知らない単位を丸ごと隠したかを見る。

    グリッド（三パネルで格子の座標を固定し、変えるのは評価へ回すセルだけ）
      パネル左上 x 130 / 340 / 550、セル 34×30、5顧客 × 5日
      y  32 タイトル / 76 パネル名 / 110..260 格子 / 284 結論
      色  青＝訓練に使うセル / 橙＝評価へ回すセル / 灰＝格子の枠
    """
    days = ["月", "火", "水", "木", "金"]
    random_cells = {(0, 2), (1, 4), (2, 1), (3, 3), (4, 0)}
    plans = [
        ("セルを無作為に分ける",
         lambda i, j: (i, j) in random_cells,
         "同じ顧客の別の日を当てているだけ", WARN),
        ("顧客ごとに分ける",
         lambda i, j: i == 3,
         "初めて会う顧客で測れる", MAIN),
        ("未来の日で分ける",
         lambda i, j: j == 4,
         "過去から未来を当てる試験になる", MAIN),
    ]
    assert sum(1 for i in range(5) for j in range(5) if plans[0][1](i, j)) == 5
    assert sum(1 for i in range(5) for j in range(5) if plans[1][1](i, j)) == 5
    assert sum(1 for i in range(5) for j in range(5) if plans[2][1](i, j)) == 5

    s = SVG(760, 308, "隠すのはセルではなく、運用でまだ知らない単位そのもの")
    s.text(52, 32, "同じ25セルでも、どの単位を丸ごと隠したかで試験の意味が変わる",
           size=14, weight="700")
    s.text(52, 54, "橙＝評価へ回すセル　／　青＝訓練に使うセル", size=10, fill=SUB)

    for p, (title, is_test, note, col) in enumerate(plans):
        x0 = 130 + p * 212
        s.text(x0, 78, title, size=12, weight="700", fill=INK)
        for j, d in enumerate(days):
            s.text(x0 + 17 + j * 34, 102, d, size=9, fill=SUB, anchor="middle")
        for i in range(5):
            if p == 0:
                s.text(x0 - 6, 128 + i * 30, "客%d" % (i + 1), size=9,
                       fill=SUB, anchor="end")
            for j in range(5):
                test = is_test(i, j)
                s.rect(x0 + j * 34, 110 + i * 30, 34, 30,
                       fill=TINT_FOCUS if test else TINT_MAIN,
                       stroke=FOCUS if test else MAIN, sw=1.2)
        s.text(x0 + 85, 284, note, size=11, fill=col, anchor="middle",
               weight="700")
    return s


def _beta_pdf(x, a, b):
    if x <= 0 or x >= 1:
        return 0.0
    lg = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
          + (a - 1) * math.log(x) + (b - 1) * math.log(1 - x))
    return math.exp(lg)


# ---------------------------------------------------------------- 23-1
def fig23_1():
    """23-1 同じ平均2%の事前分布でも、持ち込む強さで事後が動く。

    本文の新製品20台中2台。強さ100の Beta(2,98) なら事後は Beta(4,116) で平均3.33%、
    強さ10の Beta(0.2,9.8) なら Beta(2.2,27.8) で平均7.33%。尤度は共通。

    グリッド（二段で横軸を固定し、変えるのは事前分布の強さだけ）
      tx(θ) = lin(150, 690, 0, 0.30)
      上段 底辺 y 186、下段 底辺 y 306、高さはいずれも 92
      y  32 タイトル / 56 副題 / 76 上段名 / 196 下段名 / 322 目盛り
      色  灰＝事前分布 / 橙＝新製品20台の尤度 / 青＝事後分布
    """
    cases = []
    for a0, b0, strength in ((2.0, 98.0, 100), (0.2, 9.8, 10)):
        a1, b1 = a0 + 2, b0 + 18
        cases.append((a0, b0, a1, b1, strength, a1 / (a1 + b1)))
    assert cases[0][2] == 4.0 and cases[0][3] == 116.0
    assert abs(cases[0][5] - 0.033333) < 1e-6
    assert abs(cases[1][5] - 0.073333) < 1e-6

    s = SVG(760, 394, "同じ平均の事前分布でも、持ち込む強さで事後の位置が変わる")
    tx = lin(150, 690, 0, 0.30)
    s.text(52, 32, "旧製品を何票ぶん持ち込むかは、自然法則ではなく選んだ重さ",
           size=14, weight="700")
    s.text(52, 54, "新製品20台中2台が故障（尤度は上下で共通）", size=10, fill=SUB)

    def row(base, a0, b0, a1, b1, strength, post_mean, name):
        s.text(52, base - 112, name, size=12, weight="700", fill=INK)
        top = max(max(_beta_pdf(i / 600.0, a1, b1) for i in range(1, 200)),
                  max(_beta_pdf(i / 600.0, a0, b0) for i in range(1, 200)))
        for a, b, col, sw in ((a0, b0, MUTED, 2.0), (a1, b1, MAIN, 2.6)):
            pts = []
            i = 1
            while i <= 180:
                v = i / 600.0
                pts.append((tx(v), base - 92 * _beta_pdf(v, a, b) / top))
                i += 1
            polyline(s, pts, stroke=col, sw=sw)
        # 20台中2台の尤度（形だけを橙で重ねる）
        lk = [(tx(i / 600.0),
               base - 92 * (i / 600.0) ** 2 * (1 - i / 600.0) ** 18
               / max((j / 600.0) ** 2 * (1 - j / 600.0) ** 18
                     for j in range(1, 181)))
              for i in range(1, 181)]
        polyline(s, lk, stroke=FOCUS, sw=1.8, dash="5 3")
        s.line(150, base, 690, base, stroke=SUB, sw=1.2, cap="butt")
        s.line(tx(post_mean), base - 96, tx(post_mean), base + 6,
               stroke=MAIN, sw=2.0)
        s.text(tx(post_mean) + 8, base - 84,
               "事後平均 %.2f%%" % (post_mean * 100), size=11, fill=MAIN,
               weight="700")

    row(196, *cases[0], name="強さ100 の事前分布（旧製品100台ぶん）")
    row(334, *cases[1], name="強さ10 の事前分布（同じ平均2%）")
    s.text(560, 76, "灰＝事前　橙＝尤度　青＝事後", size=10, fill=SUB)
    xaxis(s, 140, 700, 350, [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30], tx,
          ["0", "5%", "10%", "15%", "20%", "25%", "30%"])
    s.text(415, 384, "新製品の故障確率", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 23-2
def fig23_2():
    """23-2 分母が小さい地域ほど、共通の中心へ強く引き寄せられる。

    本文の練習。共通中心50%・強さ10の Beta(5,5) を貸すと、
    A(0/2)は0%→41.7%、B(5/10)は50%→50%、C(50/100)は50%→50%。
    D(0/100)は同じ0件でも4.5%までしか動かない。

    グリッド
      観測の列 x 250 / 縮小後の列 x 560、ty(率) = lin(300, 96, 0, 0.6)
      行ラベル x 150、地域ごとの矢印は左右の点をまっすぐ結ぶ
      y  32 タイトル / 56 副題 / 76 列見出し / 322 注記
      色  橙＝観測した率 / 青＝共通情報を借りた後の率 / 灰＝共通中心50%
    """
    prior_a, prior_b = 5.0, 5.0
    regions = [("A地域", 0, 2), ("B地域", 5, 10), ("C地域", 50, 100),
               ("D地域", 0, 100)]
    rows = []
    for name, x, n in regions:
        raw = x / n
        post = (x + prior_a) / (n + prior_a + prior_b)
        rows.append((name, x, n, raw, post))
    assert abs(rows[0][4] - 0.4166667) < 1e-6
    assert abs(rows[1][4] - 0.5) < 1e-12
    assert abs(rows[2][4] - 0.5) < 1e-12
    assert abs(rows[3][4] - 0.0454545) < 1e-6

    s = SVG(760, 328, "同じ0件でも、分母が違えば縮む量が違う")
    tx = lin(230, 640, 0, 0.60)
    s.text(52, 32, "小さい島ほど本土の灯台を頼り、大きい島は自前の地図を使う",
           size=14, weight="700")
    s.text(52, 54, "共通中心50%・強さ10の情報を、どの地域へも同じだけ貸す",
           size=10, fill=SUB)

    s.line(tx(0.5), 88, tx(0.5), 260, stroke=MUTED, sw=1.8, dash="6 4")
    s.text(tx(0.5), 82, "共通中心 50%", size=10, fill=SUB, anchor="middle")

    notes = ["二台だけなので大きく縮む", "", "百台あるので動かない",
             "同じ0件でも百台ぶんの証拠がある"]
    for i, ((name, x, n, raw, post), note) in enumerate(zip(rows, notes)):
        y = 116 + i * 36
        s.text(222, y + 4, "%s　%d/%d" % (name, x, n), size=12, fill=INK,
               anchor="end")
        if abs(post - raw) > 1e-9:
            s.arrow(tx(raw), y, tx(post), y, stroke=MUTED, sw=1.6)
        s.circle(tx(raw), y, 6.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
        s.circle(tx(post), y, 6.5, fill=MAIN, stroke=MAIN, sw=1.0)
        s.text(tx(post) + 12, y + 4, "%.1f%%" % (post * 100), size=12,
               fill=MAIN, weight="700")
        if note:
            s.text(tx(post) + 62, y + 4, note, size=10, fill=SUB)

    xaxis(s, 220, 652, 268, [0, 0.2, 0.4, 0.6], tx, ["0", "20%", "40%", "60%"])
    s.text(436, 296, "故障率", size=10, fill=SUB, anchor="middle")
    s.text(52, 88, "橙＝観測した率", size=10, fill=FOCUS, weight="700")
    s.text(52, 104, "青＝借りた後の率", size=10, fill=MAIN, weight="700")
    s.text(52, 320, "縮む量は観測率の見た目でなく、分母と群間のばらつきで決まる",
           size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 24-1
def fig24_1():
    """24-1 どちらの端末型でも更新群が低いのに、合計では逆転する。

    本文の数値。新型では更新10台中1台（10%）・未更新90台中18台（20%）、
    旧型では更新90台中36台（40%）・未更新10台中5台（50%）。
    合計は更新37%・未更新23%で、層内と逆向きになる。

    グリッド（幅が台数、高さが故障率。面積が故障台数）
      更新群 x 130..390 / 未更新群 x 430..690、sy(率) = lin(276, 96, 0, 0.6)
      y  32 タイトル / 56 副題 / 78 群名 / 290 幅ラベル / 316 合計
      色  青＝新型 / 灰＝旧型 / 赤＝合計（層内と逆向き）
    """
    groups = {
        "更新": [("新型", 10, 1), ("旧型", 90, 36)],
        "未更新": [("新型", 90, 18), ("旧型", 10, 5)],
    }
    tot = {}
    for g, rows in groups.items():
        tot[g] = sum(f for _, _, f in rows) / sum(n for _, n, _ in rows)
    assert abs(tot["更新"] - 0.37) < 1e-12 and abs(tot["未更新"] - 0.23) < 1e-12
    assert groups["更新"][0][2] / 10 == 0.1 and groups["未更新"][0][2] / 90 == 0.2
    assert groups["更新"][1][2] / 90 == 0.4 and groups["未更新"][1][2] / 10 == 0.5

    s = SVG(760, 336, "層の中では更新が低いのに、合計では更新が高く見える")
    sy = lin(276, 96, 0, 0.6)
    s.text(52, 32, "更新群へ故障しやすい旧型が多く入った構成差が、向きを反転させる",
           size=14, weight="700")
    s.text(52, 54, "幅が台数、高さが故障率（面積が故障台数）", size=10, fill=SUB)

    def bars(x0, gname):
        rows = groups[gname]
        s.text(x0, 78, "%s群（100台）" % gname, size=12, weight="700", fill=INK)
        cur = x0
        for tname, n, f in rows:
            w = n * 2.6
            rate = f / n
            s.rect(cur, sy(rate), w, 276 - sy(rate),
                   fill=TINT_MAIN if tname == "新型" else TINT_MUTED,
                   stroke=MAIN if tname == "新型" else MUTED, sw=1.8)
            s.text(cur + w / 2, sy(rate) - 8, "%d%%" % round(rate * 100),
                   size=12, anchor="middle", weight="700",
                   fill=MAIN if tname == "新型" else SUB)
            s.text(cur + w / 2, 292, "%s %d台" % (tname, n), size=10,
                   fill=SUB, anchor="middle")
            cur += w
        s.line(x0, sy(tot[gname]), x0 + 260, sy(tot[gname]), stroke=WARN,
               sw=2.4)
        s.text(x0 + 130, 316, "合計 %d%%" % round(tot[gname] * 100), size=13,
               fill=WARN, anchor="middle", weight="700")

    bars(130, "更新")
    bars(430, "未更新")
    s.line(130, 276, 690, 276, stroke=SUB, sw=1.2, cap="butt")
    yaxis(s, 276, 96, 130, [0, 0.25, 0.5], sy, ["0", "25%", "50%"])
    return s


# ---------------------------------------------------------------- 24-2
def fig24_2():
    """24-2 入庫という一つの升を消すと、無かった関係が生まれる。

    本文の toy 例。更新 X と潜在劣化 U は独立で各50%、どちらかが1なら入庫 S=1、
    故障 Y は U と同じ。全体では更新の有無で故障率は50%どうしだが、
    入庫者だけに絞ると X=0 で100%、X=1 で50%になる。

    グリッド（二パネルで四つの升の座標を固定し、消えるのは (0,0) だけ）
      左 表 x 150..350 / 右 x 470..670、セル 100×72、行 y 118..262
      y  32 タイトル / 76 パネル名 / 100 列見出し / 286 群ごとの故障率
         312 結論
      色  青＝残っている升 / 赤＝入庫で消える升 / 橙＝結論の数値
    """
    cells = {(0, 0): 0, (0, 1): 1, (1, 0): 0, (1, 1): 1}   # Y = U
    all_x0 = [y for (x, _), y in cells.items() if x == 0]
    all_x1 = [y for (x, _), y in cells.items() if x == 1]
    assert sum(all_x0) / 2 == 0.5 and sum(all_x1) / 2 == 0.5
    sel = {k: v for k, v in cells.items() if k != (0, 0)}
    s_x0 = [y for (x, _), y in sel.items() if x == 0]
    s_x1 = [y for (x, _), y in sel.items() if x == 1]
    assert sum(s_x0) / len(s_x0) == 1.0
    assert sum(s_x1) / len(s_x1) == 0.5

    s = SVG(760, 340, "入庫者だけを見ると、効果0の更新が故障を半減して見える")
    s.text(52, 32, "分岐点は閉じるために調整し、合流点は触ると閉じた道を開ける",
           size=14, weight="700")

    def table(x0, title, drop):
        s.text(x0 - 8, 76, title, size=12, weight="700", fill=INK)
        s.text(x0 + 50, 104, "更新なし", size=10, fill=SUB, anchor="middle")
        s.text(x0 + 150, 104, "更新あり", size=10, fill=SUB, anchor="middle")
        for i, u in enumerate((1, 0)):
            s.text(x0 - 12, 158 + i * 72, "劣化%s" % ("あり" if u else "なし"),
                   size=10, fill=SUB, anchor="end")
            for j, x in enumerate((0, 1)):
                cx, cy = x0 + j * 100, 118 + i * 72
                gone = drop and (x, u) == (0, 0)
                s.rect(cx, cy, 100, 72,
                       fill=TINT_WARN if gone else TINT_MAIN,
                       stroke=WARN if gone else MAIN, sw=1.8,
                       dash="5 3" if gone else None)
                if gone:
                    s.cross(cx + 50, cy + 30, 11, stroke=WARN, sw=2.6)
                    s.text(cx + 50, cy + 60, "入庫しない", size=10, fill=WARN,
                           anchor="middle", weight="700")
                else:
                    s.text(cx + 50, cy + 42, "故障 %s" % ("あり" if cells[(x, u)]
                                                       else "なし"),
                           size=12, fill=MAIN, anchor="middle", weight="700")
        for j, (x, vals) in enumerate((("なし", s_x0 if drop else all_x0),
                                       ("あり", s_x1 if drop else all_x1))):
            rate = sum(vals) / len(vals)
            s.text(x0 + 50 + j * 100, 288, "故障 %d%%" % round(rate * 100),
                   size=13, fill=FOCUS, anchor="middle", weight="700")

    table(150, "全体で見る（更新の効果は0）", False)
    table(470, "入庫した台だけで見る", True)
    s.text(380, 320,
           "効果0のまま、入庫という合流点を条件にしただけで 100% 対 50% になる",
           size=11, anchor="middle", fill=INK, weight="700")
    return s


# ---------------------------------------------------------------- 25-1
def fig25_1():
    """25-1 閾値は気分ではなく、二つの期待損失が交差する踏切。

    本文の料金表。危険なのに継続すると損失100、安全なのに停止すると5、
    危険時に停止しても残余損失2。継続の期待損失は 100p、停止は 5-3p で、
    交点は p = 5/103 ≒ 4.85%。危険確率4%と6%で旗が変わる。

    グリッド
      tx(p) = lin(150, 660, 0, 0.12) / ty(損失) = lin(276, 92, 0, 12)
      交点 p = 0.04854 → (356.3, 202.5)
      y  32 タイトル / 56 副題 / 292 目盛り / 316 二台の判定
      色  赤＝継続の期待損失 / 青＝停止の期待損失 / 橙＝二つが交差する閾値
    """
    l_cont, l_stop_safe, l_stop_risk = 100.0, 5.0, 2.0
    thr = l_stop_safe / (l_cont + l_stop_safe - l_stop_risk)
    assert abs(thr - 5.0 / 103.0) < 1e-12
    assert abs(thr - 0.048544) < 1e-6
    at4 = (100 * 0.04, 5 - 3 * 0.04)
    at6 = (100 * 0.06, 5 - 3 * 0.06)
    assert at4[0] < at4[1] and at6[0] > at6[1]

    s = SVG(760, 344, "閾値は50%ではなく、二つの期待損失が交差する4.85%")
    tx = lin(150, 660, 0, 0.12)
    ty = lin(276, 92, 0, 12)
    s.text(52, 32, "確率を出した後に、間違え方の重さを置いて初めて行動が決まる",
           size=14, weight="700")
    s.text(52, 54, "危険なのに継続すると100、安全なのに停止すると5、危険時の停止は2",
           size=10, fill=SUB)

    polyline(s, [(tx(0), ty(0)), (tx(0.12), ty(12))], stroke=WARN, sw=2.6)
    polyline(s, [(tx(0), ty(5)), (tx(0.12), ty(5 - 0.36))], stroke=MAIN, sw=2.6)
    s.text(tx(0.104), ty(10.4) - 8, "継続の期待損失 100p", size=11, fill=WARN,
           weight="700", anchor="end")
    s.text(tx(0.104), ty(4.7) + 20, "停止の期待損失 5 − 3p", size=11,
           fill=MAIN, weight="700", anchor="end")

    s.line(tx(thr), 92, tx(thr), 286, stroke=FOCUS, sw=2.4)
    s.circle(tx(thr), ty(100 * thr), 7, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(tx(thr) + 10, 108, "閾値 4.85%", size=13, fill=FOCUS, weight="700")
    s.text(tx(thr) + 10, 126, "ここより左は継続、右は停止", size=10, fill=SUB)

    for p, (c, st), lab, lx_ in ((0.04, at4, "危険4% → 継続", 0.018),
                                 (0.06, at6, "危険6% → 停止", 0.088)):
        s.line(tx(p), ty(c), tx(p), ty(st), stroke=MUTED, sw=1.4, dash="4 3")
        s.circle(tx(p), ty(c), 4.5, fill=WARN, stroke=WARN, sw=1.0)
        s.circle(tx(p), ty(st), 4.5, fill=MAIN, stroke=MAIN, sw=1.0)
        s.text(tx(lx_), 316, lab, size=11, anchor="middle", weight="700",
               fill=INK)

    xaxis(s, 140, 670, 276, [0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12], tx,
          ["0", "2%", "4%", "6%", "8%", "10%", "12%"])
    s.text(405, 336, "危険状態である確率", size=10, fill=SUB, anchor="middle")
    yaxis(s, 276, 92, 150, [0, 5, 10], ty, ["0", "5", "10"])
    s.text(112, 84, "期待損失", size=10, fill=SUB)
    return s


# ---------------------------------------------------------------- 25-4
def fig25_4():
    """25-4 同じ400件でも、時間の形が違えば別の工程になる。

    本文の音声応答停止。10,000台中400件で率4%。だが400件のうち360件は
    同一batch・software更新直後の一時間へ固まっていた。
    合計も平均も同じ二つの時間の形を、同じ座標で並べる。

    グリッド（二段で時間軸と縦軸を固定し、変えるのは件数の並びだけ）
      tx(時) = lin(150, 690, 0, 23) / 高さは 360件で 96px
      上段 底辺 y 168 / 下段 底辺 y 300（高さは 360件 で 110px）
      y  32 タイトル / 56 副題 / 88 上段名 / 210 下段名 / 308 目盛り
      色  灰＝全期間へならした形 / 赤＝一時間へ束になった形
    """
    total, n_units = 400, 10000
    assert total / n_units == 0.04
    flat = [total / 24.0] * 24
    burst = [(400 - 360) / 23.0] * 24
    burst[9] = 360
    assert abs(sum(flat) - total) < 1e-9 and abs(sum(burst) - total) < 1e-9

    s = SVG(760, 348, "合計400件・平均4%が同じでも、時間の形はまったく違う")
    tx = lin(150, 690, 0, 23)
    s.text(52, 32, "年平均の雨量で堤防を設計すると、集中豪雨の山が消える",
           size=14, weight="700")
    s.text(52, 54, "どちらも一日で400件、10,000台に対して率4%", size=10, fill=SUB)

    def row(base, vals, col, tint, name_y, name, note):
        s.text(52, name_y, name, size=12, weight="700", fill=INK)
        s.text(52, name_y + 16, note, size=10, fill=SUB)
        for i, v in enumerate(vals):
            h = 110.0 * v / 360.0
            s.rect(tx(i) - 9, base - h, 18, h, fill=tint, stroke=col, sw=1.2)
        s.line(150, base, 700, base, stroke=SUB, sw=1.2, cap="butt")

    row(168, flat, MUTED, TINT_MUTED, 110, "全期間へならした形",
        "一時間あたり約17件")
    row(300, burst, WARN, TINT_WARN, 212, "実際の形",
        "一時間に360件、残り23時間で40件")
    s.text(tx(9) + 16, 196, "software更新直後の一時間", size=11, fill=WARN,
           weight="700")

    xaxis(s, 140, 700, 300, [0, 6, 12, 18, 23], tx,
          ["0時", "6時", "12時", "18時", "23時"])
    s.text(420, 340, "発生時刻", size=10, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 27-5
def fig27_5():
    """27-5 片方だけ有意でも、二つが有意に違う証拠にはならない。

    大都市と小地域で推定した効果は同じ −6ポイントだが、標本数が違うため
    区間の幅が違い、大都市だけが0をまたがない。
    二つの差そのものの区間は0を含む。

    グリッド
      tx(効果) = lin(200, 680, -16, 8)
      行 y  120 大都市 / 176 小地域 / 250 二つの差
      y  32 タイトル / 56 副題 / 100 0 の線ラベル / 296 目盛り / 330 結論
      色  青＝0をまたがない区間 / 灰＝0をまたぐ区間 / 橙＝二つの差の区間
    """
    est = -6.0
    se_city, se_small = 2.3, 4.7
    rows = [("大都市", est, se_city), ("小地域", est, se_small)]
    diff_se = math.sqrt(se_city ** 2 + se_small ** 2)
    assert est - 1.96 * se_city < 0 and est + 1.96 * se_city < 0
    assert est + 1.96 * se_small > 0
    assert -1.96 * diff_se < 0 < 1.96 * diff_se

    s = SVG(760, 352, "同じ推定値でも幅が違うだけで、片方だけが有意になる")
    tx = lin(200, 680, -16, 8)
    s.text(52, 32, "「片方だけ有意」は「二つが有意に違う」ではない",
           size=14, weight="700")
    s.text(52, 54, "推定した効果はどちらも −6 ポイント。違うのは標本数だけ",
           size=10, fill=SUB)

    s.line(tx(0), 96, tx(0), 286, stroke=MUTED, sw=1.8, dash="6 4")
    s.text(tx(0), 90, "効果なし（0）", size=10, fill=SUB, anchor="middle")

    for (name, e, se), y in zip(rows, (128, 184)):
        lo, hi = e - 1.96 * se, e + 1.96 * se
        col = MAIN if hi < 0 else MUTED
        s.text(190, y + 4, name, size=12, fill=INK, anchor="end")
        s.line(tx(lo), y, tx(hi), y, stroke=col, sw=2.6)
        s.line(tx(lo), y - 6, tx(lo), y + 6, stroke=col, sw=1.8)
        s.line(tx(hi), y - 6, tx(hi), y + 6, stroke=col, sw=1.8)
        s.circle(tx(e), y, 6.5, fill=col, stroke=col, sw=1.0)
        s.text(tx(hi) + 10, y + 4,
               "有意" if hi < 0 else "有意でない", size=11, fill=col,
               weight="700")

    y = 250
    lo, hi = -1.96 * diff_se, 1.96 * diff_se
    s.text(190, y + 4, "二つの差", size=12, fill=FOCUS, anchor="end",
           weight="700")
    s.line(tx(lo), y, tx(hi), y, stroke=FOCUS, sw=2.6)
    s.line(tx(lo), y - 6, tx(lo), y + 6, stroke=FOCUS, sw=1.8)
    s.line(tx(hi), y - 6, tx(hi), y + 6, stroke=FOCUS, sw=1.8)
    s.circle(tx(0), y, 6.5, fill=FOCUS, stroke=FOCUS, sw=1.0)
    s.text(tx(hi) + 10, y + 4, "0 を含む", size=11, fill=FOCUS, weight="700")

    xaxis(s, 190, 692, 286, [-15, -10, -5, 0, 5], tx,
          ["−15", "−10", "−5", "0", "+5"])
    s.text(440, 316, "返品率の変化（ポイント）", size=10, fill=SUB,
           anchor="middle")
    s.text(52, 344, "比べるべきは二本のハードルの越え方でなく、二人の距離の差",
           size=11, fill=SUB)
    return s


# ---------------------------------------------------------------- 27-7
def fig27_7():
    """27-7 「差を検出できない」と「害の上限が小さいと示した」は違う。

    許容できる害の上限（margin）を先に置くと、同じ「有意でない」区間でも、
    害が上限未満だと示せる場合と示せない場合に分かれる。これは両側の
    同等性ではなく、安全性について上側だけを見る非劣性型の問いである。
    本文の更新群100人中2件・比較群0件は、Wilson区間を使うNewcombe法では
    差がおよそ -2.0〜7.0ポイントとなり、4ポイントのmarginをまたぐ。

    グリッド
      tx(差) = lin(200, 680, -8, 10)
      行 y  126 / 182 / 238（三つの区間）
      y  32 タイトル / 56 副題 / 96 基準線ラベル / 272 目盛り / 316 結論
      色  灰＝0 の線 / 赤＝許容できる害の上限 / 青＝上限未満を示せた区間
          橙＝示せなかった区間
    """
    margin = 4.0

    def wilson_interval(x, n, z=1.96):
        p = x / n
        den = 1 + z * z / n
        center = (p + z * z / (2 * n)) / den
        half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return center - half, center + half

    def newcombe_difference(x1, n1, x2, n2):
        """Wilson score intervalsを合成したNewcombeの比率差区間（ポイント）。"""
        p1, p2 = x1 / n1, x2 / n2
        l1, u1 = wilson_interval(x1, n1)
        l2, u2 = wilson_interval(x2, n2)
        lo = p1 - p2 - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
        hi = p1 - p2 + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
        return 100 * (p1 - p2), 100 * lo, 100 * hi

    observed = newcombe_difference(2, 100, 0, 100)
    assert tuple(round(v, 1) for v in observed) == (2.0, -2.0, 7.0)
    cases = [("更新群2/100・比較群0/100", *observed),
             ("追跡を増やして幅が狭まった場合", 1.0, -1.4, 3.4),
             ("害が実際に大きかった場合", 6.0, 3.1, 8.9)]
    out = []
    for name, e, lo, hi in cases:
        if lo > 0:
            verdict, col = "害が増えている", WARN
        elif hi < margin:
            verdict, col = "上限未満を示せた", MAIN
        else:
            verdict, col = "上限をまたぐ＝まだ示せていない", FOCUS
        out.append((name, e, lo, hi, verdict, col))
    assert out[0][5] is FOCUS and out[1][5] is MAIN and out[2][5] is WARN
    assert out[0][2] < 0 < out[0][3] and out[1][2] < 0 < out[1][3]

    s = SVG(760, 336, "有意でないことと、害の上限が十分小さいと示すことは別")
    tx = lin(200, 660, -8, 11)
    s.text(52, 32, "許容できる害の上限を先に置かないと、安心へ変換できない",
           size=14, weight="700")
    s.text(52, 54, "上の二つはどちらも「有意差なし」だが、言えることが違う",
           size=10, fill=SUB)

    s.line(tx(0), 96, tx(0), 262, stroke=MUTED, sw=1.6, dash="6 4")
    s.text(tx(0), 90, "差なし", size=10, fill=SUB, anchor="middle")
    s.line(tx(margin), 96, tx(margin), 262, stroke=WARN, sw=2.2)
    s.text(tx(margin) + 8, 90, "許容できる害の上限（margin）", size=10,
           fill=WARN, weight="700")

    for (name, e, lo, hi, verdict, col), y in zip(out, (126, 182, 238)):
        s.text(190, y + 4, name, size=11, fill=INK, anchor="end")
        s.line(tx(lo), y, tx(hi), y, stroke=col, sw=2.6)
        s.line(tx(lo), y - 6, tx(lo), y + 6, stroke=col, sw=1.8)
        s.line(tx(hi), y - 6, tx(hi), y + 6, stroke=col, sw=1.8)
        s.circle(tx(e), y, 6.5, fill=col, stroke=col, sw=1.0)
        s.text(tx(lo), y - 14, verdict, size=10, fill=col, weight="700")

    xaxis(s, 190, 672, 262, [-5, 0, 5, 10], tx, ["−5", "0", "+5", "+10"])
    s.text(440, 294, "害の増加（ポイント、右ほど悪い）", size=10, fill=SUB,
           anchor="middle")
    s.text(52, 326, "margin は結果を見た後でなく、設計のときに置く", size=11,
           fill=SUB)
    return s


# ---------------------------------------------------------------- 28-1
def fig28_1():
    """28-1 罰し方を替えると、釣り合う場所が動く。

    本文の停止時間 1, 1, 1, 101 秒。二乗誤差の最小は平均26、
    絶対誤差の最小は中央値1。同じデータでも目的関数で答えが変わる。

    グリッド
      tx(θ) = lin(150, 690, -4, 110) / 各損失は自分の最大値で正規化して 高さ150
      y  32 タイトル / 56 副題 / 258 底辺 / 276 目盛り / 300 観測 / 326 結論
      色  青＝二乗誤差（谷は平均26） / 橙＝絶対誤差（谷は中央値1） / 灰＝観測点
    """
    data = [1, 1, 1, 101]
    mean = sum(data) / len(data)
    med = 1.0
    assert mean == 26.0
    assert sum(abs(v - med) for v in data) < sum(abs(v - mean) for v in data)
    assert (sum((v - mean) ** 2 for v in data)
            < sum((v - med) ** 2 for v in data))

    def sq(t):
        return sum((v - t) ** 2 for v in data)

    def ab(t):
        return sum(abs(v - t) for v in data)

    s = SVG(760, 348, "同じ四つの観測でも、罰し方を替えると釣り合う場所が動く")
    tx = lin(150, 690, -4, 110)
    s.text(52, 32, "推定量は道具の名前ではなく、何を罰するかという設計",
           size=14, weight="700")
    s.text(52, 54, "停止時間 1・1・1・101 秒", size=10, fill=SUB)

    for f, col, lab, best, dy, dxx in ((sq, MAIN, "二乗誤差", mean, -18, 14),
                                       (ab, FOCUS, "絶対誤差", med, 26, -14)):
        top = max(f(-4), f(110))
        pts = []
        t = -4.0
        while t <= 110.001:
            pts.append((tx(t), 258 - 150 * f(t) / top))
            t += 0.5
        polyline(s, pts, stroke=col, sw=2.4)
        s.circle(tx(best), 258 - 150 * f(best) / top, 6.5, fill=col,
                 stroke=col, sw=1.0)
        s.text(tx(best) + dxx, 258 - 150 * f(best) / top + dy,
               "%sの谷 → %g" % (lab, best), size=12, fill=col, weight="700",
               anchor="start" if dxx > 0 else "end")
    s.line(150, 258, 700, 258, stroke=SUB, sw=1.2, cap="butt")
    for v in set(data):
        tri_up(s, tx(v), 250, 6, fill=INK)
    s.text(tx(1), 302, "観測 1（三つ）", size=10, fill=SUB, anchor="middle")
    s.text(tx(101), 302, "観測 101", size=10, fill=SUB, anchor="middle")

    xaxis(s, 140, 700, 258, [25, 50, 75], tx, ["25", "50", "75"])
    s.text(420, 330,
           "101秒が入力ミスか本物の危険故障かで、どちらの谷を選ぶかが変わる",
           size=11, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- 29-1
def fig29_1():
    """29-1 支配される案を消し、重みを置けるなら平均し、置けないなら最悪を守る。

    本文の三案。P=(1,9)、Q=(4,4)、R=(5,7)。
    R はどちらの状態でも Q より損失が大きく、支配されている。
    同確率なら Q（平均4）、状態1が90%なら P（平均1.8）。最悪損失なら Q（4）。

    グリッド（縦横で1単位の長さをそろえた損失平面）
      lx(状態1の損失) = lin(180, 500, 0, 10) / ly(状態2の損失) = lin(300, 60, 0, 10)
      P → (212, 84) / Q → (308, 204) / R → (340, 132)
      y  32 タイトル / 56 副題 / 320 軸ラベル / 各案の注記は点の脇
      色  青＝残る候補 / 赤＝支配されて落ちる案 / 橙＝重みの置き方で変わる勝者
    """
    plans = {"P": (1.0, 9.0), "Q": (4.0, 4.0), "R": (5.0, 7.0)}
    assert plans["Q"][0] < plans["R"][0] and plans["Q"][1] < plans["R"][1]
    eq = {k: (v[0] + v[1]) / 2 for k, v in plans.items()}
    w9 = {k: 0.9 * v[0] + 0.1 * v[1] for k, v in plans.items()}
    worst = {k: max(v) for k, v in plans.items()}
    assert min(eq, key=eq.get) == "Q" and abs(eq["Q"] - 4.0) < 1e-12
    assert min(w9, key=w9.get) == "P" and abs(w9["P"] - 1.8) < 1e-12
    assert min(worst, key=worst.get) == "Q"

    s = SVG(760, 348, "支配される案を落としてから、重みか最悪かで選び分ける")
    lx = lin(180, 500, 0, 10)
    ly = lin(300, 60, 0, 10)
    s.text(52, 32, "同じ三案でも、置いた重みと守る最悪で勝者が入れ替わる",
           size=14, weight="700")
    s.text(52, 54, "軸はそれぞれの状態で受ける損失（小さいほど良い）",
           size=10, fill=SUB)

    # Q が支配する領域
    s.rect(lx(4.0), 60, 500 - lx(4.0), ly(4.0) - 60,
           fill=TINT_WARN, stroke="none", sw=0)
    s.text(lx(7.4), ly(9.2), "Q に支配される領域", size=10, fill=WARN,
           anchor="middle")

    for name, (a, b) in plans.items():
        col = WARN if name == "R" else MAIN
        s.circle(lx(a), ly(b), 8, fill=col, stroke=col, sw=1.0)
        s.text(lx(a) + 14, ly(b) + 5, "%s (%g, %g)" % (name, a, b), size=13,
               fill=col, weight="700")
    s.text(lx(5.0) + 14, ly(7.0) + 22, "Q に全状態で負ける（落選）",
           size=10, fill=WARN)

    xaxis(s, 170, 512, 300, [0, 5, 10], lx, ["0", "5", "10"])
    s.text(340, 328, "状態1での損失", size=10, fill=SUB, anchor="middle")
    yaxis(s, 300, 60, 180, [0, 5, 10], ly, ["0", "5", "10"])
    s.text(146, 76, "状態2での損失", size=10, fill=SUB)

    s.text(534, 100, "同じ確率で平均するなら", size=11, fill=INK, weight="700")
    s.text(534, 118, "P 5.0 ／ Q 4.0 ／ R 6.0 → Q", size=11, fill=FOCUS,
           weight="700")
    s.text(534, 152, "状態1が90%だと信じるなら", size=11, fill=INK,
           weight="700")
    s.text(534, 170, "P 1.8 ／ Q 4.0 ／ R 5.2 → P", size=11, fill=FOCUS,
           weight="700")
    s.text(534, 204, "重みを置けないなら最悪で", size=11, fill=INK,
           weight="700")
    s.text(534, 222, "P 9 ／ Q 4 ／ R 7 → Q", size=11, fill=FOCUS,
           weight="700")
    s.text(534, 256, "順番は「落とす → 平均する", size=10, fill=SUB)
    s.text(534, 270, "または最悪を守る」", size=10, fill=SUB)
    return s


FIGS = {
    "fig1-2-same-mean": fig1_2,
    "fig25-1-loss-threshold": fig25_1,
    "fig25-4-burst": fig25_4,
    "fig27-5-two-intervals": fig27_5,
    "fig27-7-equivalence-margin": fig27_7,
    "fig28-1-m-estimation": fig28_1,
    "fig29-1-minimax": fig29_1,
    "fig23-1-prior-strength": fig23_1,
    "fig23-2-partial-pooling": fig23_2,
    "fig24-1-simpson": fig24_1,
    "fig24-2-collider": fig24_2,
    "fig20-1-markov-doors": fig20_1,
    "fig20-3-kalman-update": fig20_3,
    "fig21-1-missing-mechanism": fig21_1,
    "fig21-3-kaplan-meier": fig21_3,
    "fig22-1-aic-bic": fig22_1,
    "fig22-2-cross-validation": fig22_2,
    "fig15-3-three-tests": fig15_3,
    "fig16-4-ridge-lasso": fig16_4,
    "fig17-1-link-function": fig17_1,
    "fig17-3-overdispersion": fig17_3,
    "fig19-1-pca-units": fig19_1,
    "fig10-1-margins-fixed": fig10_1,
    "fig10-3-jacobian": fig10_3,
    "fig11-2-minimum-order": fig11_2,
    "fig12-1-convergence": fig12_1,
    "fig12-3-delta-method": fig12_3,
    "fig13-2-boundary-mle": fig13_2,
    "fig15-2-likelihood-ratio": fig15_2,
    "fig5-1-two-levels": fig5_1,
    "fig6-2-coverage": fig6_2,
    "fig7-1-two-errors": fig7_1,
    "fig8-1-leverage": fig8_1,
    "fig8-2-collinearity": fig8_2,
    "fig9-2-blocking": fig9_2,
    "fig1-3-same-margins": fig1_3,
    "fig2-1-weighted-mean": fig2_1,
    "fig3-2-base-rate": fig3_2,
    "fig3-3-expected-value": fig3_3,
    "fig4-1-poisson-observed": fig4_1,
}


def main(argv):
    check = "--check" in argv
    only = None
    for i, a in enumerate(argv):
        if a == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
    out = Path(tempfile.mkdtemp()) if check else OUT_DIR
    diff = []
    for name, build in sorted(FIGS.items()):
        if only and only not in name:
            continue
        path = build().save(out / ("%s.svg" % name))
        if check:
            cur = OUT_DIR / ("%s.svg" % name)
            if not cur.exists() or not filecmp.cmp(cur, path, shallow=False):
                diff.append(name)
    if check:
        shutil.rmtree(out)
        if diff:
            print("差分あり: " + ", ".join(diff))
            return 1
        print("既存の図と一致")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
