#!/usr/bin/env python3
"""electromagnetism の図。

色：青=電場と電荷／黒=磁場（細い実線）／橙=その図で見る1か所（エネルギーの流れ、答え）／
赤=やる夫の誤った読み。灰は導線・目盛・補助。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/electromagnetism/figs"


def into_page(s, x, y, r=8, col=INK):
    """紙面の奥へ向かう矢（丸にバツ）。"""
    s.circle(x, y, r, fill="#ffffff", stroke=col, sw=1.4)
    d = r * 0.6
    s.line(x - d, y - d, x + d, y + d, stroke=col, sw=1.4)
    s.line(x - d, y + d, x + d, y - d, stroke=col, sw=1.4)


def gauss():
    """1-3 半径を2倍にしても、球面を貫く電気力線の本数は同じ。正方 S 440x440。

    点電荷 (220, 230)、線 16本。球面（断面の円）半径 70 と 140。
    """
    cx, cy = 220, 230
    n = 16
    s = SVG(440, 440, "点電荷から出る電気力線は途中で消えないので、半径を2倍にしても球面を貫く本数は同じ")
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        s.arrow(cx + 16 * math.cos(t), cy + 16 * math.sin(t), cx + 190 * math.cos(t),
                cy + 190 * math.sin(t), stroke=MAIN, sw=1.6)
    for r, col, sw in ((70, INK, 2.2), (140, FOCUS, 3)):
        s.circle(cx, cy, r, stroke=col, sw=sw, dash="6 4")
    s.circle(cx, cy, 12, fill=MAIN, stroke="#ffffff", sw=2)
    s.text(cx, cy + 5, "+", size=16, fill="#ffffff", anchor="middle", bold=True)
    s.text(cx + 52, cy - 58, "r", size=16, bold=True, halo=True)
    s.text(cx + 104, cy - 112, "2r", size=16, fill=FOCUS, bold=True, halo=True)
    s.note(24, 36, ["どちらの球面も16本", "面積4倍・電場1/4"])
    return s


def magnet():
    """3-1 磁力線は外でNからS、中でSからNへ通って必ず閉じる。切ると両方に極が現れる。M 560x440。

    磁石：中心 (280, 180)、長さ 120、太さ 36、右がN。外の線はNの端面から出てSの端面へ入る閉じた曲線（高さ 60, 100, 140、模式）。
    下段：切った2本の磁石 y 380、新しくできた極を橙で。
    """
    cx, cy, hl, ht = 280, 180, 60, 18
    s = SVG(560, 440, "磁力線は磁石の外でNからSへ、中でSからNへ通って必ず閉じる。切った断面には新しい極が現れる")
    for H, off, W in ((60, 6, 30), (100, 10, 55), (140, 14, 80)):
        for sign in (1, -1):
            pts = [(cx + hl, cy - sign * off), (cx + hl + W, cy - sign * (off + H * 0.3)),
                   (cx + hl + W * 0.6, cy - sign * H * 0.85), (cx, cy - sign * H),
                   (cx - hl - W * 0.6, cy - sign * H * 0.85), (cx - hl - W, cy - sign * (off + H * 0.3)),
                   (cx - hl, cy - sign * off)]
            s.poly(pts, stroke=INK, sw=1.4, smooth=True)
            s.arrow(cx + 6, cy - sign * H, cx - 6, cy - sign * H, stroke=INK, sw=1.6)
    s.rect(cx - hl, cy - ht, hl, 2 * ht, fill="#ffffff", stroke=INK, sw=1.6)
    s.rect(cx, cy - ht, hl, 2 * ht, fill=TINT[MUTED], stroke=INK, sw=1.6)
    for dy in (-8, 8):
        s.arrow(cx - hl + 8, cy + dy, cx + hl - 8, cy + dy, stroke=INK, sw=1.4, dash="4 3")
    s.text(cx - hl + 14, cy + 6, "S", size=16, bold=True)
    s.text(cx + hl - 14, cy + 6, "N", size=16, bold=True, anchor="end")
    s.text(cx, cy + ht + 20, "中は S→N", size=14, fill=SUB, anchor="middle", halo=True)
    # 切った後
    y = 380
    for x0 in (160, 320):
        s.rect(x0, y - 16, 40, 32, fill="#ffffff", stroke=INK, sw=1.6)
        s.rect(x0 + 40, y - 16, 40, 32, fill=TINT[MUTED], stroke=INK, sw=1.6)
    s.text(172, y + 6, "S", size=15, bold=True)
    s.text(228, y + 6, "N", size=15, bold=True, fill=FOCUS)
    s.text(332, y + 6, "S", size=15, bold=True, fill=FOCUS)
    s.text(388, y + 6, "N", size=15, bold=True)
    s.line(280, y - 34, 280, y + 34, stroke=WARN, sw=2, dash="5 4")
    s.text(280, y + 54, "切ると、切り口に新しい極", size=14, fill=FOCUS, anchor="middle", bold=True)
    s.note(24, 36, ["線は必ず閉じる", "湧き出し口がない"])
    return s


def lenz():
    """4-2 誘導電流は磁束の変化に逆らう向きに流れる。小さな多数 L 760x300。

    3コマ（近づける／止める／遠ざける）、左上 (20 + 250*i, 40)、幅 230。
    磁石は左から N をコイルへ向ける。コイル（x +120〜+200）の左の面の極と、誘導電流の向きを描く。
    """
    s = SVG(760, 300, "磁石を近づけるとコイルは押し返す向き、遠ざけると引き止める向きに電流が流れ、止めると流れない")
    heads = [("近づける", "+0.8 mA", "N"), ("止める", "0 mA", None), ("遠ざける", "−0.8 mA", "S")]
    for i, (hd, amp, face) in enumerate(heads):
        x0 = 20 + 250 * i
        s.badge(x0 + 14, 36, i + 1)
        s.text(x0 + 34, 42, hd, size=16, bold=True)
        s.rect(x0, 70, 230, 170, fill="#ffffff", stroke=MUTED)
        my = 155
        mx = x0 + 20
        s.rect(mx, my - 16, 36, 32, fill="#ffffff", stroke=INK, sw=1.6)
        s.rect(mx + 36, my - 16, 36, 32, fill=TINT[MUTED], stroke=INK, sw=1.6)
        s.text(mx + 10, my + 6, "S", size=14, bold=True)
        s.text(mx + 54, my + 6, "N", size=14, bold=True)
        if i != 1:
            d = 1 if i == 0 else -1
            s.arrow(mx + 36 - 20 * d, my + 34, mx + 36 + 20 * d, my + 34, stroke=INK, sw=2)
        cx0 = x0 + 120
        for k in range(5):
            s.poly([(cx0 + 16 * k, my - 34), (cx0 + 16 * k + 8, my), (cx0 + 16 * k, my + 34)],
                   stroke=MUTED, sw=2, smooth=True)
        s.rect(cx0 - 6, my - 38, 84, 76, stroke=MUTED, sw=1, dash="3 3")
        if face:
            s.text(cx0 - 12, my - 44, face, size=16, fill=FOCUS, bold=True, anchor="middle")
            d = -1 if face == "N" else 1
            s.arrow(cx0 + 36 - 26 * d, my, cx0 + 36 + 26 * d, my, stroke=FOCUS, sw=3.5)
        s.text(x0 + 115, 268, amp, size=16, fill=FOCUS if face else SUB, anchor="middle", bold=True)
    s.text(20, 294, "橙の矢印：誘導電流が作る磁場の向き", size=14, fill=FOCUS)
    s.note(500, 294, "変化に逆らう向き", size=15)
    return s


def poynting():
    """5-2 エネルギーは導線の中ではなく、まわりの空間を通って抵抗へ流れ込む。M 620x380（模式）。

    回路：電池 x 80、抵抗 x 520、上の導線 y 100（+）、下の導線 y 280（−）。
    導線の間：電場は上→下（青）、磁場は紙面の奥（丸にバツ）、S = E×B は右向き（橙）。
    """
    s = SVG(620, 380, "導線の間の空間で電場は下向き、磁場は紙面の奥向きなので、エネルギーの流れは右へ進んで抵抗へ入る")
    s.line(80, 100, 520, 100, stroke=MUTED, sw=4)
    s.line(80, 280, 520, 280, stroke=MUTED, sw=4)
    s.line(80, 100, 80, 160, stroke=MUTED, sw=4)
    s.line(80, 220, 80, 280, stroke=MUTED, sw=4)
    s.line(60, 160, 100, 160, stroke=INK, sw=3)
    s.line(70, 172, 90, 172, stroke=INK, sw=5)
    s.line(60, 208, 100, 208, stroke=INK, sw=3)
    s.line(70, 220, 90, 220, stroke=INK, sw=5)
    s.text(40, 194, "電池", size=15, anchor="end")
    s.line(520, 100, 520, 140, stroke=MUTED, sw=4)
    s.line(520, 240, 520, 280, stroke=MUTED, sw=4)
    s.rect(506, 140, 28, 100, fill=TINT[FOCUS], stroke=INK, sw=2)
    s.text(548, 194, "抵抗", size=15)
    s.text(300, 84, "+（電位が高い）", size=14, fill=SUB, anchor="middle")
    s.text(300, 308, "−（電位が低い）", size=14, fill=SUB, anchor="middle")
    s.arrow(200, 96, 240, 96, stroke=INK, sw=1.4)
    s.arrow(240, 284, 200, 284, stroke=INK, sw=1.4)
    for x in (150, 250, 350, 450):
        s.arrow(x, 112, x, 150, stroke=MAIN, sw=2)
        into_page(s, x + 26, 238)
    s.text(138, 138, "E", size=16, fill=MAIN, bold=True, anchor="end")
    s.text(176, 264, "B（奥へ）", size=14, anchor="middle")
    for y in (160, 190, 220):
        s.arrow(140, y, 460, y, stroke=FOCUS, sw=3.5 if y == 190 else 2)
    s.poly([(460, 160), (488, 170), (504, 180)], stroke=FOCUS, sw=2, smooth=True, arrow=True)
    s.poly([(460, 220), (488, 210), (504, 200)], stroke=FOCUS, sw=2, smooth=True, arrow=True)
    s.text(300, 206, "S = E×B", size=16, fill=FOCUS, anchor="middle", bold=True, halo=True)
    s.text(596, 368, "模式図", size=14, fill=SUB, anchor="end")
    s.note(24, 352, "エネルギーはまわりの空間を通って抵抗へ入る", size=15)
    return s


def displacement():
    """5-3 同じ輪 C に張った2つの面：平らな面は電流が貫き、風船の面は変化する電場が貫く。M 620x360。

    導線 y 180、左から右へ電流。コンデンサの極板 x 330 と 370。輪 C は x 200 の縦長の楕円。
    平らな面：輪 C に張った円板。風船の面：輪 C から左の極板を包んで隙間を通る。
    """
    s = SVG(620, 360, "同じ輪に張った面でも、平らな面は電流が貫き、隙間を通る風船の面は変化する電場が貫く")
    s.line(24, 180, 330, 180, stroke=MUTED, sw=4)
    s.line(370, 180, 596, 180, stroke=MUTED, sw=4)
    s.arrow(60, 168, 120, 168, stroke=INK, sw=2)
    s.text(90, 158, "電流 I", size=15, anchor="middle")
    s.rect(326, 100, 8, 160, fill=INK, stroke="none")
    s.rect(366, 100, 8, 160, fill=INK, stroke="none")
    for y in (120, 150, 210, 240):
        s.arrow(338, y, 362, y, stroke=MAIN, sw=2)
    s.text(350, 324, "電場が増える", size=14, fill=MAIN, anchor="middle", bold=True)
    s.poly([(200 + 26 * math.cos(t), 180 + 70 * math.sin(t)) for t in (2 * math.pi * k / 60 for k in range(61))],
           fill=TINT[MUTED], stroke=INK, sw=2.4)
    s.text(174, 102, "輪 C", size=16, bold=True, anchor="end")
    s.text(150, 280, ["平らな面：", "電流が貫く"], size=14, anchor="middle")
    s.poly([(200, 110), (260, 76), (338, 74), (352, 120), (352, 240), (338, 286), (260, 284), (200, 250)],
           stroke=FOCUS, sw=3, dash="7 5", smooth=True)
    s.text(420, 60, ["風船の面：隙間を通る", "電子は貫かない"], size=14, fill=FOCUS, bold=True)
    s.note(24, 40, ["電場の変化が", "電流の代わりをする"], size=15)
    return s


def wave():
    """6-3 電場と磁場は互いに直交し、同じ位相で進む。横長 L 760x340（斜めから見た模式）。

    進む向き x：原点 (80, 180) から右へ 1波長 = 300 px、2波長。
    y（上）が電場、z（手前左下へ傾けた軸、(-0.5, 0.35) 方向）が磁場。振幅 90。
    """
    ox, oy, lam, amp = 80, 180, 300, 90
    zx, zy = -0.35, 0.45
    s = SVG(760, 340, "真空を進む電磁波では、電場と磁場が互いに直交し、同じ位相で振動しながら E×B の向きへ進む")
    s.arrow(ox - 20, oy, 720, oy, stroke=INK, sw=1.6)
    s.text(726, oy + 5, "x", size=15, fill=SUB)
    s.text(740, 326, "x の向きへ進む（E×B）", size=15, anchor="end", bold=True)
    xs = [k * 4 for k in range(0, 151)]
    E = [(ox + x, oy - amp * math.sin(2 * math.pi * x / lam)) for x in xs]
    Bp = [(ox + x + zx * amp * math.sin(2 * math.pi * x / lam), oy + zy * amp * math.sin(2 * math.pi * x / lam))
          for x in xs]
    for x in range(0, 601, 25):
        v = math.sin(2 * math.pi * x / lam)
        s.line(ox + x, oy, ox + x, oy - amp * v, stroke=MAIN, sw=1)
        s.line(ox + x, oy, ox + x + zx * amp * v, oy - zy * amp * v * -1, stroke=INK, sw=1, dash="3 2")
    s.poly(E, stroke=MAIN, sw=3)
    s.poly(Bp, stroke=INK, sw=2.4)
    s.text(ox + lam / 4 + 8, oy - amp - 8, "電場 E", size=16, fill=MAIN, bold=True)
    s.text(ox + lam / 4 + zx * amp + 14, oy + zy * amp + 26, "磁場 B", size=16, bold=True)
    s.arrow(ox, oy, ox, oy - 120, stroke=SUB, sw=1.2)
    s.arrow(ox, oy, ox + zx * 110, oy + zy * 110, stroke=SUB, sw=1.2)
    s.text(ox + 6, oy - 124, "y", size=14, fill=SUB)
    s.text(ox + zx * 110 - 6, oy + zy * 110 + 16, "z", size=14, fill=SUB, anchor="end")
    s.circle(ox + lam / 4, oy - amp, 6, fill=FOCUS, stroke="#ffffff", sw=2)
    s.circle(ox + lam / 4 + zx * amp, oy + zy * amp, 6, fill=FOCUS, stroke="#ffffff", sw=2)
    s.note(430, 40, ["山と山が同じ場所にある", "（同じ位相、E = cB）"], size=15)
    return s


def lc():
    """7-2 エネルギーは電場（コンデンサ）と磁場（コイル）の間を往復する。小さな多数 L 760x300。

    4コマ、左上 (20 + 185*i, 50)、幅 170。コンデンサ（左）とコイル（右）を輪につなぐ。
    下にエネルギーの棒：左が電場、右が磁場。
    """
    s = SVG(760, 300, "LC回路ではエネルギーがコンデンサの電場とコイルの磁場の間を往復し、電流の向きが入れ替わる")
    states = [("電場に満タン", 1, 0, 0), ("磁場に満タン", 0, 1, 1), ("逆向きに満タン", -1, 0, 0),
              ("逆向きの磁場", 0, 1, -1)]
    for i, (hd, q, ub, cur) in enumerate(states):
        x0 = 20 + 185 * i
        s.badge(x0 + 14, 30, i + 1)
        s.text(x0 + 32, 36, hd, size=15, bold=True)
        s.rect(x0, 50, 170, 170, fill="#ffffff", stroke=MUTED)
        lx, rx, ty, by = x0 + 40, x0 + 130, 80, 190
        s.poly([(lx, 125), (lx, ty), (rx, ty), (rx, 105)], stroke=MUTED, sw=2)
        s.poly([(lx, 145), (lx, by), (rx, by), (rx, 165)], stroke=MUTED, sw=2)
        s.line(lx - 16, 125, lx + 16, 125, stroke=INK, sw=3)
        s.line(lx - 16, 145, lx + 16, 145, stroke=INK, sw=3)
        if q:
            top, bot = ("+", "−") if q > 0 else ("−", "+")
            s.text(lx - 26, 128, top, size=16, fill=MAIN, bold=True, anchor="middle")
            s.text(lx - 26, 156, bot, size=16, fill=MAIN, bold=True, anchor="middle")
            s.arrow(lx, 128 if q > 0 else 142, lx, 142 if q > 0 else 128, stroke=MAIN, sw=2)
        for k in range(4):
            s.poly([(rx - 10, 105 + 15 * k), (rx + 12, 112 + 15 * k), (rx - 10, 120 + 15 * k)], stroke=INK, sw=1.8,
                   smooth=True)
        if cur:
            s.arrow(x0 + 70, ty if cur > 0 else by, x0 + 100, ty if cur > 0 else by, stroke=FOCUS, sw=3)
            s.arrow(x0 + 100, by if cur > 0 else ty, x0 + 70, by if cur > 0 else ty, stroke=FOCUS, sw=3)
            s.poly([(rx + 22, 108), (rx + 34, 135), (rx + 22, 162)], stroke=INK, sw=1.2, dash="3 2", smooth=True)
        ue = 1 - ub
        s.rect(x0 + 30, 236, 50 * ue + 0.1, 12, fill=MAIN, stroke="none")
        s.rect(x0 + 30, 236, 50, 12, stroke=MAIN, sw=1)
        s.rect(x0 + 100, 236, 50 * ub + 0.1, 12, fill=INK, stroke="none")
        s.rect(x0 + 100, 236, 50, 12, stroke=INK, sw=1)
        s.text(x0 + 55, 266, "電場", size=14, fill=MAIN, anchor="middle")
        s.text(x0 + 125, 266, "磁場", size=14, anchor="middle")
    s.text(20, 292, "橙の矢印：電流　下の棒：エネルギーの置き場所", size=14, fill=SUB)
    s.note(520, 292, "4 の次は 1 に戻る", size=15)
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig1-3-gauss.svg": gauss,
        OUT / "fig3-1-magnet.svg": magnet,
        OUT / "fig4-2-lenz.svg": lenz,
        OUT / "fig5-2-poynting.svg": poynting,
        OUT / "fig5-3-displacement.svg": displacement,
        OUT / "fig6-3-wave.svg": wave,
        OUT / "fig7-2-lc.svg": lc,
    }))
