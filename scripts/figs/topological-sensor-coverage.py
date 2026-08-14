#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/topological-sensor-coverage/figs/*.svg を決定的に生成する。

3-1 の2枚だけをここで描く。ほかの図（fig1, fig2, fig5〜fig10）は画像生成で作った
PNG で、記録は scripts/figs/topological-sensor-coverage.md にある。

この2枚をコードに移した理由：どちらも「3枚の等半径円盤が2枚ずつ重なるが3枚共通
部分は持たない」という同一の配置を描く。この配置が成り立つ条件は

    d/2 < r < d/sqrt(3)      （d = 中心間距離、r = 検知半径）

という狭い区間で、しかも上端 d/sqrt(3) を超えた瞬間に中央の未被覆域が消える。
画像生成では3回続けてこの比を外し、3枚すべてに覆われた領域を「未被覆」と赤で
塗る、意味が正反対の図が出た。ここでは比を assert で突き合わせ、未被覆域の輪郭
（3本の円弧でできた曲線三角形）を円の交点から計算して描く。

配色の割り当て（この教材での意味づけ。全図で共通）
  青 #1f6fd0 : システムが持つ組合せ構造。通信辺、単体、nerve の面
  赤 #cf3b2d : どの検知円盤にも覆われていない領域、複体と現実の食い違い
  灰 #8d8d8d : 現実の物理。検知円盤の輪郭と塗り
