#!/usr/bin/env python3
"""modern-cosmology の図。

数値は本文の Planck 2018 の値（h = 0.674、Ωm = 0.315、放射 Ωr h^2 = 4.15e-5、平ら）で計算する。
色：青=本文が確かめた模型（ΛCDM）・バリオン／橙=その図で見る1か所／赤=やる夫の破綻する案。
灰は暗黒物質・目盛・補助の線。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/modern-cosmology/figs"

H = 0.674
OM, OR = 0.315, 4.15e-5 / H ** 2
OL = 1 - OM - OR
T_H = 9.778 / H                                   # 1/H0（10億年）
D_H = 299792.458 / (100 * H) * 3.2616e-3          # c/H0（10億光年）


def E(a, om=OM, ol=OL, orr=OR):
    return math.sqrt(orr / a ** 4 + om / a ** 3 + ol)


def integ(f, lo, hi, n=4000):
    """ln a で等間隔に刻んだ中点則で ∫ f(a) da。"""
    s, L0, L1 = 0.0, math.log(lo), math.log(hi)
    for i in range(n):
        a = math.exp(L0 + (L1 - L0) * (i + 0.5) / n)
        s += f(a) * a * (L1 - L0) / n
    return s


def age(a, **kw):
    """ビッグバンから尺度因子 a までの時間（10億年）。"""
    return integ(lambda x: 1 / (x * E(x, **kw)), 1e-10, a) * T_H


def chi(a0, a1):
    """a0 から a1 までに光が進む共動距離（10億光年）。"""
    return integ(lambda x: 1 / (x * x * E(x)), a0, a1) * D_H


def d_m(z):
    return chi(1 / (1 + z), 1)


def distances():
    """4-2 同じ z の天体に3つの距離。角径距離は z≈1.6 で最大になる。正方 M 560x440。

    x = 70 + z*110（z 0〜4）、y = 390 - 距離(10億光年)*10（0〜32）。
    """
    assert abs(d_m(1) - 11.1) < 0.1 and abs(d_m(1) / 2 - 5.55) < 0.05
    zs = [i / 50 for i in range(201)]
    peak = max(zs[1:], key=lambda z: d_m(z) / (1 + z))
    assert abs(peak - 1.6) < 0.05, peak
    X = lambda z: 70 + z * 110
    Y = lambda d: 390 - d * 10
    s = SVG(560, 440, "同じ天体までの距離は測り方で3つに分かれ、角径距離はz≈1.6で最大になってから減る")
    for d in (10, 20, 30):
        s.line(70, Y(d), 520, Y(d), stroke="#e6e6e6")
        s.text(62, Y(d) + 5, f"{d * 10}億", size=14, fill=SUB, anchor="end")
    for z in (1, 2, 3, 4):
        s.text(X(z), 412, str(z), size=14, fill=SUB, anchor="middle")
    s.line(70, 390, 520, 390, stroke=INK)
    s.line(70, 390, 70, 60, stroke=INK)
    s.text(520, 432, "赤方偏移 z", size=15, fill=SUB, anchor="end")
    s.text(70, 44, "距離（光年）", size=15, fill=SUB)
    dm = {z: d_m(z) for z in zs}
    s.poly([(X(z), Y(dm[z])) for z in zs], stroke=INK, sw=2.4)
    s.text(X(4) + 4, Y(dm[4]) - 8, "共動距離 D_M（今の距離）", size=14, anchor="end")
    lum = [(X(z), Y(dm[z] * (1 + z))) for z in zs if dm[z] * (1 + z) < 33]
    s.poly(lum, stroke=MUTED, sw=2.4, dash="6 4")
    s.text(lum[-1][0] + 6, lum[-1][1] + 10, "光度距離 D_L", size=14, fill=SUB)
    s.poly([(X(z), Y(dm[z] / (1 + z))) for z in zs], stroke=MAIN, sw=3.5)
    s.text(X(3.2), Y(dm[3.2] / 4.2) + 26, "角径距離 D_A（光を出したときの距離）", size=14, fill=MAIN,
           anchor="middle", bold=True)
    s.circle(X(peak), Y(dm[peak] / (1 + peak)), 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.line(X(1), 390, X(1), Y(dm[1] * 2), stroke=MUTED, dash="3 3")
    s.note(X(1.9), Y(12), ["z≈1.6 より遠いと", "かえって大きく見える"])
    return s


def a_of_t(t, **kw):
    """時刻 t（10億年）での尺度因子を二分法で求める。"""
    lo, hi = 1e-8, 50.0
    for _ in range(60):
        m = math.sqrt(lo * hi)
        if age(m, **kw) < t:
            lo = m
        else:
            hi = m
    return math.sqrt(lo * hi)


def horizons():
    """4-3 今見える光は、出たあと一度遠ざかってから近づいてきた。3つの地平線は別の線。横長 L 760x500。

    横：今の距離ではなく、その時刻の実際の距離（10億光年）0〜50、x = 80 + D*13.2。
    縦：ビッグバンからの時刻（10億年）0〜24、y = 450 - t*17。今 t0 = 13.8。
    """
    t0 = age(1)
    assert abs(t0 - 13.8) < 0.05
    X = lambda d: 80 + d * 13.2
    Y = lambda t: 450 - t * 17
    ts = [0.05 * 1.12 ** k for k in range(60) if 0.05 * 1.12 ** k < 24] + [24]
    A = {t: a_of_t(t) for t in ts}
    chi_now = chi(1e-10, 1)
    s = SVG(760, 500, "今届く光は出たあと一度遠ざかってから近づいてきた。ハッブル球、事象地平線、粒子地平線は別の線になる")
    for d in (10, 20, 30, 40, 50):
        s.text(X(d), 474, str(d * 10) + "億", size=14, fill=SUB, anchor="middle")
    for t in (5, 10, 15, 20):
        s.text(72, Y(t) + 5, f"{t * 10}億年", size=14, fill=SUB, anchor="end")
    s.line(80, 450, 740, 450, stroke=INK)
    s.line(80, 450, 80, 40, stroke=INK)
    s.text(740, 494, "その時刻の実際の距離（光年）", size=15, fill=SUB, anchor="end")
    for c in (10, 20, 30, 40):                       # 銀河（共動の点）の道
        pts = [(X(A[t] * c), Y(t)) for t in ts if A[t] * c < 50]
        s.poly(pts, stroke="#dddddd", sw=1)
    s.line(80, Y(t0), 740, Y(t0), stroke=INK, sw=1.2, dash="4 4")
    s.text(X(20), Y(t0) - 8, "今（138億年）", size=15, bold=True)
    hub = [(X(D_H / E(A[t])), Y(t)) for t in ts if D_H / E(A[t]) < 50]
    s.poly(hub, stroke=MUTED, sw=2, dash="7 4")
    hx = X(D_H / E(a_of_t(20)))
    s.text(hx - 10, Y(20), "ハッブル球 c/H", size=14, fill=SUB, anchor="end", halo=True)
    ev = [(X(A[t] * chi(A[t], 1e4)), Y(t)) for t in ts]
    s.poly(ev, stroke=MAIN, sw=2.4)
    s.text(X(a_of_t(20) * chi(a_of_t(20), 1e4)) + 10, Y(20) + 20, "事象地平線", size=15, fill=MAIN,
           bold=True, halo=True)
    par = [(X(A[t] * chi(1e-10, A[t])), Y(t)) for t in ts if A[t] * chi(1e-10, A[t]) < 50]
    s.poly(par, stroke=INK, sw=2.4)
    a10 = a_of_t(10)
    s.text(X(a10 * chi(1e-10, a10)) - 10, Y(10) - 6, "粒子地平線", size=15, anchor="end", bold=True,
           halo=True)
    cone = [(X(A[t] * (chi_now - chi(1e-10, A[t]))), Y(t)) for t in ts if t <= t0]
    cone.append((X(0), Y(t0)))
    s.poly(cone, stroke=FOCUS, sw=4.5)
    tip = max(cone, key=lambda p: p[0])
    s.text(tip[0] + 10, tip[1] + 5, "今届く光の道", size=16, fill=FOCUS, bold=True)
    s.text(X(27), Y(1.2), "灰の細線：銀河の道", size=14, fill=SUB)
    s.note(X(27), Y(5.2), ["光は最初、遠ざかりながら", "こちらへ進んでいた"])
    return s


def bao():
    """6-3 音が止まった場所にバリオンの殻が残り、今の銀河の間隔になる。小さな多数 L 760x270。

    4コマ、各 180x180、左上 (20 + 185*i, 44)、中心 (110 + 185*i, 134)。殻の半径は最大 70 px。
    """
    s = SVG(760, 270, "詰まった場所から広がった音が霧の晴れた時点で止まり、その半径にバリオンの殻が残って今の銀河の間隔になる")
    heads = ["詰まった場所", "音が広がる", "霧が晴れて止まる", "今：中心と殻に銀河"]
    rs = [0, 38, 70, 70]
    for i, (hd, r) in enumerate(zip(heads, rs)):
        cx, cy = 110 + 185 * i, 134
        s.rect(20 + 185 * i, 44, 180, 180, fill="#ffffff", stroke=MUTED)
        s.badge(34 + 185 * i, 24, i + 1)
        s.text(52 + 185 * i, 30, hd, size=15, bold=True)
        s.circle(cx, cy, 16 if i < 3 else 20, fill=TINT[MUTED], stroke=MUTED)
        if i == 0:
            s.circle(cx, cy, 10, fill=MAIN, stroke="none")
        if 0 < i < 3:
            s.circle(cx, cy, r, stroke=MAIN, sw=5)
        if i == 1:
            s.circle(cx, cy, r, stroke=FOCUS, sw=1.4, dash="3 3")
        if i == 2:
            s.circle(cx, cy, r + 12, stroke=FOCUS, sw=1.4, dash="3 3")
        if i == 3:
            s.circle(cx, cy, r, stroke=MAIN, sw=2, dash="5 4")
            for k in range(12):
                t = 2 * math.pi * k / 12 + 0.2
                s.circle(cx + r * math.cos(t), cy + r * math.sin(t), 4, fill=INK, stroke="none")
            for dx, dy in ((0, 0), (8, 5), (-7, 6), (4, -9)):
                s.circle(cx + dx, cy + dy, 4, fill=INK, stroke="none")
            s.line(cx, cy, cx + r, cy, stroke=FOCUS, sw=2.4)
            s.text(cx, 216, "殻の半径 約150 Mpc", size=14, fill=FOCUS, anchor="middle", bold=True,
                   halo=True)
    s.text(20, 252, "灰：暗黒物質（中心に残る）", size=14, fill=SUB)
    s.text(250, 252, "青：バリオン", size=14, fill=MAIN)
    s.text(370, 252, "橙の破線：光子", size=14, fill=FOCUS)
    s.text(740, 252, "模式図", size=14, fill=SUB, anchor="end")
    return s


def comoving_hubble():
    """7-2 共動ハッブル半径が縮む時期があれば、遠い2点は昔一度つながっていた。横長 M 580x400（模式）。

    横 log a、縦 log(c/aH)。傾き：インフレーション -1、放射の時代 +1、物質の時代 +1/2（同じ目盛り）。
    x = 60 + u*460（u 0〜1）、y = 330 - v*260。インフレーション終了 u=0.5、放射→物質 u=0.85、今 u=1。
    """
    X = lambda u: 60 + u * 460
    Y = lambda v: 330 - v * 260
    ue, um = 0.5, 0.85
    v = lambda u: (0.95 - u if u <= ue else
                   0.95 - ue + (u - ue) if u <= um else
                   0.95 - ue + (um - ue) + 0.5 * (u - um))
    k = v(1)                    # 今見えている一番大きな範囲（今の c/aH）
    assert k < v(0)             # インフレーションの始めには、その範囲が連絡できる範囲の内側にあった
    s = SVG(580, 400, "インフレーションで共動ハッブル半径が縮む時期があれば、今は遠い2点も昔一度は連絡できる範囲にあった")
    s.rect(X(0), Y(1.02), X(ue) - X(0), Y(-0.02) - Y(1.02), fill=TINT[FOCUS], stroke="none")
    s.text(X(ue / 2), 390, "インフレーション", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(X((ue + um) / 2), 390, "放射の時代", size=15, fill=SUB, anchor="middle")
    s.text(X((um + 1) / 2), 390, "物質", size=15, fill=SUB, anchor="middle")
    s.line(X(0), Y(0), X(1), Y(0), stroke=INK)
    s.line(X(0), Y(0), X(0), Y(1.05), stroke=INK)
    s.text(X(1), 362, "log a", size=14, fill=SUB, anchor="end")
    s.text(X(0) + 6, Y(1.05) + 4, "連絡できる範囲（共動ハッブル半径 c/aH）", size=14, fill=SUB)
    us = [i / 200 for i in range(201)]
    s.poly([(X(u), Y(v(u))) for u in us], stroke=MAIN, sw=3.5)
    s.line(X(0), Y(k), X(1), Y(k), stroke=INK, sw=1.6, dash="6 4")
    s.text(X(1) - 4, Y(k) - 10, "今見える一番大きな範囲", size=14, anchor="end")
    u_out = 0.95 - k
    u_in = 1.0
    s.circle(X(u_out), Y(k), 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.circle(X(u_in), Y(k), 7, fill=INK, stroke="#ffffff", sw=2)
    s.text(X(0.16), Y(k) - 12, "範囲の外へ出る", size=14, fill=FOCUS, bold=True)
    s.text(X(u_in) - 8, Y(k) + 26, "今また入ってくる", size=14, anchor="end")
    s.note(X(0.62), Y(0.3), ["縮む時期に一度", "つながっていた"])
    return s


def growth():
    """8-2 暗黒物質は霧が晴れる前から育ち、バリオンは晴れた後にその井戸へ落ちる。M 600x440。

    横 log10 a（-5〜0）x = 70 + (log a + 5)*96、縦 log10 δ（-6〜1）y = 390 - (log δ + 6)*44。
    暗黒物質：δ ∝ (1 + 1.5 a/a_eq) × g(a)（g は宇宙定数による伸びの鈍り、キャロルらの近似）、今 δ=1。
    バリオン：a* まで 1e-5、その後 δ_c (1 - a*/a) に追いつく。赤：バリオンだけなら δ ∝ a で今 1e-2。
    """
    a_eq, a_s = 1 / 3400, 1 / 1091

    def g(a):
        om = OM / a ** 3 / (OM / a ** 3 + OL)
        ol = 1 - om
        return 2.5 * om / (om ** (4 / 7) - ol + (1 + om / 2) * (1 + ol / 70))
    raw = lambda a: (1 + 1.5 * a / a_eq) * g(a)
    dc = lambda a: raw(a) / raw(1)
    db = lambda a: 1e-5 if a <= a_s else max(1e-5, dc(a) * (1 - a_s / a))
    only_b = lambda a: 1e-5 * a / a_s
    assert abs(only_b(1) - 1.09e-2) < 1e-3
    X = lambda la: 70 + (la + 5) * 96
    Y = lambda ld: 390 - (ld + 6) * 44
    s = SVG(600, 440, "暗黒物質のむらは霧が晴れる前から育ち、バリオンは晴れた後に暗黒物質の井戸へ落ちて追いつく")
    s.line(X(-5), Y(-6), X(0), Y(-6), stroke=INK)
    s.line(X(-5), Y(-6), X(-5), Y(1), stroke=INK)
    for la in (-5, -4, -3, -2, -1, 0):
        s.text(X(la), Y(-6) + 22, f"1e{la}" if la else "1（今）", size=14, fill=SUB, anchor="middle")
    for ld in (-6, -4, -2, 0):
        s.text(X(-5) - 8, Y(ld) + 5, f"1e{ld}" if ld else "1", size=14, fill=SUB, anchor="end")
    s.text(X(0), 436, "尺度因子 a（対数）", size=15, fill=SUB, anchor="end")
    s.text(X(-5) + 6, Y(1) + 4, "密度のむら δ（対数）", size=14, fill=SUB)
    s.line(X(-5), Y(0), X(0), Y(0), stroke=MUTED, dash="4 4")
    s.text(X(-5) + 8, Y(0) - 8, "δ≈1：固まって銀河になる目安", size=14, fill=SUB)
    for a, lab in ((a_eq, "光と物質が等しい"), (a_s, "霧が晴れる")):
        s.line(X(math.log10(a)), Y(-6), X(math.log10(a)), Y(0.6), stroke=MUTED, dash="3 3")
    s.text(X(math.log10(a_eq)) - 6, Y(-6) - 8, "z 3400", size=14, fill=SUB, anchor="end")
    s.text(X(math.log10(a_s)) + 6, Y(-6) - 8, "z 1090", size=14, fill=SUB)
    las = [-5 + 5 * i / 200 for i in range(201)]
    s.poly([(X(la), Y(math.log10(dc(10 ** la)))) for la in las], stroke=MUTED, sw=3)
    s.text(X(-4.6), Y(math.log10(dc(10 ** -4.6))) - 12, "暗黒物質", size=15, fill=SUB, bold=True)
    s.poly([(X(la), Y(math.log10(only_b(10 ** la)))) for la in las if 10 ** la >= a_s],
           stroke=WARN, sw=2.2, dash="6 4")
    s.text(X(0) - 4, Y(math.log10(only_b(1))) + 22, "バリオンだけなら 1%", size=14, fill=WARN, anchor="end",
           bold=True)
    s.poly([(X(la), Y(math.log10(db(10 ** la)))) for la in las], stroke=MAIN, sw=3.5)
    s.text(X(-4.6), Y(-5) + 20, "バリオン", size=15, fill=MAIN, bold=True)
    s.circle(X(math.log10(a_s)), Y(-5), 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.note(X(-2.3), Y(-4.4), ["晴れた後、先に掘られた", "井戸へ落ちて追いつく"])
    return s


def age_curves():
    """9-2 同じ今の膨張の速さでも、物質だけの宇宙は97億年、ΛCDM は138億年生きてきた。M 580x400。

    横：ΛCDM のビッグバンからの時刻（10億年）0〜16、x = 60 + t*30。今 13.8 で両方 a = 1、傾きも同じ。
    縦：尺度因子 a 0〜1.2、y = 340 - a*240。球状星団の年齢 120億年以上 → 今の120億年前より前に生まれた。
    """
    t_l = age(1)
    t_m = 2 / 3 * T_H
    assert abs(t_l - 13.8) < 0.05 and abs(t_m - 9.67) < 0.05
    X = lambda t: 60 + t * 30
    Y = lambda a: 340 - a * 240
    s = SVG(580, 400, "同じ今の膨張の速さでも、物質だけの宇宙は97億年しか経っておらず球状星団より若い。ΛCDMは138億年")
    s.rect(X(0), Y(1.2), X(t_l - 12) - X(0), Y(0) - Y(1.2), fill=TINT[FOCUS], stroke="none")
    s.text(X(0) + 6, Y(1.2) + 20, ["球状星団は", "ここまでに", "生まれた"], size=14, fill=FOCUS, bold=True)
    s.line(X(0), Y(0), X(16), Y(0), stroke=INK)
    s.line(X(0), Y(0), X(0), Y(1.2), stroke=INK)
    for t in (0, 4, 8, 12, 16):
        s.text(X(t), Y(0) + 22, f"{t * 10}億年" if t else "0", size=14, fill=SUB, anchor="middle")
    s.text(X(0) - 8, Y(1) + 5, "1", size=14, fill=SUB, anchor="end")
    s.text(X(0) + 6, Y(1.2) - 8, "", size=14)
    s.text(X(16), 392, "ΛCDMのビッグバンからの時刻", size=14, fill=SUB, anchor="end")
    ts = [t_l * (i / 120) ** 1.5 for i in range(121)] + [t_l + 2.2 * i / 20 for i in range(1, 21)]
    s.poly([(X(t), Y(a_of_t(t))) for t in ts], stroke=MAIN, sw=3.5)
    shift = t_l - t_m
    tm = [t_m * (i / 120) ** 1.5 for i in range(121)] + [t_m + 2.2 * i / 20 for i in range(1, 21)]
    s.poly([(X(t + shift), Y((t / t_m) ** (2 / 3))) for t in tm if (t / t_m) ** (2 / 3) <= 1.2],
           stroke=WARN, sw=2.6, dash="6 4")
    s.line(X(t_l), Y(0), X(t_l), Y(1.2), stroke=INK, dash="4 4")
    s.text(X(t_l) + 6, Y(1.2) + 16, "今", size=15, bold=True)
    s.circle(X(t_l), Y(1), 6, fill=INK, stroke="#ffffff", sw=2)
    s.circle(X(shift), Y(0), 7, fill=WARN, stroke="#ffffff", sw=2)
    s.text(X(shift) + 10, Y(0) - 12, "物質だけ：97億年", size=15, fill=WARN, bold=True)
    s.circle(X(0), Y(0), 7, fill=MAIN, stroke="#ffffff", sw=2)
    s.text(X(0) + 10, Y(0.14), "ΛCDM：138億年", size=15, fill=MAIN, bold=True)
    s.note(X(7.2), Y(0.95), ["今の傾き（H0）は同じ", "後から加速した分、昔は遅かった"], size=15)
    return s


def hubble_tension():
    """9-3 2つのテンポ表示は誤差の約4.9倍離れ、平均で消せない。横長 M 600x320。

    横：H0（km/s/Mpc）60〜84、x = 190 + (H0-60)*16。行 y = 70 + 50*i。
    """
    rows = [("Planck（模型で推す）", 67.4, 0.5, 0.5, MAIN),
            ("SH0ES（セファイド）", 73.04, 1.04, 1.04, FOCUS),
            ("赤色巨星（2021）", 69.8, 1.71, 1.71, INK),
            ("重力波 GW170817", 70.0, 8.0, 12.0, MUTED)]
    diff = 73.04 - 67.4
    sig = math.hypot(0.5, 1.04)
    assert round(diff / sig, 1) == 4.9
    X = lambda h: 190 + (h - 60) * 16
    s = SVG(600, 330, "Planckの67.4とSH0ESの73.04は誤差の約4.9倍離れている。重力波の値は幅が広く両方を含む")
    for h in (60, 65, 70, 75, 80):
        s.line(X(h), 50, X(h), 262, stroke="#ececec")
        s.text(X(h), 284, str(h), size=14, fill=SUB, anchor="middle")
    s.text(X(84), 314, "ハッブル定数 H0（km/s/Mpc）", size=14, fill=SUB, anchor="end")
    for i, (name, h, lo, hi, col) in enumerate(rows):
        y = 70 + 50 * i
        s.text(180, y + 5, name, size=15, anchor="end", fill=INK)
        s.line(X(max(60, h - lo)), y, X(min(84, h + hi)), y, stroke=col, sw=3 if col != MUTED else 2)
        s.circle(X(h), y, 7, fill=col, stroke="#ffffff", sw=2)
    s.line(X(70.2), 52, X(70.2), 250, stroke=WARN, sw=1.6, dash="5 4")
    s.text(X(70.2) + 6, 250, "平均 70.2", size=14, fill=WARN)
    s.note(X(75.2), 72, ["差 5.6 は", "誤差の約4.9倍"], size=15)
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig4-2-distances.svg": distances,
        OUT / "fig4-3-horizons.svg": horizons,
        OUT / "fig6-3-bao.svg": bao,
        OUT / "fig7-2-hubble-radius.svg": comoving_hubble,
        OUT / "fig8-2-growth.svg": growth,
        OUT / "fig9-2-age.svg": age_curves,
        OUT / "fig9-3-hubble-tension.svg": hubble_tension,
    }))
