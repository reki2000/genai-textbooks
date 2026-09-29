#!/usr/bin/env python3
"""statistics シリーズ（statistics / statistics-2 / statistics-3）の図。

色：青=観測・推定の主役／橙=注目点（平均・閾値・問い）／赤=誤り・破綻。
灰は背景・比較対象・目盛。出力先は図番号の幕で巻へ振り分ける（out）。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

BOOKS = Path(__file__).resolve().parents[2] / "docs/books"


def out(name):
    """図番号の幕（fig12-3 なら12）で巻を決める。1〜9幕は1巻、10〜24幕は2巻、25幕以降は3巻。"""
    act = int(name[3:].split("-")[0])
    book = "statistics" if act <= 9 else "statistics-2" if act <= 24 else "statistics-3"
    return BOOKS / book / "figs" / f"{name}.svg"


def lin(a0, a1, v0, v1):
    return lambda v: a0 + (v - v0) / (v1 - v0) * (a1 - a0)


def xaxis(s, X, y, ticks, fmt=str, label=None, x_label=None):
    s.line(X(ticks[0]), y, X(ticks[-1]), y, stroke=MUTED)
    for t in ticks:
        s.line(X(t), y, X(t), y + 5, stroke=MUTED)
        s.text(X(t), y + 22, fmt(t), size=14, fill=SUB, anchor="middle")
    if label:
        s.text(x_label if x_label else (X(ticks[0]) + X(ticks[-1])) / 2, y + 46, label, size=15,
               fill=SUB, anchor="middle")


def npdf(x, mu, sd):
    return math.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))


def ncdf(x, mu=0.0, sd=1.0):
    return 0.5 * (1 + math.erf((x - mu) / (sd * math.sqrt(2))))


def poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def lcg(seed):
    state = [seed]

    def nxt():
        state[0] = (1103515245 * state[0] + 12345) % (2 ** 31)
        return state[0] / float(2 ** 31)
    return nxt


def normals(seed, k):
    r, zs = lcg(seed), []
    while len(zs) < k:
        u1, u2 = r(), r()
        rr = math.sqrt(-2.0 * math.log(max(u1, 1e-12)))
        zs += [rr * math.cos(2 * math.pi * u2), rr * math.sin(2 * math.pi * u2)]
    return zs[:k]


def fit(pts):
    k = len(pts)
    mx, my = sum(x for x, _ in pts) / k, sum(y for _, y in pts) / k
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return b, my - b * mx


# ================================================================ 第1巻
def fig1_2():
    """1-2 同じ平均3,000円でも、Aは一か所に固まりBは両端へ割れる。横長 M 600x340。

    x: 0円 → 60、10,000円 → 560。A の行 y=150、B の行 y=240。A の拡大枠は右上。
    """
    A = [2800, 2900, 3000, 3100, 3200]
    B = [0, 0, 1000, 4000, 10000]
    assert sum(A) / 5 == sum(B) / 5 == 3000 and sorted(B)[2] == 1000
    s = SVG(600, 340, "同じ平均3,000円でも、Aは3,000円の近くに固まり、Bは0円と1万円へ割れる")
    X = lin(60, 560, 0, 10000)
    xaxis(s, X, 280, [0, 2000, 4000, 6000, 8000, 10000], lambda v: f"{v:,}", "希望価格（円）")
    for y, name in ((150, "A"), (240, "B")):
        s.text(24, y + 6, name, size=18, bold=True)
        s.line(X(0), y, X(10000), y, stroke=MUTED, dash="2 4")
        s.poly([(X(3000), y + 12), (X(3000) - 8, y + 26), (X(3000) + 8, y + 26)], fill=FOCUS,
               stroke="none", closed=True)
    seen = {}
    for v in B:
        k = seen.get(v, 0)
        seen[v] = k + 1
        s.circle(X(v), 240 - 18 * k, 8, fill=MAIN, stroke="#ffffff", sw=1.5)
    for v in A:
        s.circle(X(v), 150, 4, fill=MAIN, stroke="none")
    s.text(X(3000) + 14, 176, "平均 3,000", size=14, fill=FOCUS, bold=True)
    s.line(X(1000), 222, X(1000), 256, stroke=INK, sw=2)
    s.text(X(1000) + 8, 214, "中央値 1,000", size=14)
    Z = lin(360, 560, 2700, 3300)
    s.zoom((X(2650), 140, X(3350) - X(2650), 20), (330, 24, 250, 80))
    for v in A:
        s.circle(Z(v), 52, 7, fill=MAIN, stroke="#ffffff", sw=1.5)
    for v in (2800, 3000, 3200):
        s.text(Z(v), 88, f"{v:,}", size=13, fill=SUB, anchor="middle")
    s.note(40, 44, ["平均は同じ", "形はまるで違う"])
    return s


def fig1_3():
    """1-3 列ごとの分布が同じでも、組を替えると点は逆向きに走る。対照の2枚 横長 M 640x330。

    パネル k の左端 x0 = 70 + 300*k、幅 230。時間 5..25分、価格 1,000..3,000円。
    軸の外側に各列の分布（白丸）を置く。両パネルで同じ。
    """
    t = [5, 10, 15, 20, 25]
    p = [1000, 1500, 2000, 2500, 3000]
    s = SVG(640, 346, "列ごとの分布は同じでも、組を替えると散布図は右上がりから右下がりに変わる")
    for k, (title, pp) in enumerate((("一つ目の組", p), ("二つ目の組", p[::-1]))):
        x0 = 70 + 300 * k
        X = lin(x0 + 20, x0 + 210, 5, 25)
        Y = lin(240, 70, 1000, 3000)
        s.text(x0, 36, title, size=16, bold=True)
        s.rect(x0, 60, 230, 190, stroke=MUTED)
        for v in t:
            s.circle(X(v), 272, 5, fill="#ffffff", stroke=SUB, sw=1.4)
        for v in p:
            s.circle(x0 - 16, Y(v), 5, fill="#ffffff", stroke=SUB, sw=1.4)
        s.poly([(X(a), Y(b)) for a, b in zip(t, pp)], stroke=MAIN, sw=1.2, dash="4 4")
        for a, b in zip(t, pp):
            s.circle(X(a), Y(b), 8, fill=MAIN, stroke="#ffffff", sw=1.5)
    s.text(320, 302, "横：遊んだ時間　縦：希望価格　白丸：各列の値（二枚で同じ）", size=13,
           fill=SUB, anchor="middle")
    s.note(230, 332, "列は同じ。組だけが違う")
    return s


def fig2_1():
    """2-1 幅を人口比、高さを購入希望率にすると、市場全体は面積の平均34%。正方 S 460x400。

    x: 人口比 0 → 70、1 → 430。y: 0% → 330、100% → 50。
    """
    w_mem, r_mem, r_gen = 0.1, 0.7, 0.3
    total = w_mem * r_mem + (1 - w_mem) * r_gen
    assert abs(total - 0.34) < 1e-12
    s = SVG(460, 400, "会員10%・希望率70%と一般90%・希望率30%を人口比で重み付けすると、市場全体は34%")
    X = lin(70, 430, 0, 1)
    Y = lin(330, 60, 0, 0.8)
    s.rect(X(0), Y(r_mem), X(w_mem) - X(0), Y(0) - Y(r_mem), fill=TINT[FOCUS], stroke=FOCUS, sw=2)
    s.rect(X(w_mem), Y(r_gen), X(1) - X(w_mem), Y(0) - Y(r_gen), fill=TINT[MAIN], stroke=MAIN, sw=2)
    s.line(X(0), Y(total), X(1), Y(total), stroke=MAIN, sw=3, dash="8 5")
    s.text(X(1) - 4, Y(total) - 10, "市場全体 34%", size=16, fill=MAIN, anchor="end", bold=True)
    s.text(X(0.55), Y(0.15), "一般家庭 30%", size=15, anchor="middle")
    s.text(X(0), Y(r_mem) - 10, "会員 70%", size=15, bold=True)
    for v in (0, 0.4, 0.8):
        s.text(X(0) - 8, Y(v) + 5, f"{v:.0%}", size=14, fill=SUB, anchor="end")
    s.line(X(0), Y(0), X(1), Y(0), stroke=MUTED)
    s.text(X(0.05), Y(0) + 22, "10%", size=14, fill=SUB, anchor="middle")
    s.text(X(0.55), Y(0) + 22, "90%", size=14, fill=SUB, anchor="middle")
    s.text(X(0.5), 382, "幅：人口に占める割合　高さ：購入希望率", size=14, fill=SUB, anchor="middle")
    s.note(X(w_mem) + 20, Y(0.62), ["会員を1万人集めても", "左の細い柱が精密になるだけ"], color=FOCUS)
    return s


def fig3_2():
    """3-2 同じ検査機でも、故障率1%と50%では警報の意味が変わる。横長 M 620x330。

    行 k（故障率1%／50%）：入口の帯 y = 70 + 140*k、警報箱の帯 y = 110 + 140*k。
    帯は幅 400（x 180..580）を割合で分ける。
    """
    sens, fpr = 0.9, 0.05
    s = SVG(620, 330, "故障率1%の工場では警報のうち故障は15%、故障率50%の修理工場では95%")
    X = lin(180, 580, 0, 1)
    for k, prior in enumerate((0.01, 0.5)):
        y = 60 + 140 * k
        tp, fp = prior * sens, (1 - prior) * fpr
        post = tp / (tp + fp)
        s.text(24, y - 18, f"故障率 {prior:.0%} の場所", size=16, bold=True)
        s.text(170, y + 20, "入口", size=15, fill=SUB, anchor="end")
        s.rect(X(0), y, X(prior) - X(0), 28, fill=MAIN, stroke="none")
        s.rect(X(prior), y, X(1) - X(prior), 28, fill=TINT[MUTED], stroke=MUTED)
        s.text(170, y + 60, "警報箱", size=15, fill=INK, anchor="end", bold=True)
        s.rect(X(0), y + 40, X(post) - X(0), 32, fill=MAIN, stroke="none")
        s.rect(X(post), y + 40, X(1) - X(post), 32, fill=s.hatch(WARN), stroke=WARN)
        s.text(X(post / 2) if post > 0.3 else X(post) + 8, y + 62, f"故障 {post:.0%}", size=16,
               fill="#ffffff" if post > 0.3 else MAIN, anchor="middle" if post > 0.3 else "start",
               bold=True)
        if post < 0.5:
            s.text(X(0.62), y + 62, "正常品の誤警報", size=14, fill=WARN, anchor="middle", bold=True,
                   halo=True)
        assert abs(post - (0.154 if k == 0 else 0.947)) < 0.001
    s.text(X(1), 318, "青：故障品　灰：正常品　斜線：正常品への誤警報", size=13, fill=SUB, anchor="end")
    return s


def fig3_3():
    """3-3 重りの置き方が違っても、支点（期待値）は同じ800円。揺れ（標準偏差）は違う。
    小さな多数 3段、横長 M 600x420。x: 0円 → 210、10,000円 → 560。段 k の梁 y = 100 + 120*k。
    """
    plans = [("案A：毎回800円", [(0.8, 1.0)]),
             ("見積もり", [(0, 0.80), (2, 0.15), (10, 0.05)]),
             ("案B", [(0, 0.92), (10, 0.08)])]
    s = SVG(600, 420, "3つの費用計画は期待値がどれも800円だが、標準偏差は0円、約2,230円、約2,710円と違う")
    X = lin(210, 560, 0, 10)
    for k, (name, dist) in enumerate(plans):
        y = 100 + 120 * k
        mu = sum(v * p for v, p in dist)
        sd = math.sqrt(sum(v * v * p for v, p in dist) - mu ** 2)
        assert abs(mu - 0.8) < 1e-9
        s.text(24, y - 30, name, size=15, bold=True)
        s.text(24, y - 8, f"標準偏差 約{round(sd * 1000, -1):,.0f}円", size=14,
               fill=MAIN if sd > 0 else SUB, bold=sd > 2.5, halo=True)
        s.line(X(0), y, X(10), y, stroke=INK, sw=3)
        s.poly([(X(mu), y + 3), (X(mu) - 11, y + 22), (X(mu) + 11, y + 22)], fill=FOCUS,
               stroke="none", closed=True)
        for v, p in dist:
            r = 26 * math.sqrt(p)
            s.circle(X(v), y - r - 2, r, fill=TINT[MAIN], stroke=MAIN, sw=1.6)
            s.text(X(v) + r + 6, y - r + 3, f"{p:.0%}", size=13, fill=SUB)
    s.text(X(0.8) + 18, 120, "支点 ＝ 期待値 800円（3本とも同じ）", size=14, fill=FOCUS, bold=True)
    xaxis(s, X, 372, [0, 2, 4, 6, 8, 10], lambda v: f"{v * 1000:,}", None)
    return s


GAO = [0, 1, 2, 5, 1, 3, 0, 2, 4, 2]


def fig4_1():
    """4-1 十時間の実測と、平均2のポアソン分布。0回は理論13.5%に対し実測20%。
    横長 M 640x330。左 x 40..260 は時間順、右 x 330..620 は回数ごとの割合。
    """
    lam = sum(GAO) / len(GAO)
    assert lam == 2 and abs(poisson(0, 2) - 0.1353) < 1e-3
    s = SVG(640, 330, "十時間の実測と平均2のポアソン分布。0回の割合は理論13.5%、実測20%")
    s.text(24, 36, "時間順の記録", size=15, bold=True)
    Xt = lin(50, 250, 1, 10)
    Yc = lin(250, 80, 0, 5)
    for i, c in enumerate(GAO):
        x = Xt(i + 1)
        s.line(x, Yc(0), x, Yc(c), stroke=MAIN, sw=3)
        s.circle(x, Yc(c), 6, fill=FOCUS if c == 0 else MAIN, stroke="#ffffff", sw=1.5)
    s.line(Xt(1) - 10, Yc(0), Xt(10) + 10, Yc(0), stroke=MUTED)
    for v in (0, 5):
        s.text(Xt(1) - 18, Yc(v) + 5, str(v), size=14, fill=SUB, anchor="end")
    s.text(150, 276, "1〜10時間目", size=14, fill=SUB, anchor="middle")
    s.text(310, 36, "回数ごとの割合", size=15, bold=True)
    Xk = lin(350, 610, 0, 6)
    Yp = lin(250, 80, 0, 0.3)
    for k in range(7):
        th = poisson(k, lam)
        ob = GAO.count(k) / len(GAO)
        x = Xk(k)
        s.rect(x - 14, Yp(th), 28, Yp(0) - Yp(th), fill=TINT[MUTED], stroke=MUTED)
        if ob:
            s.line(x - 20, Yp(ob), x + 20, Yp(ob), stroke=FOCUS if k == 0 else MAIN, sw=4)
        s.text(x, 276, str(k), size=14, fill=SUB, anchor="middle")
    s.line(Xk(0) - 24, Yp(0), Xk(6) + 24, Yp(0), stroke=MUTED)
    s.text(Xk(3), 300, "1時間に鳴いた回数", size=14, fill=SUB, anchor="middle")
    s.text(Xk(4), 90, "灰の柱：理論", size=14, fill=SUB)
    s.text(Xk(4), 112, "横棒：実測", size=14, fill=MAIN)
    s.note(40, 314, "0回：理論 13.5% に対し実測 20%（十回だけの揺れ）")
    return s


def fig5_1():
    """5-1 個体の散らばりと、推定値の散らばりは階層が違う。縦長 M 520x560。

    上段（推定値）：標本比率の分布 x = lin(60, 460, 0.45, 0.79)、山の底 y=220。
    下段（個体）：1回の調査の100人を 20x5 の格子（y 360..460）。
    """
    p, n = 0.62, 100
    se = math.sqrt(p * (1 - p) / n)
    s = SVG(520, 560, "一回の調査の100人の違いが標準偏差、調査を繰り返したときの比率の揺れが標準誤差")
    X = lin(60, 460, 0.45, 0.79)
    Y = lambda d: 220 - d / npdf(p, p, se) * 150
    s.text(24, 34, "調査を繰り返したときの比率（推定値の散らばり）", size=15, bold=True)
    pts = [(X(v), Y(npdf(v, p, se))) for v in [0.45 + i * 0.34 / 120 for i in range(121)]]
    s.poly(pts, stroke=MAIN, sw=3)
    s.line(X(0.45), 220, X(0.79), 220, stroke=MUTED)
    for v in (0.5, 0.6, 0.7):
        s.text(X(v), 242, f"{v:.0%}", size=14, fill=SUB, anchor="middle")
    s.line(X(p - se), Y(npdf(p - se, p, se)), X(p + se), Y(npdf(p + se, p, se)), stroke=FOCUS, sw=3)
    s.text(X(p + se) + 8, Y(npdf(p + se, p, se)) + 4, "標準誤差 約4.9ポイント", size=14,
           fill=FOCUS, bold=True)
    for v in (0.57, 0.62, 0.66):
        s.circle(X(v), 220, 6, fill=FOCUS, stroke="#ffffff", sw=1.5)
    s.text(X(0.57), 266, "57", size=14, fill=FOCUS, anchor="middle")
    s.text(X(0.62), 266, "62", size=14, fill=FOCUS, anchor="middle")
    s.text(X(0.66), 266, "66", size=14, fill=FOCUS, anchor="middle")
    s.text(24, 330, "一回の調査の100人（個体の散らばり）", size=15, bold=True)
    for i in range(100):
        cx, cy = 60 + (i % 20) * 21, 360 + (i // 20) * 22
        yes = i < 62
        s.circle(cx, cy, 7, fill=MAIN if yes else "#ffffff", stroke=MAIN if yes else MUTED, sw=1.4)
    s.text(24, 490, "塗り：買いたい 62人　白：買わない 38人", size=14, fill=SUB)
    s.arrow(X(0.62), 350, X(0.62), 278, stroke=FOCUS, sw=2)
    s.note(24, 536, "カメラを向ける階層が違う")
    return s


def fig6_2():
    """6-2 動くのは網（区間）で、杭（真値62%）は固定。20本中19本が杭を覆う。
    縦長 M 480x560。x = lin(80, 440, 0.42, 0.84)、i 本目 y = 70 + 22*i。
    """
    p, n = 0.62, 100
    se = math.sqrt(p * (1 - p) / n)
    rows = []
    for z in normals(6, 20):
        ph = p + z * se
        half = 1.96 * math.sqrt(ph * (1 - ph) / n)
        rows.append((ph, ph - half, ph + half))
    miss = [i for i, (_, lo, hi) in enumerate(rows) if not lo <= p <= hi]
    assert len(miss) == 1
    s = SVG(480, 560, "同じ手順で作り直した20本の95%信頼区間のうち、19本が固定した真値62%を覆う")
    X = lin(80, 440, 0.42, 0.84)
    s.line(X(p), 52, X(p), 510, stroke=FOCUS, sw=2.4, dash="7 4")
    s.text(X(p), 40, "真の率 62%（固定）", size=15, fill=FOCUS, anchor="middle", bold=True)
    for i, (ph, lo, hi) in enumerate(rows):
        y = 70 + 22 * i
        col = WARN if i in miss else MAIN
        s.line(X(lo), y, X(hi), y, stroke=col, sw=3)
        s.circle(X(ph), y, 4, fill=col, stroke="none")
        s.text(60, y + 5, str(i + 1), size=13, fill=SUB, anchor="end")
        if i in miss:
            s.text(X(hi) + 10, y + 5, "外れた1本", size=14, fill=WARN, bold=True)
    xaxis(s, X, 520, [0.45, 0.55, 0.65, 0.75], lambda v: f"{v:.0%}")
    return s


def two_curves(s, y0, h, X, thr, alpha, beta):
    """7-1 の1パネル。H0（灰）と真の世界（青）の2つの山、閾値の右が棄却域。"""
    p0, p1, n = 0.5, 0.62, 100
    sd0, sd1 = math.sqrt(p0 * (1 - p0) / n), math.sqrt(p1 * (1 - p1) / n)
    peak = npdf(p0, p0, sd0)
    Y = lambda d: y0 + h - d / peak * (h - 20)
    xs = [0.3 + i * 0.5 / 200 for i in range(201)]
    s.poly([(X(thr), y0 + h)] + [(X(v), Y(npdf(v, p0, sd0))) for v in xs if v >= thr] +
           [(X(0.8), y0 + h)], fill=WARN, stroke="none", closed=True)
    s.poly([(X(0.3), y0 + h)] + [(X(v), Y(npdf(v, p1, sd1))) for v in xs if v <= thr] +
           [(X(thr), y0 + h)], fill=s.hatch(MAIN), stroke="none", closed=True)
    s.poly([(X(v), Y(npdf(v, p0, sd0))) for v in xs], stroke=SUB, sw=2)
    s.poly([(X(v), Y(npdf(v, p1, sd1))) for v in xs], stroke=MAIN, sw=3)
    s.line(X(0.3), y0 + h, X(0.8), y0 + h, stroke=MUTED)
    s.line(X(thr), y0 + 4, X(thr), y0 + h, stroke=FOCUS, sw=2.4)
    s.text(X(thr) + 8, y0 + 18, "境界", size=14, fill=FOCUS, bold=True)
    s.text(X(0.7) + 6, y0 + h - 30, f"誤発売 {alpha:.0%}", size=15, fill=WARN, bold=True)
    s.text(X(0.45) - 6, y0 + h - 30, f"見逃し {beta:.0%}", size=15, fill=MAIN, bold=True,
           anchor="end")


def fig7_1():
    """7-1 境界を右へ動かすと誤発売は5%→1%へ減り、見逃しは22%→47%へ増える。
    縦長 M 540x520。2パネルを上下に、x は共通 lin(50, 510, 0.3, 0.8)。
    """
    p0, p1, n = 0.5, 0.62, 100
    sd0, sd1 = math.sqrt(p0 * (1 - p0) / n), math.sqrt(p1 * (1 - p1) / n)
    s = SVG(540, 520, "境界を右へ動かすと誤発売は5%から1%へ減るが、見逃しは22%から47%へ増える")
    X = lin(50, 510, 0.3, 0.8)
    for k, (a, z) in enumerate(((0.05, 1.645), (0.01, 2.326))):
        thr = p0 + z * sd0
        beta = ncdf(thr, p1, sd1)
        assert abs(beta - (0.22 if k == 0 else 0.47)) < 0.01
        y0 = 50 + 210 * k
        s.text(24, y0 - 12, f"有意水準 {a:.0%}", size=16, bold=True)
        two_curves(s, y0, 170, X, thr, a, beta)
    xaxis(s, X, 434, [0.4, 0.5, 0.6, 0.7], lambda v: f"{v:.0%}", "100人中の購入希望率")
    s.text(X(0.5), 58, "基準50%の世界", size=14, fill=SUB, anchor="middle")
    s.text(X(0.62) + 34, 72, "真の率62%の世界", size=14, fill=MAIN)
    return s


def fig8_1():
    """8-1 残差の大きさと、傾きを回す力は別。対照の2枚 横長 M 640x340。

    もとの5点は y=x+1 上。左は (3,8)、右は (12,9) を足す。
    パネル k の x0 = 60 + 300*k、幅 250。x 0..13、y 0..14。
    """
    base = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    s = SVG(640, 340, "線から遠い点は傾きを変えず、横の端の点は残差が小さいのに傾きを回す")
    for k, (pt, title) in enumerate((((3, 8), "線から遠い一点"), ((12, 9), "横の端の一点"))):
        b, a = fit(base + [pt])
        res = pt[1] - (a + b * pt[0])
        x0 = 60 + 300 * k
        X = lin(x0, x0 + 250, 0, 13)
        Y = lin(270, 70, 0, 14)
        s.text(x0, 40, title, size=16, bold=True)
        s.rect(x0, 60, 250, 210, stroke=MUTED)
        s.line(X(0), Y(1), X(13), Y(14), stroke=MUTED, sw=2, dash="5 4")
        s.line(X(0), Y(a), X(13), Y(a + b * 13), stroke=FOCUS, sw=3)
        for x, y in base:
            s.circle(X(x), Y(y), 6, fill=MAIN, stroke="#ffffff", sw=1.5)
        s.line(X(pt[0]), Y(pt[1]), X(pt[0]), Y(a + b * pt[0]), stroke=WARN, sw=2)
        s.circle(X(pt[0]), Y(pt[1]), 8, fill=FOCUS, stroke="#ffffff", sw=1.5)
        s.text(x0 + 125, 298, f"残差 {res:+.2f}　傾き 1 → {b:.2f}", size=15, anchor="middle",
               bold=True, fill=WARN if abs(b - 1) > 0.1 else INK)
    s.text(320, 330, "灰の破線：もとの5点の線　橙：一点を足した後の線", size=13, fill=SUB, anchor="middle")
    return s


def fig8_2():
    """8-2 人口をそろえると広告費がほとんど動かず、二本の坂を分けられない。正方 M 540x440。

    x: 人口 5..70万人 → 80..500、y: 広告費 0..40 → 360..60。
    """
    pops = [10, 15, 20, 25, 30, 36, 38, 44, 49, 54, 60, 65]
    offs = [0.8, -0.6, 1.0, -0.9, 0.5, -0.4, 0.4, -1.0, 0.6, -0.7, 1.1, -0.5]
    ads = [round(p * 0.5 + o, 2) for p, o in zip(pops, offs)]
    band = [a for p, a in zip(pops, ads) if 35 <= p <= 39]
    inner, outer = max(band) - min(band), max(ads) - min(ads)
    assert round(inner, 1) == 1.8 and round(outer, 1) == 26.2
    s = SVG(540, 440, "人口をそろえた地域では広告費が1.8しか動かず、全体の広がり26.2と桁が違う")
    X = lin(80, 500, 5, 70)
    Y = lin(360, 60, 0, 40)
    s.rect(X(35), Y(40), X(39) - X(35), Y(0) - Y(40), fill=TINT[FOCUS], stroke=FOCUS, dash="5 3")
    s.text(X(37), Y(40) - 10, "人口をそろえた地域", size=14, fill=FOCUS, anchor="middle", bold=True)
    for p, a in zip(pops, ads):
        s.circle(X(p), Y(a), 7, fill=MAIN, stroke="#ffffff", sw=1.5)
    s.line(X(39) + 16, Y(max(band)), X(39) + 16, Y(min(band)), stroke=FOCUS, sw=3)
    s.text(X(39) + 24, Y(min(band)) + 20, "1.8", size=15, fill=FOCUS, bold=True)
    s.line(X(70) - 6, Y(max(ads)), X(70) - 6, Y(min(ads)), stroke=MAIN, sw=3)
    s.text(X(70) - 14, Y(min(ads)) + 4, "26.2", size=15, fill=MAIN, bold=True, anchor="end")
    xaxis(s, X, 370, [10, 20, 30, 40, 50, 60, 70], str, "人口（万人）")
    s.line(X(5), Y(0), X(5), Y(40), stroke=MUTED)
    for v in (0, 20, 40):
        s.text(X(5) - 8, Y(v) + 5, str(v), size=14, fill=SUB, anchor="end")
    s.text(24, 40, "広告費（万円）", size=15, fill=SUB)
    s.note(X(5) + 14, Y(34), ["片方だけ動いた地域が", "ほとんど無い"])
    return s


def fig9_2():
    """9-2 同じ引き出しにA/Bが両方あるかを、人数より先に見る。対照の2枚 横長 M 600x320。

    パネル k の左上 x0 = 120 + 250*k。マス 100x80、行=時間帯、列=電池。
    """
    s = SVG(600, 320, "左は対角の2マスしか埋まらず機種差を分けられない。右はどのマスにもAとBがある")
    cells = [
        ("いまの配置", {(0, 0): "AAA", (1, 1): "BBB"}),
        ("無作為化とブロック", {(0, 0): "AB", (0, 1): "BA", (1, 0): "AB", (1, 1): "BA"}),
    ]
    for k, (title, fill) in enumerate(cells):
        x0 = 120 + 250 * k
        s.text(x0, 40, title, size=16, bold=True)
        for c, lab in enumerate(("新品電池", "再利用")):
            s.text(x0 + 50 + 100 * c, 70, lab, size=14, fill=SUB, anchor="middle")
        for r in range(2):
            if k == 0:
                s.text(x0 - 12, 124 + 80 * r, ("午前", "午後")[r], size=14, fill=SUB, anchor="end")
            for c in range(2):
                x, y = x0 + 100 * c, 84 + 80 * r
                tok = fill.get((r, c), "")
                s.rect(x, y, 100, 80, fill=TINT[MUTED] if not tok else "#ffffff", stroke=MUTED)
                for j, t in enumerate(tok):
                    cx = x + 50 + (j - (len(tok) - 1) / 2) * 26
                    col = MAIN if t == "A" else FOCUS
                    s.circle(cx, y + 40, 11, fill=col, stroke="#ffffff", sw=1.5)
                    s.text(cx, y + 45.5, t, size=14, fill="#ffffff", anchor="middle", bold=True)
    s.text(170, 276, "空のマス：比べる相手がいない", size=14, fill=WARN, anchor="middle")
    s.note(370, 290, "どのマスにもAとB")
    return s


# ================================================================ 第2巻
def binom(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def panel_axes(s, x0, y0, w, h):
    s.line(x0, y0 + h, x0 + w, y0 + h, stroke=MUTED)
    s.line(x0, y0, x0, y0 + h, stroke=MUTED)


def fig10_1():
    """10-1 行和も列和も同じ二店舗が、まったく違う四箱を持つ。対照の2枚 横長 M 600x330。

    表 k の左上 x0 = 110 + 270*k, y0 = 80。セル 80x56。右と下に周辺（灰）。
    """
    tabs = {"店舗A": [[20, 30], [0, 50]], "店舗B": [[10, 40], [10, 40]]}
    for t in tabs.values():
        assert [sum(r) for r in t] == [50, 50] and [t[0][j] + t[1][j] for j in (0, 1)] == [20, 80]
    s = SVG(600, 330, "行和も列和も同じ二店舗でも、会員の返品率はAが40%、Bが20%と違う")
    for k, (name, t) in enumerate(tabs.items()):
        x0, y0 = 110 + 270 * k, 80
        s.text(x0, 40, name, size=16, bold=True)
        for j, lab in enumerate(("返品", "非返品")):
            s.text(x0 + 40 + 80 * j, y0 - 10, lab, size=14, fill=SUB, anchor="middle")
        for i, lab in enumerate(("会員", "非会員")):
            if k == 0:
                s.text(x0 - 10, y0 + 34 + 56 * i, lab, size=14, fill=SUB, anchor="end")
            for j in range(2):
                v = t[i][j]
                f = i == 0 and j == 0
                s.rect(x0 + 80 * j, y0 + 56 * i, 80, 56, fill=TINT[FOCUS] if f else "#ffffff",
                       stroke=FOCUS if f else MUTED, sw=2 if f else 1)
                s.text(x0 + 40 + 80 * j, y0 + 35 + 56 * i, str(v), size=20, anchor="middle",
                       bold=f, fill=INK)
            s.text(x0 + 176, y0 + 34 + 56 * i, str(sum(t[i])), size=15, fill=SUB, anchor="middle")
        for j in range(2):
            s.text(x0 + 40 + 80 * j, y0 + 136, str(t[0][j] + t[1][j]), size=15, fill=SUB,
                   anchor="middle")
        s.note(x0, y0 + 190, f"会員の返品率 {t[0][0] * 2}%")
    s.text(300, 316, "灰の数字（行和・列和）は二店舗で同じ", size=13, fill=SUB, anchor="middle")
    return s


def fig10_3():
    """10-3 座標を横2倍・縦3倍に伸ばしたら、密度は1/6へ薄める。横長 M 560x280。

    1単位 = 60px。元の正方形 x 60..120 / y 220..160、先の長方形 x 260..380 / y 220..40。
    どちらも4x4の方眼。左下から2列目・2行目のマスを橙にする。
    """
    assert 2 * 3 == 6 and abs((1 / 6) * 6 - 1) < 1e-12 and abs((1 / 6) * 3 - 0.5) < 1e-12
    s = SVG(560, 280, "座標を横2倍・縦3倍に伸ばすと面積は6倍になるので、密度は1から1/6へ薄める")

    def grid(x0, y0, w, h, fill):
        s.rect(x0, y0 - h, w, h, fill=fill, stroke=MAIN, sw=2)
        for i in range(1, 4):
            s.line(x0 + w * i / 4, y0 - h, x0 + w * i / 4, y0, stroke=MAIN, sw=0.8)
            s.line(x0, y0 - h * i / 4, x0 + w, y0 - h * i / 4, stroke=MAIN, sw=0.8)
        s.rect(x0 + w / 4, y0 - h / 2, w / 4, h / 4, fill=FOCUS, stroke=FOCUS)
    grid(60, 220, 60, 60, TINT[MAIN])
    grid(260, 220, 120, 180, "#f5f8fd")
    s.text(90, 148, "元：面積1", size=15, anchor="middle")
    s.text(90, 246, "密度 1", size=16, anchor="middle", bold=True, fill=MAIN)
    s.text(320, 28, "先：面積6", size=15, anchor="middle")
    s.text(320, 246, "密度 1/6", size=16, anchor="middle", bold=True, fill=MAIN)
    s.arrow(140, 190, 240, 190, stroke=SUB, sw=2)
    s.text(190, 178, "横2倍・縦3倍", size=14, fill=SUB, anchor="middle")
    s.note(400, 90, ["橙の一マスは", "元でも先でも", "確率 1/16"])
    return s


def weibull_fit():
    lo, hi = 1.0, 6.0
    for _ in range(200):
        k = (lo + hi) / 2
        eta = 210.0 / (-math.log(0.98)) ** (1.0 / k)
        if eta * math.gamma(1 + 1.0 / k) > 1000.0:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    return k, 210.0 / (-math.log(0.98)) ** (1.0 / k)


def fig11_2():
    """11-2 台数を増やすほど、最初の故障は早い側へ動く。最小値の累積分布。横長 M 600x340。

    x: 0時間 → 80、1,500時間 → 560。y: 0 → 280、1 → 60。
    """
    k, eta = weibull_fit()
    assert abs(eta * math.gamma(1 + 1 / k) - 1000) < 1
    s = SVG(600, 340, "210時間までに最初の故障が起きる確率は、1台なら2%、10台なら18%、100台なら87%")
    X = lin(80, 560, 0, 1500)
    Y = lin(280, 60, 0, 1)
    cdf = lambda t, n: 1 - math.exp(-n * (t / eta) ** k)
    s.line(X(210), Y(0), X(210), Y(1.04), stroke=FOCUS, sw=2, dash="6 4")
    s.text(X(210) + 6, Y(1.04) + 4, "210時間", size=14, fill=FOCUS, bold=True)
    for n, col, sw in ((1, MUTED, 2), (10, MAIN, 2), (100, MAIN, 3.5)):
        pts = [(X(t), Y(cdf(t, n))) for t in range(0, 1501, 10)]
        s.poly(pts, stroke=col, sw=sw)
        v = cdf(210, n)
        assert abs(v - (1 - 0.98 ** n)) < 1e-3
        s.circle(X(210), Y(v), 6, fill=FOCUS, stroke="#ffffff", sw=1.5)
        s.text(X(210) - 10, Y(v) + 5, f"{v:.0%}", size=15, anchor="end", bold=True, fill=FOCUS)
        lx = {1: 900, 10: 470, 100: 300}[n]
        s.text(X(lx) + 8, Y(cdf(lx, n)) + 18, f"{n}台の最小", size=15, fill=SUB if n == 1 else MAIN,
               bold=n == 100)
    xaxis(s, X, 280, [0, 500, 1000, 1500], lambda v: f"{v:,}", "時間")
    for v in (0, 0.5, 1):
        s.text(X(0) - 8, Y(v) + 5, f"{v:.0%}", size=14, fill=SUB, anchor="end")
    s.text(24, 36, "最初の故障がそれまでに起きる確率", size=15, fill=SUB)
    return s


def fig12_1():
    """12-1 山が0へ潰れる収束と、山が変わらない収束。2x2 の小さな多数 M 640x460。

    列 k の左端 x0 = 90 + 290*k、幅 250。上段 軌跡 y 60..200（0 は y=130）、下段 分布 y 280..400。
    """
    zs = normals(11, 120)
    shrink = [zs[i] / math.sqrt(i + 1) for i in range(60)]
    stay = zs[60:120]
    assert abs(shrink[59]) < 0.5 and max(abs(v) for v in stay[40:]) > 0.8
    s = SVG(640, 460, "Z/√n は軌跡も分布も0へ潰れるが、毎回引き直す標準正規は分布が変わらず軌跡も落ち着かない")
    for k, (title, seq, sd) in enumerate((("Z / √n：0へ確率収束", shrink, 1 / math.sqrt(60)),
                                          ("毎回引き直す Z：分布だけ一定", stay, 1.0))):
        x0 = 90 + 290 * k
        X = lin(x0, x0 + 250, 1, 60)
        Y = lin(130, 60, 0, 3)
        s.text(x0, 34, title, size=15, bold=True)
        s.line(x0, 130, x0 + 250, 130, stroke=MUTED)
        s.poly([(X(i + 1), Y(max(-3, min(3, v)))) for i, v in enumerate(seq)], stroke=MAIN, sw=2)
        s.text(x0, 220, "n = 1", size=13, fill=SUB)
        s.text(x0 + 250, 220, "n = 60", size=13, fill=SUB, anchor="end")
        Xv = lin(x0, x0 + 250, -3.2, 3.2)
        peak = npdf(0, 0, 1 / math.sqrt(60))
        pts = [(Xv(v), 400 - npdf(v, 0, sd) / peak * 110) for v in [-3.2 + i * 0.04 for i in range(161)]]
        s.poly(pts, stroke=FOCUS, sw=3)
        s.line(x0, 400, x0 + 250, 400, stroke=MUTED)
        s.text(Xv(0), 422, "0", size=14, fill=SUB, anchor="middle")
    s.text(24, 134, "軌跡", size=14, fill=SUB)
    s.text(24, 360, "分布", size=14, fill=SUB)
    s.text(320, 250, "上：一人を追った軌跡　下：n=60 での値の分布", size=13, fill=SUB, anchor="middle")
    return s


def fig12_3():
    """12-3 同じ0.01の入力の揺れでも、曲線の急な場所では出力が大きく伸びる。正方 M 540x440。

    x: p 0.3 → 80、0.95 → 500。y: オッズ 0 → 380、14 → 60。
    """
    odds = lambda p: p / (1 - p)
    slope = lambda p: 1 / (1 - p) ** 2
    assert abs(odds(0.51) - odds(0.5) - 0.0408) < 1e-3 and abs(odds(0.91) - odds(0.9) - 1.111) < 1e-3
    s = SVG(540, 440, "入力の揺れ0.01は、p=0.5では出力0.04に、p=0.9では1.00に伸びる")
    X = lin(80, 500, 0.3, 0.95)
    Y = lin(380, 60, 0, 14)
    s.poly([(X(p), Y(odds(p))) for p in [0.3 + i * 0.0025 for i in range(254)]], stroke=MAIN, sw=3)
    for p in (0.5, 0.9):
        g = slope(p)
        d = 0.06
        s.line(X(p - d), Y(odds(p) - g * d), X(p + d), Y(odds(p) + g * d), stroke=FOCUS, sw=2,
               dash="5 4")
        h = g * 0.01
        s.rect(X(p) - 5, Y(odds(p) + h / 2), 10, max(2, Y(odds(p) - h / 2) - Y(odds(p) + h / 2)),
               fill=FOCUS, stroke="none")
        s.circle(X(p), Y(odds(p)), 5, fill=INK, stroke="#ffffff", sw=1.5)
        s.text(X(p) - 14, Y(odds(p)) - 16, f"傾き {g:.0f}：出力幅 {h:.2f}", size=15, anchor="end",
               bold=True, fill=FOCUS)
    xaxis(s, X, 380, [0.3, 0.5, 0.7, 0.9], lambda v: f"{v:.1f}", "p")
    for v in (0, 5, 10):
        s.text(X(0.3) - 8, Y(v) + 5, str(v), size=14, fill=SUB, anchor="end")
    s.text(24, 40, "オッズ p/(1−p)", size=15, fill=SUB)
    s.note(96, 110, ["同じ入力幅 0.01 が", "25倍違う出力幅になる"])
    return s


def fig13_2():
    """13-2 一様分布の尤度は境界 θ=6 で最大になり、微分0では拾えない。横長 M 580x320。

    x: θ 3 → 80、14 → 540。y: 尤度（最大で正規化）0 → 260、1 → 70。
    """
    obs = [2, 4, 6]
    lik = lambda th: 0.0 if th < max(obs) else th ** -3
    top = lik(6)
    assert 2 * sum(obs) / 3 == 8
    s = SVG(580, 320, "θが6より小さいと観測6が出ないので尤度は0、θ=6の縁で最大になる")
    X = lin(80, 540, 3, 14)
    Y = lin(260, 70, 0, 1)
    s.rect(X(3), Y(1.05), X(6) - X(3), Y(0) - Y(1.05), fill=s.hatch(WARN), stroke="none")
    s.text((X(3) + X(6)) / 2, Y(0.5), "6を出せない", size=15, fill=WARN, anchor="middle", bold=True,
           halo=True)
    s.poly([(X(3), Y(0)), (X(6), Y(0)), (X(6), Y(1))] +
           [(X(t), Y(lik(t) / top)) for t in [6 + i * 0.05 for i in range(161)]], stroke=MAIN, sw=3)
    s.circle(X(6), Y(1), 7, fill=FOCUS, stroke="#ffffff", sw=1.5)
    s.text(X(6) + 12, Y(1) + 5, "最尤 θ = 6（崖の縁）", size=15, fill=FOCUS, bold=True)
    s.line(X(8), Y(0), X(8), Y(lik(8) / top), stroke=SUB, dash="4 3")
    s.text(X(8) + 6, Y(lik(8) / top) - 8, "モーメント法 8", size=14, fill=SUB)
    xaxis(s, X, 260, [4, 6, 8, 10, 12, 14], str, "θ")
    s.text(24, 40, "尤度", size=15, fill=SUB)
    return s


def fig15_2():
    """15-2 尤度比の大きい結果から棄却域へ入れる。横長 M 600x420。

    結果 k（0,1,2人）の中心 x = 260 + 130*k。柱の底 y=240、高さ = 確率*170。
    下に棄却域の2案を帯で（名前と結果は左、帯は各結果の下）。
    """
    h0 = [binom(k, 2, 0.1) for k in range(3)]
    h1 = [binom(k, 2, 0.6) for k in range(3)]
    lr = [b / a for a, b in zip(h0, h1)]
    assert abs(h0[1] + h0[2] - 0.19) < 1e-9 and abs(h1[1] + h1[2] - 0.84) < 1e-9
    assert abs(h0[0] + h0[2] - 0.82) < 1e-9
    s = SVG(600, 420, "尤度比の大きい1人・2人を棄却域にすれば誤報19%で検出力84%、左右対称の0人・2人では誤報82%")
    for k in range(3):
        x = 260 + 130 * k
        s.rect(x - 38, 240 - h0[k] * 170, 34, h0[k] * 170, fill=TINT[MUTED], stroke=MUTED)
        s.rect(x + 4, 240 - h1[k] * 170, 34, h1[k] * 170, fill=MAIN, stroke="none")
        s.text(x, 264, f"{k}人購入", size=15, anchor="middle")
        s.text(x, 48, f"尤度比 {lr[k]:.2f}" if k < 2 else "尤度比 36", size=15, anchor="middle",
               bold=True, fill=FOCUS)
    s.line(200, 240, 580, 240, stroke=MUTED)
    s.text(24, 150, "灰：H0（p=0.1）", size=14, fill=SUB)
    s.text(24, 172, "青：H1（p=0.6）", size=14, fill=MAIN)
    s.text(24, 202, "高さ：確率", size=14, fill=SUB)
    for r, (name, ks, col, res) in enumerate((("尤度比順", (1, 2), MAIN, "誤報19%・検出力84%"),
                                              ("左右対称", (0, 2), WARN, "誤報82%（予算超過）"))):
        y = 300 + 56 * r
        s.text(24, y + 8, name, size=15, bold=True, fill=col)
        s.text(24, y + 30, res, size=14, bold=True, fill=col)
        for k in ks:
            s.rect(260 + 130 * k - 50, y, 100, 28, rx=4, fill=TINT[col], stroke=col, sw=2)
            s.text(260 + 130 * k, y + 20, "棄却", size=14, fill=col, anchor="middle", bold=True)
    return s


def fig15_3():
    """15-3 同じ対数尤度の山を、高さ・距離・旗での傾きの三方向から測る。正方 M 560x460。

    x: p 0.3 → 70、0.9 → 530。y: 対数尤度（頂上からの差）0 → 120、4 → 330。
    """
    n, x, p0 = 20, 13, 0.5
    ph = x / n
    ll = lambda p: x * math.log(p) + (n - x) * math.log(1 - p)
    lr = 2 * (ll(ph) - ll(p0))
    wald = (ph - p0) ** 2 / (ph * (1 - ph) / n)
    score = (x / p0 - (n - x) / (1 - p0)) ** 2 / (n / (p0 * (1 - p0)))
    assert (round(lr, 2), round(wald, 2), round(score, 2)) == (1.83, 1.98, 1.8)
    s = SVG(560, 460, "20人中13人の対数尤度の山を、高さの差・頂上までの距離・旗での傾きで測ると1.83・1.98・1.80")
    X = lin(70, 530, 0.3, 0.9)
    Y = lin(120, 330, 0, 4)
    top = ll(ph)
    s.poly([(X(p), Y(top - ll(p))) for p in [0.3 + i * 0.005 for i in range(121)] if top - ll(p) <= 4.2],
           stroke=MAIN, sw=3)
    fx, fy = X(p0), Y(top - ll(p0))
    sx, sy = X(ph), Y(0)
    # 1 高さ：旗の高さを右へ延ばし、頂上の右で縦に測る
    s.line(fx, fy, sx + 70, fy, stroke=MUTED, dash="4 3")
    s.line(sx, sy, sx + 70, sy, stroke=MUTED, dash="4 3")
    s.line(sx + 60, sy, sx + 60, fy, stroke=INK, sw=2.4)
    s.badge(sx + 36, (sy + fy) / 2, 1)
    # 2 距離：頂上の上で横に測る
    s.line(fx, sy - 36, (fx + sx) / 2 - 16, sy - 36, stroke=INK, sw=2.4)
    s.line((fx + sx) / 2 + 16, sy - 36, sx, sy - 36, stroke=INK, sw=2.4)
    s.line(fx, sy - 44, fx, sy - 28, stroke=INK, sw=2)
    s.line(sx, sy - 44, sx, sy - 28, stroke=INK, sw=2)
    s.badge((fx + sx) / 2, sy - 36, 2)
    # 3 傾き：旗での接線
    g = x / p0 - (n - x) / (1 - p0)
    d = 0.08
    dy = Y(g * d) - Y(0)
    s.line(X(p0 - d), fy + dy, X(p0 + d), fy - dy, stroke=FOCUS, sw=2.4)
    s.badge(X(p0 - d) - 18, fy + dy, 3)
    s.circle(sx, sy, 7, fill=MUTED, stroke="#ffffff", sw=1.5)
    s.text(sx - 12, sy + 34, "頂上 0.65", size=14, fill=SUB, anchor="end")
    s.circle(fx, fy, 7, fill=FOCUS, stroke="#ffffff", sw=1.5)
    s.text(fx + 12, fy + 26, "旗：帰無 0.5", size=14, fill=FOCUS, bold=True)
    s.text(40, 380, [f"1 高さの差：尤度比 {lr:.2f}", f"2 頂上までの距離：Wald {wald:.2f}",
                     f"3 旗での傾き：score {score:.2f}"], size=15)
    return s


def fig16_4():
    """16-4 罰則は係数を一意にしても、片方だけ動かす比較を観測済みにはしない。正方 M 520x460。

    縦横同じ縮尺（1単位 125px）。x: b1 -0.6 → 70、2.6 → 470。y: b2 -0.3 → 360、1.3 → 160。
    """
    ridge = (1 / 3, 2 / 3)
    lasso = (0.0, 7 / 8)
    assert abs(ridge[0] + 2 * ridge[1] - 5 / 3) < 1e-12
    s = SVG(520, 460, "無罰則で同じ予測を返す係数の組は直線上に並び、ridgeは(0.33,0.67)、lassoは(0,0.875)を選ぶ")
    X = lin(70, 470, -0.6, 2.6)
    Y = lin(360, 160, -0.3, 1.3)
    s.line(X(-0.6), Y(0), X(2.6), Y(0), stroke=MUTED)
    s.line(X(0), Y(-0.3), X(0), Y(1.3), stroke=MUTED)
    rr = math.hypot(*ridge)
    s.poly([(X(rr * math.cos(t / 36 * math.pi)), Y(rr * math.sin(t / 36 * math.pi))) for t in range(0, 37)],
           stroke=MAIN, sw=1.4, dash="4 3")
    r = lasso[1]
    s.poly([(X(-0.6), Y(r - 0.6)), (X(0), Y(r)), (X(r), Y(0)), (X(r + 0.3), Y(-0.3))], stroke=FOCUS,
           sw=1.4, dash="4 3")
    s.line(X(2 - 2 * 1.3), Y(1.3), X(2.6), Y(-0.3), stroke=WARN, sw=3.5)
    s.text(X(1.45), Y(0.62), "同じ予測を返す組", size=15, fill=WARN, bold=True)
    s.text(X(1.45), Y(0.62) + 20, "b1 + 2b2 = 2", size=14, fill=WARN)
    s.circle(X(ridge[0]), Y(ridge[1]), 8, fill=MAIN, stroke="#ffffff", sw=2)
    s.text(X(ridge[0]) - 14, Y(ridge[1]) + 28, "ridge (0.33, 0.67)", size=15, fill=MAIN, bold=True,
           anchor="end", halo=True)
    s.circle(X(lasso[0]), Y(lasso[1]), 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(X(lasso[0]) + 12, Y(lasso[1]) - 8, "lasso (0, 0.875)", size=15, fill=FOCUS, bold=True)
    xaxis(s, X, 360, [-0.5, 0, 0.5, 1, 1.5, 2, 2.5], lambda v: f"{v:g}", "b1（テレビ）")
    s.text(24, 150, "b2（総広告費）", size=15, fill=SUB)
    s.text(24, 440, "破線：ridge と lasso の罰則が等しい線（円と菱形）", size=13, fill=SUB)
    s.note(24, 50, ["罰則が一点を選んだだけで、", "片方だけ動かしたデータは増えていない"])
    return s


def fig17_1():
    """17-1 直線を平均へ直接置くと範囲を飛び出す。扉（リンク）を挟めば範囲に収まる。
    対照の2枚 横長 M 640x340。パネル k の x0 = 70 + 300*k、幅 240、y 60..260。
    """
    s = SVG(640, 340, "恒等リンクの直線は件数で−3件、確率で120%へ飛び出すが、logとlogitの扉を通せば範囲に収まる")
    # 件数：直線 y = -3 + 2.5x、log リンクは (2,2) と (8,17) を通る指数曲線
    d = (math.log(17) - math.log(2)) / 6
    c = math.log(2) - 2 * d
    X = lin(70, 310, 0, 9)
    Y = lin(260, 60, -5, 22)
    s.text(70, 36, "件数の部屋", size=16, bold=True)
    s.rect(70, Y(0), 240, Y(-5) - Y(0), fill=s.hatch(MUTED), stroke="none")
    s.line(70, Y(0), 310, Y(0), stroke=INK, sw=1.4)
    s.poly([(X(v), Y(-3 + 2.5 * v)) for v in (0, 9.5 * 0.9)], stroke=WARN, sw=3)
    s.poly([(X(v / 10), Y(math.exp(c + d * v / 10))) for v in range(0, 86)], stroke=MAIN, sw=3)
    s.circle(X(0), Y(-3), 6, fill=WARN, stroke="#ffffff", sw=1.5)
    s.text(X(0) + 12, Y(-3) + 5, "−3件", size=15, fill=WARN, bold=True)
    s.text(X(6.4), Y(16), "log の扉", size=15, fill=MAIN, bold=True, anchor="end")
    s.text(X(4.5), 284, "広告費", size=14, fill=SUB, anchor="middle")
    # 確率：直線 y = 0.1 x、logit 曲線
    X2 = lin(370, 610, 0, 12)
    Y2 = lin(260, 60, -0.1, 1.35)
    s.text(370, 36, "確率の部屋", size=16, bold=True)
    s.rect(370, Y2(1.35), 240, Y2(1) - Y2(1.35), fill=s.hatch(MUTED), stroke="none")
    s.line(370, Y2(1), 610, Y2(1), stroke=INK, sw=1.4)
    s.line(370, Y2(0), 610, Y2(0), stroke=INK, sw=1.4)
    s.poly([(X2(0), Y2(0)), (X2(12), Y2(1.2))], stroke=WARN, sw=3)
    s.poly([(X2(v / 10), Y2(1 / (1 + math.exp(-(v / 10 - 6) * 0.9)))) for v in range(0, 121)],
           stroke=MAIN, sw=3)
    s.circle(X2(12), Y2(1.2), 6, fill=WARN, stroke="#ffffff", sw=1.5)
    s.text(X2(12) - 10, Y2(1.2) + 5, "120%", size=15, fill=WARN, bold=True, anchor="end")
    s.text(X2(9), Y2(0.62), "logit の扉", size=15, fill=MAIN, bold=True)
    s.text(X2(6), 284, "説明変数", size=14, fill=SUB, anchor="middle")
    s.text(320, 326, "斜線：その応答が取れない範囲　赤：恒等リンクの直線", size=13, fill=SUB, anchor="middle")
    return s


def fig17_3():
    """17-3 平均10件でも、分散50なら95%上側は15件でなく24件。横長 M 600x340。

    x: 件数 0 → 70、32 → 550。y: 確率 0 → 260、0.13 → 60。
    """
    mu, var = 10.0, 50.0
    r = mu ** 2 / (var - mu)
    pp = r / (r + mu)
    nb = lambda k: math.exp(math.lgamma(k + r) - math.lgamma(k + 1) - math.lgamma(r) +
                            r * math.log(pp) + k * math.log(1 - pp))

    def upper(f):
        acc = 0.0
        for k in range(400):
            acc += f(k)
            if acc >= 0.95:
                return k
    up_p, up_n = upper(lambda k: poisson(k, mu)), upper(nb)
    assert (up_p, up_n) == (15, 24)
    s = SVG(600, 340, "どちらも平均10件だが、95%上側はPoissonで15件、分散50の分布で24件")
    X = lin(70, 550, 0, 32)
    Y = lin(260, 60, 0, 0.13)
    for k in range(33):
        s.rect(X(k) - 5, Y(poisson(k, mu)), 10, Y(0) - Y(poisson(k, mu)), fill=TINT[MUTED], stroke=MUTED,
               sw=0.8)
    s.poly([(X(k), Y(nb(k))) for k in range(33)], stroke=MAIN, sw=3)
    for k, col, lab in ((up_p, SUB, "Poisson 上側 15件"), (up_n, FOCUS, "分散50 上側 24件")):
        s.line(X(k), Y(0), X(k), Y(0.1), stroke=col, sw=2.4, dash="6 4")
        s.text(X(k) + 6, Y(0.1) - (18 if k == up_p else 0), lab, size=15, fill=col, bold=True)
    s.text(X(18), Y(0.06), "灰の柱：Poisson（分散10）", size=14, fill=SUB)
    s.text(X(18), Y(0.06) + 22, "青の線：平均10・分散50", size=14, fill=MAIN)
    xaxis(s, X, 260, [0, 10, 20, 30], str, "一日の問い合わせ件数")
    return s


PCA_PTS = [(1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 3), (4, 5), (5, 4)]


def fig19_1():
    """19-1 点は動いていないのに、単位を替えると第一主成分が倒れる。正方 S 460x460。

    縦横同じ縮尺：1単位 = 70px。x: 価格 0.4 → 70、5.6 → 434。y: 満足度 0.4 → 400、5.6 → 36。
    """
    n = len(PCA_PTS)
    mx = sum(p for p, _ in PCA_PTS) / n
    my = sum(q for _, q in PCA_PTS) / n
    vxx = sum((p - mx) ** 2 for p, _ in PCA_PTS) / n
    vxy = sum((p - mx) * (q - my) for p, q in PCA_PTS) / n
    vyy = sum((q - my) ** 2 for _, q in PCA_PTS) / n
    ang_y = 0.5 * math.degrees(math.atan2(2 * 1000 * vxy, vxx * 1e6 - vyy))
    assert (vxx, vxy, vyy) == (1.5, 1.0, 1.5) and ang_y < 0.04
    s = SVG(460, 460, "同じ点群でも、1,000円単位なら第一主成分は45度、円単位ならほぼ水平に倒れる")
    X = lin(70, 434, 0.4, 5.6)
    Y = lin(400, 36, 0.4, 5.6)
    L = 2.6
    s.line(X(mx - L), Y(my - L), X(mx + L), Y(my + L), stroke=MAIN, sw=3)
    s.line(X(mx - L), Y(my), X(mx + L), Y(my), stroke=WARN, sw=3, dash="8 5")
    for p, q in PCA_PTS:
        s.circle(X(p), Y(q), 8, fill=INK, stroke="#ffffff", sw=1.5)
    s.text(X(mx + L) - 4, Y(my + L) + 22, "1,000円単位：45度", size=15, fill=MAIN, bold=True, anchor="end")
    s.text(X(mx + L), Y(my) + 22, "円単位：ほぼ0度", size=15, fill=WARN, bold=True, anchor="end")
    s.text(X(3), 440, "価格", size=15, fill=SUB, anchor="middle")
    s.text(24, 36, "満足度", size=15, fill=SUB)
    return s


def fig20_1():
    """20-1 全体10%が、正常の次5%と障害の次55%という二つの扉を隠す。横長 M 600x340。

    帯：40時間を x 60..540（1時間 12px）、y 60..90。柱：中心 x 150 / 300 / 450、底 y 290、高さ=率*300。
    """
    strip = [0] * 40
    for a in (9, 26):
        strip[a] = strip[a + 1] = 1
    assert sum(strip) / 40 == 0.1
    s = SVG(600, 340, "障害は全体では10%だが、正常の次の時間は5%、障害の次の時間は55%")
    s.text(24, 40, "40時間の記録（赤が障害）", size=15, fill=SUB)
    for i, v in enumerate(strip):
        s.rect(60 + 12 * i, 56, 12, 28, fill=WARN if v else TINT[MUTED], stroke="#ffffff", sw=1)
    for x, rate, lab, col in ((150, 0.10, "全体をならす", MUTED), (300, 0.05, "正常の次", MAIN),
                              (450, 0.55, "障害の次", FOCUS)):
        s.rect(x - 40, 290 - rate * 300, 80, rate * 300, fill=col, stroke="none")
        s.text(x, 290 - rate * 300 - 10, f"{rate:.0%}", size=18, anchor="middle", bold=True,
               fill=INK if col != MUTED else SUB)
        s.text(x, 314, lab, size=15, anchor="middle", fill=INK if col != MUTED else SUB)
    s.line(90, 290, 510, 290, stroke=MUTED)
    s.note(24, 130, "次の1時間が障害になる率")
    return s


def fig20_3():
    """20-3 揺れの大きい証言は軽く、安定した証言は重くして更新する。横長 M 600x360。

    x: 度 -0.8 → 170、7.2 → 570。行 y = 70 + 52*i（予測・3観測）、更新後 y=300。
    横棒の長さは校正での揺れの大小の比較で、数値区間ではない。
    """
    rows = [("予測", 0.05, 0.9, MUTED), ("第一センサー", 5.0, 1.9, MAIN), ("第二センサー", 0.4, 0.7, MAIN),
            ("手持ち計", 0.5, 0.35, MAIN)]
    s = SVG(600, 360, "揺れの大きい第一センサーの5.0度は軽く、手持ち計の0.5度は重く効き、更新後は0.6度")
    X = lin(170, 570, -0.8, 7.2)
    s.line(X(0), 50, X(0), 320, stroke=MUTED, dash="3 4")
    for i, (name, v, e, col) in enumerate(rows):
        y = 70 + 52 * i
        s.text(150, y + 5, name, size=15, anchor="end", fill=SUB if col == MUTED else INK)
        s.line(X(v - e), y, X(v + e), y, stroke=col, sw=10 * 0.35 / e + 1.5)
        s.circle(X(v), y, 6, fill=col, stroke="#ffffff", sw=1.5)
        s.text(X(v + e) + 8, y + 5, f"{v:g}度", size=14, fill=SUB)
    y = 300
    s.text(150, y + 5, "更新後", size=16, anchor="end", bold=True, fill=FOCUS)
    s.line(X(0.6 - 0.45), y, X(0.6 + 0.45), y, stroke=FOCUS, sw=4)
    s.circle(X(0.6), y, 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(X(1.05) + 8, y + 5, "0.6度", size=16, fill=FOCUS, bold=True)
    s.line(160, 272, 580, 272, stroke=MUTED)
    s.text(X(3.2), 346, "横棒が細く長いほど揺れが大きい（重みが軽い）", size=13, fill=SUB, anchor="middle")
    return s


def fig21_1():
    """21-1 同じ8個の空欄でも、どこが抜けたかで平均が変わる。小さな多数 3段 L 720x420。

    x: 枠 0..39 → 120..660。段 r の中心 y0 = 110 + 120*r、温度 35..43 → y0+40..y0-40。
    """
    r = lcg(23)
    temps = [round(38.0 + 2.2 * math.sin(i * 0.42) + (r() - 0.5) * 1.4, 3) for i in range(40)]
    true_mean = sum(temps) / 40
    plans = [("甲：くじで抜ける", [2, 7, 12, 18, 23, 29, 33, 38]),
             ("乙：夜勤の時間に抜ける", [0, 4, 6, 8, 10, 12, 15, 18]),
             ("丙：高温のときに抜ける", sorted(range(40), key=lambda i: -temps[i])[:8])]
    kept = lambda m: sum(t for i, t in enumerate(temps) if i not in m) / 32
    assert kept(plans[2][1]) < true_mean - 0.4 and abs(kept(plans[0][1]) - true_mean) < 0.25
    s = SVG(720, 420, "くじや夜勤で抜けても観測平均はほぼ動かないが、高温だけ抜けると平均が低く見える")
    X = lin(120, 660, 0, 39)
    for k, (name, miss) in enumerate(plans):
        y0 = 110 + 120 * k
        Y = lin(y0 + 40, y0 - 40, 35, 43)
        s.text(24, y0 - 54, name, size=15, bold=True, fill=WARN if k == 2 else INK)
        s.line(X(0), Y(true_mean), X(39), Y(true_mean), stroke=MUTED, dash="4 4")
        m = kept(miss)
        s.line(X(0), Y(m), X(39), Y(m), stroke=FOCUS if k == 2 else MAIN, sw=2)
        for i, t in enumerate(temps):
            if i in miss:
                s.line(X(i) - 5, Y(t) - 5, X(i) + 5, Y(t) + 5, stroke=WARN, sw=2)
                s.line(X(i) - 5, Y(t) + 5, X(i) + 5, Y(t) - 5, stroke=WARN, sw=2)
            else:
                s.circle(X(i), Y(t), 4.5, fill=MAIN, stroke="none")
        s.text(700, y0 - 54, f"観測平均 {m:.1f}度（真 {true_mean:.1f}）", size=14, anchor="end",
               fill=FOCUS if k == 2 else SUB, bold=k == 2)
    s.text(390, 410, "40枠の温度。×が欠測、破線が真の平均、実線が観測できた枠の平均", size=13,
           fill=SUB, anchor="middle")
    return s


def fig21_3():
    """21-3 打切りは階段を下げず、次の段の人数だけを減らす。縦長 M 520x520。

    x: 日 0 → 110、6.6 → 480。上段 追跡線 y = 70 + 32*i、下段 生存曲線 y 320..470（率 0..1）。
    """
    tracks = [(2, "fail"), (3, "censor"), (5, "fail"), (6, "alive"), (6, "alive")]
    surv = [(0, 1.0), (2, 0.8), (5, 0.8 * 2 / 3)]
    assert abs(surv[2][1] - 0.5333) < 1e-3
    s = SVG(520, 520, "3日目の追跡終了では生存率は下がらず危険集合が減るだけ、5日目の故障で0.533へ落ちる")
    X = lin(110, 480, 0, 6.6)
    s.text(24, 40, "5台の追跡", size=15, bold=True)
    for i, (t, kind) in enumerate(tracks):
        y = 70 + 32 * i
        s.text(90, y + 5, f"{i + 1}号", size=14, fill=SUB, anchor="end")
        s.line(X(0), y, X(t), y, stroke=MAIN if kind != "censor" else MUTED, sw=3)
        if kind == "fail":
            s.line(X(t) - 7, y - 7, X(t) + 7, y + 7, stroke=WARN, sw=3)
            s.line(X(t) - 7, y + 7, X(t) + 7, y - 7, stroke=WARN, sw=3)
        elif kind == "censor":
            s.line(X(t), y - 10, X(t), y + 10, stroke=SUB, sw=3)
            s.text(X(t) + 10, y + 5, "追跡終了（打切り）", size=14, fill=SUB)
    for t, n in ((2, 5), (5, 3)):
        s.line(X(t), 50, X(t), 470, stroke=MUTED, dash="3 4")
        s.text(X(t), 250, f"危険集合 {n}台", size=14, fill=FOCUS, anchor="middle", bold=True)
    s.text(24, 300, "生存率", size=15, bold=True)
    Y = lin(470, 320, 0, 1)
    pts = []
    for (t0, v), (t1, _) in zip(surv, surv[1:] + [(6.6, None)]):
        pts += [(X(t0), Y(v)), (X(t1), Y(v))]
    s.poly(pts, stroke=MAIN, sw=3.5)
    for t, v in surv[1:]:
        s.text(X(t) + 8, Y(v) - 8, f"{v:.3g}", size=15, fill=MAIN, bold=True)
    s.line(X(0), 470, X(6.6), 470, stroke=MUTED)
    for d in range(7):
        s.text(X(d), 492, str(d), size=14, fill=SUB, anchor="middle")
    s.text(X(3.3), 514, "日", size=14, fill=SUB, anchor="middle")
    s.note(X(2) + 8, Y(0.8) + 40, ["3日目は下がらない"])
    return s


def fig22_1():
    """22-1 部品代を足すと、尤度で勝った大模型が負ける。正方 M 540x460。

    x: −2logL 84 → 90、116 → 500。y: 部品数 k 0 → 390、13 → 60。
    等AIC線・等BIC線は小模型を通り、左下ほど良い。
    """
    small, large = (100.0, 2), (90.0, 10)
    pen = math.log(100)
    assert small[0] + 2 * small[1] == 104 and large[0] + 2 * large[1] == 110
    s = SVG(540, 460, "小模型を通る等AIC線・等BIC線より大模型は右上にあり、部品代込みではどちらも小模型が勝つ")
    X = lin(90, 500, 84, 116)
    Y = lin(390, 60, 0, 13)
    for slope, col, name in ((2, MAIN, "等AIC（k1つに2）"), (pen, FOCUS, "等BIC（k1つに4.61）")):
        k0, k1 = 0, 2 + 16 / slope
        s.line(X(small[0] - slope * (k0 - small[1])), Y(k0), X(small[0] - slope * (k1 - small[1])), Y(k1),
               stroke=col, sw=2.4)
    s.text(X(small[0] - 2 * 8) + 10, Y(8) + 4, "等AIC（2改善）", size=14, fill=MAIN, bold=True)
    s.text(X(small[0] - pen * 3.5) + 10, Y(3.5) + 4, "等BIC（4.61改善）", size=14, fill=FOCUS, bold=True)
    for (d, k), name in ((small, "小模型"), (large, "大模型")):
        s.circle(X(d), Y(k), 8, fill=INK, stroke="#ffffff", sw=2)
        s.text(X(d) + 12, Y(k) + 5, f"{name}（{d:g}, {k}）", size=15, bold=True)
    xaxis(s, X, 390, [85, 90, 95, 100, 105, 110, 115], str, "−2 log L（小さいほど当てはまる）")
    for v in (0, 5, 10):
        s.text(X(84) - 8, Y(v) + 5, str(v), size=14, fill=SUB, anchor="end")
    s.text(24, 40, "部品数 k", size=15, fill=SUB)
    s.note(X(104), Y(11.6), ["大模型は線の右上", "＝負け"], color=WARN)
    return s


def fig22_2():
    """22-2 同じ5セルを評価へ回しても、何を隠したかで試験の意味が変わる。小さな多数 L 720x330。

    パネル k の左上 x0 = 70 + 220*k, y0 = 90。セル 32x32、5顧客 x 5日。
    """
    rnd = {(0, 2), (1, 4), (2, 1), (3, 3), (4, 0)}
    plans = [("セルを無作為に", lambda i, j: (i, j) in rnd, "同じ顧客の別の日", WARN),
             ("顧客ごとに", lambda i, j: i == 3, "初めて会う顧客", MAIN),
             ("未来の日で", lambda i, j: j == 4, "過去から未来", MAIN)]
    s = SVG(720, 330, "評価へ回すのは同じ5セルでも、セル単位・顧客単位・未来の日で試験の意味が変わる")
    for k, (title, f, meaning, col) in enumerate(plans):
        x0, y0 = 70 + 220 * k, 90
        s.text(x0, 40, title, size=16, bold=True)
        for j, d in enumerate("月火水木金"):
            s.text(x0 + 16 + 32 * j, y0 - 10, d, size=14, fill=SUB, anchor="middle")
        for i in range(5):
            if k == 0:
                s.text(x0 - 10, y0 + 22 + 32 * i, f"客{i + 1}", size=14, fill=SUB, anchor="end")
            for j in range(5):
                hit = f(i, j)
                s.rect(x0 + 32 * j, y0 + 32 * i, 32, 32, fill=FOCUS if hit else TINT[MAIN], stroke="#ffffff",
                       sw=2)
        s.text(x0, y0 + 190, "測れるもの：", size=14, fill=SUB)
        s.text(x0, y0 + 212, meaning, size=15, fill=col, bold=True)
    s.text(360, 324, "橙：評価へ回すセル　青：学習に使うセル", size=13, fill=SUB, anchor="middle")
    return s


def beta_pdf(x, a, b):
    return math.exp((a - 1) * math.log(x) + (b - 1) * math.log(1 - x) - (math.lgamma(a) + math.lgamma(b)
                                                                            - math.lgamma(a + b)))


def fig23_1():
    """23-1 同じ平均2%の事前分布でも、持ち込む強さで事後の位置が変わる。縦長 M 560x480。

    x: θ 0 → 70、0.3 → 530。段 k の底 y = 200 + 200*k、高さ 140（段ごとに最大値で正規化）。
    """
    s = SVG(560, 480, "尤度は同じでも、事前分布の強さ100なら事後平均3.33%、強さ10なら7.33%")
    X = lin(70, 530, 0, 0.3)
    xs = [0.002 + i * 0.298 / 300 for i in range(301)]
    lik = lambda t: t ** 2 * (1 - t) ** 18
    for k, (a, b, strength) in enumerate(((2, 98, 100), (0.2, 9.8, 10))):
        base = 200 + 200 * k
        a1, b1 = a + 2, b + 18
        mean = a1 / (a1 + b1)
        assert abs(mean - (0.0333 if k == 0 else 0.0733)) < 1e-3
        curves = [(lambda t, a=a, b=b: beta_pdf(t, a, b), MUTED, 2),
                  (lik, FOCUS, 2.4), (lambda t, a=a1, b=b1: beta_pdf(t, a, b), MAIN, 3.5)]
        s.text(24, base - 158, f"事前の強さ {strength}", size=16, bold=True)
        for f, col, sw in curves:
            vals = [f(t) for t in xs]
            m = max(vals)
            s.poly([(X(t), base - min(v / m, 1) * 130) for t, v in zip(xs, vals)], stroke=col, sw=sw)
        s.line(X(0), base, X(0.3), base, stroke=MUTED)
        s.line(X(mean), base, X(mean), base - 140, stroke=MAIN, dash="4 3")
        s.text(X(mean) + 6, base - 142, f"事後平均 {mean:.2%}", size=15, fill=MAIN, bold=True)
    for v in (0, 0.1, 0.2, 0.3):
        s.text(X(v), 424, f"{v:.0%}", size=14, fill=SUB, anchor="middle")
    s.text(300, 450, "故障率 θ", size=14, fill=SUB, anchor="middle")
    s.text(24, 472, "灰：事前分布　橙：20台中2台の尤度　青：事後分布", size=13, fill=SUB)
    return s


def fig23_2():
    """23-2 同じ0件でも、分母が違えば共通中心へ引き寄せられる量が違う。正方 M 540x440。

    左の列 x=140（観測）、右の列 x=340（借りた後）。y: 率 0 → 370、0.6 → 70。
    """
    rows = [("A 0/2", 0, 2), ("B 5/10", 5, 10), ("C 50/100", 50, 100), ("D 0/100", 0, 100)]
    post = [(x + 5) / (n + 10) for _, x, n in rows]
    assert abs(post[0] - 0.4167) < 1e-3 and abs(post[3] - 0.0455) < 1e-3
    s = SVG(540, 440, "共通中心50%から同じ量を借りても、2台のAは0%から41.7%へ、100台のDは4.5%までしか動かない")
    Y = lin(370, 70, 0, 0.6)
    s.text(140, 44, "観測", size=15, anchor="middle", bold=True)
    s.text(340, 44, "借りた後", size=15, anchor="middle", bold=True)
    s.text(240, Y(0.5) - 10, "B・C は 50% のまま（共通中心も 50%）", size=13, fill=SUB, anchor="middle")
    for (name, x, n), p in zip(rows, post):
        raw = x / n
        f = name[0] in "AD"
        col = FOCUS if f else MUTED
        s.line(140, Y(raw), 340, Y(p), stroke=col, sw=3 if f else 1.4)
        s.circle(140, Y(raw), 7, fill=col, stroke="#ffffff", sw=1.5)
        s.circle(340, Y(p), 7, fill=MAIN if f else MUTED, stroke="#ffffff", sw=1.5)
        if f:
            s.text(356, Y(p) + 5, f"{name}：{p:.1%}", size=15, bold=True)
    s.text(128, Y(0) + 5, "A・D 0%", size=14, anchor="end", bold=True)
    s.text(128, Y(0.5) + 5, "50%", size=14, anchor="end", fill=SUB)
    s.text(24, 420, "太い2本が同じ0件。分母が小さいほど強く引き寄せられる", size=13, fill=SUB)
    return s


def fig24_1():
    """24-1 どちらの端末型でも更新群が低いのに、合計では更新群が高く見える。傾きグラフ 正方 M 520x440。

    左の列 x=170（更新群）、右の列 x=370（未更新群）。y: 故障率 0 → 380、60% → 80。
    丸の面積は台数に比例（100台で半径 22）。
    """
    groups = {"更新": [("新型", 10, 1), ("旧型", 90, 36)], "未更新": [("新型", 90, 18), ("旧型", 10, 5)]}
    tot = {g: sum(f for _, _, f in r) / sum(n for _, n, _ in r) for g, r in groups.items()}
    assert abs(tot["更新"] - 0.37) < 1e-9 and abs(tot["未更新"] - 0.23) < 1e-9
    s = SVG(520, 440, "新型でも旧型でも更新群が10ポイント低いのに、合計では更新37%対未更新23%で逆転する")
    Y = lin(380, 80, 0, 0.6)
    xs = {"更新": 170, "未更新": 370}
    for g, x in xs.items():
        s.text(x, 44, f"{g}群", size=16, anchor="middle", bold=True)
        s.line(x, Y(0), x, Y(0.6), stroke=MUTED)
    for k, (name, col) in enumerate((("新型", MAIN), ("旧型", SUB))):
        pts = []
        for g, x in xs.items():
            _, n, f = groups[g][k]
            pts.append((x, Y(f / n), n, f / n))
        s.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], stroke=col, sw=2.4)
        for x, y, n, r in pts:
            s.circle(x, y, 22 * math.sqrt(n / 100), fill=TINT[MAIN] if col == MAIN else TINT[MUTED],
                     stroke=col, sw=1.6)
            s.text(x - 30 if x == 170 else x + 30, y + 5, f"{r:.0%}（{n}台）", size=14,
                   anchor="end" if x == 170 else "start", fill=col)
        s.text(270, (pts[0][1] + pts[1][1]) / 2 - 10, f"{name}：上がる", size=15, anchor="middle",
               bold=True, fill=col, halo=True)
    y1, y2 = Y(tot["更新"]), Y(tot["未更新"])
    s.line(170, y1, 370, y2, stroke=WARN, sw=3.5, dash="8 5")
    s.text(270, (y1 + y2) / 2 + 26, "合計：下がる", size=15, anchor="middle", bold=True, fill=WARN, halo=True)
    s.text(140, y1 + 24, "37%", size=15, anchor="end", bold=True, fill=WARN)
    s.text(382, y2 + 5, "23%", size=15, bold=True, fill=WARN)
    for v in (0, 0.3, 0.6):
        s.text(470, Y(v) + 5, f"{v:.0%}", size=13, fill=SUB, anchor="end")
    s.text(24, 424, "縦：故障率　丸の大きさ：台数", size=13, fill=SUB)
    return s


def fig24_2():
    """24-2 入庫者だけを見ると、効果0の更新が故障を半減したように見える。対照の2枚 M 600x340。

    表 k の左上 x0 = 100 + 250*k, y0 = 90。行=更新 X、列=劣化 U、セル 90x70。故障 Y = U。
    """
    s = SVG(600, 310, "全体では更新の有無で故障率は50%どうしだが、入庫者だけにすると100%対50%に見える")
    for k, title in enumerate(("全体", "入庫者だけ")):
        x0, y0 = 100 + 250 * k, 90
        s.text(x0, 40, title, size=16, bold=True)
        s.text(x0 + 196, y0 - 10, "故障率", size=13, fill=SUB)
        for j, lab in enumerate(("劣化なし", "劣化あり")):
            s.text(x0 + 45 + 90 * j, y0 - 10, lab, size=14, fill=SUB, anchor="middle")
        for i, lab in enumerate(("更新なし", "更新あり")):
            if k == 0:
                s.text(x0 - 10, y0 + 40 + 70 * i, lab, size=14, fill=SUB, anchor="end")
            for j in range(2):
                gone = k == 1 and i == 0 and j == 0
                x, y = x0 + 90 * j, y0 + 70 * i
                s.rect(x, y, 90, 70, fill=s.hatch(WARN) if gone else (TINT[WARN] if j else TINT[MAIN]),
                       stroke=MUTED)
                s.text(x + 45, y + 42, "入庫しない" if gone else ("故障" if j else "正常"), size=15,
                       anchor="middle", fill=WARN if gone else INK, bold=gone, halo=gone)
            rate = ["50%", "50%"][i] if k == 0 else ["100%", "50%"][i]
            s.text(x0 + 196, y0 + 42 + 70 * i, rate, size=16, bold=k == 1, fill=FOCUS if k == 1 else SUB)
    s.note(100, 290, "升が一つ消えるだけで、効果0から差が生まれる")
    return s


FIGS2 = {
    "fig10-1-margins-fixed": fig10_1, "fig10-3-jacobian": fig10_3, "fig11-2-minimum-order": fig11_2,
    "fig12-1-convergence": fig12_1, "fig12-3-delta-method": fig12_3, "fig13-2-boundary-mle": fig13_2,
    "fig15-2-likelihood-ratio": fig15_2, "fig15-3-three-tests": fig15_3, "fig16-4-ridge-lasso": fig16_4,
    "fig17-1-link-function": fig17_1, "fig17-3-overdispersion": fig17_3, "fig19-1-pca-units": fig19_1,
    "fig20-1-markov-doors": fig20_1, "fig20-3-kalman-update": fig20_3,
    "fig21-1-missing-mechanism": fig21_1, "fig21-3-kaplan-meier": fig21_3, "fig22-1-aic-bic": fig22_1,
    "fig22-2-cross-validation": fig22_2, "fig23-1-prior-strength": fig23_1,
    "fig23-2-partial-pooling": fig23_2, "fig24-1-simpson": fig24_1, "fig24-2-collider": fig24_2,
}


FIGS = {
    "fig1-2-same-mean": fig1_2, "fig1-3-same-margins": fig1_3, "fig2-1-weighted-mean": fig2_1,
    "fig3-2-base-rate": fig3_2, "fig3-3-expected-value": fig3_3, "fig4-1-poisson-observed": fig4_1,
    "fig5-1-two-levels": fig5_1, "fig6-2-coverage": fig6_2, "fig7-1-two-errors": fig7_1,
    "fig8-1-leverage": fig8_1, "fig8-2-collinearity": fig8_2, "fig9-2-blocking": fig9_2,
}

if __name__ == "__main__":
    sys.exit(build({out(k): v for k, v in {**FIGS, **FIGS2}.items()}))
