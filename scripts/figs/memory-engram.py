#!/usr/bin/env python3
"""docs/books/memory-engram/figs/*.svg を決定的に生成する。"""

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

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "memory-engram" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


# --- 図1（1-4）------------------------------------------------------------
def fig_hm_amnesia_map() -> None:
    """H.M. で失われた範囲を「記憶の種類 × 出来事の時期」の2軸に置く。"""
    s = Svg(760, 430, "図1　H.M. が失ったのは、宣言的記憶の「新しい分」だけ",
            "同じ手術で、古い宣言的記憶と手続き記憶は残った。失われた範囲は時期と種類で決まる")

    x0, x1, cut = 118, 716, 470
    # 宣言的記憶：本文の表（10年以上前＝保たれる／数年前＝あいまい／直前＝ほぼ失われる）を棒の高さにする。
    base = 215
    bars = [
        (x0, 262, 0.90, "保たれる", BLUE),
        (262, 372, 0.45, "あいまい", BLUE),
        (372, cut, 0.08, "ほぼ失われる", RED),
    ]
    s.text(24, 118, "宣言的記憶", size=12.5, weight="700")
    s.text(24, 136, "言葉で言える", size=10, fill=INK2)
    for xa, xb, ratio, label, color in bars:
        h = 100 * ratio
        s.rect(xa + 4, base - h, xb - xa - 8, h, fill=color, stroke=color, rx=4,
               opacity=0.30 if color == BLUE else 0.45)
        s.text((xa + xb) / 2, base - h - 9, label, size=11, anchor="middle",
               weight="700", fill=color)
    s.rect(cut + 4, base - 100, x1 - cut - 8, 100, fill=RED, stroke=RED, rx=4,
           opacity=0.10, dash="5 4", sw=1.6)
    s.text((cut + x1) / 2, 150, "新しくは作れない", size=12, anchor="middle",
           weight="700", fill=RED)
    s.text((cut + x1) / 2, 170, "前向性健忘", size=10.5, anchor="middle", fill=RED)
    s.line(x0, base, x1, base, stroke=INK3, sw=1.4)

    # 手続き記憶：手術後も上達する。鏡映描写のはみ出し 30→20→10 を帯の中の小さな棒で示す。
    band_top, band_bottom = 250, 300
    s.text(24, 268, "手続き記憶", size=12.5, weight="700")
    s.text(24, 286, "体が覚える", size=10, fill=INK2)
    s.rect(x0, band_top, x1 - x0, band_bottom - band_top, fill=AQUA, stroke=AQUA,
           rx=8, sw=1.6, opacity=0.16)
    s.text(300, band_bottom - 18, "手術の前後を通じて保たれる", size=12,
           anchor="middle", weight="700", fill=INK)
    # 帯の中に白いカードを置き、「手術後も上達する」ことの実測（はみ出し回数）を切り出す。
    s.rect(524, 234, 192, 82, fill="#ffffff", stroke=CARD_EDGE, rx=6)
    s.text(620, 250, "手術後の鏡映描写：はみ出し回数", size=9.5, anchor="middle", fill=INK2)
    for i, (value, day) in enumerate(((30, "1日目"), (20, "2日目"), (10, "3日目"))):
        bx = 552 + i * 46
        h = value * 0.8
        s.rect(bx, 292 - h, 26, h, fill=AQUA, stroke=AQUA, rx=3, opacity=0.85)
        s.text(bx + 13, 292 - 4 - h, str(value), size=10, anchor="middle",
               weight="700", fill=AQUA)
        s.text(bx + 13, 307, day, size=9.5, anchor="middle", fill=INK2)

    # 手術の時点
    s.line(cut, 96, cut, 322, stroke=INK, sw=1.8, dash="6 4")
    s.text(cut, 88, "手術（両側の海馬を含む切除）", size=11.5, anchor="middle", weight="700")

    s.line(x0, 336, x1, 336, stroke=INK3, sw=1.2)
    for xa, xb, label in ((x0, 262, "10年以上前"), (262, 372, "数年前"),
                          (372, cut, "手術の直前"), (cut, x1, "手術より後")):
        s.text((xa + xb) / 2, 353, label, size=10.5, anchor="middle", fill=INK2)
    s.text(24, 353, "出来事の時期", size=10.5, fill=INK3)

    s.text(380, 390, "海馬は倉庫ではない。倉庫なら、古い記憶も手続き記憶も一緒に消えていたはずだ。",
           size=12.5, anchor="middle", weight="700")
    s.text(380, 412, "本人は3日目にも「こんなことをするのは初めてだ」と言った。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig1-hm-amnesia-map.svg")


