#!/usr/bin/env python3
"""fluid-mechanics の図。

色：青=流れ（速度・流量・運動量）の主役／橙=その図で見る1か所／赤=やる夫の誤ったモデル。
淡青の地色は水。灰は目盛・壁・背景。
"""
import cmath
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/fluid-mechanics/figs"
WATER = TINT[MAIN]


def pathlines():
    """1-2 向きが回る流れでは、流線・流跡線・流脈線が別の線になる。正方 S 440x440。

    一様な流れ u = U(cos wt, sin wt)、t = 0〜T で向きが右から上へ 90°回る。R = U/w。
    注入口 O = (100, 360)、1 R = 220 px。
    流跡線（t=0 に出た粒子）：x = R sin p, y = R(1 - cos p)
    流脈線（t=T の染料の列）：x = R(1 - sin p), y = R cos p
    流線（t=T）：O から真上への直線
    """
    R, ox, oy = 220, 100, 360
    P = lambda x, y: (ox + x * R, oy - y * R)
    n = 60
    path = [P(math.sin(p), 1 - math.cos(p)) for p in (k / n * math.pi / 2 for k in range(n + 1))]
    streak = [P(1 - math.sin(p), math.cos(p)) for p in (k / n * math.pi / 2 for k in range(n + 1))]
    # 流跡線の終点（最初に出た粒子の現在位置）は流脈線の先端と一致する
    assert max(abs(a - b) for a, b in zip(path[-1], streak[0])) < 1e-9
    s = SVG(440, 440, "向きが時間で変わる流れでは、同じ注入口から出る流線・流跡線・流脈線が別の線になる")
    s.line(ox, oy, ox, 60, stroke=MUTED, sw=2, dash="6 5")
    s.poly(path, stroke=MAIN, sw=3)
    s.poly(streak, stroke=FOCUS, sw=5)
    s.circle(ox, oy, 7, fill=INK, stroke="#ffffff", sw=2)
    s.text(ox - 12, oy + 24, "注入口", size=15, anchor="middle")
    s.circle(*path[-1], 7, fill=MAIN, stroke="#ffffff", sw=2)
    s.text(ox + 12, 100, ["流線", "（いまの向き）"], size=15, fill=SUB)
    s.text(P(0.78, 0.28)[0] + 8, P(0.78, 0.28)[1] + 14, ["流跡線", "（最初の粒子の道）"], size=15,
           fill=MAIN, bold=True)
    s.text(P(0.2, 0.62)[0] + 18, P(0.2, 0.62)[1] - 6, "流脈線", size=16, fill=FOCUS, bold=True,
           halo=True)
    s.arrow(250, 408, 300, 408, stroke=SUB, sw=1.6)
    s.text(306, 413, "最初の流れ", size=14, fill=SUB)
    s.arrow(40, 150, 40, 100, stroke=SUB, sw=1.6)
    s.text(40, 176, "いま", size=14, fill=SUB, anchor="middle")
    s.note(180, 40, ["煙が見せるのは流脈線", "流線とも流跡線とも違う"])
    return s


def hydrostatic():
    """2-2 側壁への水圧は深さに比例して増え、合力は底から H/3 に働く。縦長 S 440x480。

    水深 H = 12 m（底のゲージ圧 117.7 kPa / ρg）。y = 60 + 深さm*30（水面 60、底 420）。
    壁 x 300、圧力の矢印の長さ = 深さm*14。
    """
    rho, g, pb = 1000, 9.81, 117.7e3
    H = pb / (rho * g)
    assert abs(H - 12) < 0.01
    Y = lambda d: 60 + d * 30
    s = SVG(440, 480, "水圧は深さに比例して増え、側壁の下ほど強く押される。合力は底からH/3に働く")
    s.rect(24, Y(0), 276, Y(12) - Y(0), fill=WATER, stroke="none")
    s.line(24, Y(0), 300, Y(0), stroke=MAIN, sw=1.6)
    s.poly([(300, 40), (300, Y(12)), (24, Y(12))], stroke=INK, sw=4)
    for d in range(1, 13):
        L = d * 14
        s.arrow(300 - L, Y(d) - 1, 296, Y(d) - 1, stroke=MAIN, sw=1.6)
    s.line(300 - 12 * 14, Y(12), 300, Y(0), stroke=MAIN, sw=1, dash="4 3")
    yF = Y(12 - 12 / 3)
    s.arrow(310, yF, 372, yF, stroke=FOCUS, sw=5)
    s.text(312, yF - 14, "合力", size=16, fill=FOCUS, bold=True)
    s.text(312, yF + 28, "底から H/3", size=15, fill=FOCUS)
    s.text(40, Y(0) + 26, "水面", size=15, fill=MAIN)
    s.text(40, Y(6), ["水深", "H = 12 m"], size=15)
    s.text(140, Y(12) + 30, "底：117.7 kPa", size=15, anchor="middle")
    s.note(40, Y(9) + 4, ["下ほど強く", "押される"])
    return s


