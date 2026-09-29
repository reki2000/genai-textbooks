#!/usr/bin/env python3
"""orbital-mechanics-moon の図。

色：青=選んだ（正しい）軌道・速度／橙=その図で見る1か所（噴射点・答え）／赤=やる夫の破綻する案。
灰は基準の円軌道・月の軌道・目盛。地球は淡青、月は淡灰の円。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/orbital-mechanics-moon/figs"
MU = 3.986e14          # 地球の GM（m^3/s^2）
R_LEO = 6.771e6        # 低軌道の半径（m）
R_E = 6.371e6
R_MOON = 3.844e8
EARTH, MOON = TINT[MAIN], TINT[MUTED]


def conic(p, e, f0, f1, n=160):
    """近点からの角 f の範囲で、焦点を原点とする円錐曲線の点列（半径, 角）を返す。"""
    return [(p / (1 + e * math.cos(f)), f) for f in (f0 + (f1 - f0) * k / n for k in range(n + 1))]


def cannon():
    """2 撃つ速さを上げると落ちる先が遠のき、ちょうどで地面に届かなくなる。正方 S 440x440。

    地球 半径 100 px、中心 (220, 170)。山頂は真上の r0 = 1.25R（山の高さは誇張）。
    速さ k（その高さの円軌道速度=1）：0.65, 0.78, 0.88 は落ちる、1 は円、1.1 は楕円。
    """
    R, cx, cy = 100, 220, 170
    r0 = 1.25 * R
    P = lambda r, f: (cx - r * math.sin(f), cy - r * math.cos(f))   # f は山頂から左回り
    s = SVG(440, 440, "撃つ速さを上げると落ちる先が遠のき、ちょうどの速さで地面の曲がりと一致して落ち続ける")
    s.circle(cx, cy, R, fill=EARTH, stroke=MUTED, sw=1.4)
    s.poly([P(R, -0.2), P(r0, 0), P(R, 0.2)], closed=True, fill=TINT[MUTED], stroke=MUTED)
    for k in (0.65, 0.78, 0.88):
        e, p = 1 - k * k, r0 * k * k        # 山頂が遠点
        pts, f = [], 0.0
        while f < math.pi:
            r = p / (1 - e * math.cos(f))
            if r < R:
                break
            pts.append(P(r, f)); f += 0.01
        s.poly(pts, stroke=SUB, sw=1.6)
        s.circle(*pts[-1], 4, fill=SUB, stroke="none")
    s.circle(cx, cy, r0, stroke=MAIN, sw=4)
    e, p = 1.1 ** 2 - 1, r0 * 1.1 ** 2   # 山頂が近点
    s.poly([P(p / (1 + e * math.cos(f)), f) for f in (2 * math.pi * k / 200 for k in range(201))],
           stroke=MUTED, sw=1.4, dash="5 4")
    s.circle(*P(r0, 0), 6, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(cx + 12, cy - r0 - 12, "山頂から水平に撃つ", size=15, fill=FOCUS, bold=True)
    s.text(cx - 40, cy - 20, ["弱いほど", "近くに落ちる"], size=14, fill=SUB, anchor="middle")
    s.text(cx + r0 + 8, cy + 40, "ちょうど", size=15, fill=MAIN, bold=True)
    s.text(cx + 120, cy + 190, "もっと速い：楕円", size=14, fill=SUB, anchor="middle")
    s.text(416, 426, "山の高さは誇張", size=14, fill=SUB, anchor="end")
    s.note(24, 396, ["落ち続けても", "地面が同じだけ逃げる"])
    return s


def phasing():
    """3 前へ噴くと高く遅い軌道になって遅れ、後ろへ噴くと低く速い軌道で追いつく。正方 M 520x460。

    円軌道 半径 150、中心 (260, 230)、左回り。噴射点 P は真下。離心率 0.12 に誇張。
    前へ噴く：P が近点の楕円。後ろへ噴く：P が遠点の楕円。仲間は P の 40° 先。
    """
    R, cx, cy, e = 150, 260, 230, 0.12
    Pt = lambda r, f: (cx + r * math.sin(f), cy + r * math.cos(f))   # f は P（真下）から左回り
    s = SVG(520, 460, "前へ噴くと高く遅い軌道になって仲間から遅れ、後ろへ噴くと低く速い軌道で追いつく")
    s.circle(cx, cy, 34, fill=EARTH, stroke=MUTED)
    s.circle(cx, cy, R, stroke=MUTED, sw=1.4, dash="5 4")
    up = [Pt(R * (1 + e) / (1 + e * math.cos(f)), f) for f in (2 * math.pi * k / 200 for k in range(201))]
    dn = [Pt(R * (1 - e) / (1 - e * math.cos(f)), f) for f in (2 * math.pi * k / 200 for k in range(201))]
    s.poly(up, stroke=WARN, sw=2.6)
    s.poly(dn, stroke=MAIN, sw=3.5)
    px, py = Pt(R, 0)
    s.circle(px, py, 7, fill=INK, stroke="#ffffff", sw=2)
    s.text(px, py + 30, "噴射点", size=15, anchor="middle", bold=True)
    fx, fy = Pt(R, math.radians(40))
    s.circle(fx, fy, 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(fx + 14, fy + 6, "100 km 前の仲間", size=15, fill=FOCUS, bold=True)
    s.arrow(px - 60, py + 8, px - 20, py + 8, stroke=SUB, sw=1.6)
    s.text(px - 66, py + 13, "進む向き", size=14, fill=SUB, anchor="end")
    s.text(cx, cy - R * (1 + e) / (1 - e) - 10, "前へ噴く：高く遅い → 遅れる", size=15, fill=WARN,
           anchor="middle", bold=True)
    s.text(cx, cy - R * (1 - e) / (1 + e) + 30, "後ろへ噴く：低く速い", size=15, fill=MAIN, anchor="middle",
           bold=True, halo=True)
    s.text(496, 446, "高さの差は誇張（実際は約11 km）", size=14, fill=SUB, anchor="end")
    s.note(24, 40, ["追いつくには", "後ろへ噴く"])
    return s


def orbit_from(vt, vr, r=R_LEO):
    """半径 r で接線速度 vt・動径速度 vr のとき、(p, e, 噴射点の真近点角 f) を返す。"""
    h = r * vt
    eps = (vt * vt + vr * vr) / 2 - MU / r
    e = math.sqrt(max(0.0, 1 + 2 * eps * h * h / MU ** 2))
    p = h * h / MU
    f = math.acos(max(-1, min(1, (p / r - 1) / e))) if e > 1e-12 else 0.0
    return p, e, f if vr >= 0 else -f


def transfer():
    """4-3 同じ3 km/sでも、外向きなら地面へ落ち、前向きなら20万 km、3.08 km/sなら月の距離へ届く。L 760x540。

    上段（縮尺どおり）：地球中心 (130, 160)、1 px = 650 km。噴射点は地球の左（真近点角 0 が左向き）。
    右下（拡大）：枠 x 440〜740・y 270〜530、地球中心 (590, 360)、1 px = 90 km。
    外向き噴射の楕円を地面に当たるまで描く。
    """
    vc = math.sqrt(MU / R_LEO)
    a_h = (R_LEO + R_MOON) / 2
    dv_h = math.sqrt(MU * (2 / R_LEO - 1 / a_h)) - vc
    assert round(dv_h) == 3084, dv_h
    k = 1 / 650e3
    cx, cy = 130, 160
    s = SVG(760, 540, "同じ3 km/sでも外向きに噴けば地面に当たり、前向きなら遠地点20万 km、3.08 km/sで月の距離に届く")
    # 月の軌道（弧）と月
    s.poly([(cx + R_MOON * k * math.cos(t), cy + R_MOON * k * math.sin(t))
            for t in (math.radians(d) for d in range(-13, 14))], stroke=MUTED, sw=1.4, dash="5 4")
    mx = cx + R_MOON * k
    s.circle(mx, cy, 1.738e6 * k + 2, fill=MOON, stroke=INK)
    s.text(mx - 16, 36, "月の距離 38万 km", size=15, anchor="end")
    # 前向き 3.0 km/s と 3.084 km/s（噴射点が近点、遠点は右）
    for dv, col, sw, dash in ((3000, MUTED, 2, "6 4"), (dv_h, MAIN, 3.5, None)):
        p, e, _ = orbit_from(vc + dv, 0)
        pts = [(cx - r * k * math.cos(f), cy + r * k * math.sin(f)) for r, f in conic(p, e, 0, 2 * math.pi, 400)]
        s.poly(pts, stroke=col, sw=sw, dash=dash)
        if dv == 3000:
            apo = p / (1 - e)
            assert round(apo / 1e6) == 201, apo
            s.text(cx + apo * k / 2 + 20, cy - 4, ["前向き 3.0 km/s", "遠地点 20万 km"], size=15,
                   fill=SUB, anchor="middle")
    s.text(cx + 330, cy - 86, "前向き 3.08 km/s（ホーマン遷移）", size=15, fill=MAIN, bold=True)
    s.circle(cx, cy, R_E * k + 2, fill=EARTH, stroke=INK)
    s.circle(cx - R_LEO * k - 1, cy, 4, fill=FOCUS, stroke="none")
    # 下段：拡大
    zk = 1 / 90e3
    zx, zy = 590, 360
    s.zoom((cx - 14, cy - 14, 28, 28), (440, 270, 300, 260))
    s.circle(zx, zy, R_E * zk, fill=EARTH, stroke=INK, sw=1.4)
    s.text(zx, zy + 5, "地球", size=16, anchor="middle", bold=True)
    s.circle(zx, zy, R_LEO * zk, stroke=MUTED, dash="4 3")
    p, e, f0 = orbit_from(vc, 3000)
    assert abs(p / (1 + e) - 4.87e6) < 0.02e6          # 近地点は地球の中（本文：4,900 km）
    # 噴射点を左（角 180°）に置く：点の角 = 180° - (f - f0)（左回りに進む）
    pts = []
    for r, f in conic(p, e, f0, f0 + 2 * math.pi, 600):
        pts.append((zx + r * zk * math.cos(math.pi + (f - f0)), zy - r * zk * math.sin(math.pi + (f - f0))))
        if r < R_E:
            break
    s.poly(pts, stroke=WARN, sw=3)
    s.circle(*pts[-1], 7, fill=WARN, stroke="#ffffff", sw=2)
    s.text(732, 294, "地面に当たる", size=15, fill=WARN, bold=True, anchor="end")
    bx, by = zx - R_LEO * zk, zy
    s.circle(bx, by, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.arrow(bx - 4, by, bx - 44, by, stroke=WARN, sw=2.4)
    s.text(452, 520, "外向き 3.0 km/s", size=15, fill=WARN, bold=True)
    s.text(732, 520, "拡大：低軌道のまわり", size=14, fill=SUB, anchor="end")
    s.note(40, 340, ["同じ3 km/sでも", "外向きなら地面へ", "前向きなら20万 km"])
    return s


def window():
    """4-4 旅は5日と決まっているので、月が114°先にいる時を待って出発する。正方 M 480x460。

    縮尺どおり：地球中心 (240, 230)、月の軌道 半径 190 px。宇宙船は地球の左で出発し、
    左回りに半周して右の遠地点へ。月は出発時に 114° 先（右下）、5日で 66° 進んで右へ。
    """
    a = (R_LEO + R_MOON) / 2
    T = math.pi * math.sqrt(a ** 3 / MU)
    moved = 360 * T / 86400 / 27.3
    lead = 180 - moved
    assert round(T / 86400) == 5 and round(moved) == 66 and round(lead) == 114, (T, moved)
    Rm, cx, cy = 190, 240, 230
    k = Rm / R_MOON
    P = lambda r, deg: (cx + r * math.cos(math.radians(deg)), cy - r * math.sin(math.radians(deg)))
    s = SVG(480, 460, "旅の時間は5日と決まっているので、月が出発点から114°先にいる時を待って出発する")
    s.circle(cx, cy, Rm, stroke=MUTED, sw=1.4, dash="5 4")
    e = (R_MOON - R_LEO) / (R_MOON + R_LEO)
    p = a * (1 - e * e)
    half = [P(p / (1 + e * math.cos(f)) * k, 180 + math.degrees(f)) for f in (math.pi * j / 200 for j in range(201))]
    s.poly(half, stroke=MAIN, sw=3.5)
    s.circle(cx, cy, 6, fill=EARTH, stroke=INK)
    m0 = 180 + lead
    s.circle(*P(Rm, m0), 11, fill="#ffffff", stroke=INK, sw=1.4, dash="3 3")
    s.text(*P(Rm + 22, m0), "出発時の月", size=15, anchor="start")
    s.poly([P(Rm + 10, d) for d in range(int(m0) + 4, 360 - 4, 2)], stroke=FOCUS, sw=3, arrow=True)
    s.text(*P(Rm - 14, 318), "5日で66°", size=16, fill=FOCUS, bold=True, anchor="end")
    s.circle(*P(Rm, 0), 11, fill=MOON, stroke=INK, sw=1.6)
    s.text(P(Rm, 0)[0] - 4, P(Rm, 0)[1] - 18, "5日後に会う", size=15, anchor="end", bold=True)
    s.poly([P(46, 180 + d) for d in range(0, int(lead) + 1, 2)], stroke=INK, sw=1.4)
    s.line(cx, cy, *P(Rm, m0), stroke=SUB, sw=1, dash="3 3")
    s.line(cx, cy, *P(Rm, 180), stroke=SUB, sw=1, dash="3 3")
    s.text(*P(64, 180 + lead / 2), "114°", size=16, bold=True)
    s.text(P(Rm, 180)[0] + 8, P(Rm, 180)[1] - 10, "出発点の方向", size=14, fill=SUB)
    s.text(cx + 40, cy + 70, "半周 5日", size=15, fill=MAIN, bold=True)
    s.note(24, 40, ["狙うのではなく", "114°になる時を待つ"])
    return s


def inclination():
    """4-4 北緯28.5°の射場を通る軌道面は、どう寝かせても28.5°より浅くならない。横長 S 470x340。

    地球を横から見る：中心 (200, 180)、半径 130。射場は右の縁、緯度 28.5°。
    射場と中心を通る面を真横から見ると直線になり、その傾きが最小の軌道傾斜角。
    """
    lat = 28.5
    R, cx, cy = 130, 200, 180
    s = SVG(470, 340, "北緯28.5°の射場を通る軌道面は赤道に対して28.5°より浅く寝かせられない")
    s.circle(cx, cy, R, fill=EARTH, stroke=INK, sw=1.4)
    s.line(cx, cy - R - 20, cx, cy + R + 20, stroke=MUTED, dash="3 3")
    s.line(cx - R - 40, cy, cx + R + 40, cy, stroke=WARN, sw=2, dash="6 4")
    s.text(cx - R - 40, cy - 8, "赤道の面", size=15, fill=WARN, halo=True)
    t = math.radians(lat)
    sx, sy = cx + R * math.cos(t), cy - R * math.sin(t)
    L = R + 50
    s.line(cx - L * math.cos(t), cy + L * math.sin(t), cx + L * math.cos(t), cy - L * math.sin(t),
           stroke=MAIN, sw=3.5)
    s.circle(sx, sy, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(sx + 12, sy + 22, "射場 北緯28.5°", size=15, fill=FOCUS, bold=True)
    s.poly([(cx + 70 * math.cos(math.radians(d)), cy - 70 * math.sin(math.radians(d)))
            for d in range(0, int(lat) + 1)], stroke=INK, sw=1.4)
    s.text(cx + 76, cy - 12, "28.5°", size=15, bold=True)
    s.text(cx - L * math.cos(t) - 4, cy + L * math.sin(t) + 22, "最も寝かせた軌道面", size=15, fill=MAIN,
           bold=True)
    s.note(24, 40, "軌道面は地球の中心を通る")
    return s


def assist():
    """4-5 月から見た速さは変わらず向きだけ変わる。地球から見ると0.19が最大1.85になる。M 520x440。

    地球から見た速度の平面：原点 O (60, 220)、1 km/s = 190 px、右が月の進む向き。
    月の速度 1.02 の先端 M を中心に、月から見た速さ 0.83 の円（出ていける速度の全部）。
    """
    vm, vinf = 1.02, 0.83
    assert round(vm - vinf, 2) == 0.19 and round(vm + vinf, 2) == 1.85
    k, ox, oy = 190, 60, 220
    X = lambda v: ox + v * k
    s = SVG(520, 440, "月から見た速さは0.83 km/sのまま向きだけ変わり、地球から見ると0.19 km/sが最大1.85 km/sになる")
    s.circle(X(vm), oy, vinf * k, fill=TINT[MUTED], stroke=MUTED, sw=1.4, dash="5 4")
    s.text(X(vm), oy - vinf * k - 12, "月から見て 0.83 km/s で出ていける向き", size=14, fill=SUB,
           anchor="middle")
    s.arrow(ox, oy, X(vm) - 4, oy, stroke=MUTED, sw=2)
    s.text(X(vm / 2) + 30, oy + 26, "月 1.02", size=15, fill=SUB, anchor="middle")
    s.arrow(X(vm), oy - 30, X(vm - vinf) + 4, oy - 30, stroke=MAIN, sw=2, dash="5 4")
    s.text(X(vm - vinf / 2), oy - 40, "入る 0.83", size=14, fill=MAIN, anchor="middle")
    s.arrow(ox, oy + 50, X(vm - vinf), oy + 50, stroke=MAIN, sw=3)
    s.text(X(vm - vinf) + 8, oy + 56, "地球から見て 0.19", size=15, fill=MAIN, bold=True)
    s.arrow(ox, oy + 96, X(vm + vinf), oy + 96, stroke=FOCUS, sw=4)
    s.text(X(vm + vinf) - 4, oy + 124, "出る：最大 1.85", size=16, fill=FOCUS, anchor="end", bold=True)
    s.circle(ox, oy, 5, fill=INK, stroke="none")
    s.text(ox - 8, oy + 5, "O", size=15, anchor="end")
    s.circle(X(vm), oy, 5, fill=INK, stroke="none")
    s.note(24, 404, "無料ではなく、動く月との取引")
    return s


def corridor():
    """6-3 再突入の角度には、深すぎず浅すぎない数度の幅しかない。横長 M 600x340（模式）。

    地球の縁：中心 (300, 1500)、半径 1200（上端 y 300）。大気の帯は厚さ 70。
    入口 E (60, 70) から3本：深すぎ・回廊・浅すぎ。許される入口の向きを橙の扇で示す。
    """
    Rg, gx, gy = 1200, 300, 1500
    s = SVG(600, 340, "再突入の角度は深すぎても浅すぎても死ぬ。通ってよいのは数度の幅の回廊だけ")
    arc = lambda r: [(gx + r * math.sin(math.radians(d)), gy - r * math.cos(math.radians(d)))
                     for d in range(-16, 17)]
    s.poly(arc(Rg + 70) + arc(Rg)[::-1], closed=True, fill=TINT[MAIN], stroke="none")
    s.poly(arc(Rg), stroke=INK, sw=2)
    s.text(40, 300, "大気", size=15, fill=MAIN)
    ex, ey = 60, 70
    fan = [(ex, ey)] + [(ex + 200 * math.cos(math.radians(d)), ey + 200 * math.sin(math.radians(d)))
                        for d in (22, 30)]
    s.poly(fan, closed=True, fill=TINT[FOCUS], stroke=FOCUS, sw=1)
    s.poly([(ex, ey), (200, 150), (300, 250), (350, 312)], stroke=WARN, sw=2.6, smooth=True)
    s.text(235, 215, ["深すぎ：", "減速と熱で死ぬ"], size=15, fill=WARN, bold=True, anchor="end")
    s.poly([(ex, ey), (220, 150), (380, 226), (470, 250)], stroke=MAIN, sw=4, smooth=True)
    s.text(478, 256, "回廊", size=16, fill=MAIN, bold=True)
    s.poly([(ex, ey), (240, 150), (380, 200), (470, 190), (560, 140)], stroke=WARN, sw=2.6, dash="6 4",
           smooth=True)
    s.text(560, 124, "浅すぎ：弾かれる", size=15, fill=WARN, anchor="end", bold=True)
    s.text(ex + 160, ey + 40, "入ってよい向き：数度", size=15, fill=FOCUS, bold=True)
    s.text(576, 30, "模式図（角度と高さは誇張）", size=14, fill=SUB, anchor="end")
    s.note(24, 40, "入口 約11 km/s")
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig2-cannon.svg": cannon,
        OUT / "fig3-phasing.svg": phasing,
        OUT / "fig4-3-transfer.svg": transfer,
        OUT / "fig4-4-window.svg": window,
        OUT / "fig4-4-inclination.svg": inclination,
        OUT / "fig4-5-assist.svg": assist,
        OUT / "fig6-3-corridor.svg": corridor,
    }))
