#!/usr/bin/env python3
"""回路図の部品記号を `svgkit.Svg` の上へ描く共通ヘルパ。

教材別スクリプト（`scripts/figs/{ID}.py`）から import して使う。各関数は描画だけ
を行い、端子の座標を dict で返す。返った端子を `wire()` でつなぐと、素子の内部
寸法を呼び出し側が知らなくても結線できる。

    t = triode(s, 300, 200)
    wire(s, [t["plate"], (300, 120), (420, 120)])

座標は左上原点。向きは `facing` で与える（"up" / "down" / "left" / "right"）。
"""

from __future__ import annotations

from svgkit import INK, INK2, INK3, RED

WIRE = "#3f3e3b"       # 結線の既定色
SW = 1.7               # 結線の既定の太さ
PART = INK             # 素子の輪郭
FILL = "#ffffff"       # 素子の地


def wire(s, points, color=WIRE, sw=SW, dash=None):
    """折れ線で結線する。points は (x, y) の列。"""
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points)
    s.path(d, stroke=color, sw=sw, dash=dash)


def dot(s, x, y, color=WIRE, r=3.2):
    """接続点（結線が電気的につながっていることを示す黒丸）。"""
    s.circle(x, y, r, fill=color, stroke=color)


def cross(s, x, y, color=RED, r=6, sw=2):
    """×印。切れている・使えない・棄却したことを示す。"""
    s.line(x - r, y - r, x + r, y + r, stroke=color, sw=sw)
    s.line(x - r, y + r, x + r, y - r, stroke=color, sw=sw)


def label(s, x, y, text, size=10.5, fill=INK2, anchor="middle", weight="400"):
    s.text(x, y, text, size=size, fill=fill, anchor=anchor, weight=weight)


# --- 電源・負荷 -------------------------------------------------------------
def battery(s, x, y, length=34, facing="right", cells=2, text=""):
    """電池記号。(x, y) を負極側の端子とし、facing の向きへ length 伸びる。

    返り値の "minus" が (x, y)、"plus" が反対端。
    """
    dx, dy = _dir(facing)
    px, py = -dy, dx          # 素子の幅方向
    pitch = length / (cells * 2 - 0.5)
    pos = 0.0
    for i in range(cells):
        for long_plate in (False, True):
            half = 11 if long_plate else 6.5
            cx, cy = x + dx * pos, y + dy * pos
            s.line(cx + px * half, cy + py * half, cx - px * half, cy - py * half,
                   stroke=PART, sw=2.4 if long_plate else 3.4)
            pos += pitch
    end = (x + dx * length, y + dy * length)
    if text:
        label(s, (x + end[0]) / 2 + px * 22, (y + end[1]) / 2 + py * 22 + 4, text)
    return {"minus": (x, y), "plus": end}


def lamp(s, cx, cy, r=14, lit=False, text=""):
    """電球記号（丸の中に×）。lit=True で点灯色にする。"""
    glow = "#f6b93b"
    s.circle(cx, cy, r, fill=glow if lit else FILL, stroke=PART, sw=1.8,
             opacity=0.9 if lit else None)
    k = r * 0.62
    s.line(cx - k, cy - k, cx + k, cy + k, stroke=PART, sw=1.5)
    s.line(cx - k, cy + k, cx + k, cy - k, stroke=PART, sw=1.5)
    if lit:
        for a in (-1, 0, 1):
            s.line(cx + a * 9, cy - r - 5, cx + a * 11, cy - r - 12,
                   stroke=glow, sw=2.2)
    if text:
        label(s, cx, cy + r + 15, text)
    return {"left": (cx - r, cy), "right": (cx + r, cy),
            "top": (cx, cy - r), "bottom": (cx, cy + r)}


