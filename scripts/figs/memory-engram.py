#!/usr/bin/env python3
"""memory-engram の図（自力描画の模式図）。

色：青=主信号・増強する経路（AMPA受容体・Na・LTP）／橙=一致検出・修飾・選択
（NMDA受容体・Ca・ドーパミン・ノルアドレナリン・タグ・ミクログリア）／赤=抑制・弱化・回収・除去。
灰=膜・核・背景の構造。どれも模式図で縮尺は不同。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/memory-engram/figs"
PRE = "#f4f4f4"      # 送り手の細胞質
POST = "#eef3fb"     # 受け手の細胞質
EDGE = "#9a9a9a"


# ---------------------------------------------------------------- 部品
def sample(pts, closed=False, k=8):
    """点列を通る Catmull-Rom 曲線上の点を返す（塗りを曲線の内側に収めるため）。"""
    n = len(pts)
    at = (lambda i: pts[i % n]) if closed else (lambda i: pts[max(0, min(n - 1, i))])
    out = []
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        for j in range(k):
            t = j / k
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c])
                                    * t * t + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    return out + ([] if closed else [pts[-1]])


def membrane(s, pts, closed=False, fill=None, smooth=True):
    """細胞膜。灰の太線に白の芯を重ねて二重線に見せる。fill で細胞質を塗る（開いた膜は両端を直線で閉じる）。"""
    if fill:
        s.poly(sample(pts, closed) if smooth else pts, fill=fill, stroke="none", closed=True)
    s.poly(pts, stroke=EDGE, sw=7, closed=closed, smooth=smooth)
    s.poly(pts, stroke="#f7f7f7", sw=3, closed=closed, smooth=smooth)


def channel(s, x, y, col, h=46, w=13, gap=7, plug=False):
    """膜（水平、中心 y）を貫くイオンチャネル。中央の隙間が通り道。plug=True で Mg の栓。"""
    for dx in (-(gap / 2 + w), gap / 2):
        s.rect(x + dx, y - h / 2, w, h, fill=TINT[col], stroke=col, sw=2, rx=5)
    if plug:
        s.circle(x, y - 4, 8, fill="#b5b5b5", stroke=INK, sw=1.2)


def vesicle(s, x, y, r=11, col=MUTED):
    s.circle(x, y, r, fill="#ffffff", stroke=EDGE, sw=1.6)
    for k in range(3):
        a = k * 2.1 + 0.5
        s.circle(x + r * 0.42 * math.cos(a), y + r * 0.42 * math.sin(a), 2.2, fill=col, stroke="none")


def dots(s, pts, col, r=4):
    for x, y in pts:
        s.circle(x, y, r, fill=col, stroke="none")


def tag(s, x, y, text, col=MAIN, size=14, fill=None):
    """分子名の札。(x, y) は中心。"""
    w = len(text) * size * 0.62 + 16 if text.isascii() else len(text) * size + 16
    s.rect(x - w / 2, y - 14, w, 28, rx=6, fill=fill or "#ffffff", stroke=col, sw=1.6)
    s.text(x, y + 5, text, size=size, anchor="middle", fill=INK, bold=True)
    return w


def flow(s, pts, col=MAIN, sw=2.2, dash=None):
    s.poly(pts, stroke=col, sw=sw, smooth=len(pts) > 2, arrow=True, dash=dash)


def tree(s, x, y, ang, length, depth, sw, col=EDGE, spread=0.42):
    """決定的に枝分かれする樹状突起。角度はラジアン、各段で2本に分かれる。"""
    x2, y2 = x + length * math.cos(ang), y + length * math.sin(ang)
    s.line(x, y, x2, y2, stroke=col, sw=sw)
    if depth:
        for d in (-spread, spread):
            tree(s, x2, y2, ang + d, length * 0.7, depth - 1, max(1.2, sw * 0.62), col, spread)


# ---------------------------------------------------------------- 2-1
def neuron():
    """2-3 ニューロン全体と、軸索終末の1接点の拡大。全体＋拡大 L 760x540。

    上段 y 30..250：細胞体 (150,140)、樹状突起は細胞体の周り、軸索は x 190 → 600、終末は x 620..680。
    下段 y 300..520：拡大。送り手の終末 x 60..330、受け手のスパイン x 400..720、間隙 x 330..400。
    """
    s = SVG(760, 540, "樹状突起は細胞体の近くに茂り、1本の軸索は遠くで終末を作り、送り手と受け手の膜は隙間を挟んで向き合う")
    cx, cy = 150, 140
    for a, L in ((200, 44), (160, 50), (245, 46), (120, 40), (285, 38), (75, 36)):
        r = math.radians(a)
        tree(s, cx + 30 * math.cos(r), cy + 30 * math.sin(r), r, L, 3, 5)
    s.poly([(cx - 32, cy), (cx - 18, cy - 30), (cx + 16, cy - 32), (cx + 34, cy - 6), (cx + 28, cy + 26),
            (cx - 6, cy + 34), (cx - 30, cy + 20)], fill="#ececec", stroke=EDGE, sw=2, closed=True, smooth=True)
    s.circle(cx - 2, cy, 12, fill="#cfcfcf", stroke=EDGE, sw=1.4)
    s.poly([(cx + 32, cy + 4), (300, cy + 10), (450, cy), (600, cy + 6)], stroke=EDGE, sw=4, smooth=True)
    ends = [(655, 88), (675, 122), (680, 160), (668, 196)]
    for ex, ey in ends:
        s.poly([(600, cy + 6), (630, (cy + ey) / 2), (ex, ey)], stroke=EDGE, sw=2.2, smooth=True)
        s.circle(ex, ey, 7, fill="#ececec", stroke=EDGE, sw=1.6)
    s.arrow(320, 108, 440, 108, stroke=MAIN, sw=3)
    s.text(380, 96, "信号の向き", size=15, fill=MAIN, anchor="middle", bold=True)
    s.text(40, 36, "樹状突起", size=15, bold=True)
    s.text(cx + 44, cy + 56, "細胞体（核）", size=15)
    s.text(450, 168, "軸索（1本）", size=15, anchor="middle")
    s.text(640, 236, "軸索終末", size=15, anchor="end")
    s.zoom((654, 182, 28, 28), (40, 290, 680, 230))
    # 拡大：送り手の終末（左）と受け手のスパイン（右）
    membrane(s, [(40, 350), (170, 346), (280, 322), (330, 360), (330, 460), (280, 490), (170, 466), (40, 462)],
             closed=False, fill=PRE)
    membrane(s, [(720, 336), (590, 340), (450, 316), (400, 360), (400, 460), (450, 500), (590, 474), (720, 470)],
             closed=False, fill=POST)
    for vx, vy in ((200, 390), (240, 430), (275, 385), (230, 470 - 40)):
        vesicle(s, vx, vy)
    s.line(340, 410, 390, 410, stroke=INK, sw=1.4)
    s.line(340, 402, 340, 418, stroke=INK, sw=1.4)
    s.line(390, 402, 390, 418, stroke=INK, sw=1.4)
    s.text(365, 440, "隙間", size=15, anchor="middle", bold=True)
    s.text(365, 460, "約20nm", size=15, anchor="middle", bold=True)
    s.text(80, 336, "送り手（軸索終末）", size=15)
    s.text(700, 324, "受け手（樹状突起）", size=15, anchor="end")
    s.note(470, 400, ["袋は別々のまま、", "隙間で向き合う"])
    return s


# ---------------------------------------------------------------- 2-2
def nmda_gate():
    """2-6 NMDA受容体は、脱分極でMgの栓が抜けたときだけCaを通す。対照の2枚 横長 M 680x400。

    パネル k の左端 x0 = 20 + 340*k、幅 320。膜 y=200（上が細胞外、下が受け手の細胞内）。
    AMPA受容体 x0+90、NMDA受容体 x0+230。
    """
    s = SVG(680, 400, "静止時はNMDA受容体のMgの栓がCaを遮り、AMPA受容体からのNaで脱分極するとMgが抜けてCaが入る")
    for k, (title, col) in enumerate((("静止時", SUB), ("脱分極時", FOCUS))):
        x0 = 20 + 340 * k
        s.text(x0 + 10, 34, title, size=17, bold=True, fill=INK if k == 0 else FOCUS)
        s.rect(x0, 200, 320, 150, fill=POST, stroke="none")
        membrane(s, [(x0, 200), (x0 + 320, 200)], smooth=False)
        s.text(x0 + 8, 186, "細胞外", size=13, fill=SUB)
        s.text(x0 + 8, 226, "細胞内", size=13, fill=SUB)
        ax, nx = x0 + 90, x0 + 215
        dots(s, [(ax - 6, 120), (nx - 6, 120)], MAIN, 5)
        s.text(x0 + 160, 76, "グルタミン酸", size=14, anchor="middle")
        s.line(x0 + 130, 82, ax + 4, 112, stroke=SUB, sw=1)
        s.line(x0 + 190, 82, nx - 10, 112, stroke=SUB, sw=1)
        channel(s, ax, 200, MAIN)
        channel(s, nx, 200, FOCUS, plug=k == 0)
        s.text(ax, 150, "AMPA", size=14, anchor="middle", bold=True, fill=MAIN)
        s.text(nx, 150, "NMDA", size=14, anchor="middle", bold=True, fill=FOCUS)
        s.arrow(ax, 160, ax, 280, stroke=MAIN, sw=3)
        s.text(ax, 304, "Na が入る", size=15, anchor="middle", fill=MAIN, bold=True)
        if k == 0:
            s.text(nx + 14, 200, "Mg", size=14, bold=True)
            s.line(nx, 232, nx, 262, stroke=SUB, sw=2, dash="3 3")
            s.line(nx - 8, 266, nx + 8, 282, stroke=WARN, sw=3)
            s.line(nx - 8, 282, nx + 8, 266, stroke=WARN, sw=3)
            s.text(nx, 312, "Ca は通れない", size=15, anchor="middle", fill=WARN, bold=True)
        else:
            s.circle(nx + 50, 128, 8, fill="#b5b5b5", stroke=INK, sw=1.2)
            flow(s, [(nx + 4, 190), (nx + 22, 152), (nx + 40, 134)], SUB, 1.6)
            s.text(nx + 50, 108, "Mg が抜ける", size=13, anchor="middle")
            s.arrow(nx, 160, nx, 280, stroke=FOCUS, sw=3.5)
            s.text(nx, 304, "Ca が入る", size=15, anchor="middle", fill=FOCUS, bold=True)
    s.note(360, 380, "鍵は二つ：グルタミン酸と脱分極")
    return s


# ---------------------------------------------------------------- 3-1
def early_ltp():
    """3-3 一致検出から受容体が増えるまで。スパインの断面を読み順1〜5で。縦長 M 560x640。

    送り手の終末 y 20..120、シナプス後膜 y=170（x 110..450）、スパインの頭 y 170..420、首 y 420..520。
    """
    s = SVG(560, 640, "グルタミン酸と脱分極が一致するとNMDA受容体からCaが入り、CaM・CaMKIIを経てAMPA受容体が増える")
    membrane(s, [(90, 20), (110, 90), (200, 124), (360, 124), (450, 90), (470, 20)], fill=PRE)
    for vx in (200, 260, 320, 380):
        vesicle(s, vx, 70)
    dots(s, [(230, 142), (270, 148), (310, 142), (350, 150)], MAIN, 4)
    membrane(s, [(70, 170), (110, 168), (450, 168), (490, 170), (500, 300), (440, 420), (330, 450), (330, 560),
                 (230, 560), (230, 450), (120, 420), (60, 300)], closed=True, fill=POST)
    s.text(500, 40, "送り手", size=14, fill=SUB, anchor="end")
    s.text(76, 540, "受け手のスパイン", size=14, fill=SUB)
    ax, nx = 190, 350
    channel(s, ax, 170, MAIN)
    channel(s, nx, 170, FOCUS)
    s.text(ax - 26, 214, "AMPA", size=13, anchor="end", fill=MAIN, bold=True)
    s.text(nx + 26, 214, "NMDA", size=13, fill=FOCUS, bold=True)
    s.badge(40, 130, 1)
    s.text(60, 136, "放出", size=14)
    s.arrow(ax, 198, ax, 240, stroke=MAIN, sw=3)
    s.text(ax, 262, "Na → 脱分極", size=14, anchor="middle", fill=MAIN, bold=True)
    s.badge(ax - 60, 240, 2)
    s.arrow(nx, 198, nx, 240, stroke=FOCUS, sw=3.5)
    s.text(nx, 262, "Mg が抜け Ca", size=14, anchor="middle", fill=FOCUS, bold=True)
    s.badge(nx + 70, 240, 3)
    tag(s, 300, 320, "Ca・CaM", FOCUS)
    flow(s, [(nx, 272), (320, 300)], FOCUS)
    tag(s, 300, 380, "CaMKII", MAIN)
    s.arrow(300, 334, 300, 364, stroke=MAIN, sw=2.2)
    s.badge(236, 380, 4)
    # 5：リン酸化と挿入
    flow(s, [(262, 372), (215, 330), (198, 204)], MAIN, 2, "5 4")
    s.text(206, 300, "リン酸化", size=13, anchor="end", fill=MAIN)
    s.circle(420, 300, 18, fill="#ffffff", stroke=EDGE, sw=2)
    channel(s, 420, 300, MAIN, h=22, w=7, gap=4)
    flow(s, [(338, 388), (400, 360), (420, 318)], MAIN, 2)
    flow(s, [(438, 290), (462, 230), (440, 182)], MAIN, 2.4)
    channel(s, 430, 170, MAIN)
    s.text(470, 330, "小胞で運び", size=13, fill=MAIN)
    s.text(470, 348, "膜へ挿入", size=13, fill=MAIN)
    s.badge(490, 280, 5)
    s.note(40, 606, ["受容体が増え、同じ入力で", "受け手がより強く応える"])
    return s


# ---------------------------------------------------------------- 3-2
def branch():
    """3-5 同じNMDA受容体のCaでも、高く短いとLTP、低く長いとLTD。対照の2枚 横長 M 680x440。

    パネル k の x0 = 20 + 340*k。上に Ca の時間経過（小グラフ）、下にスパイン（膜 y=170）。
    """
    s = SVG(680, 440, "海馬では同じNMDA受容体からのCaでも、高く短いとCaMKIIを経てLTP、低く長いとカルシニューリンを経てLTD")
    for k, (title, col, trace, enz, act, res) in enumerate((
            ("高く短い Ca", MAIN, [(0, 0), (20, 0), (26, 1), (34, 0), (100, 0)], "CaMKII", "リン酸化・挿入", "LTP：強くなる"),
            ("低く長い Ca", WARN, [(0, 0), (20, 0), (24, 0.3), (84, 0.3), (88, 0), (100, 0)], "カルシニューリン",
             "脱リン酸化・回収", "LTD：弱くなる"))):
        x0 = 20 + 340 * k
        s.text(x0 + 10, 34, title, size=17, bold=True, fill=col)
        s.poly([(x0 + 180 + t * 1.3, 90 - v * 44) for t, v in trace], stroke=col, sw=3)
        s.line(x0 + 180, 90, x0 + 312, 90, stroke=MUTED)
        s.text(x0 + 246, 110, "時間", size=12, fill=SUB, anchor="middle")
        membrane(s, [(x0 + 30, 170), (x0 + 290, 170), (x0 + 300, 280), (x0 + 250, 360), (x0 + 200, 380),
                     (x0 + 200, 430), (x0 + 120, 430), (x0 + 120, 380), (x0 + 60, 350), (x0 + 20, 280)],
                 closed=True, fill=POST)
        channel(s, x0 + 110, 170, FOCUS)
        s.text(x0 + 110, 130, "NMDA", size=13, anchor="middle", fill=FOCUS, bold=True)
        s.arrow(x0 + 110, 198, x0 + 110, 226, stroke=FOCUS, sw=3)
        tag(s, x0 + 110, 250, enz, col, size=13)
        s.arrow(x0 + 110, 266, x0 + 110, 292, stroke=col, sw=2.2)
        s.text(x0 + 110, 314, act, size=13, anchor="middle", fill=col, bold=True)
        if k == 0:
            s.circle(x0 + 230, 260, 16, fill="#ffffff", stroke=EDGE, sw=1.8)
            channel(s, x0 + 230, 260, MAIN, h=20, w=6, gap=4)
            flow(s, [(x0 + 238, 242), (x0 + 250, 210), (x0 + 236, 190)], MAIN, 2.4)
            channel(s, x0 + 230, 170, MAIN)
        else:
            channel(s, x0 + 230, 170, WARN)
            flow(s, [(x0 + 230, 196), (x0 + 246, 226), (x0 + 234, 244)], WARN, 2.4)
            s.circle(x0 + 230, 260, 16, fill="#ffffff", stroke=EDGE, sw=1.8)
            channel(s, x0 + 230, 260, WARN, h=20, w=6, gap=4)
        s.text(x0 + 230, 130, "AMPA", size=13, anchor="middle", fill=col, bold=True)
        s.note(x0 + 10, 410, res, color=col)
    return s



# ---------------------------------------------------------------- 4-1
def dendrite_body(s, y_top, y_bot, x0, x1, spines=(), nucleus=None, fill=POST):
    """横に伸びる樹状突起（上辺にスパイン）と、右端（または左端）の細胞体。
    spines は (x, 高さ, 頭の半径)。nucleus は (cx, cy, r)。"""
    top = []
    x = x0
    for sx, h, r in sorted(spines):
        top += [(x, y_top), (sx - r * 0.9, y_top), (sx - 6, y_top - h * 0.5), (sx - r, y_top - h),
                (sx, y_top - h - r * 0.9), (sx + r, y_top - h), (sx + 6, y_top - h * 0.5), (sx + r * 0.9, y_top)]
        x = sx + r * 0.9
    top += [(x1, y_top)]
    membrane(s, top, fill=None)
    s.poly(sample(top) + [(x1, y_bot), (x0, y_bot)], fill=fill, stroke="none", closed=True)
    membrane(s, top)
    membrane(s, [(x0, y_bot), (x1, y_bot)], smooth=False)
    if nucleus:
        cx, cy, r = nucleus
        s.circle(cx, cy, r, fill="#f2f2f2", stroke=EDGE, sw=2, dash="7 4")
        s.text(cx, cy - r + 26, "核", size=15, anchor="middle", fill=SUB, bold=True)


def late_ltp():
    """4-2 スパインの信号がERKへ合流し、核のCREBを動かして新しいタンパク質を作る。横長 L 760x340。

    左端に活動したスパイン（x 70）、右端に核（中心 620,160、半径 100）。読み順 1〜4。
    """
    s = SVG(760, 340, "活動スパインのCa・CaMとcAMP・PKAの信号がERKへ合流し、核のCREBを介して新しいタンパク質を作る")
    membrane(s, [(40, 60), (90, 50), (130, 90), (200, 90), (500, 50), (620, 30), (740, 40), (740, 300),
                 (620, 290), (500, 270), (200, 240), (130, 240), (90, 270), (40, 260)], closed=True, fill=POST)
    s.circle(620, 160, 100, fill="#f2f2f2", stroke=EDGE, sw=2, dash="7 4")
    s.text(620, 86, "核", size=15, anchor="middle", fill=SUB, bold=True)
    s.text(50, 40, "活動したスパイン", size=14, fill=SUB)
    tag(s, 150, 130, "Ca・CaM", FOCUS)
    tag(s, 150, 200, "cAMP・PKA", FOCUS)
    s.badge(92, 164, 1)
    flow(s, [(210, 130), (260, 155), (292, 162)], FOCUS)
    flow(s, [(222, 200), (262, 176), (292, 168)], FOCUS)
    tag(s, 345, 165, "MAPK経路", MAIN)
    s.badge(345, 124, 2)
    s.arrow(398, 165, 432, 165, stroke=MAIN, sw=2.4)
    tag(s, 464, 165, "ERK", MAIN)
    flow(s, [(490, 165), (540, 155), (570, 140)], MAIN, 2.6)
    s.badge(540, 126, 3)
    tag(s, 600, 130, "CREB", MAIN)
    tag(s, 668, 130, "CBP", FOCUS, size=14)
    s.poly([(560 + i * 8, 172 + 5 * math.sin(i)) for i in range(15)], stroke=INK, sw=1.6, smooth=True)
    s.text(640, 196, "転写 → mRNA", size=14, anchor="middle")
    flow(s, [(620, 208), (620, 240), (620, 276)], MAIN, 2.6)
    s.badge(660, 260, 4)
    s.text(620, 324, "新しいタンパク質 → 後期LTP", size=15, anchor="middle", bold=True, fill=MAIN)
    s.note(40, 304, ["遠いスパインの信号が", "核の転写へ届く"])
    return s


# ---------------------------------------------------------------- 4-2
def tagging():
    """4-3 タグの付いたシナプスだけが、核から運ばれたタンパク質を捕獲する。横長 L 760x400。

    樹状突起 y 230..290（x 30..560）、右に細胞体と核。スパイン A x=110、B x=260、C x=410。
    """
    s = SVG(760, 400, "強い活動のAと弱い活動のBはタグを持ち、核から運ばれたタンパク質を捕獲するが、活動しなかったCでは通過する")
    dendrite_body(s, 230, 290, 30, 560, [(110, 90, 34), (260, 90, 30), (410, 90, 30)])
    membrane(s, [(560, 230), (600, 170), (700, 150), (740, 220), (720, 330), (620, 350), (560, 290)],
             fill=POST, smooth=True)
    s.circle(655, 250, 50, fill="#f2f2f2", stroke=EDGE, sw=2, dash="6 4")
    s.text(655, 256, "核", size=15, anchor="middle", fill=SUB, bold=True)
    for x, name, n, col in ((110, "強い活動 A", 3, MAIN), (260, "弱い活動 B", 1, MAIN), (410, "活動なし C", 0, MUTED)):
        s.text(x, 60, name, size=15, anchor="middle", bold=True, fill=INK if n else SUB)
        for k in range(n):
            s.poly([(x - 14 + 14 * k, 70), (x - 20 + 14 * k, 86), (x - 12 + 14 * k, 86), (x - 18 + 14 * k, 102)],
                   stroke=MAIN, sw=2.4)
        if n:
            s.line(x + 24, 196, x + 24, 168, stroke=INK, sw=1.6)
            s.poly([(x + 24, 168), (x + 42, 174), (x + 24, 180)], fill=FOCUS, stroke=FOCUS, closed=True)
            s.text(x + 46, 196, "タグ", size=14, fill=FOCUS, bold=True)
    flow(s, [(610, 290), (500, 262), (330, 262), (140, 262)], MAIN, 2.6)
    for x in (110, 260):
        flow(s, [(x + 6, 262), (x, 210), (x, 170)], MAIN, 2.2)
        dots(s, [(x - 8, 150), (x + 6, 144), (x - 2, 160)], MAIN, 4)
        s.text(x - 36, 222, "捕獲", size=14, fill=MAIN, anchor="end")
    s.text(410, 320, "通過", size=14, anchor="middle", fill=SUB, bold=True)
    s.text(470, 312, "新しいタンパク質", size=14, fill=MAIN)
    dots(s, [(560, 280), (580, 276), (596, 286)], MAIN, 4)
    s.note(30, 370, "荷物は全体へ流れ、受け取るのはタグのある接点だけ")
    return s


# ---------------------------------------------------------------- 4-3
def arc():
    """4-4 核から運ばれたArc mRNAが樹状突起で局所翻訳され、AMPA受容体の回収を助ける。横長 L 760x440。

    樹状突起 y 180..300（x 40..740）、左端に核。活動したスパイン x=560（上に送り手）。
    下段 y 360..430：恒常性調節（多くの接点で回収）。
    """
    s = SVG(760, 440, "核で転写されたArc mRNAが活動シナプスの近くで翻訳され、ArcがAMPA受容体の回収を助ける")
    dendrite_body(s, 180, 300, 40, 740, [(220, 60, 24), (380, 60, 24), (560, 70, 30)])
    s.circle(40, 240, 70, fill="#f2f2f2", stroke=EDGE, sw=2, dash="7 4")
    s.text(40, 246, "核", size=15, fill=SUB, bold=True)
    membrane(s, [(510, 20), (520, 60), (560, 76), (600, 60), (610, 20)], fill=PRE)
    for i, x in enumerate((140, 220, 300, 380, 450)):
        s.circle(x, 250, 7, fill=FOCUS, stroke="#ffffff", sw=1.5)
    flow(s, [(120, 250), (300, 250), (470, 250)], FOCUS, 2)
    s.text(150, 284, "Arc mRNA を運ぶ", size=14, fill=FOCUS, bold=True)
    s.badge(96, 222, 1)
    for i in range(4):
        s.circle(500 + 16 * i, 212, 7, fill=TINT[MAIN], stroke=MAIN, sw=1.4)
    s.poly([(488 + 5 * i, 222 + 3 * math.sin(i)) for i in range(15)], stroke=FOCUS, sw=1.6, smooth=True)
    s.text(530, 240, "局所翻訳", size=14, anchor="middle", fill=MAIN, bold=True)
    s.badge(470, 206, 2)
    channel(s, 560, 108, WARN, h=30, w=9, gap=5)
    flow(s, [(574, 124), (606, 150), (596, 180)], WARN, 2.4)
    s.circle(596, 196, 16, fill="#ffffff", stroke=EDGE, sw=1.6)
    channel(s, 596, 196, WARN, h=18, w=6, gap=4)
    s.text(624, 176, "AMPA受容体を回収", size=14, fill=WARN, bold=True)
    s.badge(680, 140, 3)
    s.text(40, 350, "細胞全体の活動が高いとき（恒常性調節）", size=14, fill=SUB, bold=True)
    for i in range(9):
        x = 60 + 76 * i
        channel(s, x, 392, WARN, h=20, w=6, gap=4)
        s.arrow(x + 16, 384, x + 26, 412, stroke=WARN, sw=1.6)
    s.line(30, 392, 730, 392, stroke=EDGE, sw=3)
    s.note(420, 430, "多くの接点が少しずつ下がる", color=WARN)
    return s


# ---------------------------------------------------------------- 4-4
def bdnf():
    """4-5 BDNFの正のフィードバック。輪の形 正方 M 580x540。

    スパイン（左上）→ TrkB → ERK → 核内の CREB・転写 → 核外へ mRNA → 翻訳 → 分泌で戻る。読み順1〜5。
    核は下（中心 330,440、半径 110）。
    """
    s = SVG(580, 540, "分泌されたBDNFがTrkBとERKを介して核内CREBを動かし、核外で翻訳された新しいBDNFが分泌へ戻る")
    membrane(s, [(40, 120), (60, 80), (130, 70), (190, 110), (330, 150), (560, 150), (560, 540), (40, 540)],
             closed=False, fill=POST)
    s.circle(330, 450, 100, fill="#f2f2f2", stroke=EDGE, sw=2, dash="7 4")
    s.text(330, 372, "核", size=15, anchor="middle", fill=SUB, bold=True)
    dots(s, [(150, 36), (176, 28), (204, 40)], MAIN, 6)
    s.text(150, 20, "BDNF", size=15, fill=MAIN, bold=True, anchor="end")
    for dx in (0, 22):
        channel(s, 230 + dx, 118, MAIN, h=34, w=7, gap=4)
    s.text(270, 108, "TrkB", size=15, fill=MAIN, bold=True)
    flow(s, [(190, 44), (222, 70), (236, 100)], MAIN)
    s.badge(262, 64, 1)
    tag(s, 240, 210, "ERK", MAIN)
    s.arrow(240, 142, 240, 194, stroke=MAIN, sw=2.4)
    s.badge(284, 210, 2)
    tag(s, 300, 420, "CREB → 転写", MAIN)
    flow(s, [(240, 226), (250, 320), (286, 404)], MAIN, 2.4)
    s.badge(230, 380, 3)
    s.poly([(390 + 6 * i, 470 + 5 * math.sin(i * 1.2)) for i in range(12)], stroke=FOCUS, sw=2, smooth=True)
    s.text(420, 500, "BDNF mRNA", size=14, anchor="middle", fill=FOCUS, bold=True)
    flow(s, [(456, 460), (470, 380), (480, 330)], FOCUS, 2.4)
    s.text(490, 380, "核の外へ", size=13, fill=FOCUS)
    tag(s, 480, 310, "翻訳", MAIN)
    s.badge(530, 300, 4)
    flow(s, [(480, 292), (440, 200), (300, 80), (220, 44)], FOCUS, 3)
    s.text(400, 116, "新しいBDNFを分泌", size=14, fill=FOCUS, bold=True)
    s.badge(350, 92, 5)
    s.note(40, 300, ["分子は入れ替わっても", "回り方が状態を保つ"])
    return s


# ---------------------------------------------------------------- 7-1
def amygdala():
    """7-2 音と痛みが扁桃体の同じニューロンへ収束し、ノルアドレナリンが別経路で固定化を修飾する。横長 M 680x440。

    ニューロン（中心 330,220）。左から音（上）と痛み（下）、右上から青斑核のノルアドレナリン。
    """
    s = SVG(680, 440, "音と痛みは外側扁桃体の同じニューロンへ収束し、ノルアドレナリンは別経路から固定化を強める")
    for a in (200, 150, 250, 100, 300, 20, 60):
        r = math.radians(a)
        tree(s, 330 + 40 * math.cos(r), 220 + 40 * math.sin(r), r, 40, 2, 5, spread=0.5)
    s.poly([(292, 220), (310, 184), (350, 182), (372, 214), (360, 254), (318, 262)], fill="#ececec",
           stroke=EDGE, sw=2, closed=True, smooth=True)
    s.text(330, 76, "外側扁桃体のニューロン", size=14, anchor="middle", fill=SUB)
    s.poly([(20, 120), (150, 124), (240, 170)], stroke=MAIN, sw=6, smooth=True)
    s.circle(248, 176, 10, fill=MAIN, stroke="none")
    s.text(24, 108, "音の線", size=15, fill=MAIN, bold=True)
    s.text(24, 146, "強くなる", size=13, fill=MAIN)
    s.poly([(20, 330), (150, 322), (240, 266)], stroke=INK, sw=3, smooth=True)
    s.circle(248, 260, 9, fill=INK, stroke="none")
    s.text(24, 306, "痛みの線", size=15, bold=True)
    s.text(150, 222, "同時に活動", size=13, anchor="middle", fill=SUB)
    s.text(150, 240, "→ NMDA依存LTP", size=13, anchor="middle", fill=SUB)
    s.circle(610, 50, 24, fill="#ececec", stroke=EDGE, sw=2)
    s.text(570, 30, "青斑核", size=14, anchor="end", fill=SUB, bold=True)
    s.poly([(596, 70), (520, 130), (410, 170)], stroke=FOCUS, sw=3, smooth=True, dash="7 4")
    s.circle(402, 174, 8, fill=FOCUS, stroke="none")
    s.text(510, 110, "ノルアドレナリン", size=14, fill=FOCUS, bold=True)
    tag(s, 540, 214, "β受容体", FOCUS, size=13)
    for i, t in enumerate(("cAMP・PKA", "ERK", "CREB")):
        tag(s, 540, 264 + 44 * i, t, FOCUS, size=13)
        s.arrow(540, 230 + 44 * i, 540, 248 + 44 * i, stroke=FOCUS, sw=2)
    s.text(540, 420, "固定化を強める", size=15, anchor="middle", fill=FOCUS, bold=True)
    s.arrow(540, 374, 540, 402, stroke=FOCUS, sw=2)
    s.note(24, 420, "情報の線と、修飾の号令は別の道")
    return s


# ---------------------------------------------------------------- 7-2
def striatum():
    """7-3 送り手と受け手の発火が残す数秒のトレースに、ドーパミンが重なると書き込みが確定する。
    横長 M 660x420。上段は時間のグラフ（x: 0秒 → 90、6秒 → 600）、下段は細胞内の反応。
    """
    s = SVG(660, 420, "送り手と受け手の発火が数秒の適格度トレースを残し、その間にドーパミンが届くと書き込みが確定する")
    X = lambda t: 90 + t * 85
    s.rect(X(0.5), 40, X(3.5) - X(0.5), 160, fill=TINT[MAIN], stroke="none")
    s.text(24, 34, "時間（秒）", size=14, fill=SUB)
    for i, (lab, t, col) in enumerate((("送り手", 0.3, MAIN), ("受け手", 0.5, MAIN))):
        y = 70 + 36 * i
        s.text(80, y + 5, lab, size=14, anchor="end")
        s.line(X(0), y, X(6), y, stroke=MUTED)
        s.poly([(X(t) - 4, y), (X(t), y - 20), (X(t) + 4, y)], stroke=col, sw=2.4)
    y0 = 200
    s.text(80, y0 - 20, "トレース", size=14, anchor="end", fill=MAIN, bold=True)
    s.line(X(0), y0, X(6), y0, stroke=MUTED)
    s.poly([(X(0.5), y0)] + [(X(0.5 + t / 10), y0 - 56 * math.exp(-t / 10 / 1.2)) for t in range(56)],
           stroke=MAIN, sw=3)
    s.text(X(2), 34, "数秒の窓", size=14, anchor="middle", fill=MAIN, bold=True)
    s.line(X(2.4), 50, X(2.4), y0, stroke=FOCUS, sw=3)
    s.circle(X(2.4), 50, 6, fill=FOCUS, stroke="none")
    s.text(X(2.4) + 10, 56, "ドーパミン", size=14, fill=FOCUS, bold=True)
    s.line(X(5), 90, X(5), y0, stroke=MUTED, sw=2, dash="4 4")
    s.text(X(5), 84, "遅すぎる", size=13, anchor="middle", fill=SUB)
    xs = (110, 250, 390)
    for x, t in zip(xs, ("D1受容体", "cAMP・PKA", "DARPP-32")):
        tag(s, x, 270, t, FOCUS, size=13)
    s.arrow(160, 270, 196, 270, stroke=FOCUS, sw=2)
    s.arrow(310, 270, 336, 270, stroke=FOCUS, sw=2)
    tag(s, 560, 270, "ホスファターゼ", WARN, size=13)
    s.line(446, 270, 492, 270, stroke=WARN, sw=2.4)
    s.line(492, 260, 492, 280, stroke=WARN, sw=2.4)
    s.text(470, 300, "抑える", size=13, anchor="middle", fill=WARN)
    s.note(24, 360, ["窓の中に3つ目の条件が来たら、", "リン酸化された状態が消えにくくなる"])
    return s


# ---------------------------------------------------------------- 7-3
def cerebellum():
    """7-4 平行線維と登上線維が時間窓で重なると、AMPA受容体が回収されてLTDが起き、下流のブレーキが緩む。
    縦長 M 600x600。上：プルキンエ細胞と2種の入力、中：膜での回収、下：回路の帰結。
    """
    s = SVG(600, 600, "平行線維と登上線維の活動が重なるとAMPA受容体が回収されてLTDが起き、プルキンエ細胞の抑制が緩んでまばたきが出る")
    cx = 380
    for a in (-60, -80, -100, -120):
        r = math.radians(a)
        tree(s, cx, 200, r, 60, 3, 5, spread=0.35)
    s.poly([(cx - 22, 206), (cx - 16, 240), (cx, 250), (cx + 16, 240), (cx + 22, 206)], fill="#ececec",
           stroke=EDGE, sw=2, closed=True, smooth=True)
    s.line(cx, 250, cx, 290, stroke=EDGE, sw=4)
    s.text(cx + 30, 240, "プルキンエ細胞", size=14, fill=SUB)
    for i in range(3):
        s.arrow(20, 70 + 22 * i, 520, 70 + 22 * i, stroke=MAIN, sw=2)
    s.text(24, 56, "平行線維：状況と時刻", size=14, fill=MAIN, bold=True)
    s.poly([(560, 290), (520, 200), (470, 150), (430, 110), (410, 70)], stroke=FOCUS, sw=4, smooth=True)
    s.text(470, 300, "登上線維", size=14, fill=FOCUS, bold=True)
    s.text(470, 318, "誤差信号", size=13, fill=FOCUS)
    s.zoom((392, 60, 30, 30), (20, 150, 250, 170))
    s.rect(20, 150, 250, 60, fill=PRE, stroke="none")
    membrane(s, [(20, 210), (270, 210)], smooth=False)
    s.rect(20, 214, 250, 104, fill=POST, stroke="none")
    channel(s, 80, 210, MUTED, h=30, w=9, gap=5)
    s.text(80, 172, "代謝型", size=12, anchor="middle", fill=SUB)
    s.text(80, 188, "グルタミン酸受容体", size=12, anchor="middle", fill=SUB)
    tag(s, 110, 260, "PKC", WARN, size=13)
    s.arrow(84, 228, 100, 244, stroke=WARN, sw=1.8)
    channel(s, 200, 210, WARN, h=30, w=9, gap=5)
    flow(s, [(208, 228), (222, 256), (214, 276)], WARN, 2.4)
    s.circle(210, 292, 16, fill="#ffffff", stroke=EDGE, sw=1.6)
    channel(s, 210, 292, WARN, h=18, w=6, gap=4)
    s.text(146, 304, "AMPA受容体を回収", size=13, anchor="end", fill=WARN, bold=True)
    s.text(24, 344, "LTD：平行線維からの入力が弱まる", size=14, fill=WARN, bold=True)
    y = 450
    s.circle(120, y, 30, fill="#ececec", stroke=EDGE, sw=2)
    s.text(120, y + 52, "プルキンエ細胞", size=13, anchor="middle", fill=SUB)
    s.circle(330, y, 30, fill="#ececec", stroke=EDGE, sw=2)
    s.text(330, y + 52, "小脳核", size=13, anchor="middle", fill=SUB)
    s.line(152, y, 294, y, stroke=WARN, sw=3, dash="8 5")
    s.line(296, y - 12, 296, y + 12, stroke=WARN, sw=3)
    s.text(224, y - 12, "抑制が緩む", size=14, anchor="middle", fill=WARN, bold=True)
    s.arrow(362, y, 450, y, stroke=MAIN, sw=3)
    s.text(460, y + 6, "まばたき", size=15, fill=MAIN, bold=True)
    s.note(24, 580, "弱めることが、出力を出すことになる")
    return s


# ---------------------------------------------------------------- 8-1
def pruning():
    """8-4 補体で印を付けられた弱いシナプスだけを、ミクログリアが貪食する。正方 M 600x560。

    受け手の樹状突起は縦（x 300..348）。左から強い接点（y 130）と弱い接点（y 360）。
    ミクログリアは左下（中心 140,480）から突起を伸ばし、弱い接点を下から包む。
    """
    s = SVG(600, 560, "活動の強いシナプスは残り、補体の印が付いた弱いシナプスだけをミクログリアが貪食する")
    membrane(s, [(300, 0), (298, 560), (350, 560), (348, 0)], closed=True, fill="#f0f0f0", smooth=False)
    s.text(360, 40, "受け手の樹状突起", size=14, fill=SUB)
    membrane(s, [(20, 110), (170, 110), (230, 80), (280, 110), (286, 150), (230, 180), (170, 150), (20, 150)],
             fill=TINT[MAIN])
    for x in (200, 236):
        vesicle(s, x, 130, 10, MAIN)
    s.text(24, 96, "活動が強い", size=15, fill=MAIN, bold=True)
    s.arrow(360, 130, 408, 130, stroke=MAIN, sw=3)
    s.text(420, 136, "残る", size=17, fill=MAIN, bold=True)
    membrane(s, [(20, 340), (170, 340), (230, 312), (280, 340), (286, 380), (230, 410), (170, 380), (20, 380)],
             fill="#f7f7f7")
    s.text(24, 326, "活動が弱い", size=15, fill=SUB, bold=True)
    for x, y, a in ((236, 306, 0), (272, 318, 0.6), (190, 420, 3.1), (244, 420, 3.1)):
        dx, dy = math.sin(a), -math.cos(a)
        s.line(x, y, x + 12 * dx, y + 12 * dy, stroke=WARN, sw=2)
        s.poly([(x + 18 * dx - 6 * dy, y + 18 * dy + 6 * dx), (x + 12 * dx, y + 12 * dy),
                (x + 18 * dx + 6 * dy, y + 18 * dy - 6 * dx)], stroke=WARN, sw=2)
    s.text(150, 288, "補体の印", size=15, fill=WARN, bold=True)
    s.poly([(140, 430), (210, 440), (240, 490), (200, 540), (100, 545), (50, 500), (70, 450)],
           fill=TINT[FOCUS], stroke=FOCUS, sw=2, closed=True, smooth=True)
    s.poly([(190, 440), (220, 424), (262, 418), (292, 396)], stroke=FOCUS, sw=8, smooth=True)
    s.poly([(110, 432), (120, 400), (150, 392), (170, 386)], stroke=FOCUS, sw=8, smooth=True)
    s.circle(140, 494, 18, fill="#f0c890", stroke=FOCUS, sw=1.4)
    s.text(250, 520, "ミクログリア", size=15, fill=FOCUS, bold=True)
    s.text(380, 440, "補体受容体で印を認識し、", size=14, fill=FOCUS)
    s.text(380, 460, "弱い接点を包んで食べる", size=14, fill=FOCUS)
    s.note(24, 230, ["印が付くのは", "弱い接点だけ"], color=WARN)
    return s


FIGS = {
    "fig1-neuron-overview": neuron, "fig2a-nmda-gate": nmda_gate, "fig2-early-ltp": early_ltp,
    "fig3-ltp-ltd-branch": branch, "fig4-late-ltp-nucleus": late_ltp, "fig5-synaptic-tagging": tagging,
    "fig6-local-translation-arc": arc, "fig7-bdnf-feedback": bdnf, "fig8-amygdala-circuit": amygdala,
    "fig9-striatum-three-factor": striatum, "fig10-cerebellar-ltd": cerebellum, "fig11-complement-pruning": pruning,
}

if __name__ == "__main__":
    sys.exit(build({OUT / f"{k}.svg": v for k, v in FIGS.items()}))