def floating():
    """2-3 同じ船体で重心の高さだけ変えると、傾いたときに戻るか倒れるかが分かれる。対照の2枚 M 640x360。

    船体（断面）幅 4、高さ 3.2、喫水 1。20°傾ける。1 = 40 px。
    左パネル中心 x 170、右 x 470、水面 y 190。重心 KG：左 1.0（バラストを底へ）、右 2.6（モーターが上）。
    """
    b, hgt, d, th = 4.0, 3.2, 1.0, math.radians(20)
    KM = d / 2 + b * b / (12 * d)
    assert 1.0 < KM < 2.6
    k = 40

    def submerged():
        # 船体座標（キール中央が原点、上が +y）。水線 y = d - x tanθ（右舷が上がる向きに傾ける）
        wl = lambda x: d - x * math.tan(th)
        return [(-b / 2, 0), (b / 2, 0), (b / 2, wl(b / 2)), (-b / 2, wl(-b / 2))]

    def centroid(poly):
        A = cx = cy = 0
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            c = x1 * y2 - x2 * y1
            A += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
        return cx / (3 * A), cy / (3 * A), A / 2

    bx, by, area = centroid(submerged())
    assert abs(area - b * d) < 1e-9

    def world(x, y, cx0):
        # 船体座標を θ だけ回して、水線の中点が水面 y=190 に来るよう置く
        xr = x * math.cos(th) - (y - d) * math.sin(th)
        yr = x * math.sin(th) + (y - d) * math.cos(th)
        return cx0 + xr * k, 190 - yr * k

    s = SVG(640, 360, "重心が低ければ傾いても浮力と重力の組が船を戻し、重心が高ければさらに倒す")
    for cx0, KG, ok in ((170, 1.0, True), (470, 2.6, False)):
        s.rect(cx0 - 140, 190, 280, 130, fill=WATER, stroke="none")
        s.line(cx0 - 140, 190, cx0 + 140, 190, stroke=MAIN, sw=1.4)
        hull = [world(x, y, cx0) for x, y in ((-b / 2, 0), (b / 2, 0), (b / 2, hgt), (-b / 2, hgt))]
        s.poly(hull, closed=True, fill="#ffffff", stroke=INK, sw=2)
        sub = [world(x, y, cx0) for x, y in submerged()]
        s.poly(sub, closed=True, fill=TINT[MUTED], stroke="none")
        s.poly(hull, closed=True, stroke=INK, sw=2)
        gx, gy = world(0, KG, cx0)
        Bx, By = world(bx, by, cx0)
        s.arrow(gx, gy, gx, gy + 70, stroke=INK, sw=3)
        s.circle(gx, gy, 6, fill=INK, stroke="#ffffff", sw=2)
        away = 1 if gx > Bx else -1   # 文字は相手の点と反対側へ
        s.text(gx + away * 12, gy - 4, "G", size=16, anchor="start" if away > 0 else "end", bold=True)
        s.arrow(Bx, By, Bx, By - 70, stroke=MAIN, sw=3)
        s.circle(Bx, By, 6, fill=MAIN, stroke="#ffffff", sw=2)
        s.text(Bx - away * 12, By + 20, "B", size=16, fill=MAIN, bold=True,
               anchor="end" if away > 0 else "start")
        # 復元なら B は G より「沈んだ側」（左）にある
        restoring = Bx < gx
        assert restoring == ok, (Bx, gx)
        col = MAIN if ok else WARN
        s.text(cx0, 350, "戻る：バラストを底へ" if ok else "倒れる：モーターが上", size=16, fill=col,
               anchor="middle", bold=True)
        # 回る向き：左へ傾いた船体を、戻すなら時計回り、倒すなら反時計回り
        arc = [(cx0 + 120 * math.cos(math.radians(a)), 190 - 120 * math.sin(math.radians(a)))
               for a in range(130, 60, -5)]
        s.poly(arc if ok else arc[::-1], stroke=col, sw=3, smooth=True, arrow=True)
    s.note(24, 40, ["B が G より沈んだ側に来れば戻る"], size=15)
    return s