# --- 図2（2-1）------------------------------------------------------------
def fig_neuron_and_synapse() -> None:
    """配線は既にあり、変えられるのは接点の効きだけ、という舞台を先に置く。"""
    s = Svg(760, 430, "図2　線を引き直すのではなく、接点の効きを変える",
            "大人の脳では配線はもう引いてある。以降の幕で書き換わるのは、この接点1個の効きだけ")

    # --- ① 細胞どうしのつながり
    s.rect(24, 86, 406, 268, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(227, 110, "① つながりは、もう引いてある", size=12.5, anchor="middle",
           weight="700", fill=BLUE)

    # 送り手の細胞：樹状突起（左上）→ 細胞体 → 軸索（右下）
    for dx, dy in ((-40, -40), (-6, -54), (32, -44)):
        s.path(f"M84,162 L{84 + dx},{162 + dy} M{84 + dx * 0.6:.0f},{162 + dy * 0.6:.0f} "
               f"L{84 + dx * 0.6 + 14:.0f},{162 + dy * 0.6 - 18:.0f}", stroke=INK3, sw=1.8)
    s.circle(84, 162, 23, fill="#ffffff", stroke=INK3, sw=2)
    s.circle(84, 162, 9, fill=VIOLET, opacity=0.25)
    s.path("M105,172 L178,194 L232,210", stroke=INK3, sw=2.4)
    s.circle(243, 214, 11, fill="#ffffff", stroke=INK3, sw=2)
    s.line(130, 126, 104, 116, stroke=INK3, sw=1)
    s.text(134, 130, "樹状突起（受け手）", size=10, fill=INK2, weight="700")
    s.text(84, 200, "細胞体", size=10, anchor="middle", fill=INK2, weight="700")
    s.text(160, 186, "軸索（送り手）", size=10, anchor="middle", fill=INK2, weight="700")

    # 受け手の細胞：終末とのあいだに隙間を残す
    s.path("M275,232 L322,258 M296,245 L306,229", stroke=INK3, sw=1.8)
    s.circle(348, 278, 23, fill="#ffffff", stroke=INK3, sw=2)
    s.circle(348, 278, 9, fill=VIOLET, opacity=0.25)
    s.arrow(370, 288, 408, 302, color=INK3, sw=2)
    s.text(416, 254, "次の細胞の", size=10, anchor="end", fill=INK2, weight="700")
    s.text(416, 268, "樹状突起", size=10, anchor="end", fill=INK2, weight="700")
    s.text(416, 318, "さらに次へ", size=9.5, anchor="end", fill=INK3)

    # 拡大する接点
    s.circle(259, 223, 24, fill="none", stroke=BLUE, sw=2, dash="4 3")
    s.text(259, 160, "シナプス", size=11, anchor="middle", weight="700", fill=BLUE)
    s.arrow(259, 168, 259, 192, color=BLUE, sw=1.6)

    s.lines_of_text(38, 322, ["大脳皮質の神経細胞：約160億個",
                              "1個が持つシナプス：平均で数千個"], size=10, fill=INK2, lh=16)

    # --- ② 接点の拡大
    s.rect(456, 86, 280, 268, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(596, 110, "② 変えられるのは、この効き", size=12.5, anchor="middle",
           weight="700", fill=ORANGE)
    for ax, ay in ((456, 120), (456, 320)):
        s.line(281, 223, ax, ay, stroke=BLUE, sw=1.2, dash="4 4", opacity=0.7)

    s.rect(506, 132, 180, 60, fill="#ffffff", stroke=INK3, rx=22, sw=2)
    s.text(596, 126, "シナプス前終末（送り手）", size=10, anchor="middle",
           weight="700", fill=INK2)
    for vx, vy in ((540, 156), (568, 150), (598, 158), (628, 150)):
        s.circle(vx, vy, 8, fill=ORANGE, opacity=0.25, stroke=ORANGE, sw=1.4)
    s.text(596, 182, "小胞に詰めて溜めてある", size=9.5, anchor="middle", fill=INK3)
    for gx in (568, 590, 612):
        s.circle(gx, 212, 4.5, fill=ORANGE)
    s.text(466, 216, "シナプス間隙", size=9.5, fill=INK3)
    s.text(700, 216, "グルタミン酸", size=10, anchor="end", weight="700", fill=ORANGE)

    s.rect(496, 234, 200, 22, fill="#eef0ef", stroke=CARD_EDGE, rx=3)
    for i in range(4):
        s.rect(520 + i * 44, 228, 26, 34, fill="#f0f6fe", stroke=BLUE, rx=4, sw=1.8)
    s.text(596, 284, "受け手に並ぶ受容体", size=10.5, anchor="middle", weight="700", fill=BLUE)
    s.text(596, 308, "この数と効きが「重み」", size=12.5, anchor="middle", weight="700", fill=BLUE)
    s.text(596, 330, "増やせば増強、減らせば抑圧", size=10.5, anchor="middle", fill=INK2)

    s.text(380, 382, "大人の脳で配線を新設していたら、映画をその日のうちに覚えて帰ることはできない。",
           size=12, anchor="middle", weight="700")
    s.text(380, 406, "速いのは工事ではなく、既にある接点の効きを変えること。これをシナプス可塑性という。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig2-neuron-and-synapse.svg")


# --- 図3（2-5）------------------------------------------------------------
def _nmda_panel(s, px: float, title: str, glutamate: bool, depolarized: bool,
                opened: bool) -> None:
    pw = 224
    s.rect(px, 86, pw, 268, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(px + pw / 2, 110, title, size=12.5, anchor="middle", weight="700",
           fill=AQUA if opened else BLUE)

    mem_top, mem_bottom = 196, 222
    s.rect(px + 14, mem_top, pw - 28, mem_bottom - mem_top, fill="#eef0ef",
           stroke=CARD_EDGE, rx=3)
    s.text(px + 16, 138, "細胞外", size=9.5, fill=INK3)
    s.text(px + 16, 254, "細胞内", size=9.5, fill=INK3)

    ampa_x, nmda_x = px + 44, px + 138
    for rx_, name in ((ampa_x, "AMPA"), (nmda_x, "NMDA")):
        s.rect(rx_, mem_top - 8, 42, mem_bottom - mem_top + 16, fill="#ffffff",
               stroke=INK3, rx=5, sw=1.5)
        s.text(rx_ + 21, 288, name, size=10.5, anchor="middle", weight="700", fill=INK2)

    if glutamate:
        for cx in (ampa_x + 10, ampa_x + 31, nmda_x + 10, nmda_x + 31):
            s.circle(cx, 178, 4.5, fill=ORANGE)
        s.text(px + 14, 160, "グルタミン酸あり", size=10.5, weight="700", fill=ORANGE)
        # AMPA は常に開く。
        s.arrow(ampa_x + 21, 186, ampa_x + 21, 244, color=BLUE, sw=1.6)
        s.text(ampa_x + 21, 262, "Na⁺", size=10, anchor="middle", fill=BLUE, weight="700")
    else:
        s.text(px + 14, 160, "グルタミン酸なし", size=10.5, weight="700", fill=INK3)
        s.line(ampa_x + 8, 178, ampa_x + 34, 178, stroke=INK3, sw=1.5, dash="4 3")

    if depolarized:
        s.text(px + pw / 2, 320, "内側は脱分極（マイナスが弱い）", size=10.5,
               anchor="middle", weight="700", fill=VIOLET)
        # 引き止める力が弱まり、栓が穴の外へ出る。
        s.circle(px + 196, 176, 7, fill=VIOLET, opacity=0.55)
        s.text(px + 210, 158, "Mg²⁺ 外れる", size=10, anchor="end",
               weight="700", fill=VIOLET)
    else:
        s.text(px + pw / 2, 320, "内側は −70 mV のまま", size=10.5, anchor="middle",
               weight="700", fill=INK2)
        s.circle(nmda_x + 21, mem_top + 13, 7, fill=VIOLET)
        s.text(nmda_x + 21, 254, "Mg²⁺ が栓", size=10, anchor="middle",
               weight="700", fill=VIOLET)

    if opened:
        s.arrow(nmda_x + 21, 186, nmda_x + 21, 248, color=AQUA, sw=2.4)
        s.text(nmda_x + 21, 268, "Ca²⁺", size=11.5, anchor="middle", weight="700", fill=AQUA)
    verdict = "Ca²⁺ 流入 ○" if opened else "Ca²⁺ 流入 ×"
    s.text(px + pw / 2, 340, verdict, size=13, anchor="middle", weight="700",
           fill=AQUA if opened else RED)


def fig_nmda_and_gate() -> None:
    """NMDA受容体が「送り手が撃った」かつ「受け手が興奮した」の AND でしか開かないこと。"""
    s = Svg(760, 430, "図3　NMDA受容体は、二つの鍵が同時に回ったときだけ開く",
            "グルタミン酸だけでも脱分極だけでも Ca²⁺ は入らない。両方そろった入力だけが選ばれる")
    _nmda_panel(s, 24, "① グルタミン酸だけ", glutamate=True, depolarized=False, opened=False)
    _nmda_panel(s, 268, "② 脱分極だけ", glutamate=False, depolarized=True, opened=False)
    _nmda_panel(s, 512, "③ 両方そろう", glutamate=True, depolarized=True, opened=True)
    s.text(380, 372, "グルタミン酸＝送り手が撃った、脱分極＝受け手が強く興奮した。ヘッブの二条件が、そのまま栓の外れ方になっている。",
           size=12, anchor="middle", weight="700")
    s.text(380, 398, "細胞内の Ca²⁺ 濃度は外の約1万分の1。少し入るだけで跳ね上がり、電気の話が化学の話に切り替わる。",
           size=11.5, anchor="middle", fill=INK2)
    s.save("fig3-nmda-and-gate.svg")


# --- 図4（3-5）------------------------------------------------------------
def fig_calcium_bidirectional() -> None:
    """同じ Ca²⁺ で増強と抑圧が分かれるのは、閾値の違う2つの酵素が置いてあるから。"""
    s = Svg(760, 430, "図4　同じカルシウムが、濃度だけで逆を向く",
            "低い濃度ではカルシニューリンだけが動き、高い濃度で CaMKII が加わる")

    x0, x1 = 130, 706
    base = 296
    top = 112
    thr_cn, thr_camk = 268, 452

    s.rect(x0, top, thr_cn - x0, base - top, fill=GRID, stroke="none", opacity=0.35)
    s.rect(thr_cn, top, thr_camk - thr_cn, base - top, fill=ORANGE, stroke="none", opacity=0.13)
    s.rect(thr_camk, top, x1 - thr_camk, base - top, fill=BLUE, stroke="none", opacity=0.13)
    s.text((x0 + thr_cn) / 2, 104, "何も起きない", size=11.5, anchor="middle", fill=INK3, weight="700")
    s.text((thr_cn + thr_camk) / 2, 104, "抑圧（LTD）", size=12.5, anchor="middle",
           fill=ORANGE, weight="700")
    s.text((thr_camk + x1) / 2, 104, "増強（LTP）", size=12.5, anchor="middle",
           fill=BLUE, weight="700")

    def activation(threshold: float, color: str, label: str, label_x: float) -> None:
        # ロジスティック曲線。閾値で活性 0.5、幅は 44 単位に固定する。
        pts = []
        for i in range(0, 121):
            x = x0 + (x1 - x0) * i / 120
            a = 1.0 / (1.0 + 2.718281828459045 ** (-(x - threshold) / 22.0))
            pts.append((x, base - a * (base - top - 26)))
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        s.path(d, stroke=color, sw=2.6)
        s.line(threshold, top + 8, threshold, base, stroke=color, sw=1.4, dash="4 4")
        s.text(label_x, base - (base - top - 26) * 0.5 - 12, label, size=11.5,
               fill=color, weight="700", anchor="middle")

    activation(thr_cn, ORANGE, "カルシニューリン", thr_cn - 66)
    activation(thr_camk, BLUE, "CaMKII", thr_camk + 44)

    s.line(x0, base, x1, base, stroke=INK3, sw=1.5)
    s.arrow(x0, base, x1 + 8, base, color=INK3, sw=1.5)
    s.text(x0, base + 22, "低い", size=11, fill=INK2)
    s.text(x1, base + 22, "高い", size=11, fill=INK2, anchor="end")
    s.text((x0 + x1) / 2, base + 22, "細胞内カルシウム濃度", size=11.5, anchor="middle",
           fill=INK2, weight="700")
    s.text(24, 150, "酵素の", size=10.5, fill=INK3)
    s.text(24, 166, "活性", size=10.5, fill=INK3)

    s.rect(24, 334, 348, 56, fill="#ffffff", stroke=ORANGE, rx=8, sw=1.6)
    s.lines_of_text(38, 354, ["1 Hz × 15分（900回）：低く長い", "→ リン酸を外す → AMPA受容体を回収 → EPSP 100 → 60"],
                    size=11, fill=INK, lh=18)
    s.rect(388, 334, 348, 56, fill="#ffffff", stroke=BLUE, rx=8, sw=1.6)
    s.lines_of_text(402, 354, ["テタヌス刺激：高く短い", "→ リン酸を付ける → AMPA受容体を追加 → EPSP 100 → 170"],
                    size=11, fill=INK, lh=18)
    s.text(380, 414, "判定装置は要らない。動き出す濃度をずらした部品を二つ置くだけで、向きが分かれる。",
           size=12, anchor="middle", weight="700")
    s.save("fig4-calcium-bidirectional.svg")


# --- 図5（4-3）------------------------------------------------------------
def fig_synaptic_tag_capture() -> None:
    """タンパク質は細胞じゅうへ配られ、旗が立ったシナプスだけが捕まえる。"""
    s = Svg(760, 430, "図5　宛先は荷物ではなく、受け取る側の旗で決まる",
            "強い刺激が作ったタンパク質は全体へ配られ、弱く叩かれてタグの立った線Bだけが捕獲する")

    # 細胞体と核
    cell_y = 244
    s.circle(96, cell_y, 40, fill="#ffffff", stroke=INK3, sw=1.8)
    s.circle(96, cell_y, 19, fill=VIOLET, opacity=0.22, stroke=VIOLET, sw=1.5)
    s.text(96, cell_y + 4, "核", size=12, anchor="middle", weight="700", fill=VIOLET)
    s.text(96, cell_y + 60, "転写・翻訳", size=10.5, anchor="middle", fill=VIOLET, weight="700")

    branches = [
        (152, "線A", "強いテタヌス3回", BLUE, True, "後期LTP"),
        (244, "線B", "弱いテタヌス1回", ORANGE, True, "初期LTP＋タグ"),
        (336, "線C", "刺激なし", INK3, False, "素通り"),
    ]
    for y, name, stim, color, tagged, note in branches:
        s.path(f"M132,{cell_y - (cell_y - y) * 0.24:.1f} L212,{y} L300,{y}", stroke=INK3, sw=2.4)
        s.rect(300, y - 18, 84, 36, fill="#ffffff", stroke=color, rx=7, sw=1.8)
        s.text(342, y + 4, name, size=12.5, anchor="middle", weight="700", fill=color)
        s.text(212, y - 12, stim, size=10.5, fill=color, weight="700")
        # 配られたタンパク質（同じ数を全枝へ配る）
        for k in range(3):
            s.circle(228 + k * 28, y + 14, 4, fill=VIOLET, opacity=0.75)
        if tagged:
            s.line(400, y - 17, 400, y + 13, stroke=AQUA, sw=2)
            s.path(f"M400,{y - 17} L422,{y - 11} L400,{y - 5} Z", fill=AQUA, stroke=AQUA, sw=1)
            s.text(428, y + 2, "タグ", size=10.5, fill=AQUA, weight="700")
        else:
            s.text(400, y + 2, "タグなし", size=10.5, fill=INK3, weight="700")
        s.text(474, y + 2, note, size=10.5, fill=color if tagged else INK3, weight="700")
    s.text(276, 106, "強い刺激が核を動かし、タンパク質は細胞じゅうへ配られる（●）", size=11,
           fill=VIOLET, weight="700", anchor="middle")

    # 6時間後の EPSP
    cx_mid, cy_base = 654, 330
    s.text(cx_mid, 132, "6時間後の EPSP", size=11.5, anchor="middle", weight="700")
    s.text(cx_mid, 150, "破線＝刺激前の 100", size=9.5, anchor="middle", fill=RED)
    s.line(580, cy_base - 13.5, 736, cy_base - 13.5, stroke=RED, sw=1.4, dash="4 3")
    for i, (label, value, color) in enumerate((("線A", 165, BLUE), ("線B", 150, ORANGE),
                                               ("線B\n対照", 100, INK3))):
        bx = 588 + i * 50
        h = (value - 90) * 1.35
        s.rect(bx, cy_base - h, 34, h, fill=color, stroke=color, rx=4, opacity=0.75)
        s.text(bx + 17, cy_base - h - 8, str(value), size=11, anchor="middle",
               weight="700", fill=color)
        s.lines_of_text(bx + 17, 350, label.split("\n"), size=10, fill=INK2,
                        anchor="middle", lh=13)
    s.line(580, cy_base, 736, cy_base, stroke=INK3, sw=1.2)

    s.text(380, 392, "線Bは同じ弱い刺激しか受けていない。隣の線Aが強かったかどうかで、6時間後が 150 と 100 に分かれる。",
           size=11.5, anchor="middle", weight="700")
    s.text(380, 414, "旗の寿命は1〜2時間ほど。時間が空きすぎると捕まえられない。",
           size=11, anchor="middle", fill=INK2)
    s.save("fig5-synaptic-tag-capture.svg")


# --- 図6（5-4）------------------------------------------------------------
def fig_engram_tagging() -> None:
    """「いつ」を薬で、「どの細胞」を c-Fos で選び、光で呼び出す。"""
    s = Svg(760, 400, "図6　いつを薬で、どの細胞を c-Fos で選ぶ",
            "標識できる窓のあいだに活動した細胞にだけ ChR2 が入り、あとから光で呼び出せる")

    stages = [
        (24, "1日目：薬を抜く", "標識ON", AQUA,
         ["箱Aで足に電気ショック", "→ 活動した歯状回の細胞で", "　c-Fos のスイッチが入る", "→ その細胞に ChR2 が作られる"]),
        (268, "2日目：薬を戻す", "標識OFF", INK3,
         ["別の箱Bに入れる", "形も匂いも違う、怖くない箱", "→ マウスは普通に歩き回る", "→ 新しい標識は付かない"]),
        (512, "そこで青い光を当てる", "呼び出し", BLUE,
         ["光が当たるのは、1日目に", "活動した細胞だけ", "→ その場でフリージング", "→ 目の前に怖いものは無い"]),
    ]
    for px, title, badge, color, rows in stages:
        s.rect(px, 86, 224, 150, fill="#ffffff", stroke=CARD_EDGE, rx=8)
        s.text(px + 14, 110, title, size=12, weight="700")
        s.rect(px + 14, 120, 62, 20, fill=color, stroke=color, rx=6, opacity=0.20)
        s.text(px + 45, 134, badge, size=10.5, anchor="middle", weight="700", fill=color)
        s.lines_of_text(px + 14, 166, rows, size=10.5, fill=INK, lh=19)
    s.arrow(252, 161, 264, 161, color=INK2, sw=1.8)
    s.arrow(496, 161, 508, 161, color=INK2, sw=1.8)

    s.rect(24, 256, 712, 106, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(38, 280, "すくんだ時間の割合（本文の記述に対応する定性的な比較。実測値ではない）",
           size=10.5, fill=INK2)
    rows = [("光なし", 0.18, INK3), ("光あり", 0.78, BLUE),
            ("標識のとき学習させず＋光", 0.16, INK3)]
    for i, (label, level, color) in enumerate(rows):
        y = 300 + i * 20
        s.text(216, y + 4, label, size=10.5, anchor="end", fill=INK)
        s.rect(228, y - 5, 466, 11, fill=GRID, stroke="none", rx=5, opacity=0.6)
        s.rect(228, y - 5, 466 * level, 11, fill=color, stroke=color, rx=5, opacity=0.85)

    s.text(380, 382, "呼び出せるし、抑える道具を入れれば止められる。ただしマウスで、戻ったのは「恐怖」だ。",
           size=12, anchor="middle", weight="700")
    s.save("fig6-engram-tagging.svg")


# --- 図7（6-4）------------------------------------------------------------
def fig_reconsolidation() -> None:
    """固定化済みの記憶でも、想起させると再びタンパク質合成に依存する。"""
    s = Svg(760, 430, "図7　思い出させてから薬を入れたときだけ、消える",
            "固定化の終わった記憶も、想起でいったんほどけ、固め直しにタンパク質合成が要る")

    x_learn, x_op, x_test = 176, 430, 630
    s.text(24, 128, "薬＝アニソマイシン", size=10, fill=INK3)
    s.text(x_learn, 106, "学習（音→ショック）", size=11, anchor="middle", weight="700", fill=INK2)
    s.text(x_op, 106, "1日後の操作", size=11, anchor="middle", weight="700", fill=INK2)
    s.text(x_test, 106, "翌日のテスト", size=11, anchor="middle", weight="700", fill=INK2)

    rows = [
        ("何もしない", [], "すくむ", BLUE),
        ("薬だけ", ["薬"], "すくむ", BLUE),
        ("音を聞かせる＋薬", ["想起", "薬"], "すくまない", RED),
    ]
    for i, (label, ops, result, color) in enumerate(rows):
        y = 150 + i * 56
        s.text(24, y + 4, label, size=11, fill=INK, weight="700")
        s.line(x_learn, y, x_test - 46, y, stroke=GRID, sw=2)
        s.circle(x_learn, y, 7, fill=ORANGE)
        for k, op in enumerate(ops):
            ox = x_op - 34 + k * 68
            s.circle(ox, y, 7, fill=VIOLET if op == "想起" else RED)
            s.text(ox, y - 14, op, size=10, anchor="middle", weight="700",
                   fill=VIOLET if op == "想起" else RED)
        if not ops:
            s.text(x_op, y - 14, "なし", size=10, anchor="middle", fill=INK3)
        s.rect(x_test - 40, y - 15, 106, 30, fill=color, stroke=color, rx=7,
               sw=1.6, opacity=0.16)
        s.text(x_test + 13, y + 4, result, size=12, anchor="middle", weight="700", fill=color)

    s.rect(24, 324, 712, 62, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    boxes = [(44, "固まった記憶", BLUE), (232, "想起でほどける", VIOLET),
             (420, "タンパク質合成", ORANGE), (600, "また固まる", BLUE)]
    for bx, label, color in boxes:
        s.rect(bx, 338, 120, 34, fill="#ffffff", stroke=color, rx=7, sw=1.6)
        s.text(bx + 60, 359, label, size=11, anchor="middle", weight="700", fill=color)
    for bx in (164, 352, 540):
        s.arrow(bx, 355, bx + 66, 355, color=INK2, sw=1.6)
    s.line(561, 343, 585, 367, stroke=RED, sw=3)
    s.line(585, 343, 561, 367, stroke=RED, sw=3)
    s.text(573, 332, "薬で合成を止めると、二度と固まらない", size=10.5, anchor="middle",
           weight="700", fill=RED)

    s.text(380, 410, "想起は読み出しではない。思い出すたびに、記憶は書き直されている。",
           size=12.5, anchor="middle", weight="700")
    s.save("fig7-reconsolidation.svg")


# --- 図8（8-1）------------------------------------------------------------
def fig_synapse_density_pruning() -> None:
    """知識が増える時期に、シナプス密度は減っている。"""
    s = Svg(760, 430, "図8　シナプス密度のピークは、何も知らない生後8か月",
            "ヒト一次視覚野の目安（成人＝100）。そこから3〜4割を削って成人の値に落ち着く")

    points = [("出生時", 60), ("生後8か月", 160), ("4歳", 130), ("11歳", 110), ("成人", 100)]
    x0, x1 = 150, 690
    y_base, y_top = 324, 128

    def y_of(v: float) -> float:
        # 40〜180 を y_base〜y_top へ線形に写す。
        return y_base - (v - 40) * (y_base - y_top) / 140.0

    for grid_v in (50, 100, 150):
        gy = y_of(grid_v)
        s.line(x0 - 12, gy, x1 + 16, gy, stroke=GRID, sw=1)
        s.text(x0 - 20, gy + 4, str(grid_v), size=10.5, anchor="end", fill=INK3)
    s.line(x0 - 12, y_of(100), x1 + 16, y_of(100), stroke=INK3, sw=1.4, dash="5 4")
    s.text(52, 116, "シナプス密度", size=11, fill=INK2, weight="700")

    xs = [x0 + (x1 - x0) * i / (len(points) - 1) for i in range(len(points))]
    d = "M" + " L".join(f"{x:.1f},{y_of(v):.1f}" for x, (_, v) in zip(xs, points))
    s.path(d, stroke=BLUE, sw=3)
    for x, (label, v) in zip(xs, points):
        s.circle(x, y_of(v), 6, fill="#ffffff", stroke=BLUE, sw=2.6)
        s.text(x, y_of(v) - 14, str(v), size=11, anchor="middle", weight="700", fill=BLUE)
        s.text(x, y_base + 22, label, size=10.5, anchor="middle", fill=INK2)
    s.line(x0 - 12, y_base, x1 + 16, y_base, stroke=INK3, sw=1.4)

    s.text(xs[1], y_of(160) - 32, "ピーク：成人の1.6倍", size=11.5, anchor="middle",
           weight="700", fill=ORANGE)
    # ピークの水準からどれだけ落ちるかを、縦の矢印で 160 → 100 として示す。
    drop_x = 632
    s.line(xs[1] + 10, y_of(160), drop_x, y_of(160), stroke=ORANGE, sw=1.4, dash="5 4")
    s.arrow(drop_x, y_of(160) + 4, drop_x, y_of(100) - 4, color=ORANGE, sw=2.2)
    s.text(drop_x, y_of(160) - 12, "ここから3〜4割を削る（刈り込み）", size=11,
           fill=ORANGE, weight="700", anchor="end")

    s.text(x0 - 12, 372, "横軸は等間隔で、年齢の実尺ではない。ピークの時期は場所による（前頭前野はもっと遅い）。",
           size=10.5, fill=INK3)
    s.text(380, 402, "知ることが増えていく時期に、シナプスの数は減っている。育つことは、減ることでもある。",
           size=12.5, anchor="middle", weight="700")
    s.save("fig8-synapse-density-pruning.svg")


FIGURES = (
    fig_hm_amnesia_map,
    fig_neuron_and_synapse,
    fig_nmda_and_gate,
    fig_calcium_bidirectional,
    fig_synaptic_tag_capture,
    fig_engram_tagging,
    fig_reconsolidation,
    fig_synapse_density_pruning,
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
    with tempfile.TemporaryDirectory(prefix="memory-engram-figs-") as tmp:
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
