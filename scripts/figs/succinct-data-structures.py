#!/usr/bin/env python3
"""succinct-data-structures の図。

色：青=1のビット・構造の本体／橙=問い合わせ位置・いま追っている区間／赤=無駄・要件違反。
灰は0のビット・目盛・背景。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/succinct-data-structures/figs"


def cell(s, x, y, w, h, ch, on=None, focus=False, size=15):
    """1文字のセル。on=True で1のビット（青地）、False で0（白地・灰字）。"""
    fill = TINT[MAIN] if on else "#ffffff"
    s.rect(x, y, w, h, fill=fill, stroke=FOCUS if focus else MUTED, sw=2.4 if focus else 1)
    s.text(x + w / 2, y + h / 2 + size * 0.36, ch, size=size, anchor="middle",
           fill=MAIN if on else (SUB if on is False else INK), bold=bool(on))


def h0(p):
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def entropy():
    """1-2 1の割合が小さいほど、1要素に要る情報は1ビットを下回る。正方 M 520x400。

    x: 70 (p=0) … 470 (p=0.5)   y: 330 (0ビット) … 50 (1ビット)
    """
    assert abs(h0(0.01) - 0.0808) < 1e-3
    s = SVG(520, 400, "1の割合が1%なら、1要素あたり約0.081ビットで足りるのに、普通のビット列は1ビット払う")
    X = lambda p: 70 + p / 0.5 * 400
    Y = lambda b: 330 - b * 280
    curve = [(X(p), Y(h0(p))) for p in [i / 400 for i in range(1, 201)]]
    s.poly([(X(0), Y(0))] + curve + [(X(0.5), Y(1)), (X(0), Y(1))], fill=s.hatch(WARN),
           stroke="none", closed=True)
    s.line(X(0), Y(0), X(0.5), Y(0), stroke=MUTED)
    s.line(X(0), Y(0), X(0), Y(1.05), stroke=MUTED)
    for p in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        s.text(X(p), 352, f"{p:g}", size=14, fill=SUB, anchor="middle")
    for b in (0, 0.5, 1):
        s.text(60, Y(b) + 5, f"{b:g}", size=14, fill=SUB, anchor="end")
    s.text(X(0.25), 384, "1の割合 p", size=15, fill=SUB, anchor="middle")
    s.text(24, 34, "1要素あたりのビット数", size=15, fill=SUB)
    s.line(X(0), Y(1), X(0.5), Y(1), stroke=INK, sw=2)
    s.text(X(0.5) - 4, Y(1) - 10, "普通のビット列：1ビット", size=15, anchor="end")
    s.poly([(X(0), Y(0))] + curve, stroke=MAIN, sw=3.5)
    s.text(X(0.33), Y(h0(0.33)) + 30, "理論下限 H0(p)", size=15, fill=MAIN, bold=True)
    s.text(X(0.16), Y(0.78), "払いすぎ", size=15, fill=WARN, bold=True, halo=True)
    s.circle(X(0.01), Y(h0(0.01)), 6, fill=FOCUS, stroke="#ffffff", sw=2)
    s.note(X(0.01) + 22, Y(0.2), ["避難所1%なら", "0.081ビットで足りる"])
    return s


RANK_BITS = ["0010100110010100", "1100101001000101", "0110000110001010"]


def rank():
    """2-1 rank は大区画の累積＋小区画の累積＋残りの実測。M 600x340。

    16ビットのスーパーブロックを1行に折り、3行で48ビット。ブロックは4ビット。
    x: 40 大区画の累積 / 110 + 26*j + 6*(j//4) 各ビット
    y: 行 r の上端 76 + 84*r、高さ 34。小区画の累積は各行の上 14
    """
    rows = [[int(b) for b in r] for r in RANK_BITS]
    flat = sum(rows, [])
    i = 31
    S = [sum(flat[:16 * r]) for r in range(3)]
    L = [sum(flat[16:16 + 4 * k]) for k in range(4)]
    rem = sum(flat[28:31])
    assert (S[1], L[3], rem, sum(flat[:i])) == (6, 5, 1, 12)

    s = SVG(600, 360, "rank(31) は、大区画の累積6、小区画の累積5、残り3ビットの実測1を足して12")
    X = lambda j: 110 + 26 * j + 6 * (j // 4)
    Y = lambda r: 76 + 84 * r
    s.text(40, 34, "大区画", size=14, fill=SUB, anchor="middle")
    s.text(40, 52, "の累積", size=14, fill=SUB, anchor="middle")
    s.text(X(0), 34, "小区画の累積（大区画の中で）と、ビット列", size=14, fill=SUB)
    for r, bits in enumerate(rows):
        foc_row = r == 1
        s.text(40, Y(r) + 23, str(S[r]), size=18, anchor="middle",
               fill=FOCUS if foc_row else SUB, bold=foc_row)
        for k in range(4):
            val = sum(bits[:4 * k])
            used = foc_row and k == 3
            s.text(X(4 * k) + 2, Y(r) - 8, str(val), size=14 if not used else 16,
                   fill=FOCUS if used else SUB, bold=used)
        for j, b in enumerate(bits):
            pos = 16 * r + j
            done = pos < i
            cell(s, X(j), Y(r), 26, 34, str(b), on=bool(b) if done else None,
                 focus=28 <= pos < 31, size=15)
            if not done:
                s.rect(X(j), Y(r), 26, 34, fill="#ffffff", stroke=MUTED)
                s.text(X(j) + 13, Y(r) + 23, str(b), size=15, fill=MUTED, anchor="middle")
    qx = X(15) - 3
    s.line(qx, Y(1) - 20, qx, Y(1) + 48, stroke=FOCUS, sw=2.5)
    s.text(qx, Y(1) + 64, "i = 31", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.badge(40, Y(1) - 20, 1)
    s.badge(X(12) - 14, Y(1) - 14, 2)
    s.badge(X(13) + 13, Y(1) + 50, 3)
    s.note(110, 336, "6 ＋ 5 ＋ 1 ＝ 12：表を2回引き、3ビットだけ数える")
    return s


def select_ones():
    """2-2 1を8個ごとに標本すると、区間の長さは密度しだいで大きくぶれる。横長 L 760x250。

    位置 0..119 を x = 40 + 5.6*pos に置く。1は背の高い青線、0は短い灰線。
    標本（8個ごとの1）は上に橙の丸。区間の括弧は y=170。
    """
    ones = list(range(2, 10)) + [11, 20, 29, 38, 47, 56, 65, 74] + \
        list(range(83, 91)) + [92, 110]
    samples = ones[0::8]
    lens = [samples[k + 1] - samples[k] for k in range(len(samples) - 1)]
    assert lens[1] / lens[0] > 7 and lens[1] / lens[2] > 7
    s = SVG(760, 250, "1を8個ごとに標本すると、区間の長さは密度しだいで7倍以上ぶれる")
    X = lambda p: 40 + 5.6 * p + 2.8
    s.line(40, 110, 40 + 5.6 * 120, 110, stroke=MUTED)
    for p in range(120):
        if p in ones:
            s.line(X(p), 110, X(p), 76, stroke=MAIN, sw=2.4)
        else:
            s.line(X(p), 110, X(p), 102, stroke=MUTED)
    for p in samples:
        s.circle(X(p), 62, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(X(samples[0]) + 12, 50, "標本（1を8個ごと）", size=15, fill=FOCUS, bold=True)
    for k, (a, b) in enumerate(zip(samples, samples[1:])):
        xa, xb = X(a), X(b) - 5
        long = lens[k] > 40
        col = WARN if long else MAIN
        s.poly([(xa, 132), (xa, 142), (xb, 142), (xb, 132)], stroke=col, sw=2)
        s.text((xa + xb) / 2, 168, f"長さ {lens[k]}", size=16, fill=col,
               anchor="middle", bold=True)
        s.text((xa + xb) / 2, 190, "密：表引きで済む" if not long else "疎：位置を直接持つ",
               size=14, fill=SUB, anchor="middle")
    s.note(240, 232, "同じ8個の1でも、区間の長さは7倍以上違う")
    return s


EF = [3, 8, 9, 21, 37]


def elias_fano():
    """3-1 上位部は整数として保存せず、ビット列の1の位置へ移す。縦長 M 480x620。

    上段 y 60..170：値・上位・下位の表（列 i の x = 120 + 68*i）
    中段 y 250..290：上位ビット列（位置 p の x = 60 + 40*p）。列 i から位置 h+i へ矢印
    下段 y 380..560：i=3 の復元を読み順1〜3で
    """
    Lb = 3
    hi = [v >> Lb for v in EF]
    lo = [v & 7 for v in EF]
    pos = [h + i for i, h in enumerate(hi)]
    assert pos == [0, 2, 3, 5, 8]
    bits = "".join("1" if p in pos else "0" for p in range(max(pos) + 1))
    assert bits == "101101001"
    s = SVG(480, 630, "上位部 h は位置 h+i の1になり、select(i) − i で戻る。上位部は整数として保存しない")
    CX = lambda i: 120 + 68 * i
    PX = lambda p: 60 + 40 * p
    for r, (name, vals) in enumerate([("値 x", EF), ("上位 h", hi), ("下位 3ビット", lo)]):
        y = 70 + 42 * r
        s.text(24, y, name, size=15, fill=SUB)
        for i, v in enumerate(vals):
            f = i == 3
            s.text(CX(i) + 30, y, str(v), size=17, anchor="middle",
                   fill=FOCUS if f else (MAIN if r == 1 else INK), bold=f or r == 1)
    s.rect(CX(3) + 8, 46, 44, 132, stroke=FOCUS, sw=2, rx=6)
    s.text(CX(3) + 30, 36, "i = 3", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(24, 344, "上位ビット列：位置 h+i に1を置く", size=15, fill=SUB)
    for p, b in enumerate(bits):
        cell(s, PX(p), 250, 40, 40, b, on=b == "1", focus=p == pos[3], size=17)
        s.text(PX(p) + 20, 310, str(p), size=14, fill=SUB, anchor="middle")
    for i in range(5):
        s.arrow(CX(i) + 30, 184, PX(pos[i]) + 20, 244, stroke=FOCUS if i == 3 else MUTED,
                sw=2.4 if i == 3 else 1.4)
    s.text(24, 400, "復元（i = 3）", size=15, fill=SUB)
    steps = [f"select1(3) ＝ {pos[3]}", f"h ＝ {pos[3]} − 3 ＝ {hi[3]}",
             f"x ＝ {hi[3]} × 8 ＋ {lo[3]} ＝ {EF[3]}"]
    for k, t in enumerate(steps):
        s.badge(40, 440 + 50 * k - 6, k + 1)
        s.text(64, 440 + 50 * k, t, size=18, bold=k == 2, fill=FOCUS if k == 2 else INK)
    s.note(40, 600, "整数列の読み出しが、ビット列の select に変わった")
    return s


TREE = [("日本", 0, None), ("東京都", 1, 0), ("大阪府", 1, 0), ("港区", 2, 1),
        ("新宿区", 2, 1), ("大阪市", 2, 2), ("六本木", 3, 3), ("芝浦", 3, 3)]


def louds_bits():
    out = []
    for v in range(len(TREE)):
        d = sum(1 for t in TREE if t[2] == v)
        out.append("1" * d + "0")
    return out


def louds():
    """4-1 LOUDS：0がノードの区切り、1の並び順が子のノード番号。縦長 M 520x620。

    木 y 50..330（段 d の y = 60 + 80*d）。ビット列 y 420、セル幅 30。
    """
    groups = louds_bits()
    assert "".join(groups) == "110110101100000"
    xs = {0: 260, 1: 150, 2: 380, 3: 90, 4: 220, 5: 380, 6: 60, 7: 160}
    s = SVG(520, 620, "LOUDSでは各ノードの子の数を1で並べ0で閉じる。東京都の2個の1は全体で3番目と4番目なので、子は節3と節4")
    kids = {3, 4}
    for v, (name, d, par) in enumerate(TREE):
        if par is not None:
            s.line(xs[par], 60 + 80 * (d - 1) + 16, xs[v], 60 + 80 * d - 16,
                   stroke=FOCUS if par == 1 else MUTED, sw=2.4 if par == 1 else 1.2)
    for v, (name, d, par) in enumerate(TREE):
        f = v == 1 or v in kids
        s.rect(xs[v] - 44, 60 + 80 * d - 16, 88, 32, rx=6, fill=TINT[FOCUS] if f else "#ffffff",
               stroke=FOCUS if f else MUTED, sw=2 if f else 1.2)
        s.text(xs[v], 60 + 80 * d + 6, f"{v} {name}", size=15, anchor="middle", bold=f)
    s.text(24, 384, "子の数だけ1、最後に0（幅優先順）", size=15, fill=SUB)
    x, one = 24, 0
    for v, g in enumerate(groups):
        x0 = x
        for b in g:
            f = v == 1
            cell(s, x, 400, 30, 38, b, on=b == "1", focus=f, size=16)
            if b == "1":
                one += 1
                s.text(x + 15, 460, str(one), size=15, anchor="middle",
                       fill=FOCUS if one in kids else MAIN, bold=one in kids)
            x += 30
        s.text((x0 + x) / 2, 486, f"節{v}" if len(g) > 1 else str(v), size=14,
               fill=FOCUS if v == 1 else SUB, anchor="middle")
        x += 4
    s.text(24, 520, "青の数字：その1が指す子（何番目の1か）", size=14, fill=MAIN)
    s.text(24, 542, "下の数字：その0で閉じるノード", size=14, fill=SUB)
    s.note(24, 588, ["東京都の1は3番目と4番目 → 子は節3と節4"])
    return s


def bp():
    """4-2 括弧列の excess：部分木は「深さ2から出て深さ2へ戻る」連続区間。横長 M 640x330。

    x: 位置 k の境界 = 60 + 34*k（k=0..16）。y: 深さ d = 250 − 44*d
    """
    seq = ["(", "(", "(", "(", ")", "(", ")", ")", "(", ")", ")", "(", "(", ")", ")", ")"]
    ex = [0]
    for c in seq:
        ex.append(ex[-1] + (1 if c == "(" else -1))
    p, q = 2, 7
    assert ex[p] == 2 and ex[q + 1] == 2 and min(ex[p + 1:q + 1]) > 2 and (q - p + 1) // 2 == 3
    s = SVG(640, 340, "港区の開き括弧から深さ2へ初めて戻るまでが港区の部分木で、3ノード分の連続区間になる")
    X = lambda k: 60 + 34 * k
    Y = lambda d: 250 - 44 * d
    s.rect(X(p), Y(4) - 20, X(q + 1) - X(p), Y(0) - Y(4) + 20, fill=TINT[FOCUS], stroke="none")
    for d in range(5):
        s.text(40, Y(d) + 5, str(d), size=14, fill=SUB, anchor="end")
        s.line(X(0), Y(d), X(16), Y(d), stroke=MUTED if d != 2 else FOCUS, sw=1 if d != 2 else 1.6,
               dash=None if d != 2 else "6 4")
    s.text(24, 28, "深さ（excess）", size=15, fill=SUB)
    s.poly([(X(k), Y(e)) for k, e in enumerate(ex)], stroke=MAIN, sw=3.5)
    for k, c in enumerate(seq):
        f = p <= k <= q
        s.text((X(k) + X(k + 1)) / 2, 284, c, size=20, anchor="middle",
               fill=FOCUS if f else INK, bold=f)
    s.text((X(p) + X(q + 1)) / 2, 312, "港区の部分木", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.note(X(10), Y(4) + 6, ["対応する ) は", "深さ2へ初めて戻る位置"])
    return s


WS = [3, 1, 3, 7, 2, 3, 1, 6, 4, 3, 2, 7]


def wavelet(matrix):
    """5-1 / 5-2 同じ列・同じ区間 [2,9) を、木（ノードごとに切れる）と行列（1本につながる）で。
    M 560x380。両図で座標を固定し、違うのは2段目の並べ方だけ。

    x: セル j = 60 + 34*j。木の右ノードだけ +40 ずらす。y: 1段目 110、2段目 250
    """
    l, r = 2, 9
    b0 = [v >> 2 & 1 for v in WS]
    z = [v for v in WS if not v >> 2 & 1]
    o = [v for v in WS if v >> 2 & 1]
    Z0 = len(z)
    left = (b0[:l].count(0), b0[:r].count(0))
    right = (b0[:l].count(1), b0[:r].count(1))
    assert left == (2, 6) and right == (0, 3) and Z0 == 8
    title = ("Wavelet Matrix では2段目が1本につながり、1側の区間は Z0=8 だけ右へずれる" if matrix
             else "Wavelet Tree では区間 [2,9) が左の子では [2,6)、右の子では [0,3) へ移る")
    s = SVG(560, 380, title)
    X = lambda j: 60 + 34 * j

    def row(vals, y, x0, lo, hi, bitpos):
        for j, v in enumerate(vals):
            b = v >> bitpos & 1
            x = x0 + 34 * j
            s.text(x + 17, y - 10, str(v), size=14, fill=SUB, anchor="middle")
            cell(s, x, y, 34, 36, str(b), on=bool(b), size=16)
        if hi > lo:
            s.poly([(x0 + 34 * lo, y + 46), (x0 + 34 * lo, y + 54), (x0 + 34 * hi, y + 54),
                    (x0 + 34 * hi, y + 46)], stroke=FOCUS, sw=2.4)

    s.text(24, 60, "1段目：値の上のビット（4以上なら1）", size=15, fill=SUB)
    row(WS, 110, X(0), l, r, 2)
    s.text((X(l) + X(r)) / 2, 186, "[2, 9)", size=15, fill=FOCUS, anchor="middle", bold=True)
    s.text(24, 196, "2段目：次のビット", size=15, fill=SUB)
    if matrix:
        row(z + o, 250, X(0), *left, 1)
        s.poly([(X(Z0 + right[0]), 296), (X(Z0 + right[0]), 304), (X(Z0 + right[1]), 304),
                (X(Z0 + right[1]), 296)], stroke=FOCUS, sw=2.4)
        s.line(X(Z0), 226, X(Z0), 300, stroke=INK, sw=2, dash="5 4")
        s.text(X(Z0) + 6, 222, "Z0 = 8（0の総数）", size=15, bold=True)
        s.text((X(2) + X(6)) / 2, 326, "[2, 6)", size=15, fill=FOCUS, anchor="middle", bold=True)
        s.text((X(8) + X(11)) / 2, 326, "[8, 11)", size=15, fill=FOCUS, anchor="middle", bold=True)
        s.note(24, 364, "木の切れ目が消え、1側の区間は Z0 だけ右へずれる")
    else:
        row(z, 250, X(0), *left, 1)
        row(o, 250, X(Z0) + 40, *right, 1)
        s.text(X(0), 226, "0側（値 0〜3）", size=14, fill=SUB)
        s.text(X(Z0) + 40, 226, "1側（値 4〜7）", size=14, fill=SUB)
        s.text((X(2) + X(6)) / 2, 326, "[2, 6)", size=15, fill=FOCUS, anchor="middle", bold=True)
        s.text(X(Z0) + 40 + 34 * 1.5, 326, "[0, 3)", size=15, fill=FOCUS, anchor="middle", bold=True)
        s.note(24, 364, "区間は区間のまま、左右の子へ写る")
    return s


ROWS = ["$banana", "a$banan", "ana$ban", "anana$b", "banana$", "na$bana", "nana$ba"]


def bwt():
    """6-1 L の a と F の a は、同じ順序のまま対応する。正方 M 560x380。

    左：巡回列の表（列 c の x = 70 + 30*c、行 r の y = 70 + 40*r）
    右：L（x=380）から F（x=500）へ、a の3本を結ぶ
    """
    Lc = "".join(r[-1] for r in ROWS)
    Fc = "".join(r[0] for r in ROWS)
    assert Lc == "annb$aa" and Fc == "$aaabnn"
    La = [i for i, c in enumerate(Lc) if c == "a"]
    Fa = [i for i, c in enumerate(Fc) if c == "a"]
    s = SVG(600, 380, "Lの1・2・3番目のaは、Fの1・2・3番目のaへ順序を保ったまま対応する")
    Y = lambda r: 70 + 40 * r
    s.text(70 + 15, 40, "F", size=16, anchor="middle", bold=True, fill=MAIN)
    s.text(70 + 30 * 6 + 15, 40, "L", size=16, anchor="middle", bold=True, fill=MAIN)
    for r, row in enumerate(ROWS):
        s.text(44, Y(r) + 6, str(r), size=14, fill=SUB, anchor="end")
        for c, ch in enumerate(row):
            edge = c in (0, 6)
            s.text(70 + 30 * c + 15, Y(r) + 6, ch, size=17, anchor="middle",
                   fill=INK if edge else MUTED, bold=edge)
    s.rect(70, Y(0) - 18, 30, 280, stroke=MAIN, sw=1.6, rx=4)
    s.rect(70 + 180, Y(0) - 18, 30, 280, stroke=MAIN, sw=1.6, rx=4)
    s.text(380, 40, "L", size=16, anchor="middle", bold=True, fill=MAIN)
    s.text(500, 40, "F", size=16, anchor="middle", bold=True, fill=MAIN)
    for r in range(7):
        for x, ch in ((380, Lc[r]), (500, Fc[r])):
            a = ch == "a"
            s.text(x, Y(r) + 6, ch, size=17, anchor="middle", fill=FOCUS if a else SUB, bold=a)
    for k, (i, j) in enumerate(zip(La, Fa)):
        s.arrow(394, Y(i), 486, Y(j), stroke=FOCUS, sw=2.2)
        s.text(360, Y(i) + 6, f"{k + 1}番目", size=14, fill=FOCUS, anchor="end")
    s.text(522, Y(0) + 6, "← C[a] ＝ 1", size=14, fill=SUB)
    s.note(300, 362, "順序を保ったまま移る")
    return s


SUF = ["$", "a$", "ana$", "anana$", "banana$", "na$", "nana$"]


def backward():
    """6-2 後方検索は a → na → ana と区間を移し、件数は区間の幅。小さな多数 L 760x330。

    パネル k の左端 x = 30 + 250*k。行 r の y = 90 + 30*r。
    """
    def interval(pat):
        rows = [r for r, t in enumerate(SUF) if t.startswith(pat)]
        return rows[0], rows[-1] + 1
    steps = [("a", interval("a")), ("na", interval("na")), ("ana", interval("ana"))]
    assert [iv for _, iv in steps] == [(1, 4), (5, 7), (2, 4)]
    s = SVG(760, 330, "後方検索は a、na、ana と区間を移し、ana は2行、つまり2件")
    for k, (pat, (lo, hi)) in enumerate(steps):
        x0 = 30 + 250 * k
        s.text(x0, 44, f"{pat} の区間 [{lo}, {hi})", size=17, bold=True, fill=FOCUS)
        s.rect(x0 + 24, 90 + 30 * lo - 21, 170, 30 * (hi - lo), fill=TINT[FOCUS], stroke=FOCUS,
               sw=2, rx=4)
        for r, t in enumerate(SUF):
            inside = lo <= r < hi
            s.text(x0 + 10, 90 + 30 * r, str(r), size=14, fill=SUB, anchor="end")
            s.text(x0 + 34, 90 + 30 * r, t, size=16, fill=INK if inside else MUTED, bold=inside)
        if k < 2:
            nxt = steps[k + 1][0][0]
            s.arrow(x0 + 200, 70, x0 + 238, 70, stroke=FOCUS, sw=2.4)
            s.text(x0 + 219, 60, f"前に {nxt}", size=14, fill=FOCUS, anchor="middle")
    s.note(530, 314, "件数 ＝ 区間の幅 ＝ 2")
    return s


def budget():
    """8-2 容量と応答の平面。最小容量の案は応答要件の線を越える。正方 M 560x440。

    x: 300MiB → 70、700MiB → 510。y: 0ms → 360、100ms → 60
    """
    X = lambda m: 70 + (m - 300) / 400 * 440
    Y = lambda t: 360 - t * 3
    s = SVG(560, 440, "最小容量の圧縮中心版は中央値なら要件内だが、locate が50msを超える。要件を満たすのはハイブリッド版")
    s.rect(X(300), Y(50), X(512) - X(300), Y(0) - Y(50), fill=TINT[MAIN], stroke="none")
    s.line(X(512), Y(0), X(512), Y(100), stroke=MAIN, sw=1.6, dash="6 4")
    s.line(X(300), Y(50), X(700), Y(50), stroke=MAIN, sw=1.6, dash="6 4")
    s.text(X(512) + 6, Y(96), "512MiB", size=14, fill=MAIN)
    s.text(X(700) - 4, Y(50) - 8, "50ms", size=14, fill=MAIN, anchor="end")
    s.line(X(300), Y(0), X(700), Y(0), stroke=MUTED)
    s.line(X(300), Y(0), X(300), Y(100), stroke=MUTED)
    for m in (300, 400, 500, 600, 700):
        s.text(X(m), Y(0) + 22, str(m), size=14, fill=SUB, anchor="middle")
    for t in (0, 50, 100):
        s.text(X(300) - 8, Y(t) + 5, str(t), size=14, fill=SUB, anchor="end")
    s.text(X(500), 420, "総容量（MiB）", size=15, fill=SUB, anchor="middle")
    s.text(24, 36, "検索応答（ms）", size=15, fill=SUB)
    # (名前, 容量, 中央値, 上端, 上端の名前, 色)
    for name, m, med, top, tname, col in [
        ("圧縮中心", 403, 19, 88, "locate 88", WARN),
        ("ハイブリッド", 458, 11, 43, "99% 43", MAIN),
        ("Plain中心", 621, 6, None, None, MUTED),
    ]:
        if top:
            s.line(X(m), Y(med), X(m), Y(top), stroke=col, sw=3)
            s.line(X(m) - 8, Y(top), X(m) + 8, Y(top), stroke=col, sw=3)
            s.text(X(m) + 12, Y(top) + 5, tname, size=14, fill=col, bold=True)
        s.circle(X(m), Y(med), 7, fill=col, stroke="#ffffff", sw=2)
        s.text(X(m) - 12, Y(med) + 5, name, size=15, fill=INK if col != MUTED else SUB, anchor="end")
    s.arrow(X(660), Y(4), X(700) - 2, Y(4), stroke=MUTED, sw=2)
    s.text(X(700) - 4, Y(4) - 26, "フラット 1.84GiB", size=14, fill=SUB, anchor="end")
    s.note(X(528), Y(88), ["最小容量の案は", "応答要件を", "越える"], color=WARN)
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig1-1-entropy.svg": entropy,
        OUT / "fig2-1-rank.svg": rank,
        OUT / "fig2-2-select.svg": select_ones,
        OUT / "fig3-1-elias-fano.svg": elias_fano,
        OUT / "fig4-1-louds.svg": louds,
        OUT / "fig4-2-bp.svg": bp,
        OUT / "fig5-1-wavelet-tree.svg": lambda: wavelet(False),
        OUT / "fig5-2-wavelet-matrix.svg": lambda: wavelet(True),
        OUT / "fig6-1-bwt-lf.svg": bwt,
        OUT / "fig6-2-backward-search.svg": backward,
        OUT / "fig8-1-budget.svg": budget,
    }))