def operating_point():
    """3-3 ノズルを絞ると系統曲線が立ち、ポンプ曲線との交点が左へ動く。正方 S 500x420。

    流量 q（元の作動点=1）、揚程 h。ポンプ h = 24 - 6q^2、系統 h = 7 + k q^2。
    元：k = 11（q=1 で交わる）。絞った後：q = 0.26 で交わる k。
    x = 70 + q*300、y = 360 - h*12。
    """
    pump = lambda q: 24 - 6 * q * q
    k2 = (pump(0.26) - 7) / 0.26 ** 2
    X = lambda q: 70 + q * 300
    Y = lambda h: 360 - h * 12
    qs = [i / 100 for i in range(0, 131)]
    s = SVG(500, 420, "出口を絞ると配管系の曲線が立ち、ポンプ曲線との交点が左へ動いて流量が減る")
    s.line(70, 360, 480, 360, stroke=INK)
    s.line(70, 360, 70, 40, stroke=INK)
    s.text(480, 392, "流量", size=15, fill=SUB, anchor="end")
    s.text(64, 32, "揚程", size=15, fill=SUB, anchor="start")
    s.poly([(X(q), Y(pump(q))) for q in qs], stroke=INK, sw=3)
    s.text(X(1.3) - 4, Y(pump(1.3)) - 12, "ポンプ", size=15, anchor="end", bold=True)
    s.poly([(X(q), Y(7 + 11 * q * q)) for q in qs if 7 + 11 * q * q < 27], stroke=MAIN, sw=2.4)
    s.text(X(1.14), Y(22) - 4, "20 mm", size=15, fill=MAIN, bold=True)
    s.poly([(X(q), Y(7 + k2 * q * q)) for q in qs if 7 + k2 * q * q < 27], stroke=FOCUS, sw=3.5)
    s.text(X(0.3) + 4, Y(26) + 4, "5 mm に絞る", size=15, fill=FOCUS, bold=True)
    s.line(70, Y(7), 480, Y(7), stroke=MUTED, dash="4 4")
    s.text(476, Y(7) - 8, "静水頭差", size=14, fill=SUB, anchor="end")
    for q, col in ((1, MAIN), (0.26, FOCUS)):
        s.circle(X(q), Y(pump(q)), 7, fill=col, stroke="#ffffff", sw=2)
        s.line(X(q), Y(pump(q)) + 8, X(q), 360, stroke=col, dash="3 3")
    s.text(X(1), 380, "1", size=15, fill=MAIN, anchor="middle")
    s.text(X(0.26), 380, "0.26", size=15, fill=FOCUS, anchor="middle")
    s.arrow(X(0.9), Y(pump(0.9)) - 22, X(0.36), Y(pump(0.36)) - 22, stroke=FOCUS, sw=2)
    s.note(210, 250, ["交点が左へ", "流量は0.26倍"])
    return s


