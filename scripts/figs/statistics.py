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


FIGS = {
    "fig1-2-same-mean": fig1_2, "fig1-3-same-margins": fig1_3, "fig2-1-weighted-mean": fig2_1,
    "fig3-2-base-rate": fig3_2, "fig3-3-expected-value": fig3_3, "fig4-1-poisson-observed": fig4_1,
    "fig5-1-two-levels": fig5_1, "fig6-2-coverage": fig6_2, "fig7-1-two-errors": fig7_1,
    "fig8-1-leverage": fig8_1, "fig8-2-collinearity": fig8_2, "fig9-2-blocking": fig9_2,
}

if __name__ == "__main__":
    sys.exit(build({out(k): v for k, v in FIGS.items()}))
