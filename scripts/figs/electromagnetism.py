#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/electromagnetism/figs/*.svg を決定的に生成する。

配色の割り当て（この教材での意味づけ。作図規約の3系統に対応させる）
  青 #1f6fd0 : 電気側（電荷・電場・電流）
  橙 #e07b1f : 磁気側（磁場・磁束）と、場が運ぶエネルギー・放射
  赤 #cf3b2d : 打ち消し・矛盾など、その図で壊れるものだけ
  灰 #8d8d8d : 装置・境界・補助
形でも区別する（電場は実線の直線矢印、磁場は円・輪、結果は太い矢印）。

選定の根拠・却下した候補・向きの物理チェックは
scripts/figs/electromagnetism.md に残す。
"""
import filecmp
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (  # noqa: E402
    SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB,
    TINT_MAIN, TINT_FOCUS, TINT_WARN, TINT_MUTED,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "electromagnetism" / "figs"


def ellipse_path(cx, cy, rx, ry):
    return (f"M {cx - rx} {cy} A {rx} {ry} 0 1 0 {cx + rx} {cy} "
            f"A {rx} {ry} 0 1 0 {cx - rx} {cy}")


def sine_path(x0, x1, ybase, amp, wavelength, phase=0.0, diag=(0.0, 0.0), step=6):
    pts = []
    x = x0
    while x <= x1:
        t = math.sin(2 * math.pi * (x - x0) / wavelength + phase)
        pts.append((x + diag[0] * amp * t, ybase - amp * t + diag[1] * amp * t))
        x += step
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
    d += " ".join(f"L {px:.1f} {py:.1f}" for px, py in pts[1:])
    return d


# ---------------------------------------------------------------- fig1-2
def fig_polarization():
    """1-2 分極：中性の紙が帯電した下敷きに引かれる理由。

    グリッド
      下敷き  x 70..140, y 60..260（縦の帯、+ を3個）
      紙の分子  中心 (300,160) (450,160) (600,160)、楕円 rx 62 ry 44
                各分子の中で - は左 (中心-26)、+ は右 (中心+26)
      力の矢印  y 282: 引く力は左向き長 90、離す力は右向き長 45
    """
    s = SVG(760, 330, "中性の紙でも、近い側の負電荷への引力が遠い側の正電荷への反発より強く、全体として引かれる")
    s.rect(70, 60, 70, 200, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
    for y in (100, 160, 220):
        s.text(105, y + 7, "+", size=20, fill=MAIN, anchor="middle", weight="700")
    s.text(105, 292, "正に帯電した下敷き", size=13, anchor="middle", weight="700")

    for cx in (300, 450, 600):
        s.path(ellipse_path(cx, 160, 62, 44), stroke=INK, sw=1.4, dash="5 4")
        s.circle(cx - 26, 160, 13, fill="#ffffff", stroke=MAIN, sw=1.6)
        s.text(cx - 26, 166, "-", size=16, fill=MAIN, anchor="middle", weight="700")
        s.circle(cx + 26, 160, 13, fill="#ffffff", stroke=FOCUS, sw=1.6)
        s.text(cx + 26, 166, "+", size=16, fill=FOCUS, anchor="middle", weight="700")
    s.text(450, 92, "紙の中の電荷の偏り（分極）", size=14, anchor="middle", weight="700")
    s.text(274, 232, "近い側", size=12, fill=MAIN, anchor="middle")
    s.text(476, 232, "遠い側", size=12, fill=FOCUS, anchor="middle")

    s.arrow(330, 282, 240, 282, stroke=MAIN, sw=3.2)
    s.text(285, 308, "引く力", size=13, fill=MAIN, anchor="middle", weight="700")
    s.arrow(520, 282, 565, 282, stroke=FOCUS, sw=2.0)
    s.text(543, 308, "離す力", size=13, fill=FOCUS, anchor="middle", weight="700")
    return s


# ---------------------------------------------------------------- fig1-3
def fig_field_lines():
    """1-3 電気力線：単独の正電荷と負電荷。

    グリッド（2パネル、中心 y=205）
      A 正電荷  中心 (200,205) r 20、矢印は8方向へ外向き
      B 負電荷  中心 (560,205) r 20、矢印は外側から中心へ（8方向）
      仕切り x=380、パネル名 y=52
    本文に双極子は登場しないため、対の配置は描かない（選定記録参照）。
    """
    s = SVG(760, 360, "電気力線は正電荷から出て負電荷に入り、接線が電場の向き、密度が強さを表す")
    s.line(380, 40, 380, 330, stroke=MUTED, sw=1)
    s.text(200, 52, "正電荷", size=14, anchor="middle", weight="700")
    s.text(560, 52, "負電荷", size=14, anchor="middle", weight="700")

    for cx, sign, inward in ((200, "+", False), (560, "-", True)):
        for k in range(8):
            a = k * math.pi / 4
            dx, dy = math.cos(a), math.sin(a)
            if inward:
                s.arrow(cx + 96 * dx, 205 + 96 * dy, cx + 30 * dx, 205 + 30 * dy,
                        stroke=MAIN, sw=1.8)
            else:
                s.arrow(cx + 30 * dx, 205 + 30 * dy, cx + 96 * dx, 205 + 96 * dy,
                        stroke=MAIN, sw=1.8)
        s.circle(cx, 205, 20, fill=TINT_MAIN, stroke=MAIN, sw=1.8)
        s.text(cx, 212, sign, size=18, fill=MAIN, anchor="middle", weight="700")
    s.text(380, 348, "線の接線が電場の向き、線の密度が強さ", size=12, fill=SUB,
           anchor="middle")
    return s


# ---------------------------------------------------------------- fig3-2
def fig_wire_loops():
    """3-2 直線電流のまわりの磁場：同心円と方位磁針（断面）。

    グリッド
      中心 (380,195)。導線の断面 r 24（電流は手前向き＝点）
      磁場の円 r 66 / 112 / 158。反時計回りが正:
        上 (380,83) では左向き、右 (492,195) では上向き、
        下 (380,307) では右向き、左 (268,195) では下向き
      方位磁針は r112 の円上の4点に白丸＋矢印で置く
    """
    s = SVG(760, 390, "電流を手前へ流すと、磁場は導線を中心とする同心円を反時計回りに回る")
    cx, cy = 380, 195
    for r in (66, 112, 158):
        s.circle(cx, cy, r, fill="none", stroke=FOCUS, sw=1.6)
    s.arrow(cx - 4, cy - 158, cx - 52, cy - 158, stroke=FOCUS, sw=2.0)
    s.arrow(cx + 158, cy + 4, cx + 158, cy - 44, stroke=FOCUS, sw=2.0)
    s.arrow(cx + 4, cy + 158, cx + 52, cy + 158, stroke=FOCUS, sw=2.0)
    s.arrow(cx - 158, cy - 4, cx - 158, cy + 44, stroke=FOCUS, sw=2.0)
    for nx, ny, dx, dy in ((cx, cy - 112, -1, 0), (cx + 112, cy, 0, -1),
                           (cx, cy + 112, 1, 0), (cx - 112, cy, 0, 1)):
        s.circle(nx, ny, 15, fill="#ffffff", stroke=INK, sw=1.3)
        s.arrow(nx - 9 * dx, ny - 9 * dy, nx + 9 * dx, ny + 9 * dy,
                stroke=INK, sw=2.0)
    s.circle(cx, cy, 24, fill=TINT_MAIN, stroke=MAIN, sw=2.0)
    s.circle(cx, cy, 5, fill=MAIN, stroke=MAIN, sw=0)
    s.text(120, 60, "磁場 B は同心円", size=14, fill=FOCUS, weight="700")
    s.text(120, 84, "丸は方位磁針の向き", size=12, fill=SUB)
    s.text(560, 330, "導線の断面", size=13, weight="700")
    s.text(560, 352, "点は電流が手前向き", size=12, fill=SUB)
    return s


# ---------------------------------------------------------------- fig3-3
def fig_lorentz():
    """3-3 ローレンツ力：F は v と B の両方に垂直。

    グリッド（原点 (250,245)）
      v  (280,0)  → 先端 (530,245)、青
      B  (100,-150) → 先端 (350,95)、橙。破線の平行四辺形で平面を示す
      F  (0,-195) → 先端 (250,50)、黒の太矢印
      直角マークは v-F 間 (250..268, 227..245)
    """
    s = SVG(760, 330, "磁場中の正電荷への力は、速度と磁場の両方に垂直で、速さは変えない")
    ox, oy = 250, 245
    s.line(ox + 280, oy, ox + 380, oy - 150, stroke=SUB, sw=1.2, dash="5 4")
    s.line(ox + 100, oy - 150, ox + 380, oy - 150, stroke=SUB, sw=1.2, dash="5 4")
    s.arrow(ox, oy, ox + 280, oy, stroke=MAIN, sw=2.6)
    s.arrow(ox, oy, ox + 100, oy - 150, stroke=FOCUS, sw=2.6)
    s.arrow(ox, oy, ox, oy - 195, stroke=INK, sw=3.4)
    s.path(f"M {ox + 18} {oy} V {oy - 18} H {ox}", stroke=INK, sw=1.3)
    s.circle(ox, oy, 15, fill="#ffffff", stroke=FOCUS, sw=1.8)
    s.text(ox, oy + 5, "q", size=13, anchor="middle", weight="700")
    s.text(ox + 292, oy + 5, "v 速度", size=14, fill=MAIN, weight="700")
    s.text(ox + 108, oy - 166, "B 磁場", size=14, fill=FOCUS, weight="700")
    s.text(ox + 12, oy - 182, "F 力", size=14, weight="700")
    s.text(ox + 150, oy - 196, "F は v と B の両方に垂直", size=14, weight="700")
    s.text(ox + 150, oy - 172, "力と速度も垂直なので、速さは変わらない", size=12,
           fill=SUB)
    s.text(ox, oy + 52, "正電荷の場合。負電荷では力は逆向き", size=12, fill=SUB)
    return s


# ---------------------------------------------------------------- fig4-2
def fig_lenz():
    """4-2 レンツの法則：近づく N 極と、増えた磁束を打ち消す誘導磁場。

    グリッド
      磁石  x 56..226, y 158..198（右半分が N）
      コイルの輪  中心 y=178、rx 26 ry 88、cx = 400, 444, 488, 532
      磁束の矢印  y 138 と 218、x 250→600（青、右向き）
      誘導磁場の矢印  y 84、x 600→330（橙、左向き）
      輪の前側の電流  各輪の中心 (cx,178) に下向きの橙矢印
        （誘導磁場が左向きになる電流は、輪の前側では下向き）
    """
    s = SVG(760, 360, "N極が近づいて磁束が増えると、誘導電流は逆向きの磁場を作って増加を打ち消す")
    s.rect(56, 158, 85, 40, fill=TINT_FOCUS, stroke=FOCUS, sw=1.6)
    s.rect(141, 158, 85, 40, fill=TINT_MAIN, stroke=MAIN, sw=1.6)
    s.text(98, 184, "S", size=16, fill=FOCUS, anchor="middle", weight="700")
    s.text(183, 184, "N", size=16, fill=MAIN, anchor="middle", weight="700")
    s.arrow(96, 232, 176, 232, stroke=INK, sw=2.4)
    s.text(136, 258, "近づく", size=13, anchor="middle", weight="700")

    for cx in (400, 444, 488, 532):
        s.path(ellipse_path(cx, 178, 26, 88), stroke=INK, sw=1.8)
    s.arrow(250, 138, 596, 138, stroke=MAIN, sw=2.2)
    s.arrow(250, 218, 596, 218, stroke=MAIN, sw=2.2)
    s.text(300, 122, "磁束が増える", size=13, fill=MAIN, weight="700")
    s.arrow(600, 84, 330, 84, stroke=FOCUS, sw=3.0)
    s.text(465, 62, "誘導磁場は逆向き", size=14, fill=FOCUS, anchor="middle",
           weight="700")
    for cx in (400, 444, 488, 532):
        s.arrow(cx, 150, cx, 206, stroke=FOCUS, sw=2.4)
    s.text(620, 160, "輪の前側では", size=12, fill=FOCUS)
    s.text(620, 182, "電流は下向き", size=12, fill=FOCUS)
    s.text(380, 322, "変化を強める向きなら、エネルギーが無から増えてしまう", size=13,
           anchor="middle", weight="700")
    return s


# ---------------------------------------------------------------- fig4-3
def fig_motor_generator():
    """4-3 モーターと発電機は同じ構造の双方向変換。

    グリッド（2パネル、仕切り x=380）
      各パネル: N 極の塊 (px+30,120,44,120) / S 極の塊 (px+256,120,44,120)
                コイルは中心 (px+165,180) の回転する長方形（傾き 25 度）
                軸は水平の破線 y=180、回転は上の弧矢印
      A (px=20)  下に電池 (140,284,90,30)
      B (px=400) 右下に電流計の丸 (665,296) r 24
    """
    s = SVG(760, 350, "コイルと磁石の同じ組が、電流で回せばモーター、回せば発電機になる")

    def device(px, title):
        s.text(px + 165, 44, title, size=15, anchor="middle", weight="700")
        s.rect(px + 30, 120, 44, 120, fill=TINT_MAIN, stroke=MAIN, sw=1.6)
        s.text(px + 52, 186, "N", size=16, fill=MAIN, anchor="middle", weight="700")
        s.rect(px + 256, 120, 44, 120, fill=TINT_FOCUS, stroke=FOCUS, sw=1.6)
        s.text(px + 278, 186, "S", size=16, fill=FOCUS, anchor="middle", weight="700")
        s.line(px + 74, 180, px + 256, 180, stroke=SUB, sw=1.4, dash="5 4")
        cx, cy = px + 165, 180
        pts = [(cx - 62, cy - 26), (cx + 34, cy - 52), (cx + 62, cy + 26),
               (cx - 34, cy + 52)]
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts) + " Z"
        s.path(d, stroke=INK, sw=2.2)
        s.path(f"M {cx - 58} 108 A 66 66 0 0 1 {cx + 58} 108", stroke=FOCUS,
               sw=2.2)
        s.arrow(cx + 58, 108, cx + 66, 122, stroke=FOCUS, sw=2.2)

    s.line(380, 24, 380, 330, stroke=MUTED, sw=1)
    device(20, "モーター：電気 → 回転")
    device(400, "発電機：回転 → 電気")
    s.rect(140, 284, 90, 30, fill=TINT_MAIN, stroke=MAIN, sw=1.6)
    s.text(185, 304, "電池", size=13, fill=MAIN, anchor="middle", weight="700")
    s.line(150, 284, 150, 246, stroke=INK, sw=1.4)
    s.line(220, 284, 220, 246, stroke=INK, sw=1.4)
    s.text(185, 340, "電流がコイルを回す", size=12, anchor="middle", fill=SUB)
    s.circle(665, 296, 24, fill="#ffffff", stroke=INK, sw=1.8)
    s.text(665, 302, "A", size=15, anchor="middle", weight="700")
    s.line(648, 276, 600, 244, stroke=INK, sw=1.4)
    s.line(684, 276, 636, 244, stroke=INK, sw=1.4)
    s.arrow(452, 300, 528, 300, stroke=INK, sw=2.2)
    s.text(490, 340, "外から回すと電流が流れる", size=12, anchor="middle",
           fill=SUB)
    return s


# ---------------------------------------------------------------- fig5-2
def fig_poynting():
    """5-2 ポインティングベクトル：エネルギーは空間を通って抵抗へ入る。

    グリッド
      左パネル  回路の輪 x 60..420 / 電池は左辺 / 抵抗は右辺のジグザグ。
                空間側の太い矢印は上下の外側を電池→抵抗へ (y 84 と 296)、
                右端で抵抗へ向かう (x 420 の上下)
      右パネル  抵抗の断面: 中心 (628,176)、B の同心円 r 44 / 74、
                S の矢印は上下左右から内向き（橙、太）。
                電流と電場は奥向き（中心の×印）
    """
    s = SVG(760, 380, "電磁エネルギーは導線のまわりの空間を流れ、抵抗の表面から内側へ入る")
    s.path("M 60 110 H 420 M 60 270 H 420", stroke=INK, sw=2.0)
    s.line(60, 110, 60, 150, stroke=INK, sw=2.0)
    s.line(60, 230, 60, 270, stroke=INK, sw=2.0)
    s.line(48, 176, 72, 176, stroke=INK, sw=3.2)
    s.line(54, 190, 66, 190, stroke=INK, sw=1.8)
    s.text(60, 320, "電池", size=13, anchor="middle", weight="700")
    s.path("M 420 110 L 420 140 L 404 158 L 436 176 L 404 194 L 436 212 "
           "L 420 230 L 420 270", stroke=INK, sw=2.0)
    s.text(420, 320, "抵抗", size=13, anchor="middle", weight="700")
    s.arrow(96, 84, 380, 84, stroke=FOCUS, sw=6)
    s.arrow(96, 296, 380, 296, stroke=FOCUS, sw=6)
    s.arrow(420, 88, 420, 124, stroke=FOCUS, sw=5)
    s.arrow(420, 292, 420, 256, stroke=FOCUS, sw=5)
    s.text(238, 62, "エネルギーの流れ S", size=14, fill=FOCUS, anchor="middle",
           weight="700")
    s.text(238, 352, "導線は流れを導く", size=12, fill=SUB, anchor="middle")

    cx, cy = 628, 176
    s.circle(cx, cy, 74, fill="none", stroke=FOCUS, sw=1.5)
    s.circle(cx, cy, 44, fill="none", stroke=FOCUS, sw=1.5)
    s.arrow(cx - 44, cy - 4, cx - 44, cy + 22, stroke=FOCUS, sw=1.8)
    s.arrow(cx + 44, cy + 4, cx + 44, cy - 22, stroke=FOCUS, sw=1.8)
    s.circle(cx, cy, 20, fill=TINT_MUTED, stroke=INK, sw=1.6)
    s.line(cx - 8, cy - 8, cx + 8, cy + 8, stroke=INK, sw=1.8, role="glyph")
    s.line(cx + 8, cy - 8, cx - 8, cy + 8, stroke=INK, sw=1.8, role="glyph")
    for x1, y1, x2, y2 in ((cx, 66, cx, 96), (cx, 256, cx, 226),
                           (518, cy, 548, cy), (738, cy, 708, cy)):
        s.arrow(x1, y1, x2, y2, stroke=FOCUS, sw=4.2)
    s.text(cx, 296, "抵抗の断面", size=13, anchor="middle", weight="700")
    s.text(cx, 318, "×は電流と電場が奥向き", size=11, fill=SUB, anchor="middle")
    s.text(cx, 340, "B は同心円、S は外から内へ", size=11, fill=SUB,
           anchor="middle")
    return s


# ---------------------------------------------------------------- fig5-3
def fig_capacitor_surfaces():
    """5-3 面の取り方：平らな面は伝導電流、膨らんだ面は変位電流が貫く。

    グリッド
      閉曲線 C  破線の長方形 x 250..610, y 70..300
      導線  水平線 y=185（左は x 120..470、右は x 552..690）
      極板  左 x=470..482 / 右 x=540..552, y 110..260（間隔 58）
      面1  x=330 の縦の面（楕円 rx 16 ry 95）: 導線が貫く
      面2  C の内側から極板間へ膨らむ破線の輪郭（橙）
      極板間の E  矢印は左→右に3本（y 140,185,230）
    """
    s = SVG(760, 380, "同じ閉曲線でも、面の取り方で貫くものが伝導電流から変位電流へ替わり、答えは一致する")
    s.line(120, 185, 470, 185, stroke=INK, sw=2.4)
    s.line(552, 185, 690, 185, stroke=INK, sw=2.4)
    s.rect(470, 110, 12, 150, fill=TINT_MAIN, stroke=MAIN, sw=1.6)
    s.rect(540, 110, 12, 150, fill=TINT_FOCUS, stroke=FOCUS, sw=1.6)
    s.text(476, 92, "+", size=15, fill=MAIN, anchor="middle", weight="700")
    s.text(546, 92, "-", size=15, fill=FOCUS, anchor="middle", weight="700")
    for y, ln in ((140, 34), (185, 44), (230, 34)):
        s.arrow(490, y, 490 + ln, y, stroke=MAIN, sw=2.0)
    s.text(462, 140, "電場が増える", size=12, fill=MAIN, anchor="end")
    s.rect(250, 70, 360, 230, fill="none", stroke=INK, sw=1.6, dash="7 5")
    s.text(250, 52, "閉曲線 C", size=14, weight="700")
    s.arrow(430, 70, 500, 70, stroke=INK, sw=2.0)
    s.path(ellipse_path(330, 185, 16, 95), stroke=MAIN, sw=1.8, fill=TINT_MAIN,
           op=0.55)
    s.text(330, 316, "面1：伝導電流 I が貫く", size=13, fill=MAIN, anchor="middle",
           weight="700")
    s.path("M 430 78 C 560 84, 596 130, 596 185 C 596 244, 552 288, 470 294",
           stroke=FOCUS, sw=1.8, dash="6 4")
    s.text(596, 316, "面2：変位電流が貫く", size=13, fill=FOCUS, anchor="end",
           weight="700")
    s.text(120, 160, "導線", size=12, fill=SUB)
    s.text(120, 340, "どちらの面でも磁場の循環は同じ", size=13, weight="700")
    return s


# ---------------------------------------------------------------- fig6-3
def fig_em_wave():
    """6-3 電磁波：E と B は同位相で直交し、E×B の向きへ進む。

    グリッド
      進行軸  y=205、x 60..710。波長 300（x 60..360 が1周期）
      E  振幅 92 の正弦（画面の縦 = z 方向、青の実線）
      B  正方向を斜め下 (0.32, 0.95) として射影した正弦（橙）。
         横ずれを小さくし、山と谷の位置が E とそろって見えるようにする
      ベクトルの矢印  位相 1/4, 3/4, 5/4, 7/4 周期の位置で軸から波形へ引く
    """
    s = SVG(760, 380, "電磁波では電場と磁場が同じ位相で直交して振動し、波は E×B の向きへ進む")
    s.arrow(60, 205, 716, 205, stroke=INK, sw=1.6)
    s.text(716, 190, "進行方向", size=13, anchor="end", weight="700")
    s.path(sine_path(60, 710, 205, 92, 300), stroke=MAIN, sw=2.6)
    s.path(sine_path(60, 710, 205, 44, 300, diag=(0.32, 1.95)), stroke=FOCUS,
           sw=2.6)
    for frac in (0.25, 0.75, 1.25, 1.75):
        x = 60 + 300 * frac
        t = math.sin(2 * math.pi * frac)
        s.arrow(x, 205, x, 205 - 92 * t, stroke=MAIN, sw=2.0)
        s.arrow(x, 205, x + 14 * t, 205 + 42 * t, stroke=FOCUS, sw=2.0)
    s.text(135, 84, "電場 E", size=14, fill=MAIN, weight="700")
    s.text(150, 330, "磁場 B", size=14, fill=FOCUS, weight="700")
    s.text(470, 84, "山と谷の位置がそろう（同位相）", size=13, weight="700")
    s.text(470, 330, "E と B と進行方向は互いに直交", size=12, fill=SUB)
    return s


FIGS = {
    "fig1-2-polarization": fig_polarization,
    "fig1-3-field-lines": fig_field_lines,
    "fig3-2-wire-loops": fig_wire_loops,
    "fig3-3-lorentz": fig_lorentz,
    "fig4-2-lenz": fig_lenz,
    "fig4-3-motor-generator": fig_motor_generator,
    "fig5-2-poynting": fig_poynting,
    "fig5-3-capacitor-surfaces": fig_capacitor_surfaces,
    "fig6-3-em-wave": fig_em_wave,
}


def main(argv):
    check = "--check" in argv
    out = Path(tempfile.mkdtemp()) if check else OUT_DIR
    diff = []
    for name, build in sorted(FIGS.items()):
        path = build().save(out / f"{name}.svg")
        if check:
            cur = OUT_DIR / f"{name}.svg"
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