def resistor(s, x, y, length=40, facing="right", text=""):
    """抵抗（箱形）。(x, y) から facing へ length。"""
    dx, dy = _dir(facing)
    px, py = -dy, dx
    lead = (length - 26) / 2
    ax, ay = x + dx * lead, y + dy * lead
    bx, by = x + dx * (lead + 26), y + dy * (lead + 26)
    wire(s, [(x, y), (ax, ay)])
    wire(s, [(bx, by), (x + dx * length, y + dy * length)])
    s.path(f"M {ax + px * 7:g} {ay + py * 7:g} L {bx + px * 7:g} {by + py * 7:g} "
           f"L {bx - px * 7:g} {by - py * 7:g} L {ax - px * 7:g} {ay - py * 7:g} Z",
           stroke=PART, fill=FILL, sw=1.6)
    if text:
        label(s, (ax + bx) / 2 + px * 17, (ay + by) / 2 + py * 17 + 4, text)
    return {"a": (x, y), "b": (x + dx * length, y + dy * length)}


def capacitor(s, x, y, facing="right", gap=7, text=""):
    """コンデンサ（平行平板）。(x, y) が中心。"""
    dx, dy = _dir(facing)
    px, py = -dy, dx
    half = 12
    for sign in (-1, 1):
        cx, cy = x + dx * sign * gap / 2, y + dy * sign * gap / 2
        s.line(cx + px * half, cy + py * half, cx - px * half, cy - py * half,
               stroke=PART, sw=2.6)
    if text:
        label(s, x + px * 24, y + py * 24 + 4, text)
    return {"a": (x - dx * gap / 2, y - dy * gap / 2),
            "b": (x + dx * gap / 2, y + dy * gap / 2)}


def ground(s, x, y, text=""):
    """接地記号。(x, y) が上端の端子。"""
    wire(s, [(x, y), (x, y + 8)])
    for i, half in enumerate((11, 7, 3.5)):
        s.line(x - half, y + 8 + i * 5, x + half, y + 8 + i * 5, stroke=PART, sw=2.2)
    if text:
        label(s, x, y + 38, text)
    return {"top": (x, y)}


# --- スイッチ・接点 ---------------------------------------------------------
def pushbutton(s, x, y, width=34, pressed=False, text=""):
    """押しボタン。(x, y) が左端子、右へ width。"""
    s.line(x, y, x + 8, y, stroke=WIRE, sw=SW)
    s.line(x + width - 8, y, x + width, y, stroke=WIRE, sw=SW)
    dot(s, x + 8, y, r=2.6)
    dot(s, x + width - 8, y, r=2.6)
    if pressed:
        s.line(x + 8, y, x + width - 8, y, stroke=PART, sw=2.4)
        s.line(x + width / 2, y - 14, x + width / 2, y - 3, stroke=PART, sw=2.4)
    else:
        s.line(x + 8, y - 1, x + width - 6, y - 13, stroke=PART, sw=2.4)
        s.line(x + width / 2, y - 22, x + width / 2, y - 9, stroke=PART, sw=2.4)
    s.line(x + width / 2 - 9, y - 22, x + width / 2 + 9, y - 22, stroke=PART, sw=3)
    if text:
        label(s, x + width / 2, y + 18, text)
    return {"a": (x, y), "b": (x + width, y)}


def contact(s, x, y, width=34, closed=False, text=""):
    """リレーの接点（常開）。closed=True で閉じた状態。"""
    s.line(x, y, x + 9, y, stroke=WIRE, sw=SW)
    s.line(x + width - 9, y, x + width, y, stroke=WIRE, sw=SW)
    dot(s, x + 9, y, r=2.6)
    dot(s, x + width - 9, y, r=2.6)
    if closed:
        s.line(x + 9, y, x + width - 9, y, stroke=PART, sw=2.6)
    else:
        s.line(x + 9, y, x + width - 7, y - 14, stroke=PART, sw=2.6)
    if text:
        label(s, x + width / 2, y + 19, text)
    return {"a": (x, y), "b": (x + width, y), "arm": (x + width / 2, y - 7)}