def elbow():
    """5-1 圧力差がなくても、流れの向きを曲げたエルボは外側へ押される。正方 S 420x420。

    上から見たエルボ：水は左から入り（+x）、曲がって上へ出る。曲がりの中心 (150, 170)、
    内壁の半径 60、外壁 110。流量 100 kg/s、速さ 5 m/s → 各成分 500 N、合力 707 N。
    """
    mdot, U = 100, 5
    F = math.hypot(mdot * U, mdot * U)
    assert round(F) == 707
    s = SVG(420, 420, "エルボは水の運動量の向きを90度変えるので、圧力差がなくても外側斜め下へ707 Nで押される")
    cx, cy, r1, r2 = 150, 170, 60, 110
    arc = lambda r: [(cx + r * math.sin(a), cy + r * math.cos(a))
                     for a in (k / 30 * math.pi / 2 for k in range(31))]
    inner = [(24, cy + r1)] + arc(r1) + [(cx + r1, 30)]
    outer = [(24, cy + r2)] + arc(r2) + [(cx + r2, 30)]
    s.poly(inner + outer[::-1], closed=True, fill=WATER, stroke="none")
    s.poly(inner, stroke=INK, sw=3)
    s.poly(outer, stroke=INK, sw=3)
    s.arrow(34, cy + 85, 112, cy + 85, stroke=MAIN, sw=4)
    s.text(30, cy + 146, ["入る運動量", "右向き 500 N"], size=15, fill=MAIN)
    s.arrow(cx + 85, 150, cx + 85, 64, stroke=MAIN, sw=4)
    s.text(cx + 124, 90, ["出る運動量", "上向き 500 N"], size=15, fill=MAIN)
    ex, ey = cx + r2 * math.sin(math.pi / 4), cy + r2 * math.cos(math.pi / 4)
    L = 90
    s.arrow(ex + 6, ey + 6, ex + 6 + L / math.sqrt(2), ey + 6 + L / math.sqrt(2), stroke=FOCUS, sw=5)
    s.text(404, ey + 40 + L / math.sqrt(2), "配管が受ける 707 N", size=16, fill=FOCUS, anchor="end",
           bold=True)
    s.note(24, 50, ["圧力差ゼロでも", "向きを曲げれば", "外へ押される"])
    return s


