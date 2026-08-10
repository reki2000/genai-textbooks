#!/usr/bin/env python3
"""docs/books/memory-chip/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import (
    AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, VIOLET,
    Svg as SvgDocument,
)
import circuitkit as ck

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "memory-chip" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)

PANEL = "#f4f5f4"       # 小パネルの地


def panel(s, x, y, w, h, title, sub="", color=INK3):
    """図の中の小さな区画。複数の回路を1枚へ並べるときの枠。"""
    s.rect(x, y, w, h, fill=PANEL, stroke=CARD_EDGE, rx=8)
    s.text(x + 12, y + 20, title, size=12.5, weight="700", fill=color)
    if sub:
        s.text(x + 12, y + 37, sub, size=10.5, fill=INK2)


def step_badge(s, x, y, n, color=INK):
    """回路上に置く手順番号。丸囲み数字は使わず、丸と数字で描く。"""
    s.circle(x, y, 8.5, fill=color, stroke=color)
    s.text(x, y + 4, str(n), size=11, anchor="middle", weight="700", fill="#ffffff")


# --- 図2（1-2）--------------------------------------------------------------
def fig_relay_latch() -> None:
    """電球回路と自己保持リレーを並べ、差が帰還線1本であることを見せる。"""
    s = Svg(760, 386, "図2　記憶を作ったのは素子ではなく、出力を入力へ戻す1本の線",
            "左は入力を外すと消える表示器。右は同じ電池と接点でも、赤い帰還経路があるので残る")

    # --- 左：電球メモリ（表示器）
    panel(s, 24, 74, 320, 244, "電球＋電池＋スイッチ", "1-1でやる夫が作った物")
    lx0, lx1, ly0, ly1 = 96, 288, 156, 268
    ck.battery(s, lx0, 190, length=34, facing="down", text="電池")
    ck.wire(s, [(lx0, ly0), (lx0, 190)])
    ck.wire(s, [(lx0, 224), (lx0, ly1), (lx1, ly1)])
    ck.wire(s, [(lx0, ly0), (lx0 + 40, ly0)])
    pb = ck.pushbutton(s, lx0 + 40, ly0, width=40, pressed=False, text="スイッチ")
    ck.wire(s, [pb["b"], (lx1, ly0), (lx1, 199)])
    ck.lamp(s, lx1, 213, r=14, lit=False)
    ck.wire(s, [(lx1, 227), (lx1, ly1)])
    s.text(184, 300, "指を離すと、その瞬間に消える", size=11.5, anchor="middle",
           weight="700", fill=RED)

    # --- 右：自己保持リレー
    panel(s, 364, 74, 372, 244, "自己保持リレー", "1-2でやる夫が作った物")
    rx0, rx1, ry0, ry1 = 424, 700, 156, 290
    ck.battery(s, rx0, 190, length=34, facing="down", text="電池")
    ck.wire(s, [(rx0, ry0), (rx0, 190)])
    ck.wire(s, [(rx0, 224), (rx0, ry1)])
    # 上の行：リセット（常閉）→ 節点A → セットボタン → 節点B
    ck.wire(s, [(rx0, ry0), (rx0 + 14, ry0)])
    rst = ck.contact(s, rx0 + 14, ry0, width=36, closed=True, text="リセット")
    node_a = (rx0 + 78, ry0)
    ck.wire(s, [rst["b"], node_a])
    ck.dot(s, *node_a)
    st = ck.pushbutton(s, node_a[0] + 34, ry0, width=40, pressed=False, text="セット")
    node_b = (rx1, ry0)
    ck.wire(s, [node_a, st["a"]])
    ck.wire(s, [st["b"], node_b])
    # 下の行：自分の接点を通る帰還経路
    fb_y = 224
    ck.wire(s, [node_a, (node_a[0], fb_y), (node_a[0] + 34, fb_y)], color=RED, sw=2.8)
    self_c = ck.contact(s, node_a[0] + 34, fb_y, width=40, closed=True)
    s.line(self_c["a"][0] + 9, fb_y, self_c["b"][0] - 9, fb_y, stroke=RED, sw=2.8)
    s.text(node_a[0] + 54, fb_y + 21, "自分の接点", size=10.5, anchor="middle",
           weight="700", fill=RED)
    ck.wire(s, [self_c["b"], (node_b[0], fb_y), node_b], color=RED, sw=2.8)
    ck.dot(s, *node_b, color=RED)
    # 右辺からコイルへ
    ck.wire(s, [node_b, (rx1, ry1)])
    cl = ck.coil(s, 556, ry1, width=48, energized=True)
    s.text(580, ry1 + 22, "コイル", size=10.5, anchor="middle", weight="700", fill=RED)
    ck.wire(s, [(rx1, ry1), cl["b"]])
    ck.wire(s, [cl["a"], (rx0, ry1)])
    # 機械的な連結（コイルが接点を引く）
    s.line(580, ry1 - 12, 580, fb_y + 30, stroke=INK3, sw=1.4, dash="3 4")
    s.line(580, fb_y + 30, node_a[0] + 54, fb_y + 30, stroke=INK3, sw=1.4, dash="3 4")
    s.line(node_a[0] + 54, fb_y + 30, node_a[0] + 54, fb_y + 8, stroke=INK3, sw=1.4, dash="3 4")

    step_badge(s, node_a[0] + 54, ry0 - 36, 1)
    step_badge(s, 580, ry1 - 26, 2)
    step_badge(s, node_a[0] + 14, fb_y - 20, 3, color=RED)
    # 帰還経路を回る電流の向き
    for px, py, qx, qy in ((node_a[0], fb_y - 26, node_a[0], fb_y - 8),
                           (node_b[0] - 26, fb_y, node_b[0] - 10, fb_y)):
        s.arrow(px, py, qx, qy, color=RED, sw=2)

    s.lines_of_text(364, 338, [
        "1. セットを一瞬押すとコイルへ電流が流れる",
        "2. コイルが鉄片を引き、自分の接点が閉じる",
        "3. ボタンを離しても、赤い経路が自分のコイルへ電流を戻し続ける",
    ], size=11.5, lh=16)
    s.text(184, 346, "帰還経路がない", size=11.5, anchor="middle", fill=INK2)
    s.save("fig2-relay-latch.svg")


# --- 図1（1-2）--------------------------------------------------------------
def fig_repeater() -> None:
    """電信中継器の回路。弱った入力で、現地の電池から新品の入/切を作り直す。"""
    s = Svg(760, 396, "図1　中継器は信号を増幅しない。判定して、新しい信号を作り直す",
            "弱った電流はコイルを動かすためだけに使う。線路へ出るのは現地の電池が作る新品の入／切")

    y = 208
    # --- 送信側
    panel(s, 24, 96, 148, 200, "送信側", "")
    ck.battery(s, 60, y, length=30, facing="right", text="電池")
    key = ck.pushbutton(s, 106, y, width=38, pressed=True, text="電鍵")
    ck.wire(s, [(90, y), key["a"]])
    ck.wire(s, [(60, y), (60, 268), (148, 268), (148, y)])
    ck.wire(s, [key["b"], (172, y)])

    # --- 100km の線路
    s.line(172, y, 236, y, stroke=ck.WIRE, sw=1.7)
    s.line(236, y, 300, y, stroke=INK3, sw=1.2, dash="7 5")
    s.text(236, y - 14, "100km の電線", size=11, anchor="middle", fill=INK2)
    s.text(236, y + 26, "抵抗と漏れで電流が弱る", size=10.5, anchor="middle", fill=RED)

    # --- 中継器
    panel(s, 304, 96, 240, 200, "中継器（リレー）", "")
    cl = ck.coil(s, 322, y, width=50)
    s.text(347, y - 20, "弱い電流でも鉄片は動く", size=10, anchor="middle", fill=INK2)
    ck.wire(s, [(300, y), cl["a"]])
    ck.wire(s, [cl["b"], (400, y), (400, 274), (322, 274), (322, y)])
    ck.battery(s, 442, 150, length=30, facing="right")
    s.text(457, 138, "現地の新品電池", size=10, anchor="middle", fill=INK2)
    cn = ck.contact(s, 442, 250, width=44, closed=True)
    s.text(464, 270, "判定した結果で閉じる", size=10, anchor="middle", fill=INK2)
    # コイルが接点を引く機械的な連結
    s.line(347, y + 12, 347, 232, stroke=INK3, sw=1.4, dash="3 4")
    s.line(347, 232, 464, 232, stroke=INK3, sw=1.4, dash="3 4")
    s.line(464, 232, 464, 243, stroke=INK3, sw=1.4, dash="3 4")
    ck.wire(s, [(472, 150), (516, 150), (516, 250), (486, 250)])
    ck.wire(s, [(442, 250), (426, 250), (426, 322), (596, 322)])
    ck.wire(s, [(442, 150), (426, 150), (426, 190)])
    ck.dot(s, 426, 150)
    s.arrow(596, 322, 736, 322, color=BLUE, sw=2.6)
    s.text(666, 310, "次の100kmへ", size=11, anchor="middle", weight="700", fill=BLUE)

    # --- 右：入ってきた信号と、作り直した信号
    panel(s, 564, 96, 172, 200, "線路の信号", "")
    s.text(650, 138, "入ってきた信号", size=10.5, anchor="middle", fill=RED)
    for i, level in enumerate((0.34, 0.28, 0.36)):
        h = 40 * level
        s.rect(586 + i * 44, 176 - h, 30, h, fill=RED, stroke=RED, rx=2, opacity=0.55)
    s.line(578, 176, 722, 176, stroke=INK3, sw=1.2)
    s.text(650, 192, "弱く、崩れている", size=10, anchor="middle", fill=RED)
    s.line(578, 206, 722, 206, stroke=INK, sw=1.2, dash="4 4")
    s.text(650, 220, "しきい値で入／切を判定", size=10, anchor="middle", weight="700")
    for i in range(3):
        s.rect(586 + i * 44, 272 - 40, 30, 40, fill=BLUE, stroke=BLUE, rx=2, opacity=0.75)
    s.line(578, 272, 722, 272, stroke=INK3, sw=1.2)
    s.text(650, 288, "作り直した新品の入／切", size=10, anchor="middle", fill=BLUE)

    s.text(380, 362, "入ってきた波形は捨てている。先へ運ばれるのは「入だったか、切だったか」という判定だけ。",
           size=12.5, anchor="middle", weight="700")
    s.text(380, 382, "この構造が、コアの検出増幅器、DRAMの再生、NANDの誤り訂正まで繰り返し現れる。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig1-repeater.svg")


# --- 図3（1-3）--------------------------------------------------------------
def fig_matrix_select() -> None:
    """1本ずつ引く配線と、行×列の交点で選ぶ配線を同じ100点で比べる。"""
    s = Svg(760, 372, "図3　100個を選ぶのに、線は100本要るのか、20本で足りるのか",
            "電話交換機が先に解いた。行と列の交点なら、線の本数は個数の平方根の側で増える")

    # --- 左：1個ずつ専用線
    panel(s, 24, 74, 330, 248, "1個ずつ専用線を引く", "1-3でやる夫が最初に考えた案")
    ox, oy = 96, 132
    for r in range(10):
        for c in range(10):
            s.circle(ox + c * 18, oy + r * 15, 3.4, fill="#ffffff", stroke=INK3, sw=1.1)
    for r in range(10):
        for c in range(10):
            s.line(52, 296, ox + c * 18, oy + r * 15, stroke=RED, sw=0.4, opacity=0.30)
    s.circle(52, 296, 5, fill=INK, stroke=INK)
    s.text(189, 306, "線が100本。1万ビットなら1万本", size=11.5, anchor="middle",
           weight="700", fill=RED)

    # --- 右：行列
    panel(s, 374, 74, 362, 248, "行と列の交点を選ぶ", "クロスバー交換機と同じ考え")
    gx, gy, pitch = 452, 132, 24
    for r in range(10):
        y = gy + r * 15
        color = ORANGE if r == 4 else INK3
        s.line(gx - 26, y, gx + 9 * pitch + 12, y, stroke=color,
               sw=2.2 if r == 4 else 0.9)
    for c in range(10):
        x = gx + c * pitch
        color = BLUE if c == 6 else INK3
        s.line(x, gy - 22, x, gy + 9 * 15 + 12, stroke=color, sw=2.2 if c == 6 else 0.9)
    for r in range(10):
        for c in range(10):
            hit = (r == 4 and c == 6)
            s.circle(gx + c * pitch, gy + r * 15, 4.6 if hit else 3.0,
                     fill=RED if hit else "#ffffff", stroke=RED if hit else INK3,
                     sw=1.6 if hit else 1.1)
    s.text(gx - 30, gy + 4 * 15 - 8, "行", size=11, anchor="end", weight="700", fill=ORANGE)
    s.text(gx + 6 * pitch, gy - 30, "列", size=11, anchor="middle", weight="700", fill=BLUE)
    s.text(555, 306, "線は 10＋10＝20本で、100か所を指定できる", size=11.5,
           anchor="middle", weight="700", fill=INK)

    s.text(380, 350, "この行列は、このあと磁気コアの一致電流、DRAMの行と列、"
                     "SSDの論理アドレス変換まで形を変えて続く。",
           size=12.5, anchor="middle", weight="700")
    s.save("fig3-matrix-select.svg")


# --- 図5（3-4）--------------------------------------------------------------
def fig_core_coincident() -> None:
    """一致電流選択。半分ずつの電流では反転せず、交点だけが反転する。"""
    s = Svg(760, 412, "図5　半分の電流を2本、交点で足す。そこだけが反転する",
            "コア1個を反転させる電流を I とすると、X線とY線へ I/2 ずつ流せば、交点だけが I を受ける")

    # --- 左：4×4 のコア面
    panel(s, 24, 74, 380, 306, "コア面（4×4）", "選ぶのは X1 と Y1 の交点1個")
    x0, y0, pitch = 122, 176, 50
    sel_r, sel_c = 1, 1
    for r in range(4):
        y = y0 + r * pitch
        on = (r == sel_r)
        s.line(x0 - 48, y, x0 + 3 * pitch + 32, y, stroke=ORANGE if on else INK3,
               sw=3 if on else 1.1, opacity=1 if on else 0.7)
        s.text(x0 - 54, y + 4, f"X{r}", size=10.5, anchor="end",
               fill=ORANGE if on else INK3, weight="700" if on else "400")
    for c in range(4):
        x = x0 + c * pitch
        on = (c == sel_c)
        s.line(x, y0 - 38, x, y0 + 3 * pitch + 26, stroke=BLUE if on else INK3,
               sw=3 if on else 1.1, opacity=1 if on else 0.7)
        s.text(x, y0 - 44, f"Y{c}", size=10.5, anchor="middle",
               fill=BLUE if on else INK3, weight="700" if on else "400")
    for r in range(4):
        for c in range(4):
            hit = (r == sel_r and c == sel_c)
            half = (r == sel_r) != (c == sel_c)
            ck.core_ring(s, x0 + c * pitch, y0 + r * pitch, r=15, highlight=hit)
            # 選択コアの真上のセルだけは、下の式と重なるので注記を省く
            if half and not (c == sel_c and r == sel_r - 1):
                s.text(x0 + c * pitch + 23, y0 + r * pitch - 17, "I/2", size=9.5,
                       anchor="middle", fill=INK3)
    s.text(x0 + sel_c * pitch, y0 + sel_r * pitch - 26, "I/2 + I/2 = I　反転する",
           size=11, anchor="middle", weight="700", fill=RED)
    s.text(214, 366, "I/2 だけのコアは反転しない。交点だけが反転する。",
           size=11.5, anchor="middle", weight="700")

    # --- 右：コア1個を貫く4本の線
    panel(s, 424, 74, 312, 306, "コア1個を貫く線", "書込み2本・読出し1本・保護1本")
    import math
    cx, cy = 566, 218
    wires = (
        (-0.62, ORANGE, "X線", "I/2 を流す"),
        (-0.21, BLUE, "Y線", "I/2 を流す"),
        (0.21, AQUA, "センス線", "反転を検出する"),
        (0.62, VIOLET, "禁止線", "反転させない"),
    )
    threads = [(ang, color, 104) for ang, color, _, _ in wires]
    ck.core_ring(s, cx, cy, r=52, threads=threads)
    for ang, color, name, note in wires:
        dx, dy = math.cos(ang), math.sin(ang)
        s.text(cx + dx * 110, cy + dy * 110 - 3, name, size=11,
               anchor="start", fill=color, weight="700")
        s.text(cx + dx * 110, cy + dy * 110 + 12, note, size=9.5,
               anchor="start", fill=color)
    s.text(580, 366, "同じ1個の輪に、4本の別々の役目の線を手で通す。",
           size=11.5, anchor="middle", weight="700")

    s.text(380, 402, "原理は勝った。しかしこの手作業が1ビットごとに要るので、量産で負けた。",
           size=12.5, anchor="middle", weight="700", fill=INK)
    s.save("fig5-core-coincident.svg")


# --- 図6（3-4）--------------------------------------------------------------
def fig_core_destructive() -> None:
    """読出しは観察ではなく破壊と復元であることを、8ビットの実体で追う。"""
    s = Svg(760, 462, "図6　読出しは観察ではない。壊してから、同じ値を書き戻している",
            "`10110010` を1語読むと、コアの実体はいったん `00000000` になる")

    stages = (
        ("1. 選択", "X線とY線へ I/2 ずつ", "10110010", "", ORANGE),
        ("2. 0方向へ強制", "1だったコアだけ反転し\nセンス線にパルスが出る", "00000000", "", RED),
        ("3. レジスタへ保存", "検出増幅器がパルスを\n判定して確かな1へ戻す", "00000000", "10110010", BLUE),
        ("4. 書き戻し", "保存した値で\n元の磁化へ戻す", "10110010", "10110010", AQUA),
    )
    w, gap = 168, 12
    for i, (title, note, bits, reg, color) in enumerate(stages):
        x = 24 + i * (w + gap)
        s.rect(x, 80, w, 288, fill=PANEL, stroke=CARD_EDGE, rx=8)
        s.text(x + w / 2, 104, title, size=12.5, anchor="middle", weight="700", fill=color)
        for j, line in enumerate(note.split("\n")):
            s.text(x + w / 2, 124 + j * 15, line, size=10, anchor="middle", fill=INK2)
        for b, ch in enumerate(bits):
            bx = x + 26 + (b % 4) * 30
            by = 192 + (b // 4) * 40
            ck.core_ring(s, bx, by, r=12, state=int(ch),
                         highlight=(i == 1 and stages[0][2][b] == "1"))
        s.text(x + w / 2, 262, "コアの実体", size=9.5, anchor="middle", fill=INK3)
        s.rect(x + 14, 270, w - 28, 26, fill="#ffffff", stroke=CARD_EDGE, rx=5)
        s.text(x + w / 2, 288, bits, size=13, anchor="middle", weight="700", fill=INK)
        s.text(x + w / 2, 320, "レジスタ", size=9.5, anchor="middle", fill=INK3)
        s.rect(x + 14, 328, w - 28, 26, fill="#ffffff" if reg else PANEL,
               stroke=CARD_EDGE, rx=5, dash=None if reg else "4 4")
        s.text(x + w / 2, 346, reg or "（空）", size=13 if reg else 11,
               anchor="middle", weight="700" if reg else "400",
               fill=BLUE if reg else INK3)
        if i < 3:
            s.arrow(x + w + 1, 214, x + w + gap - 1, 214, color=INK3, sw=2)

    for i, (st, name) in enumerate(((1, "磁化が時計回り＝1（帯を塗った輪）"),
                                    (0, "反時計回り＝0（白い輪）"))):
        lx = 210 + i * 250
        ck.core_ring(s, lx, 388, r=20, state=st)
        s.text(lx + 28, 392, name, size=10.5, anchor="start", fill=INK2)

    s.text(380, 430, "外から見た1回の読出しの裏で、破壊と復元が必ず対になっている。",
           size=12.5, anchor="middle", weight="700")
    s.text(380, 450, "DRAM もこの形をそのまま受け継ぐ。物理は違うのに、読出しの構造が同じになる。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig6-core-destructive.svg")


# --- 図4（2-3）--------------------------------------------------------------
def fig_eccles_jordan() -> None:
    """交差結合した2本の真空管。勝っている側がますます勝つ正帰還を回路上で追う。"""
    s = Svg(760, 430, "図4　増幅器を2個、出力と入力を交差してつなぐと、勝敗が固定される",
            "Eccles-Jordan（1918）。片方が勝つほど相手を抑え、抑えられた相手は反撃できなくなる")

    rail_l, rail_r = 232, 628
    top, bot = 132, 356
    ax, bx = 300, 560
    s.line(rail_l, top, rail_r, top, stroke=ck.WIRE, sw=2.2)
    s.text(rail_l - 8, top + 4, "B+", size=11.5, anchor="end", weight="700")
    s.line(rail_l, bot, rail_r, bot, stroke=ck.WIRE, sw=2.2)
    ck.ground(s, 430, bot)

    tube_y = 268
    nodes = {}
    for name, x, side, winning in (("A", ax, "right", True), ("B", bx, "left", False)):
        r = ck.resistor(s, x, top, length=54, facing="down")
        s.text(x - 22, top + 30, "陽極抵抗", size=10, anchor="end", fill=INK2)
        t = ck.triode(s, x, tube_y, r=30, grid_side=side)
        ck.wire(s, [r["b"], t["plate"]])
        ck.wire(s, [t["cathode"], (x, bot)])
        ck.dot(s, x, bot)
        plate_node = (x, top + 62)
        ck.dot(s, *plate_node)
        nodes[name] = {"plate": plate_node, "grid": t["grid"]}
        color = RED if winning else INK3
        s.text(x + (-44 if name == "A" else 44), tube_y - 14, name, size=15,
               anchor="middle", weight="700", fill=color)
        s.text(x, tube_y + 62, "電流が流れている" if winning else "止まっている",
               size=10.5, anchor="middle", weight="700", fill=color)
        s.text(x + (-38 if name == "A" else 38), top + 66,
               "陽極は低い" if winning else "陽極は高い", size=10.5,
               anchor="end" if name == "A" else "start", weight="700", fill=color)

    # 交差結合：中央で交差する2本の斜め線
    ck.wire(s, [nodes["A"]["plate"], nodes["B"]["grid"]], color=RED, sw=2.6)
    ck.wire(s, [nodes["B"]["plate"], nodes["A"]["grid"]], color=INK3, sw=2.2)
    s.text(430, 176, "Aの陽極 → Bの格子", size=11, anchor="middle", weight="700", fill=RED)
    s.text(430, 252, "Bの陽極 → Aの格子", size=11, anchor="middle", fill=INK3)

    # 正帰還のループ説明
    s.rect(24, 108, 186, 148, fill=PANEL, stroke=CARD_EDGE, rx=8)
    s.text(117, 130, "勝つほど勝つ理由", size=12, anchor="middle", weight="700", fill=RED)
    s.lines_of_text(40, 154, [
        "Aに電流が流れる",
        "→ Aの陽極電圧が下がる",
        "→ Bの格子が下げられる",
        "→ Bがますます止まる",
        "→ Bの陽極は高いまま",
        "→ Aの格子を高く保つ",
    ], size=10.5, lh=16, fill=INK)

    # セット／リセット入力：格子へ一瞬だけ押し込む
    for name, node, text, color in (("A", nodes["A"]["grid"], "セット", RED),
                                    ("B", nodes["B"]["grid"], "リセット", INK3)):
        sx = node[0] + (26 if name == "A" else -26)
        s.arrow(sx, node[1] + 46, node[0] + (4 if name == "A" else -4), node[1] + 4,
                color=color, sw=1.8, dash="5 4")
        s.text(sx + (6 if name == "A" else -6), node[1] + 60, text, size=10.5,
               anchor="start" if name == "A" else "end", fill=color, weight="700")

    s.rect(24, 272, 186, 84, fill=PANEL, stroke=CARD_EDGE, rx=8)
    s.text(117, 294, "2つの安定状態", size=12, anchor="middle", weight="700")
    s.lines_of_text(117, 316, [
        "A入 / B切　と　A切 / B入",
        "中間は不安定で、どちらかへ倒れる",
    ], size=10.5, lh=16, fill=INK2, anchor="middle")

    s.text(380, 400, "セット側を一瞬押して勝敗をひっくり返せば、入力を戻しても状態が残る。これが1ビット。",
           size=12.5, anchor="middle", weight="700")
    s.text(380, 420, "この交差帰還は、真空管からCMOS、6T SRAM、DRAMの検出増幅器まで生き残る。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig4-eccles-jordan.svg")


FIGURES = (
    fig_repeater,
    fig_relay_latch,
    fig_matrix_select,
    fig_core_coincident,
    fig_core_destructive,
    fig_eccles_jordan,
)

def render_all(out_dir: Path) -> None:
    global Svg
    Svg = partial(SvgDocument, out_dir=out_dir)
    for render in FIGURES:
        render()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        render_all(OUT_DIR)
        return 0
    with tempfile.TemporaryDirectory(prefix="memory-chip-figs-") as tmp:
        generated_dir = Path(tmp)
        render_all(generated_dir)
        generated = {p.name: p for p in generated_dir.glob("*.svg")}
        existing = {p.name: p for p in OUT_DIR.glob("*.svg")}
        stale = sorted(name for name in generated.keys() | existing.keys()
                       if name not in generated or name not in existing
                       or generated[name].read_bytes() != existing[name].read_bytes())
    if stale:
        print("stale, missing, or unexpected figures:", file=sys.stderr)
        for name in stale:
            print(f"  {OUT_DIR / name}", file=sys.stderr)
        return 1
    print(f"OK: {len(generated)} figures are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