def coil(s, x, y, width=44, height=20, text="", energized=False):
    """電磁石コイル（箱に斜線）。(x, y) が左端子。"""
    color = RED if energized else PART
    s.line(x, y, x + (width - 30) / 2, y, stroke=WIRE, sw=SW)
    s.line(x + width - (width - 30) / 2, y, x + width, y, stroke=WIRE, sw=SW)
    bx = x + (width - 30) / 2
    s.rect(bx, y - height / 2, 30, height, fill=FILL, stroke=color, rx=2, sw=1.8)
    for i in range(3):
        s.line(bx + 6 + i * 9, y - height / 2, bx + 1 + i * 9, y + height / 2,
               stroke=color, sw=1.3)
    if text:
        label(s, x + width / 2, y - height / 2 - 8, text,
              fill=RED if energized else INK2, weight="700" if energized else "400")
    return {"a": (x, y), "b": (x + width, y),
            "core": (x + width / 2, y + height / 2)}


# --- 能動素子 ---------------------------------------------------------------
def triode(s, cx, cy, r=26, text="", grid_side="left"):
    """三極管。plate（陽極）が上、cathode（陰極）が下、grid（格子）が横。

    grid_side で格子端子の向きを選ぶ。交差結合を描くときは、2本の管の格子を
    互いに向き合わせると結線がきれいに交差する。
    """
    sign = -1 if grid_side == "left" else 1
    s.circle(cx, cy, r, fill=FILL, stroke=PART, sw=1.8)
    # 陽極：上の短い板
    s.line(cx - 11, cy - 12, cx + 11, cy - 12, stroke=PART, sw=2.6)
    wire(s, [(cx, cy - 12), (cx, cy - r)])
    # 格子：破線
    s.line(cx - 13, cy, cx + 13, cy, stroke=PART, sw=1.6, dash="4 4")
    wire(s, [(cx + sign * 13, cy), (cx + sign * r, cy)])
    # 陰極：への字とヒータ
    s.path(f"M {cx - 11:g} {cy + 14:g} L {cx:g} {cy + 8:g} L {cx + 11:g} {cy + 14:g}",
           stroke=PART, sw=2.4)
    wire(s, [(cx, cy + 11), (cx, cy + r)])
    if text:
        label(s, cx + r + 8, cy + 4, text, anchor="start")
    return {"plate": (cx, cy - r), "grid": (cx + sign * r, cy),
            "cathode": (cx, cy + r)}


def mosfet(s, cx, cy, kind="n", text="", facing="right"):
    """MOSFET。facing="right" ならゲートが左、ドレインが上、ソースが下。

    kind は "n"（nMOS）か "p"（pMOS）。pMOS はゲート端子に丸を付ける。
    """
    sign = 1 if facing == "right" else -1
    gx = cx - sign * 22                    # ゲート縦棒の x
    chx = cx - sign * 14                   # チャネル縦棒の x
    s.line(gx, cy - 13, gx, cy + 13, stroke=PART, sw=2.4)
    if kind == "p":
        s.circle(gx - sign * 5, cy, 4, fill=FILL, stroke=PART, sw=1.6)
        wire(s, [(gx - sign * 9, cy), (cx - sign * 40, cy)])
    else:
        wire(s, [(gx, cy), (cx - sign * 40, cy)])
    for y0, y1 in ((cy - 13, cy - 5), (cy - 3, cy + 3), (cy + 5, cy + 13)):
        s.line(chx, y0, chx, y1, stroke=PART, sw=2.4)
    wire(s, [(chx, cy - 9), (cx, cy - 9), (cx, cy - 24)])
    wire(s, [(chx, cy + 9), (cx, cy + 9), (cx, cy + 24)])
    if text:
        label(s, cx + sign * 12, cy + 4, text, anchor="start" if sign > 0 else "end")
    return {"gate": (cx - sign * 40, cy), "drain": (cx, cy - 24),
            "source": (cx, cy + 24)}


def inverter(s, cx, cy, w=46, h=34, text="", facing="right"):
    """論理反転器（三角と丸）。facing="right" で入力が左、出力が右。"""
    sign = 1 if facing == "right" else -1
    x0 = cx - sign * w / 2
    x1 = cx + sign * w / 2
    s.path(f"M {x0:g} {cy - h / 2:g} L {x0:g} {cy + h / 2:g} L {x1 - sign * 7:g} {cy:g} Z",
           stroke=PART, fill=FILL, sw=1.8)
    s.circle(x1 - sign * 3.5, cy, 3.6, fill=FILL, stroke=PART, sw=1.6)
    if text:
        label(s, cx - sign * 6, cy + 4, text, anchor="middle", size=10)
    return {"in": (x0, cy), "out": (x1, cy)}