def pipe_profile():
    """6-3 円管の層流は一様でなく放物線。中心は平均の2倍。対照の2枚 M 600x300。

    管の縦断面：上壁 y 70、下壁 y 230、中心 150、R = 80 px。
    左パネル（やる夫の案）x 60〜260、右パネル（放物線）x 340〜540。矢印の根元 x 80 / 360。
    平均速度 U を 90 px とする。
    """
    Upx = 90
    s = SVG(600, 300, "円管の層流の速度は一様ではなく放物線で、中心は平均速度の2倍になる")
    for x0, label, col in ((60, "やる夫の案：ほぼ一様", WARN), (340, "実際：放物線", MAIN)):
        s.rect(x0, 70, 200, 160, fill=WATER, stroke="none")
        s.line(x0, 70, x0 + 200, 70, stroke=INK, sw=3)
        s.line(x0, 230, x0 + 200, 230, stroke=INK, sw=3)
        s.text(x0 + 100, 50, label, size=16, fill=col, anchor="middle", bold=True)
    ys = [70 + 160 * i / 14 for i in range(15)]
    for y in ys[1:-1]:
        r = abs(y - 150) / 80
        plug = Upx * (1 if r < 0.8 else (1 - r) / 0.2) * 1.05
        s.arrow(80, y, 80 + plug, y, stroke=WARN, sw=1.8)
        u = 2 * Upx * (1 - r * r)
        s.arrow(360, y, 360 + u, y, stroke=MAIN, sw=1.8)
    s.line(80, 70, 80, 230, stroke=MUTED)
    s.line(360, 70, 360, 230, stroke=MUTED)
    s.poly([(360 + 2 * Upx * (1 - ((y - 150) / 80) ** 2), y) for y in range(70, 231, 4)], stroke=MAIN,
           sw=3)
    s.line(360 + Upx, 76, 360 + Upx, 224, stroke=FOCUS, sw=2.4, dash="5 4")
    s.text(360 + Upx, 262, "平均 U", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(360 + 2 * Upx + 8, 156, "中心 2U", size=15, fill=MAIN, bold=True)
    s.text(80, 262, "壁の近くだけ遅い", size=15, fill=WARN)
    s.note(330, 288, "中心だけ測ると流量を2倍に誤る", size=15)
    return s


def pohl(eta, lam):
    """ポールハウゼンの4次多項式の速度分布。λ = -12 で壁面せん断がゼロ。"""
    if eta >= 1:
        return 1.0
    return 2 * eta - 2 * eta ** 3 + eta ** 4 + lam / 6 * eta * (1 - eta) ** 3


def separation():
    """9-2 逆圧力勾配では壁のすぐ上から先に止まり、逆流して剥離する。横長 L 760x330。

    壁 y 290。5つの断面 x = 90, 230, 370, 510, 650。
    λ = 6, 0, -6, -12, -20（-12 が剥離点、壁面せん断ゼロ）。境界層の厚さ 60〜150 px。
    外側の速度（矢印の長さ）= 110 px × 1, .95, .9, .86, .82。
    """
    xs = [90, 230, 370, 510, 650]
    lams = [6, 0, -6, -12, -20]
    thick = [60, 78, 98, 122, 150]
    ue = [1, .95, .9, .86, .82]
    tw = [2 + l / 6 for l in lams]
    assert tw[3] == 0 and tw[4] < 0 < tw[2]
    s = SVG(760, 330, "逆圧力勾配の中では壁のすぐ上の流れが先に止まり、その先で逆流して流れが壁から離れる")
    s.rect(24, 290, 712, 14, fill=s.hatch(MUTED), stroke="none")
    s.line(24, 290, 736, 290, stroke=INK, sw=2)
    edge = [(x, 290 - t) for x, t in zip(xs, thick)]
    s.poly([(24, 290 - 52)] + edge + [(736, 290 - 164)], stroke=MUTED, sw=1.4, dash="5 4", smooth=True)
    s.text(40, 290 - 62, "境界層の外縁", size=14, fill=SUB)
    # 剥離した流線と逆流域
    s.poly([(510, 290), (570, 262), (650, 232), (736, 212)], stroke=FOCUS, sw=2, dash="6 4",
           smooth=True)
    s.text(700, 272, "逆流", size=15, fill=WARN, anchor="middle", bold=True)
    for i, (x, lam, t, u) in enumerate(zip(xs, lams, thick, ue)):
        pts = [(x + 110 * u * pohl(j / 40, lam), 290 - t * j / 40) for j in range(41)]
        pts += [(x + 110 * u, 290 - t - 18)]
        s.line(x, 290, x, 290 - t - 18, stroke=MUTED, sw=1)
        s.poly(pts, stroke=WARN if lam < -12 else MAIN, sw=2.6)
        for j in (6, 16, 28, 40):
            v = 110 * u * pohl(j / 40, lam)
            if abs(v) > 12:
                s.arrow(x, 290 - t * j / 40, x + v, 290 - t * j / 40,
                        stroke=WARN if v < 0 else MAIN, sw=1.3)
    s.circle(510, 290, 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(510, 318, "剥離点：壁の傾きがゼロ", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.arrow(160, 40, 600, 40, stroke=INK, sw=2)
    s.text(380, 30, "下流ほど圧力が高い（逆圧力勾配）", size=15, anchor="middle")
    s.note(40, 90, ["壁のすぐ上が", "先に力尽きる"])
    return s


# --- 翼（ジューコフスキー翼、非粘性の循環つき流れ、クッタ条件） ---
FOIL_ALPHA, FOIL_MU = math.radians(6), complex(-0.08, 0.08)


def foil_flow():
    a = abs(1 - FOIL_MU)
    beta = math.asin(FOIL_MU.imag / a)
    gam = 4 * math.pi * a * math.sin(FOIL_ALPHA + beta)

    def dwdz(zeta):
        w = zeta - FOIL_MU
        return (cmath.exp(-1j * FOIL_ALPHA) - a * a * cmath.exp(1j * FOIL_ALPHA) / w ** 2
                + 1j * gam / (2 * math.pi * w))

    def f(q):
        J = 1 - 1 / q ** 2
        return (dwdz(q) / J).conjugate() / J

    def zeta_of(z):
        r = cmath.sqrt(z * z - 4)
        c1, c2 = (z + r) / 2, (z - r) / 2
        return c1 if abs(c1 - FOIL_MU) >= abs(c2 - FOIL_MU) else c2

    def track(z0, T, dt=0.002, every=0.05):
        q, t, out, n, i = zeta_of(z0), 0.0, [(0.0, z0)], round(every / dt), 0
        while t < T - 1e-9:
            k1 = f(q); k2 = f(q + dt / 2 * k1); k3 = f(q + dt / 2 * k2); k4 = f(q + dt * k3)
            q += dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4); t += dt; i += 1
            if i % n == 0:
                out.append((round(t, 6), q + 1 / q))
        return out

    outline = [FOIL_MU + a * cmath.exp(1j * 2 * math.pi * k / 240) for k in range(240)]
    return [q + 1 / q for q in outline], track


def airfoil():
    """9-3 同時に出た上下の粒子は再会しない。上の粒子が先に後縁を過ぎる。横長 L 760x380。

    ジューコフスキー翼（弦 約4、迎角6°、クッタ条件で循環を決める）。
    x = 30 + (x+3.2)*90、y = 190 - y*90。粒子は x=-5 で分岐流線の上下 0.08 から同時に出す。
    """
    outline, track = foil_flow()
    X = lambda z: 30 + (z.real + 3.2) * 90
    Y = lambda z: 190 - z.imag * 90
    inside = lambda z: -3.2 <= z.real <= 4.7 and -1.7 <= z.imag <= 1.6
    ys = -0.9842   # x=-5 で翼の上と下へ分かれる境目（二分探索で求めた値）
    s = SVG(760, 380, "同じ時刻に翼の前で並んでいた上下の粒子は再会せず、上面の粒子が先に後縁を過ぎる")
    for dy in (-0.9, -0.5, 0.45, 0.9, 1.35):
        pts = [(X(z), Y(z)) for t, z in track(complex(-5, ys + dy), 11, every=0.05) if inside(z)]
        s.poly(pts, stroke=MUTED, sw=1.2)
    s.poly([(X(z), Y(z)) for z in outline], closed=True, fill=TINT[MUTED], stroke=INK, sw=2.4)
    up = track(complex(-5, ys + 0.08), 9, every=0.05)
    lo = track(complex(-5, ys - 0.08), 9, every=0.05)
    s.poly([(X(z), Y(z)) for t, z in up if inside(z)], stroke=FOCUS, sw=2)
    s.poly([(X(z), Y(z)) for t, z in lo if inside(z)], stroke=MAIN, sw=2)
    marks = [k * 0.5 for k in range(19)]
    for tr, col in ((up, FOCUS), (lo, MAIN)):
        for t, z in tr:
            if any(abs(t - m) < 1e-6 for m in marks) and inside(z):
                s.circle(X(z), Y(z), 4.5, fill=col, stroke="#ffffff", sw=1.2)
    tq = 6.5
    zu = next(z for t, z in up if abs(t - tq) < 1e-6)
    zl = next(z for t, z in lo if abs(t - tq) < 1e-6)
    assert zu.real > 1.95 and zl.real < 0.6, (zu, zl)
    s.line(X(zu), Y(zu), X(zl), Y(zl), stroke=INK, sw=1.6, dash="4 3")
    s.circle(X(zu), Y(zu), 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.circle(X(zl), Y(zl), 8, fill=MAIN, stroke="#ffffff", sw=2)
    s.text((X(zu) + X(zl)) / 2 + 30, (Y(zu) + Y(zl)) / 2 + 38, "同じ時刻", size=15, anchor="middle",
           bold=True)
    s.text(X(complex(-3, 0)), 340, "点は等しい時間ごとの位置", size=14, fill=SUB)
    s.text(X(complex(-1.4, 0.5)), Y(complex(0, 0.55)), "上面を通る粒子", size=15, fill=FOCUS,
           bold=True, halo=True)
    s.text(X(complex(-1.2, 0)), Y(complex(0, -0.62)), "下面を通る粒子", size=15, fill=MAIN, bold=True,
           halo=True)
    s.note(470, 70, ["上が先に後縁を過ぎる", "上下は再会しない"])
    return s


def area_mach(M, g=1.4):
    return (1 / M) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * M * M)) ** ((g + 1) / (2 * (g - 1)))


def mach_of(ratio, supersonic):
    lo, hi = (1.0, 5.0) if supersonic else (1e-3, 1.0)
    for _ in range(80):
        m = (lo + hi) / 2
        if (area_mach(m) > ratio) == supersonic:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def laval():
    """9-4 亜音速は細くして加速、音速を超えたら広げて加速。上下2段 M 600x460。

    位置 s = 0〜1、喉部 s = 0.4。面積比 A/A* は収縮部 3.0→1、拡大部 1→1.461（出口 Ma 1.82）。
    上段：ノズル（半径 ∝ √(A/A*)）中心 y 120、1 = 34 px。下段：マッハ数 y = 420 - Ma*120。
    x = 60 + s*500。
    """
    st = 0.4
    exit_ratio = area_mach(1.82)
    ratio = lambda s_: (1 + 2.0 * ((st - s_) / st) ** 2 if s_ <= st
                        else 1 + (exit_ratio - 1) * ((s_ - st) / (1 - st)) ** 1.4)
    assert abs(ratio(0) - 3.0) < 1e-9 and abs(ratio(1) - exit_ratio) < 1e-9
    X = lambda s_: 60 + s_ * 500
    ss = [i / 100 for i in range(101)]
    rad = lambda s_: 34 * math.sqrt(ratio(s_))
    s = SVG(600, 460, "収縮部で亜音速のまま加速し、喉部でマッハ1になり、拡大部で超音速へ加速する")
    s.poly([(X(u), 120 - rad(u)) for u in ss] + [(X(u), 120 + rad(u)) for u in ss[::-1]], closed=True,
           fill=TINT[MAIN], stroke="none")
    for sign in (-1, 1):
        s.poly([(X(u), 120 + sign * rad(u)) for u in ss], stroke=INK, sw=3)
    s.line(X(st), 40, X(st), 420, stroke=FOCUS, sw=2, dash="5 4")
    s.text(X(st), 30, "喉部", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(X(0.18), 125, "細くして加速", size=15, anchor="middle", halo=True)
    s.text(X(0.75), 125, "広げて加速", size=15, anchor="middle", halo=True)
    Y = lambda M: 420 - M * 120
    s.line(60, 420, 560, 420, stroke=INK)
    s.line(60, 420, 60, 190, stroke=INK)
    s.line(60, Y(1), 560, Y(1), stroke=MUTED, dash="4 4")
    s.text(52, Y(1) + 5, "1", size=15, fill=SUB, anchor="end")
    s.text(52, Y(0) + 5, "0", size=15, fill=SUB, anchor="end")
    s.text(52, Y(1.82) + 5, "1.82", size=15, fill=SUB, anchor="end")
    s.text(66, 206, "マッハ数", size=15, fill=SUB)
    Ms = [mach_of(ratio(u), u > st) if abs(u - st) > 1e-9 else 1.0 for u in ss]
    assert abs(Ms[-1] - 1.82) < 1e-3
    s.poly([(X(u), Y(m)) for u, m in zip(ss, Ms)], stroke=MAIN, sw=3.5)
    s.circle(X(st), Y(1), 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(X(0.2), Y(0.3) - 12, "亜音速", size=15, fill=SUB, anchor="middle")
    s.text(X(0.8), Y(1.15), "超音速", size=15, fill=SUB, anchor="middle")
    s.note(X(0.5), 350, ["Ma 1 を超えたら", "広げないと加速しない"], size=15)
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig1-2-pathlines.svg": pathlines,
        OUT / "fig2-2-hydrostatic.svg": hydrostatic,
        OUT / "fig2-3-floating.svg": floating,
        OUT / "fig3-3-operating-point.svg": operating_point,
        OUT / "fig5-1-elbow.svg": elbow,
        OUT / "fig6-3-pipe-profile.svg": pipe_profile,
        OUT / "fig9-2-separation.svg": separation,
        OUT / "fig9-3-airfoil.svg": airfoil,
        OUT / "fig9-4-laval.svg": laval,
    }))