形でも必ず区別する（未被覆＝白地に赤の斜線／3枚共通＝淡い青のべた塗り、
現実の穴＝実線／複体に隠れた穴＝破線）。
"""
import filecmp
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (  # noqa: E402
    SVG, INK, SUB, MAIN, WARN, MUTED, TINT_MAIN, TINT_MUTED,
)

OUT_DIR = (Path(__file__).resolve().parents[2]
           / "docs" / "books" / "topological-sensor-coverage" / "figs")

# 3-1 で共有する配置。中心間距離 d に対する検知半径の比。
#   R_NONE : d/2 < r < d/sqrt(3) → 2枚ずつ重なるが3枚共通部分は無い
#   R_TRIPLE : r > d/sqrt(3)     → 3枚共通部分ができる
# R_NONE は区間 (0.500, 0.5774) のほぼ中央に取る。下端に寄せると2枚の重なりが
# 見えなくなり、上端に寄せると中央の未被覆域が消えるため。
R_NONE = 0.53
R_TRIPLE = 0.62

HATCH_ID = "tsc-hatch-warn"
HATCH = (f'<pattern id="{HATCH_ID}" width="7" height="7" '
         f'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<rect width="7" height="7" fill="#ffffff"/>'
         f'<line x1="0" y1="0" x2="0" y2="7" stroke="{WARN}" stroke-width="1.5"/>'
         f'</pattern>')


# ---------------------------------------------------------------- 幾何
def triangle(cx, cy_apex, d):
    """1辺 d の正三角形の頂点を [1, 2, 3] の順で返す。

    本文 3-1 の配置に合わせ、1 を上、2 を右下、3 を左下に置く。この向きだと
    中央の未被覆域が本文の言う「▽」、3枚共通部分が ASCII アートの「▲」になる。
    逆向きに置くと、どちらも本文と上下が反転する。
    """
    h = d * math.sqrt(3) / 2
    return [(cx, cy_apex), (cx + d / 2, cy_apex + h), (cx - d / 2, cy_apex + h)]


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _inner_crossing(c1, c2, r, ref):
    """円 c1, c2 の2交点のうち ref に近いほう。"""
    d = _dist(c1, c2)
    half = d / 2
    h = math.sqrt(r * r - half * half)
    mid = ((c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2)
    ux, uy = -(c2[1] - c1[1]) / d, (c2[0] - c1[0]) / d
    cand = [(mid[0] + h * ux, mid[1] + h * uy), (mid[0] - h * ux, mid[1] - h * uy)]
    return min(cand, key=lambda p: _dist(p, ref))


def _crossings(c1, c2, r):
    """円 c1, c2 の2交点。"""
    d = _dist(c1, c2)
    half = d / 2
    h = math.sqrt(r * r - half * half)
    mid = ((c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2)
    ux, uy = -(c2[1] - c1[1]) / d, (c2[0] - c1[0]) / d
    return ((mid[0] + h * ux, mid[1] + h * uy), (mid[0] - h * ux, mid[1] - h * uy))


def lens_region(c1, c2, r):
    """2円の重なり（レンズ形）の輪郭点列。"""
    pa, pb = _crossings(c1, c2, r)
    pts = _arc(c1, r, pa, pb, _nearest_on_circle(c1, r, c2))
    pts += _arc(c2, r, pb, pa, _nearest_on_circle(c2, r, c1))
    return pts


def lens_tip(c1, c2, r, ref, out):
    """レンズの長い方の先端のうち、ref から遠いほう。out だけ外へ伸ばした点。"""
    pa, pb = _crossings(c1, c2, r)
    tip = max((pa, pb), key=lambda p: _dist(p, ref))
    ux, uy = (tip[0] - ref[0]) / _dist(tip, ref), (tip[1] - ref[1]) / _dist(tip, ref)
    return (tip[0] + ux * out, tip[1] + uy * out)


def _nearest_on_circle(c, r, ref):
    """円 c 上で ref に最も近い点。"""
    d = _dist(c, ref)
    return (c[0] + (ref[0] - c[0]) * r / d, c[1] + (ref[1] - c[1]) * r / d)


def _arc(c, r, p_from, p_to, through, n=40):
    """円 c 上を p_from から p_to まで、through を通る向きに回る点列。"""
    ang = lambda p: math.atan2(p[1] - c[1], p[0] - c[0])  # noqa: E731
    a0, a1, at = ang(p_from), ang(p_to), ang(through)
    two = 2 * math.pi
    ccw = (a1 - a0) % two
    span = ccw if (at - a0) % two < ccw else ccw - two
    return [(c[0] + r * math.cos(a0 + span * i / n),
             c[1] + r * math.sin(a0 + span * i / n)) for i in range(n + 1)]


def middle_region(centers, r):
    """3円の中央にできる領域の輪郭点列。

    r < d/sqrt(3) なら「どの円にも属さない領域」（辺が内側へ凹んだ曲線三角形）、
    r > d/sqrt(3) なら「3円すべてに属する領域」（辺が外側へ凸な曲線三角形）。
    どちらも同じ作図で出る。角は2円の交点のうち重心に近いほう、辺は各円のうち
    重心に最も近い側の弧。
    """
    c1, c2, c3 = centers
    g = centroid(centers)
    p12 = _inner_crossing(c1, c2, r, g)
    p23 = _inner_crossing(c2, c3, r, g)
    p31 = _inner_crossing(c3, c1, r, g)
    pts = []
    pts += _arc(c1, r, p12, p31, _nearest_on_circle(c1, r, g))
    pts += _arc(c3, r, p31, p23, _nearest_on_circle(c3, r, g))
    pts += _arc(c2, r, p23, p12, _nearest_on_circle(c2, r, g))
    return pts


def to_path(pts):
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"


def scaled(pts, src, dst, k):
    return [(dst[0] + (x - src[0]) * k, dst[1] + (y - src[1]) * k) for x, y in pts]


def check_config(centers, r, covered):
    """本文の主張と配置を突き合わせる。

    covered=False : どの円にも入らない中央の点が存在する（3-1 前半の▽）
    covered=True  : 中央が3円すべてに入る（円盤を広げたあと）
    """
    d = _dist(centers[0], centers[1])
    for a, b in ((0, 1), (1, 2), (2, 0)):
        assert abs(_dist(centers[a], centers[b]) - d) < 1e-6, "正三角形でない"
    assert r > d / 2, "2枚ずつが重ならない"
    g = centroid(centers)
    reach = min(_dist(g, c) for c in centers)
    if covered:
        assert r > d / math.sqrt(3), "3枚共通部分ができない"
        assert reach < r, "重心が円盤の外にある"
    else:
        assert r < d / math.sqrt(3), "3枚共通部分ができてしまう"
        assert reach > r, "重心が覆われてしまう"


LENS_FILL = "#e4e4e4"


def disks(s, centers, r, labels=None, label_pull=0.62):
    """検知円盤3枚。2枚ずつの重なりを一段濃い地色で塗って見えるようにする。"""
    g = centroid(centers)
    for c in centers:
        s.circle(c[0], c[1], r, fill=TINT_MUTED, stroke="none", sw=0)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        s.path(to_path(lens_region(centers[a], centers[b], r)),
               fill=LENS_FILL, stroke="none", sw=0)
    for c in centers:
        s.circle(c[0], c[1], r, fill="none", stroke=MUTED, sw=1.3)
    for c, name in zip(centers, labels or []):
        ux, uy = (c[0] - g[0]) / _dist(c, g), (c[1] - g[1]) / _dist(c, g)
        s.text(c[0] + ux * r * label_pull, c[1] + uy * r * label_pull + 4,
               name, size=13, fill=SUB, anchor="middle")


# ---------------------------------------------------------------- fig3
def fig3():
    """3-1 円盤を広げて3重交差ができると、nerve に面が1枚入る。

    上段が現実の検知円盤、下段が対応する nerve。左右で3つの中心位置は同一で、
    変えるのは半径だけ（左 0.53d、右 0.62d）。円盤は本文の配置に合わせて
    B1 を上、B2 を右下、B3 を左下に置く。中央の未被覆域は本文の言う「▽」、
    3枚共通部分は ASCII アートの「▲」の向きになる。

    グリッド（先に宣言し、この座標だけを使う）
      キャンバス 760x584
      上段 中心間距離 d=156、頂点 y=140、左の上頂点 x=180 / 右 x=580
           左 B1(180,140) B2(258,275.10) B3(102,275.10) 重心(180,230.07) r=82.68
           右 B1(580,140) B2(658,275.10) B3(502,275.10) 重心(580,230.07) r=96.72
      下段 1辺100の三角形、上頂点 y=440
           左 B1(180,440) B2(230,526.60) B3(130,526.60)
           右 B1(580,440) B2(630,526.60) B3(530,526.60)
      文字 26 見出し / 190・324 A・B・C / 392 中央注記 / 426・540 nerve 頂点 / 570 脚注
      色  灰＝検知円盤（2枚の重なりは一段濃く）/ 赤＝どの円盤にも入らない領域
          青＝nerve と3枚共通部分
    """
    s = SVG(760, 584,
            "3枚の円盤が2枚ずつしか重ならないとき nerve は輪だけになり、"
            "3枚が重なると nerve に面が1枚入る")
    s.defs.append(HATCH)
    d = 156.0
    r_no, r_yes = d * R_NONE, d * R_TRIPLE
    left = triangle(180, 140, d)
    right = triangle(580, 140, d)
    check_config(left, r_no, covered=False)
    check_config(right, r_yes, covered=True)
    gl = centroid(left)

    s.text(180, 26, "3重交差なし", size=15, weight="700", anchor="middle")
    s.text(580, 26, "3重交差あり", size=15, weight="700", anchor="middle")

    # 上段左：どの円盤にも入らない中央（▽）
    disks(s, left, r_no, ["B1", "B2", "B3"])
    s.path(to_path(middle_region(left, r_no)),
           fill=f"url(#{HATCH_ID})", stroke=WARN, sw=2.6)
    # 2枚ずつの重なり3か所。外側の先端のすぐ外に記号を置く
    for name, a, b in (("A", 0, 1), ("B", 1, 2), ("C", 2, 0)):
        x, y = lens_tip(left[a], left[b], r_no, gl, 22)
        s.text(x, y + 4, name, size=13, anchor="middle")
    s.text(180, 392, "中央は未被覆", size=13, fill=WARN, anchor="middle")

    # 上段右：3枚が重なる（▲）
    disks(s, right, r_yes, ["B1", "B2", "B3"])
    s.path(to_path(middle_region(right, r_yes)), fill=TINT_MAIN, stroke=MAIN, sw=2.6)
    s.text(580, 392, "3枚が重なる", size=13, fill=MAIN, anchor="middle")

    # 下段：nerve
    for cx, filled, caption in ((180, False, "nerve：面が入らない"),
                                (580, True, "nerve：面が入る")):
        n = triangle(cx, 440, 100)
        g = centroid(n)
        if filled:
            s.path(to_path(n), fill=TINT_MAIN, stroke="none", sw=0)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            s.line(n[a][0], n[a][1], n[b][0], n[b][1], stroke=MAIN, sw=3,
                   role="connector")
        for p, name in zip(n, ["B1", "B2", "B3"]):
            s.circle(p[0], p[1], 4.5, fill=INK, stroke="none", sw=0)
            ux, uy = (p[0] - g[0]) / _dist(p, g), (p[1] - g[1]) / _dist(p, g)
            s.text(p[0] + ux * 18, p[1] + uy * 18 + 4, name, size=12,
                   fill=SUB, anchor="middle")
        s.text(cx, 570, caption, size=13, fill=MAIN, anchor="middle")
    return s


# ---------------------------------------------------------------- fig4
def fig4():
    """3-1 通信は三角形、現実は穴。

    左は現実の検知円盤（fig3 の左上と同じ比 0.53d）、右は同じ3台から作った
    Rips 複体。右の破線は、左の未被覆域を三角形の縮尺へ写したもの。頂点の
    並びは fig3 と同じく 1 が上、2 が右下、3 が左下。

    グリッド（先に宣言し、この座標だけを使う）
      キャンバス 760x448
      左  中心間距離 d=180、上頂点 y=158、上頂点 x=225、r=95.40
          1(225,158) 2(315,313.88) 3(135,313.88) 重心(225,261.96)
      右  1辺130の三角形、上頂点 y=175、上頂点 x=630
          1(630,175) 2(695,287.58) 3(565,287.58) 重心(630,249.86)
          破線の縮尺 k = 130/180
      矢印 (432,262)->(500,262)
      文字 26 見出し / 120 通信注記 / 144・327 頂点番号 / 428 未被覆注記
           140 三角形注記 / 161・301 頂点番号 / 428 破線注記
      色  灰＝検知円盤 / 青＝通信辺と複体の面 / 赤＝未被覆域
    """
    s = SVG(760, 448,
            "3台は全ペアが通信できるのでRips複体は三角形を入れるが、"
            "現実の検知円盤は中央を覆っていない")
    s.defs.append(HATCH)
    d = 180.0
    r = d * R_NONE
    real = triangle(225, 158, d)
    check_config(real, r, covered=False)
    g = centroid(real)

    s.text(225, 26, "現実：検知円盤", size=15, weight="700", anchor="middle")
    s.text(630, 26, "Rips複体", size=15, weight="700", anchor="middle")

    # 左：検知円盤と、全ペアの通信辺
    disks(s, real, r)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        s.line(real[a][0], real[a][1], real[b][0], real[b][1], stroke=MAIN, sw=3,
               role="connector")
    hole = middle_region(real, r)
    s.path(to_path(hole), fill=f"url(#{HATCH_ID})", stroke=WARN, sw=2.6)
    for p, name in zip(real, ["1", "2", "3"]):
        s.circle(p[0], p[1], 5, fill=INK, stroke="none", sw=0)
        ux, uy = (p[0] - g[0]) / _dist(p, g), (p[1] - g[1]) / _dist(p, g)
        s.text(p[0] + ux * 18, p[1] + uy * 18 + 4, name, size=13, anchor="middle")
    s.text(225, 120, "全ペアが通信できる", size=12, fill=MAIN, anchor="middle")
    s.text(225, 428, "中央は未被覆", size=13, fill=WARN, anchor="middle")

    s.arrow(432, 262, 500, 262, stroke=MUTED, sw=3)

    # 右：Rips複体。面が入り、未被覆域は面の下に隠れる
    rips = triangle(630, 175, 130)
    gr = centroid(rips)
    s.path(to_path(rips), fill=TINT_MAIN, stroke="none", sw=0)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        s.line(rips[a][0], rips[a][1], rips[b][0], rips[b][1], stroke=MAIN, sw=3,
               role="connector")
    s.path(to_path(scaled(hole, g, gr, 130.0 / d)), stroke=WARN, sw=2.2, dash="6 4")
    for p, name in zip(rips, ["1", "2", "3"]):
        s.circle(p[0], p[1], 5, fill=INK, stroke="none", sw=0)
        ux, uy = (p[0] - gr[0]) / _dist(p, gr), (p[1] - gr[1]) / _dist(p, gr)
        s.text(p[0] + ux * 18, p[1] + uy * 18 + 4, name, size=13, anchor="middle")
    s.text(630, 140, "三角形が入る", size=12, fill=MAIN, anchor="middle")
    s.text(630, 428, "覆われていない場所", size=13, fill=WARN, anchor="middle")
    return s


FIGS = {
    "fig3-disks-and-nerve": fig3,
    "fig4-rips-triangle-vs-real-hole": fig4,
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
