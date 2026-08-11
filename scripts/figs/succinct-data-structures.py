#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/succinct-data-structures/figs/*.svg を決定的に生成する。

作図規約は .claude/skills/zuhan/references/conventions.md、配置と検査は同 references/repo.md。
本教材での色の割り当て（3系統）:
  E_BLUE  1 のビット・索引が指す先
  ACCENT  いま問い合わせている位置・区間
  H_RED   要件違反・余計に払っている量
数値は本文の入力値から計算し、描く前に assert で本文の値と突き合わせる。
"""
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (  # noqa: E402
    SVG, E_BLUE, H_RED, INK, SUB, FIX_GRAY, ACCENT, N_TINT, P_TINT, DEP_TINT, OX_TINT,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "succinct-data-structures" / "figs"


# ---------------------------------------------------------------- 共通ヘルパ

def r1(v):
    """座標を1桁へ丸めて出力を決定的にする。"""
    return round(float(v), 1)


def bit_cells(s, bits, x0, y, cw, ch, size=None, sw=1.0,
              one_fill=N_TINT, zero_fill="#ffffff", stroke=FIX_GRAY):
    """0/1 の並びをセル列として描く。1 は淡い地色＋青字、0 は白地＋灰字。"""
    size = size or min(cw * 0.62, ch * 0.55)
    for k, b in enumerate(bits):
        b = int(b)
        x = r1(x0 + k * cw)
        s.rect(x, y, r1(cw), ch, fill=one_fill if b else zero_fill, stroke=stroke, sw=sw)
        s.text(r1(x + cw / 2), r1(y + ch * 0.71), str(b), size=r1(size),
               fill=E_BLUE if b else SUB, anchor="middle", weight="700" if b else "400")


def char_cells(s, chars, x0, y, cw, ch, size=13, fill="#ffffff", stroke=FIX_GRAY, ink=INK):
    for k, c in enumerate(chars):
        x = r1(x0 + k * cw)
        s.rect(x, y, r1(cw), ch, fill=fill, stroke=stroke, sw=1.0)
        s.text(r1(x + cw / 2), r1(y + ch * 0.7), c, size=size, fill=ink, anchor="middle")


def span_bar(s, x1, x2, y, h, label, fill, ink=INK, size=12, label_inside=True):
    """区間を表す横棒。ラベルは棒の中（入らなければ右横）へ直接置く。"""
    s.rect(r1(x1), y, r1(x2 - x1), h, fill=fill, stroke=ink, sw=1.2, rx=3)
    if label_inside:
        s.text(r1((x1 + x2) / 2), r1(y + h * 0.72), label, size=size, fill=ink, anchor="middle")
    else:
        s.text(r1(x2 + 8), r1(y + h * 0.72), label, size=size, fill=ink)


def bracket(s, x1, x2, y, depth=6, color=SUB, sw=1.2, up=True):
    """区間の上（または下）に置く括弧。引き出し線を使わずに範囲を示す。"""
    d = -depth if up else depth
    s.line(r1(x1), r1(y + d), r1(x2), r1(y + d), stroke=color, sw=sw)
    s.line(r1(x1), r1(y + d), r1(x1), y, stroke=color, sw=sw)
    s.line(r1(x2), r1(y + d), r1(x2), y, stroke=color, sw=sw)


# ---------------------------------------------------------------- 図1-1

def fig1_entropy():
    """1-2：1の割合 p と、1要素あたりの理論下限。

    グリッド  760 x 400
      プロット領域 x 130..700 / y 80..330
      x は log10(p)、p は 0.001..0.5。y は H0 の 0..1.08
    """
    W, H = 760, 400
    X0, X1, Y0, Y1 = 130, 700, 330, 80          # Y0 が H0=0、Y1 が H0=1.08
    PLO, PHI, HMAX = 0.001, 0.5, 1.08

    def h0(p):
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    def px(p):
        return X0 + (math.log10(p) - math.log10(PLO)) / (math.log10(PHI) - math.log10(PLO)) * (X1 - X0)

    def py(v):
        return Y0 - v / HMAX * (Y0 - Y1)

    assert abs(h0(0.01) - 0.0808) < 5e-4, h0(0.01)      # 本文の 0.0808
    assert abs(h0(0.5) - 1.0) < 1e-12

    s = SVG(W, H, "1の割合が偏るほど1要素あたりの必要ビット数は1ビットより小さくなる")

    # 軸
    s.line(X0, Y0, X1, Y0, stroke=INK, sw=1.4)
    s.line(X0, Y0, X0, Y1 - 6, stroke=INK, sw=1.4)
    for v, lab in [(0.0, "0"), (0.5, "0.5"), (1.0, "1.0")]:
        y = r1(py(v))
        s.line(X0 - 5, y, X0, y, stroke=INK, sw=1.2)
        s.text(X0 - 10, y + 4, lab, size=11, fill=SUB, anchor="end")
    for p, lab in [(0.001, "0.001"), (0.01, "0.01"), (0.1, "0.1"), (0.5, "0.5")]:
        x = r1(px(p))
        s.line(x, Y0, x, Y0 + 5, stroke=INK, sw=1.2)
        s.text(x, Y0 + 20, lab, size=11, fill=SUB, anchor="middle")

    # 曲線と、普通のビットベクトルが余計に払う面積
    ps = [PLO * (PHI / PLO) ** (k / 200) for k in range(201)]
    curve = [(r1(px(p)), r1(py(h0(p)))) for p in ps]
    ceil_y = r1(py(1.0))
    area = "M " + " L ".join(f"{x} {y}" for x, y in curve)
    area += f" L {curve[-1][0]} {ceil_y} L {curve[0][0]} {ceil_y} Z"
    s.path(area, stroke="none", sw=0, fill=P_TINT)
    s.line(X0, ceil_y, X1, ceil_y, stroke=H_RED, sw=1.6, dash="7 4")
    s.path("M " + " L ".join(f"{x} {y}" for x, y in curve), stroke=E_BLUE, sw=2.6)

    # 注目点 p=0.01
    xq, yq = r1(px(0.01)), r1(py(h0(0.01)))
    s.line(xq, Y0, xq, yq, stroke=ACCENT, sw=1.2, dash="3 3")
    s.circle(xq, yq, 5.5, fill=ACCENT, stroke=ACCENT, sw=0)
    mid = r1((yq + ceil_y) / 2)
    s.arrow(xq, mid - 6, xq, ceil_y + 4, stroke=H_RED, sw=1.6)
    s.arrow(xq, mid + 6, xq, yq - 4, stroke=H_RED, sw=1.6)
    s.text(xq + 10, mid + 4, "12倍", size=13, fill=H_RED, weight="700")
    s.text(xq + 10, yq + 18, "避難所 1% で 0.081 ビット", size=12, fill=ACCENT, weight="700")

    # p=0.5
    x5, y5 = r1(px(0.5)), ceil_y
    s.circle(x5, y5, 5.5, fill="#ffffff", stroke=E_BLUE, sw=2)
    s.text(x5 - 10, y5 - 12, "半々なら縮まない", size=12, fill=E_BLUE, anchor="end")

    s.text(X0 + 8, ceil_y - 12, "普通のビットベクトル 1ビット/要素", size=12, fill=H_RED)
    s.text(r1(px(0.03)), r1(py(0.62)), "余計に払っている分", size=12, fill=H_RED)
    s.text(X0 - 24, Y1 - 18, "1要素あたりの必要ビット数 H0(p)", size=13, fill=INK, weight="700")
    s.text(X1, Y0 + 44, "1 の割合 p（対数目盛）", size=12, fill=INK, anchor="end")
    return "fig1-1-entropy.svg", s


# ---------------------------------------------------------------- 図2-1

BITS48 = ("0010100110010100"      # 本文のやる市 16ビット
          "1001000101100010"
          "0100110001010010")


def fig2_rank():
    """2-1：rank_1(31) = S + L + popcount。

    グリッド  760 x 300
      セル列 x 68..692（48セル x 13）、y 118..144
      寄与の帯 y 50 / 72 / 94、区画の目盛 y 148..186
    """
    n, SB, BL, q = 48, 16, 4, 31
    bits = [int(c) for c in BITS48]
    assert len(bits) == n and sum(bits) == 18

    def rank(i):
        return sum(bits[:i])

    S = [rank(SB * j) for j in range(n // SB)]                       # 全体先頭からの累積
    L = [rank(BL * b) - S[(BL * b) // SB] for b in range(n // BL)]   # スーパーブロック内の累積
    sb, blk = q // SB, q // BL
    rem = bits[BL * blk:q]
    assert S == [0, 6, 12] and L[7] == 5 and sum(rem) == 1
    assert S[sb] + L[blk] + sum(rem) == rank(q) == 12

    W, H = 760, 300
    CW, X0, YC, CH = 13, 68, 118, 26

    def cx(i):
        return r1(X0 + i * CW)

    s = SVG(W, H, "rank は大区画の累積、小区画の累積、残りの popcount の3つを足すだけで求まる")

    span_bar(s, cx(0), cx(SB), 50, 16, "スーパーブロック累積 S = 6", N_TINT)
    span_bar(s, cx(SB), cx(BL * blk), 72, 16, "ブロック累積 L = 5", OX_TINT)
    span_bar(s, cx(BL * blk), cx(q), 94, 16, "残りを popcount = 1", P_TINT,
             label_inside=False, size=11)

    bit_cells(s, bits, X0, YC, CW, CH, size=8.5)

    # 区画の目盛。ブロックはスーパーブロック内の累積値を直下へ置く
    for b in range(n // BL):
        x = cx(BL * b)
        s.line(x, YC + CH, x, YC + CH + 8, stroke=FIX_GRAY, sw=1.0)
        s.text(r1(x + BL * CW / 2), YC + CH + 22, str(L[b]), size=11, fill=SUB, anchor="middle")
    for j in range(n // SB + 1):
        x = cx(SB * j)
        s.line(x, YC - 4, x, YC + CH + 40, stroke=INK, sw=1.3, dash="4 3")
        if j < len(S):
            s.text(r1(x + SB * CW / 2), YC + CH + 56, "S = " + str(S[j]),
                   size=12, fill=INK, anchor="middle", weight="700")

    # 問い合わせ位置
    s.line(cx(q), 44, cx(q), YC + CH + 10, stroke=ACCENT, sw=2)
    s.text(cx(q) + 6, 40, "i = 31", size=12, fill=ACCENT, weight="700")

    s.text(X0, 226, "小さい数字：ブロック先頭までの累積（スーパーブロック内）", size=11, fill=SUB)
    s.text(X0, 262, "rank_1(31) = 6 + 5 + 1 = 12", size=17, fill=INK, weight="700")
    return "fig2-1-rank.svg", s


# ---------------------------------------------------------------- 図2-2

def fig2_select():
    """2-2：select の標本は1の個数で刻む。区間の長さは密度で7倍違う。

    グリッド  760 x 360
      ビット帯 x 68..688 / y 150..182
      疎な区間 68..610（1,120ビット）、密な区間 610..688（160ビット）。幅の比は 7:1 で本文の値に比例
    """
    W, H = 760, 360
    XA, XB, XE = 68, 610, 688
    YB, HB = 150, 32
    assert abs((XB - XA) / (XE - XB) - 1120 / 160) < 0.1     # 幅は本文の比に比例させる
    s = SVG(W, H, "1を8個ごとに標本すると、同じ8個でも区間の長さは密度で桁が変わる")

    s.rect(XA, YB, XB - XA, HB, fill=N_TINT, stroke=FIX_GRAY, sw=1.0)
    s.rect(XB, YB, XE - XB, HB, fill=OX_TINT, stroke=FIX_GRAY, sw=1.0)

    # 1 の位置。疎な区間は 8 個を広く、密な区間は同じ 8 個を詰めて置く
    for x in [XA + 30 + k * 68 for k in range(8)] + [XB + 8 + k * 8.5 for k in range(8)]:
        s.line(r1(x), YB + 3, r1(x), YB + HB - 3, stroke=E_BLUE, sw=2.4)

    for x, lab in [(XA, "0"), (XB, "8"), (XE, "16")]:
        s.arrow(r1(x), 110, r1(x), YB - 3, stroke=ACCENT, sw=2)
        s.text(r1(x), 102, lab, size=12, fill=ACCENT, anchor="middle", weight="700")
    s.text(XA, 82, "1 を 8 個ごとに標本する（何ビット目かでは刻まない）", size=12,
           fill=ACCENT, weight="700")

    s.dim(XA, XB, YB + HB + 28, "1 が 8 個 / 幅 1,120 ビット")
    s.line(XB, YB + HB + 4, XB, YB + HB + 76, stroke=SUB, sw=1.0)
    s.line(XE, YB + HB + 4, XE, YB + HB + 76, stroke=SUB, sw=1.0)
    s.line(XB, YB + HB + 72, XE, YB + HB + 72, stroke=SUB, sw=1.0)
    s.text(XE, YB + HB + 94, "1 が 8 個 / 幅 160 ビット", size=11, fill=SUB, anchor="end")

    for y, tint, lab in [(300, N_TINT, "疎な区間：8 個の位置をそのまま保存する（区間が長いので割に合う）"),
                         (330, OX_TINT, "密な区間：短いので、さらに分割して表引きする")]:
        s.rect(XA, y - 12, 22, 16, fill=tint, stroke=FIX_GRAY, sw=1.0)
        s.text(XA + 32, y, lab, size=12, fill=INK)
    return "fig2-2-select.svg", s


# ---------------------------------------------------------------- 図3-1

def fig3_elias_fano():
    """3-1：Elias-Fano。上位部が上位ビット列の「位置」へ移る。

    グリッド  760 x 360
      上位ビット列 9セル x 46、x 250..664、y 116..146
      行 位置p / 順位i / 上位h / 下位 / 値x を y 108 / 186 / 216 / 254 / 300
    """
    vals, U, m = [3, 8, 9, 21, 37], 64, 5
    Lb = int(math.log2(U // m))
    assert Lb == 3
    hi = [v >> Lb for v in vals]
    lo = [v & ((1 << Lb) - 1) for v in vals]
    ones = [h + i for i, h in enumerate(hi)]
    assert hi == [0, 1, 1, 2, 4] and lo == [3, 0, 1, 5, 5]
    assert ones == [0, 2, 3, 5, 8]
    nb = ones[-1] + 1
    bits = [1 if k in ones else 0 for k in range(nb)]
    assert "".join(map(str, bits)) == "101101001"
    assert (hi[3] << Lb) | lo[3] == 21 and ones[3] - 3 == hi[3]

    W, H = 760, 360
    CW, X0, YC, CH = 46, 250, 116, 30
    LX = 238

    def cx(k):
        return r1(X0 + k * CW + CW / 2)

    s = SVG(W, H, "上位部は上位ビット列の1の位置へ移り、select で引き算するだけで戻る")

    # 注目列（本文の i=3）
    s.rect(r1(cx(5) - CW / 2), 62, CW, 250, fill=OX_TINT, stroke="none", sw=0)

    # 構築：位置 h + i へ 1 を置く
    s.text(LX, 84, "1 を置く位置 h + i", size=12, fill=INK, anchor="end", weight="700")
    for i, p in enumerate(ones):
        s.text(cx(p), 84, f"{hi[i]}+{i}", size=12, fill=ACCENT, anchor="middle", weight="700")

    bit_cells(s, bits, X0, YC, CW, CH, size=15)
    s.text(LX, 108, "位置 p", size=12, fill=SUB, anchor="end")
    for k in range(nb):
        s.text(cx(k), 108, str(k), size=11, fill=SUB, anchor="middle")

    rows = [
        (186, "順位 i", [str(i) for i in range(m)], SUB, 12),
        (216, "上位 h = p - i", [str(v) for v in hi], INK, 13),
        (300, "値 x = 8h + 下位", [str(v) for v in vals], INK, 14),
    ]
    for y, lab, cells, col, size in rows:
        s.text(LX, y, lab, size=12, fill=INK, anchor="end", weight="700")
        for i, p in enumerate(ones):
            s.text(cx(p), y, cells[i], size=size, fill=col, anchor="middle",
                   weight="700" if size > 12 else "400")

    s.text(LX, 262, "下位 3 ビット", size=12, fill=INK, anchor="end", weight="700")
    for i, p in enumerate(ones):
        x = r1(cx(p) - 20)
        s.rect(x, 240, 40, 28, fill=N_TINT, stroke=FIX_GRAY, sw=1.0)
        s.text(cx(p), 259, format(lo[i], "03b"), size=12, fill=E_BLUE, anchor="middle")

    s.text(X0, 336, "h_i = select_1(i) - i", size=15, fill=INK, weight="700")
    s.text(X0 + 190, 336, "select_1(3) = 5 なので h = 2、下位 5、x = 21", size=12, fill=ACCENT)
    return "fig3-1-elias-fano.svg", s


# ---------------------------------------------------------------- 木（4-1 / 4-2 共有）

TREE = [
    ("日本", [1, 2]),
    ("東京都", [3, 4]),
    ("大阪府", [5]),
    ("港区", [6, 7]),
    ("新宿区", []),
    ("大阪市", []),
    ("六本木", []),
    ("芝浦", []),
]
# 木の描画座標（4-1 で使う。ノード番号は 4-2 でもそのまま使う）
NODE_XY = {0: (390, 70), 1: (250, 145), 2: (540, 145), 3: (160, 220),
           4: (330, 220), 5: (540, 220), 6: (110, 295), 7: (215, 295)}


def louds_bits():
    out = []
    for _, ch in TREE:
        out += [1] * len(ch) + [0]
    return out


def fig4_louds():
    """4-1：LOUDS の 0 と 1 が木のどこに対応するか。

    グリッド  760 x 520
      木 y 55..310（ノード箱 76x30）
      見出し y 330、区切り括弧 y 362、ビット列 15セル x 40、x 80..680、y 372..404
    """
    bits = louds_bits()
    n = len(TREE)
    assert len(bits) == 2 * n - 1 == 15
    assert "".join(map(str, bits)) == "110110101100000"
    zeros = [i for i, b in enumerate(bits) if b == 0]
    onepos = [i for i, b in enumerate(bits) if b == 1]
    assert zeros == [2, 5, 7, 10, 11, 12, 13, 14]          # select_0(v) = ノード v の終端
    child_of = {p: k + 1 for k, p in enumerate(onepos)}     # rank_1(p) + 1 = 子のノード番号
    assert child_of[6] == 5 and child_of[9] == 7

    W, H = 760, 520
    BW, BH = 76, 30
    CW, X0, YC, CH = 40, 80, 372, 32

    def cx(k):
        return r1(X0 + k * CW + CW / 2)

    s = SVG(W, H, "LOUDS の 0 はノードの終端、1 は子。ポインタなしで rank と select が親子をつなぐ")

    for v, (name, ch) in enumerate(TREE):
        x, y = NODE_XY[v]
        for c in ch:
            xc, yc = NODE_XY[c]
            s.line(x, y + BH / 2, xc, yc - BH / 2, stroke=FIX_GRAY, sw=1.4, role="connector")
    for v, (name, ch) in enumerate(TREE):
        x, y = NODE_XY[v]
        s.rect(r1(x - BW / 2), r1(y - BH / 2), BW, BH, fill=N_TINT, stroke=INK, sw=1.3, rx=4)
        s.text(x + 6, y + 5, name, size=13, fill=INK, anchor="middle")
        s.circle(r1(x - BW / 2 + 1), r1(y - BH / 2 + 1), 10, fill="#ffffff", stroke=SUB, sw=1.2)
        s.text(r1(x - BW / 2 + 1), r1(y - BH / 2 + 5), str(v), size=11, fill=SUB, anchor="middle")

    # ノードごとの 1^d 0 の区切りと、そのノード番号
    start = 0
    for v, (_, ch) in enumerate(TREE):
        end = start + len(ch) + 1
        x1, x2 = r1(X0 + start * CW + 2), r1(X0 + end * CW - 2)
        bracket(s, x1, x2, YC - 2, depth=8, color=SUB)
        s.text(r1((x1 + x2) / 2), YC - 16, str(v), size=12, fill=SUB, anchor="middle", weight="700")
        start = end

    bit_cells(s, bits, X0, YC, CW, CH, size=16)
    for p, c in child_of.items():
        s.text(cx(p), YC + CH + 20, str(c), size=13, fill=E_BLUE, anchor="middle", weight="700")

    s.text(X0, 334, "幅優先順に、子の数だけ 1 を並べ、0 で閉じる", size=12, fill=INK, weight="700")
    s.text(X0, YC + CH + 46, "上の数字：ノード番号（0 の並び順 = select_0）", size=11, fill=SUB)
    s.text(X0, YC + CH + 64, "下の数字：その 1 が指す子のノード番号（rank_1 + 1）", size=11, fill=E_BLUE)
    s.text(X0, YC + CH + 92, "15 ビット = 2n - 1。ポインタ 3 本 x 8 ノードなら 192 ビット", size=13,
           fill=INK, weight="700")
    return "fig4-1-louds.svg", s


def bp_sequence():
    """深さ優先の括弧列を (ビット, ノード番号, 開きか) の列で返す。"""
    seq = []

    def walk(v):
        seq.append((1, v, True))
        for c in TREE[v][1]:
            walk(c)
        seq.append((0, v, False))

    walk(0)
    return seq


def fig4_bp():
    """4-2：括弧列の excess と、連続区間になる部分木。

    グリッド  760 x 420
      excess 折れ線 x 95..703（16位置 x 38）、深さ 0..4 を y 300..80（55/段）
      括弧セル y 320..348、位置番号 y 366、ノード番号 y 386
    """
    seq = bp_sequence()
    bits = [b for b, _, _ in seq]
    n = len(TREE)
    assert len(bits) == 2 * n == 16
    depth, d = [], 0
    for b in bits:
        d += 1 if b else -1
        depth.append(d)
    assert depth == [1, 2, 3, 4, 3, 4, 3, 2, 3, 2, 1, 2, 3, 2, 1, 0]
    op = next(i for i, (b, v, o) in enumerate(seq) if v == 3 and o)
    cl = next(i for i, (b, v, o) in enumerate(seq) if v == 3 and not o)
    assert (op, cl) == (2, 7) and (cl - op + 1) // 2 == 3

    W, H = 760, 420
    CW, X0, YCELL, CHC = 38, 95, 320, 28
    DY0, DSTEP = 300, 55

    def x(i):
        return r1(X0 + i * CW)

    def yd(v):
        return r1(DY0 - v * DSTEP)

    s = SVG(W, H, "深さ優先の括弧列では、部分木がひとつながりの区間として現れる")

    # 港区（節3）の部分木の帯
    s.rect(x(op), 66, r1(x(cl + 1) - x(op)), 288, fill=OX_TINT, stroke="none", sw=0)

    for v in range(5):
        s.line(X0 - 6, yd(v), x(16), yd(v), stroke="#e2e2e2", sw=1.0)
        s.text(X0 - 12, yd(v) + 4, str(v), size=11, fill=SUB, anchor="end")

    pts = [(x(0), yd(0))]
    for i, dv in enumerate(depth):
        pts.append((x(i), yd(dv)))
        pts.append((x(i + 1), yd(dv)))
    s.path("M " + " L ".join(f"{a} {b}" for a, b in pts), stroke=E_BLUE, sw=2.6)

    s.line(x(op), yd(2), x(cl + 1), yd(2), stroke=ACCENT, sw=1.8, dash="6 4")
    s.circle(x(op), yd(2), 5, fill=ACCENT, stroke=ACCENT, sw=0)
    s.circle(x(cl + 1), yd(2), 5, fill=ACCENT, stroke=ACCENT, sw=0)

    for i, (b, v, o) in enumerate(seq):
        cell = "(" if b else ")"
        hot = i in (op, cl)
        s.rect(x(i), YCELL, CW, CHC, fill=OX_TINT if hot else "#ffffff",
               stroke=ACCENT if hot else FIX_GRAY, sw=1.6 if hot else 1.0)
        s.text(r1(x(i) + CW / 2), YCELL + 20, cell, size=16,
               fill=ACCENT if hot else INK, anchor="middle", weight="700")
        s.text(r1(x(i) + CW / 2), YCELL + 46, str(i), size=10, fill=SUB, anchor="middle")
        if o:
            s.text(r1(x(i) + CW / 2), YCELL + 66, str(v), size=12, fill=E_BLUE,
                   anchor="middle", weight="700")

    s.text(X0 - 12, 60, "深さ（excess）", size=12, fill=INK, weight="700")
    s.text(x(cl + 1) + 10, yd(2) - 8, "同じ深さへ初めて戻る位置", size=11, fill=ACCENT)
    # 結論は帯の中の空いている場所へ直接置く（引き出し線を引かない）
    s.text(x(op) + 10, 252, "節 3 の部分木", size=13, fill=ACCENT, weight="700")
    s.text(x(op) + 10, 274, "= 連続した 6 ビット", size=12, fill=ACCENT)
    s.text(x(op) + 10, 294, "= (7 - 2 + 1) / 2 = 3 ノード", size=12, fill=ACCENT)
    s.text(X0, 404, "( は 1、) は 0。下の数字は開き括弧のノード番号（図4-1と同じ番号）",
           size=11, fill=SUB)
    return "fig4-2-bp.svg", s


# ---------------------------------------------------------------- 数値列（5-1 / 5-2 共有）

SEQ = [3, 1, 3, 7, 2, 3, 1, 6, 4, 3, 2, 7]
LO, HI = 2, 9          # 本文と同じ区間 [2, 9)


def bit_at(v, level, nbits=3):
    return (v >> (nbits - 1 - level)) & 1


def fig5_wavelet_tree():
    """5-1：Wavelet Tree の上で区間 [2,9) がどこへ写るか。

    グリッド  760 x 440
      根   12セル x 26、x 200..512、y 95
      階層1 左8セル x 70..278 / 右4セル x 470..574、y 215
      階層2 2/6/1/3セル、x 55 / 160 / 450 / 520、y 330
      階層名は右端 x 630
    """
    root = list(SEQ)
    b0 = [bit_at(v, 0) for v in root]
    left = [v for v in root if not bit_at(v, 0)]
    right = [v for v in root if bit_at(v, 0)]
    assert left == [3, 1, 3, 2, 3, 1, 3, 2] and right == [7, 6, 4, 7]
    b1l = [bit_at(v, 1) for v in left]
    b1r = [bit_at(v, 1) for v in right]
    ll = [v for v in left if not bit_at(v, 1)]
    lr = [v for v in left if bit_at(v, 1)]
    rl = [v for v in right if not bit_at(v, 1)]
    rr = [v for v in right if bit_at(v, 1)]
    assert (ll, lr, rl, rr) == ([1, 1], [3, 3, 2, 3, 3, 2], [4], [7, 6, 7])

    r0 = lambda i: sum(1 for b in b0[:i] if b == 0)      # noqa: E731
    r1_ = lambda i: sum(1 for b in b0[:i] if b == 1)     # noqa: E731
    L0, R0 = r0(LO), r0(HI)
    L1, R1 = r1_(LO), r1_(HI)
    assert (L0, R0) == (2, 6) and (L1, R1) == (0, 3)

    W, H = 760, 440
    CW, CH = 26, 28
    ROOT_X, ROOT_Y = 200, 95
    LX1, RX1, Y1 = 70, 470, 215
    Y2 = 330
    s = SVG(W, H, "値域を半分ずつ割る木の上で、区間はそのまま子の区間へ写る")

    def node(x, y, vals, bits, rng, hl=None, hlab=None):
        for k, v in enumerate(vals):
            s.text(r1(x + k * CW + CW / 2), y - 8, str(v), size=11, fill=SUB, anchor="middle")
        bit_cells(s, bits, x, y, CW, CH, size=14)
        s.text(r1(x + len(vals) * CW / 2), y + CH + 18, rng, size=11, fill=SUB, anchor="middle")
        if hl:
            a, b = hl
            x1, x2 = r1(x + a * CW), r1(x + b * CW)
            s.rect(x1, y - 4, r1(x2 - x1), CH + 8, fill="none", stroke=ACCENT, sw=2, rx=3)
            s.text(r1((x1 + x2) / 2), y - 26, hlab, size=12, fill=ACCENT,
                   anchor="middle", weight="700")

    node(ROOT_X, ROOT_Y, root, b0, "値 0-7", (LO, HI), "[2, 9)")
    node(LX1, Y1, left, b1l, "値 0-3", (L0, R0), "[2, 6)")
    node(RX1, Y1, right, b1r, "値 4-7", (L1, R1), "[0, 3)")
    node(55, Y2, ll, [bit_at(v, 2) for v in ll], "値 0-1")
    node(160, Y2, lr, [bit_at(v, 2) for v in lr], "値 2-3")
    node(450, Y2, rl, [bit_at(v, 2) for v in rl], "値 4-5")
    node(520, Y2, rr, [bit_at(v, 2) for v in rr], "値 6-7")

    edges = [((356, ROOT_Y + CH + 24), (174, Y1 - 38)),
             ((356, ROOT_Y + CH + 24), (522, Y1 - 38)),
             ((174, Y1 + CH + 24), (81, Y2 - 14)),
             ((174, Y1 + CH + 24), (238, Y2 - 14)),
             ((522, Y1 + CH + 24), (463, Y2 - 14)),
             ((522, Y1 + CH + 24), (559, Y2 - 14))]
    for (ax, ay), (bx, by) in edges:
        s.line(ax, ay, bx, by, stroke=FIX_GRAY, sw=1.3, role="connector")

    s.text(292, 158, "rank_0 で左へ", size=12, fill=E_BLUE, anchor="end")
    s.text(420, 158, "rank_1 で右へ", size=12, fill=E_BLUE)
    s.text(ROOT_X, 50, "S（施設種別列）", size=12, fill=INK, weight="700")
    s.text(630, ROOT_Y + 20, "最上位ビット", size=11, fill=SUB)
    s.text(630, Y1 + 20, "第2ビット", size=11, fill=SUB)
    s.text(630, Y2 + 20, "第3ビット", size=11, fill=SUB)
    s.text(55, 416, "ノードごとにビット列が分かれる = ノードごとにポインタが要る", size=12, fill=H_RED)
    return "fig5-1-wavelet-tree.svg", s


def fig5_wavelet_matrix():
    """5-2：同じ木を階層ごとに平らへ並べ替える。Z_d だけ右へずれる。

    グリッド  760 x 460
      3行 x 12セル x 38、x 180..636、行 y 105 / 240 / 355
      区間の札 行0は上 y 77、行1は上 y 212。矢印とその札は隙間 143..212
    """
    order = [list(SEQ)]
    rows, Z = [], []
    for d in range(3):
        cur = order[-1]
        b = [bit_at(v, d) for v in cur]
        rows.append(b)
        Z.append(sum(1 for x in b if x == 0))
        order.append([v for v in cur if not bit_at(v, d)] + [v for v in cur if bit_at(v, d)])
    assert Z == [8, 3, 4]
    assert order[1] == [3, 1, 3, 2, 3, 1, 3, 2, 7, 6, 4, 7]
    assert order[2] == [1, 1, 4, 3, 3, 2, 3, 3, 2, 7, 6, 7]

    r0 = lambda i: sum(1 for b in rows[0][:i] if b == 0)      # noqa: E731
    r1_ = lambda i: sum(1 for b in rows[0][:i] if b == 1)     # noqa: E731
    zl, zr = r0(LO), r0(HI)
    ol, orr = Z[0] + r1_(LO), Z[0] + r1_(HI)
    assert (zl, zr) == (2, 6) and (ol, orr) == (8, 11)

    W, H = 760, 460
    CW, CH, X0 = 38, 30, 180
    YS = [105, 240, 355]
    s = SVG(W, H, "階層ごとに0を前へ寄せると木の境界が消え、1側の区間は Z だけ右へずれる")

    def cx(k):
        return r1(X0 + k * CW)

    for d, y in enumerate(YS):
        for k, v in enumerate(order[d]):
            s.text(r1(cx(k) + CW / 2), y - 8, str(v), size=11, fill=SUB, anchor="middle")
        bit_cells(s, rows[d], X0, y, CW, CH, size=15)
        s.text(160, y + 20, f"階層{d}", size=12, fill=INK, anchor="end", weight="700")
        s.text(650, y + 20, f"Z_{d} = {Z[d]}", size=12, fill=INK, weight="700")

    # 一つ上の階層の 0 の個数が、この行の並べ替えの境界になる。札は下の注記へまとめる
    for d in (1, 2):
        xb = cx(Z[d - 1])
        s.line(xb, YS[d] - 22, xb, YS[d] + CH + 8, stroke=H_RED, sw=1.8, dash="5 3")

    def mark(y, a, b, lab, dy):
        x1, x2 = cx(a), cx(b)
        s.rect(x1, y - 4, r1(x2 - x1), CH + 8, fill="none", stroke=ACCENT, sw=2, rx=3)
        s.text(r1((x1 + x2) / 2), y + dy, lab, size=12, fill=ACCENT, anchor="middle", weight="700")

    mark(YS[0], LO, HI, "[2, 9)", dy=-28)
    mark(YS[1], zl, zr, "[2, 6)", dy=-28)
    mark(YS[1], ol, orr, "[8, 11)", dy=-28)
    s.arrow(r1(cx(3) + 10), YS[0] + CH + 14, r1(cx(3) + 10), YS[1] - 46, stroke=E_BLUE, sw=2)
    s.text(r1(cx(3) + 18), 182, "rank_0", size=12, fill=E_BLUE)
    s.arrow(r1(cx(7) + 20), YS[0] + CH + 14, r1(cx(9) + 8), YS[1] - 46, stroke=E_BLUE, sw=2)
    s.text(r1(cx(9) + 18), 182, "Z_0 + rank_1", size=12, fill=E_BLUE)

    s.text(X0, 52, "各階層が 1 本の連続ビット列になり、ノードのポインタが消える",
           size=12, fill=INK, weight="700")
    s.text(X0, 412, "赤い破線は一つ上の階層の 0 の個数 Z。そこで 0 側と 1 側が分かれる",
           size=11, fill=H_RED)
    s.text(X0, 436, "図5-1 で [0, 3) だった 1 側の区間が、Z_0 = 8 だけ右へずれている",
           size=12, fill=ACCENT, weight="700")
    return "fig5-2-wavelet-matrix.svg", s


# ---------------------------------------------------------------- BWT（6-1 / 6-2 共有）

TEXT = "banana$"


def rotations():
    n = len(TEXT)
    rots = sorted(TEXT[i:] + TEXT[:i] for i in range(n))
    return rots


def fig6_bwt():
    """6-1：F と L の同じ文字は同じ順序で対応する。

    グリッド  760 x 400
      巡回表 x 80..220（7文字 x 20）、行 y 95..305（35刻み）
      抜き出し L列 x 320..366 / F列 x 480..526
    """
    rots = rotations()
    F = "".join(r[0] for r in rots)
    Lc = "".join(r[-1] for r in rots)
    assert F == "$aaabnn" and Lc == "annb$aa"
    C = {c: sum(1 for ch in TEXT if ch < c) for c in set(TEXT)}
    assert C["a"] == 1 and C["b"] == 4 and C["n"] == 5
    la = [i for i, c in enumerate(Lc) if c == "a"]
    fa = [i for i, c in enumerate(F) if c == "a"]
    assert la == [0, 5, 6] and fa == [1, 2, 3]
    for k, i in enumerate(la):
        assert C["a"] + k == fa[k]                      # LF(i) = C[c] + rank_c(L, i)

    W, H = 760, 400
    ROWY = [95 + 35 * k for k in range(7)]
    CW, X0, RH = 20, 80, 26
    LCX, FCX, BW2 = 320, 480, 46
    s = SVG(W, H, "L の k 番目の a は F の k 番目の a と同じ行。だから LF 写像で1文字前へ戻れる")

    s.text(X0, 72, "辞書順に並べた巡回列", size=12, fill=INK, weight="700")
    for r, y in enumerate(ROWY):
        s.text(X0 - 14, y + 18, str(r), size=11, fill=SUB, anchor="end")
        for k, ch in enumerate(rots[r]):
            fill = N_TINT if k == 0 else (OX_TINT if k == 6 else "#ffffff")
            s.rect(r1(X0 + k * CW), y, CW, RH, fill=fill, stroke=FIX_GRAY, sw=0.9)
            s.text(r1(X0 + k * CW + CW / 2), y + 18, ch, size=13, fill=INK, anchor="middle")

    s.text(LCX + BW2 / 2, 72, "L（行の末尾）", size=12, fill=INK, anchor="middle", weight="700")
    s.text(FCX + BW2 / 2, 72, "F（行の先頭）", size=12, fill=INK, anchor="middle", weight="700")
    for r, y in enumerate(ROWY):
        s.rect(LCX, y, BW2, RH, fill=OX_TINT, stroke=FIX_GRAY, sw=1.0)
        s.text(LCX + BW2 / 2, y + 18, Lc[r], size=15, fill=INK, anchor="middle")
        s.rect(FCX, y, BW2, RH, fill=N_TINT, stroke=FIX_GRAY, sw=1.0)
        s.text(FCX + BW2 / 2, y + 18, F[r], size=15, fill=INK, anchor="middle")

    for k in range(3):
        y1, y2 = ROWY[la[k]] + RH / 2, ROWY[fa[k]] + RH / 2
        s.arrow(LCX + BW2 + 6, y1, FCX - 6, y2, stroke=E_BLUE, sw=1.8)
        s.text(LCX + BW2 + 12, y1 - 8, str(k + 1), size=11, fill=E_BLUE, weight="700")
        s.text(FCX - 12, y2 - 8, str(k + 1), size=11, fill=E_BLUE, anchor="end", weight="700")

    bx = FCX + BW2 + 8
    s.line(bx, ROWY[0], bx, ROWY[0] + RH, stroke=H_RED, sw=2)
    s.text(bx + 8, ROWY[0] + 18, "C[a] = 1", size=12, fill=H_RED, weight="700")
    s.text(bx + 8, ROWY[0] + 36, "a より小さい文字の数", size=10, fill=H_RED)

    s.text(X0, 360, "LF(i) = C[c] + rank_c(L, i)", size=16, fill=INK, weight="700")
    s.text(LCX, 360, "青い矢印は a の1番目から3番目。順序は入れ替わらない", size=12, fill=E_BLUE)
    return "fig6-1-bwt-lf.svg", s


def fig6_backward_search():
    """6-2：後方検索で区間が3段階で狭まる。

    グリッド  760 x 400
      接尾辞表 x 75..205、行 y 100..310（35刻み）
      区間の帯 x 280 / 390 / 500 / 610（幅54）
    """
    rots = rotations()
    sufs = [r[:r.index("$") + 1] for r in rots]
    assert sufs == ["$", "a$", "ana$", "anana$", "banana$", "na$", "nana$"]
    Lc = "".join(r[-1] for r in rots)
    C = {c: sum(1 for ch in TEXT if ch < c) for c in set(TEXT)}

    def step(l, r, c):
        rl = sum(1 for x in Lc[:l] if x == c)
        rr = sum(1 for x in Lc[:r] if x == c)
        return C[c] + rl, C[c] + rr

    steps = [("", 0, 7)]
    l, r = 0, 7
    for c, pat in [("a", "a"), ("n", "na"), ("a", "ana")]:
        l, r = step(l, r, c)
        steps.append((pat, l, r))
    assert steps == [("", 0, 7), ("a", 1, 4), ("na", 5, 7), ("ana", 2, 4)]

    W, H = 760, 420
    ROWY = [100 + 35 * k for k in range(7)]
    RH = 26
    BARX = [280, 390, 500, 610]
    BARW = 54
    s = SVG(W, H, "後方検索は1文字ごとに rank を2回引いて区間を移すだけで、件数は区間幅に出る")

    s.text(75, 78, "接尾辞（辞書順）", size=12, fill=INK, weight="700")
    s.text(215, 78, "L", size=12, fill=INK, anchor="middle", weight="700")
    for k, y in enumerate(ROWY):
        s.text(66, y + 18, str(k), size=11, fill=SUB, anchor="end")
        s.text(75, y + 18, sufs[k], size=13, fill=INK)
        s.rect(202, y, 26, RH, fill=OX_TINT, stroke=FIX_GRAY, sw=0.9)
        s.text(215, y + 18, Lc[k], size=13, fill=INK, anchor="middle")

    labels = ["空文字列", "a", "na", "ana"]
    for k, (pat, a, b) in enumerate(steps):
        x = BARX[k]
        y1 = ROWY[a] - 4
        y2 = ROWY[b - 1] + RH + 4
        s.rect(x, y1, BARW, r1(y2 - y1), fill=OX_TINT if k else DEP_TINT,
               stroke=ACCENT if k else FIX_GRAY, sw=1.6 if k else 1.2, rx=4)
        s.text(r1(x + BARW / 2), 78, labels[k], size=13, fill=ACCENT if k else SUB,
               anchor="middle", weight="700")
        s.text(r1(x + BARW / 2), 362, f"[{a}, {b})", size=12, fill=INK, anchor="middle")

    for k in range(3):
        ax = BARX[k] + BARW + 4
        bx = BARX[k + 1] - 4
        ay = r1((ROWY[steps[k][1]] + ROWY[steps[k][2] - 1] + RH) / 2)
        by = r1((ROWY[steps[k + 1][1]] + ROWY[steps[k + 1][2] - 1] + RH) / 2)
        s.arrow(ax, ay, bx, by, stroke=E_BLUE, sw=2)
        lab = "a を付ける" if k != 1 else "n を付ける"
        s.text(r1((ax + bx) / 2), r1(min(ay, by) - 14), lab, size=10, fill=E_BLUE, anchor="middle")

    s.text(280, 396, "各段階は rank を 2 回。一致件数 = r - l = 2", size=14, fill=INK, weight="700")
    return "fig6-2-backward-search.svg", s


# ---------------------------------------------------------------- 図8-1

def fig8_budget():
    """8-2：容量と応答の平面で、要件の箱に入るのはどれか。

    グリッド  760 x 420
      プロット x 120..690 / y 340..70（0..95ms）
      x は log10(MiB)、380..2100
    """
    W, H = 760, 420
    X0, X1, Y0, Y1 = 120, 690, 340, 70
    MLO, MHI, TMAX = 380.0, 2100.0, 95.0
    BUDGET, LIMIT = 512.0, 50.0

    def px(v):
        return r1(X0 + (math.log10(v) - math.log10(MLO)) / (math.log10(MHI) - math.log10(MLO)) * (X1 - X0))

    def py(v):
        return r1(Y0 - v / TMAX * (Y0 - Y1))

    # 本文 8-2 / 9-1 の実測値。tail は最悪値が本文にあるものだけ
    cases = [
        ("フラット配列", 1884.0, 4.0, None, "起動不可"),
        ("Plain 中心", 621.0, 6.0, None, "予算超過"),
        ("圧縮中心", 403.0, 19.0, 88.0, "locate 88ms で要件を越える"),
        ("ハイブリッド", 458.0, 11.0, 43.0, "99パーセンタイル 43ms"),
    ]
    s = SVG(W, H, "最小容量の案は応答要件の線を越える。要件の箱に入るのは少し大きいハイブリッド版")

    s.rect(X0, py(LIMIT), r1(px(BUDGET) - X0), r1(Y0 - py(LIMIT)), fill=N_TINT, stroke="none", sw=0)
    s.line(X0, Y0, X1, Y0, stroke=INK, sw=1.4)
    s.line(X0, Y0, X0, Y1 - 6, stroke=INK, sw=1.4)
    for v in (25, 50, 75):
        s.line(X0 - 5, py(v), X0, py(v), stroke=INK, sw=1.2)
        s.text(X0 - 10, py(v) + 4, str(v), size=11, fill=SUB, anchor="end")
    s.text(X0 - 10, Y0 + 4, "0", size=11, fill=SUB, anchor="end")
    for v in (400, 512, 1000, 2000):
        s.line(px(v), Y0, px(v), Y0 + 5, stroke=INK, sw=1.2)
        s.text(px(v), Y0 + 20, str(v), size=11, fill=SUB, anchor="middle")

    s.line(px(BUDGET), Y1 - 6, px(BUDGET), Y0, stroke=H_RED, sw=1.8, dash="7 4")
    s.line(X0, py(LIMIT), X1, py(LIMIT), stroke=H_RED, sw=1.8, dash="7 4")
    s.text(px(BUDGET) + 8, Y1 + 8, "メモリ予算 512MiB", size=12, fill=H_RED, weight="700")
    s.text(X1, py(LIMIT) - 8, "応答要件 50ms", size=12, fill=H_RED, anchor="end", weight="700")

    # 札は棒の上端（尾を持つ案）か点の横（持たない案）へ置き、上下にずらして重なりを避ける
    place = {"圧縮中心": (12, 84, 102), "ハイブリッド": (12, 216, 234),
             "Plain 中心": (12, 316, 334), "フラット配列": (-12, 318, 336)}
    for name, mib, med, tail, note in cases:
        x = px(mib)
        if tail is not None:
            col = H_RED if tail > LIMIT else E_BLUE
            s.line(x, py(med), x, py(tail), stroke=col, sw=2.4)
            s.line(x - 7, py(tail), x + 7, py(tail), stroke=col, sw=2.4)
        s.circle(x, py(med), 6, fill=INK, stroke=INK, sw=0)
        dx, ny, yy = place[name]
        anchor = "end" if dx < 0 else "start"
        ok = mib <= BUDGET and (tail or med) <= LIMIT
        s.text(x + dx, ny, name, size=13, fill=INK, anchor=anchor, weight="700")
        if note:
            s.text(x + dx, yy, note, size=11, fill=E_BLUE if ok else H_RED, anchor=anchor)

    s.text(X0 - 14, Y1 - 24, "検索応答 [ms]（丸は中央値、棒の上端は最悪値）",
           size=12, fill=INK, weight="700")
    s.text(X0, Y0 + 44, "青い領域が要件を満たす範囲", size=11, fill=E_BLUE)
    s.text(X1, Y0 + 44, "総容量 [MiB]（対数目盛）", size=12, fill=INK, anchor="end")
    return "fig8-1-budget.svg", s


# ---------------------------------------------------------------- 実行

FIGURES = [fig1_entropy, fig2_rank, fig2_select, fig3_elias_fano, fig4_louds,
           fig4_bp, fig5_wavelet_tree, fig5_wavelet_matrix, fig6_bwt,
           fig6_backward_search, fig8_budget]


def build(dest):
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for fn in FIGURES:
        name, svg = fn()
        svg.save(dest / name)
        names.append(name)
    return names


def main():
    if "--check" in sys.argv:
        tmp = Path(tempfile.mkdtemp())
        try:
            names = build(tmp)
            bad = []
            for name in names:
                a, b = OUT_DIR / name, tmp / name
                if not a.exists() or a.read_bytes() != b.read_bytes():
                    bad.append(name)
            if bad:
                print("再生成結果と差分あり: " + ", ".join(bad))
                return 1
            print(f"{len(names)} 枚とも一致")
            return 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    build(OUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