# --- 記憶素子 ---------------------------------------------------------------
def core_ring(s, cx, cy, r=13, state=None, highlight=False, threads=()):
    """磁気コア（フェライトの輪）。state は 1／0／None。

    state を与えると、輪の帯そのものを周回する磁化の向きを描く。矢印頭は marker
    ではなく三角形で描く（marker は線幅に比例して大きくなり、小さな輪からはみ出す）。

    threads に角度（ラジアン）と色の組を渡すと、輪の穴を通る線を描く。線は先に
    引いてから輪の帯で覆うので、帯の下をくぐって穴から出るように見える。
    """
    import math
    color = RED if highlight else PART
    band = (r + (r - 5.5)) / 2
    for ang, wcolor, length in threads:
        dx, dy = math.cos(ang), math.sin(ang)
        s.line(cx - dx * length, cy - dy * length, cx + dx * length, cy + dy * length,
               stroke=wcolor, sw=2.2)
    # 輪の帯。太い白のストロークで線を隠してから、内外の輪郭を引く。
    s.circle(cx, cy, band, fill="none", stroke=FILL, sw=r - (r - 5.5))
    if state:
        # 小さく描いても1と0を見分けられるよう、1は帯を塗る。
        s.circle(cx, cy, band, fill="none", stroke=color, sw=r - (r - 5.5), opacity=0.30)
    s.circle(cx, cy, r, fill="none", stroke=color, sw=2.4 if highlight else 1.9)
    s.circle(cx, cy, r - 5.5, fill="none", stroke=color, sw=1.4)
    if state is not None and band >= 14:
        # 帯の上の周回矢印。1 は時計回り、0 は反時計回り。矢印頭の位置が左右で
        # 変わるので、小さく描いても向きを見分けられる。
        sweep = 1 if state else 0
        a0, a1 = (-2.75, -0.35) if state else (-0.35, -2.75)
        p0 = (cx + band * math.cos(a0), cy + band * math.sin(a0))
        p1 = (cx + band * math.cos(a1), cy + band * math.sin(a1))
        s.path(f"M {p0[0]:g} {p0[1]:g} A {band:g} {band:g} 0 0 {sweep} {p1[0]:g} {p1[1]:g}",
               stroke=color, sw=max(2.0, band * 0.22))
        # 終端の三角形（接線方向を向ける）
        tang = a1 + (math.pi / 2 if state else -math.pi / 2)
        tx, ty = math.cos(tang), math.sin(tang)
        nx, ny = -ty, tx
        h, w = band * 0.42, band * 0.26
        s.path(f"M {p1[0] + tx * h:g} {p1[1] + ty * h:g} "
               f"L {p1[0] + nx * w:g} {p1[1] + ny * w:g} "
               f"L {p1[0] - nx * w:g} {p1[1] - ny * w:g} Z",
               stroke=color, fill=color, sw=1)
    return {"center": (cx, cy), "r": r}


def cell_1t1c(s, cx, cy, text="", charged=None):
    """DRAM の 1T1C セル。ワード線が左、ビット線が上、下は板（対向電極）。"""
    m = mosfet(s, cx, cy - 6, kind="n")
    cap_top = (cx, cy + 18)
    wire(s, [m["source"], cap_top])
    c = capacitor(s, cx, cy + 26, facing="down")
    wire(s, [c["b"], (cx, cy + 40)])
    s.line(cx - 13, cy + 40, cx + 13, cy + 40, stroke=PART, sw=2.4)
    if charged is not None:
        for i in range(3 if charged else 0):
            s.circle(cx - 7 + i * 7, cy + 33, 2.4, fill=RED, stroke=RED)
    if text:
        label(s, cx, cy + 56, text)
    return {"word": m["gate"], "bit": m["drain"], "plate": (cx, cy + 40)}


def _dir(facing):
    return {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[facing]
