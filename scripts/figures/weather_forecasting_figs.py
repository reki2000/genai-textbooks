#!/usr/bin/env python3
"""docs/books/weather-forecasting/figs/*.svg を生成する。

図は本文の「壁」に一対一で対応させ、教材を読まずに図だけ見ても
何が問題で何が解決なのかが分かる説明図にする。

    python3 scripts/figures/weather_forecasting_figs.py

出力先の SVG はソース扱い（docs/ 配下）でコミットする。
"""

from __future__ import annotations

import math
from functools import partial
from pathlib import Path

from svgkit import (  # noqa: F401  （教材ごとに使う色が違うためまとめて import する）
    AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, SURFACE, VIOLET, Svg,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "weather-forecasting" / "figs"
Svg = partial(Svg, out_dir=OUT_DIR)


# ---------------------------------------------------------------------------
# 図1　予測可能性の限界（第1幕）
# ---------------------------------------------------------------------------
def fig_predictability():
    s = Svg(760, 430, "図1　誤差は指数で育つ ── 予測可能性の2週間の壁",
            "倍加時間 2 日。初期誤差を 160 倍精密にしても、予報限界は 15 日から 30 日にしか延びない")
    L, R, T, B = 92, 706, 84, 336
    lo, hi = -5.0, 0.0   # log10(相対誤差)
    days_max = 32.0

    def X(d):
        return L + d / days_max * (R - L)

    def Y(e):
        return B - (math.log10(e) - lo) / (hi - lo) * (B - T)

    for k in range(int(lo), int(hi) + 1):
        y = Y(10.0 ** k)
        s.line(L, y, R, y, stroke=GRID, sw=1)
        sup = str(-k).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
        label = "1" if k == 0 else f"10⁻{sup}"
        s.text(L - 10, y + 4, label, size=11, fill=INK3, anchor="end")
    for d in range(0, 33, 5):
        s.line(X(d), T, X(d), B, stroke=GRID, sw=1, opacity=0.55)
        s.text(X(d), B + 18, f"{d}", size=11, fill=INK3, anchor="middle")
    s.line(L, T, L, B, stroke=INK3, sw=1)
    s.line(L, B, R, B, stroke=INK3, sw=1)
    s.text(X(days_max / 2), B + 38, "予報時間（日）", size=12, fill=INK2, anchor="middle")
    s.text(24, 76, "相対誤差", size=11, fill=INK2)

    # 飽和線
    s.line(L, Y(1.0), R, Y(1.0), stroke=RED, sw=1.6, dash="5 4")
    s.text(R - 4, Y(1.0) - 9, "飽和＝予報の意味を失う", size=11.5, fill=RED, anchor="end")

    def growth(e0, color, label, label_dy):
        d_end = math.log2(1.0 / e0) * 2.0
        s.path(f"M{X(0):.1f},{Y(e0):.1f} L{X(d_end):.1f},{Y(1.0):.1f}", stroke=color, sw=2.4)
        s.circle(X(0), Y(e0), 4.5, fill=color)
        s.circle(X(d_end), Y(1.0), 5, fill="#ffffff", stroke=color, sw=2.4)
        s.line(X(d_end), Y(1.0), X(d_end), B, stroke=color, sw=1.4, dash="4 4")
        s.text(X(d_end), B - 8, f"約{d_end:.0f}日", size=12.5, fill=color, anchor="middle", weight="700")
        s.text(X(0) + 10, Y(e0) + label_dy, label, size=11.5, fill=color, weight="700")
        return d_end

    growth(1 / 200, BLUE, "初期誤差 0.5%（＝1/200）", 22)
    growth(1 / 32768, ORANGE, "初期誤差 0.003%（＝1/32768）", 22)

    # 「160倍精密に」を示す縦の対比
    s.arrow(L + 14, Y(1 / 200) + 6, L + 14, Y(1 / 32768) - 6, color=INK2, sw=1.4)
    s.lines_of_text(L + 22, (Y(1 / 200) + Y(1 / 32768)) / 2 - 6,
                    ["初期観測を", "160倍精密に"], size=10.5, fill=INK2, lh=14)

    s.lines_of_text(24, 396, [
        "誤差は倍加時間ごとに 2 倍という指数関数で育つため、予報期間を線形に延ばすには初期観測を指数的に良くするしかない。",
        "だからどれだけ測定技術を磨いても、限界は 2 週間前後に貼りついたままになる（ローレンツの予測可能性の限界）。",
    ], size=11.5, lh=17)
    s.save("fig1-predictability-limit.svg")


# ---------------------------------------------------------------------------
# 図2　リチャードソンの145 hPa（第2幕）
# ---------------------------------------------------------------------------
def fig_richardson():
    s = Svg(760, 400, "図2　リチャードソンの145 hPa ── 初期不均衡が生む偽の巨大振動",
            "方程式も初期値も正しい。風と気圧がわずかに釣り合っていないだけで、重力波ノイズが本物の信号を覆い隠す")
    L, R, T, B = 92, 470, 92, 300
    ymax = 170.0

    def X(h):
        return L + h / 6.0 * (R - L)

    def Y(p):
        return (T + B) / 2 - p / ymax * (B - T) / 2

    for p in (-150, -75, 0, 75, 150):
        s.line(L, Y(p), R, Y(p), stroke=GRID, sw=1)
        s.text(L - 8, Y(p) + 4, f"{p:+d}" if p else "0", size=10.5, fill=INK3, anchor="end")
    s.line(L, T, L, B, stroke=INK3, sw=1)
    for h in range(0, 7, 2):
        s.text(X(h), B + 18, f"{h}h", size=10.5, fill=INK3, anchor="middle")
    s.text(24, 84, "気圧変化 (hPa)", size=11, fill=INK2)

    pts = []
    for i in range(241):
        h = 6.0 * i / 240
        amp = 145 * (h / 6.0) ** 1.4
        pts.append((X(h), Y(amp * math.sin(2 * math.pi * h / 0.9) - 0.17 * h)))
    s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), stroke=ORANGE, sw=2)
    s.path(f"M{X(0):.1f},{Y(0):.1f} L{X(6):.1f},{Y(-1):.1f}", stroke=BLUE, sw=2.4)

    peak = min(pts, key=lambda p: p[1])
    s.circle(peak[0], peak[1], 5, fill="#ffffff", stroke=ORANGE, sw=2.2)
    s.text(peak[0] - 12, peak[1] - 12, "145 hPa", size=13, fill=ORANGE, anchor="end", weight="700")
    s.text(peak[0] - 12, peak[1] + 4, "＝計算された答え", size=11, fill=ORANGE, anchor="end")
    s.text(L + 14, T + 18, "本物の信号（ほぼ 0 に見える）", size=11.5, fill=BLUE, weight="700")
    s.arrow(L + 40, T + 26, L + 30, Y(0) - 6, color=BLUE, sw=1.2)

    # 拡大パネル
    px, py, pw, ph = 540, 92, 176, 208
    s.rect(px, py, pw, ph, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(px + pw / 2, py - 10, "拡大：縦軸 ±2 hPa", size=11.5, fill=INK2, anchor="middle")
    for p2, lab in ((2, "+2"), (0, "0"), (-2, "-2")):
        yy = py + ph / 2 - p2 / 2.4 * ph / 2
        s.line(px + 8, yy, px + pw - 8, yy, stroke=GRID, sw=1)
        s.text(px + 4, yy + 4, lab, size=10, fill=INK3, anchor="end")
    s.path(
        f"M{px + 14:.1f},{py + ph / 2:.1f} L{px + pw - 14:.1f},{py + ph / 2 + 1.0 / 2.4 * ph / 2:.1f}",
        stroke=BLUE, sw=2.4)
    s.lines_of_text(px + 14, py + ph / 2 + 66, ["実際の6時間の気圧変化", "は 1 hPa にも満たない"],
                    size=10.5, fill=BLUE, lh=14, weight="700")
    s.arrow(px - 14, py + ph / 2, px + 4, py + ph / 2, color=INK3, sw=1.2)
    s.line(X(6), Y(0), px - 30, py + ph / 2, stroke=INK3, sw=1, dash="3 3")

    s.lines_of_text(24, 348, [
        "初期データのわずかな不均衡が巨大な重力波（気象的にはノイズ）を励起し、本物のゆっくりした変化を桁違いに上回る。",
        "処方箋は方程式ではなく初期化（initialization）── ENIAC の成功例は、重力波を含まない方程式を選ぶことで回避した。",
    ], size=11.5, lh=17)
    s.save("fig2-richardson.svg")


# ---------------------------------------------------------------------------
# 図3　解像度2倍のコスト（第2幕・第6幕）
# ---------------------------------------------------------------------------
def fig_cost():
    s = Svg(760, 386, "図3　解像度を2倍にしたときのコスト ── 物理16倍、ML推論8倍",
            "格子点は 3 次元で 2³＝8 倍。物理モデルにはさらに CFL 条件による時間刻み半減（×2）が上乗せされる")
    base_y = 286
    top_y = 92
    scale = (base_y - top_y) / 16.0

    def bar(x, w, value, color, label, sub, seg=None):
        h = value * scale
        s.rect(x, base_y - h, w, h, fill=color, rx=4, opacity=0.16)
        s.rect(x, base_y - h, w, h, fill="none", stroke=color, rx=4, sw=1.8)
        if seg:
            hs = seg * scale
            s.rect(x, base_y - h, w, hs, fill=color, rx=4, opacity=0.5)
            s.line(x, base_y - h + hs, x + w, base_y - h + hs, stroke=SURFACE, sw=2)
        s.text(x + w / 2, base_y - h - 14, f"×{value:g}", size=17, fill=color,
               anchor="middle", weight="700")
        s.text(x + w / 2, base_y + 22, label, size=12.5, fill=INK, anchor="middle", weight="700")
        s.text(x + w / 2, base_y + 40, sub, size=11, fill=INK2, anchor="middle")

    s.line(96, base_y, 700, base_y, stroke=INK3, sw=1)
    bar(120, 120, 1, INK3, "変更前", "Δx のまま")
    bar(320, 120, 8, BLUE, "ML 予報器の推論", "格子点 8 倍のみ")
    bar(520, 120, 16, ORANGE, "物理モデル (NWP)", "8 倍 × 時間ステップ 2 倍", seg=8)

    s.line(660, base_y - 16 * scale, 690, base_y - 16 * scale, stroke=ORANGE, sw=1.2)
    s.line(660, base_y - 8 * scale, 690, base_y - 8 * scale, stroke=ORANGE, sw=1.2)
    s.arrow(688, base_y - 8 * scale - 2, 688, base_y - 16 * scale + 2, color=ORANGE, sw=1.3)
    s.text(694, base_y - 12 * scale, "CFL の罰", size=11, fill=ORANGE, weight="700")

    s.lines_of_text(24, 364, [
        "6 時間先を一度に写す ML 予報器には「細かくしたら時間刻みも細かく」という罰が付かない。速さの差はここから来る。",
    ], size=11.5, lh=17)
    s.save("fig3-cost-scaling.svg")


# ---------------------------------------------------------------------------
# 図4　緯度経度格子 vs 正20面体メッシュ（4-1）
# ---------------------------------------------------------------------------
def _ortho(lat, lon, lat0=22.0, lon0=10.0):
    """正射図法。可視なら (x, y)、裏側なら None。"""
    p, l = math.radians(lat), math.radians(lon)
    p0, l0 = math.radians(lat0), math.radians(lon0)
    cosc = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0)
    if cosc < 0:
        return None
    x = math.cos(p) * math.sin(l - l0)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0)
    return x, y


def _icosphere(depth=2):
    t = (1 + 5 ** 0.5) / 2
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
             (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [tuple(c / math.sqrt(sum(v * v for v in p)) for c in p) for p in verts]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
             (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    cache: dict[tuple[int, int], int] = {}

    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            m = tuple((verts[a][i] + verts[b][i]) / 2 for i in range(3))
            n = math.sqrt(sum(c * c for c in m))
            verts.append(tuple(c / n for c in m))
            cache[key] = len(verts) - 1
        return cache[key]

    for _ in range(depth):
        nf = []
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nf
    edges = set()
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            edges.add((min(e), max(e)))
    return verts, sorted(edges)


def fig_sphere():
    s = Svg(760, 430, "図4　舞台は球面 ── 緯度経度格子の歪みと、正20面体メッシュ",
            "同じ地球を 2 通りに区切る。左は極で升目が潰れ、経度に切れ目がある。右はどこでもほぼ同じ大きさの三角形")
    R = 108
    cx1, cy1, cx2, cy2 = 208, 200, 552, 200

    for cx, cy in ((cx1, cy1), (cx2, cy2)):
        s.circle(cx, cy, R, fill="#ffffff", stroke=CARD_EDGE, sw=1.5)

    # 左：緯度経度格子
    for lat in range(-75, 76, 15):
        pts = []
        for k in range(361):
            q = _ortho(lat, k)
            if q:
                pts.append((cx1 + q[0] * R, cy1 - q[1] * R))
            elif pts:
                break
        if len(pts) > 1:
            s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), stroke=BLUE, sw=1, opacity=0.75)
    for lon in range(0, 360, 15):
        pts = []
        for k in range(-90, 91, 2):
            q = _ortho(k, lon)
            pts.append((cx1 + q[0] * R, cy1 - q[1] * R) if q else None)
        run: list[tuple[float, float]] = []
        for p in pts + [None]:
            if p:
                run.append(p)
            elif run:
                if len(run) > 1:
                    s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in run),
                           stroke=BLUE, sw=1, opacity=0.75)
                run = []
    # 赤道と緯度60°の升目を強調
    for lat0, lat1, color, tag in ((0, 15, ORANGE, "赤道 ≈111 km"), (60, 75, RED, "緯度60° ≈56 km")):
        pts = []
        for lo_, la_ in [(0, lat0), (15, lat0), (15, lat1), (0, lat1)]:
            q = _ortho(la_, lo_)
            if q:
                pts.append((cx1 + q[0] * R, cy1 - q[1] * R))
        if len(pts) == 4:
            s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z",
                   stroke=color, fill=color, sw=2, opacity=0.9)
    q = _ortho(88, 10)
    s.circle(cx1 + q[0] * R, cy1 - q[1] * R, 7, fill="none", stroke=RED, sw=2)
    s.text(cx1 + q[0] * R + 12, cy1 - q[1] * R - 4, "極：升目が0に潰れる", size=11, fill=RED, weight="700")
    seam = []
    for k in range(-90, 91, 2):
        q = _ortho(k, 0)
        if q:
            seam.append((cx1 + q[0] * R, cy1 - q[1] * R))
    s.path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seam), stroke=VIOLET, sw=2.2, dash="5 4")
    s.text(cx1 - 4, cy1 + 128, "経度0°＝360°（紫）。平らな画像では左端と右端に分かれてしまう",
           size=11, fill=INK2, anchor="middle")
    s.text(cx1 + 30, cy1 + 44, "≈111 km", size=10.5, fill=ORANGE, weight="700")
    s.text(cx1 - 30, cy1 - 58, "≈56 km", size=10.5, fill=RED, weight="700", anchor="end")

    # 右：正20面体メッシュ
    verts, edges = _icosphere(2)
    for a, b in edges:
        pa, pb = verts[a], verts[b]
        la = math.degrees(math.asin(pa[2])), math.degrees(math.atan2(pa[1], pa[0]))
        lb = math.degrees(math.asin(pb[2])), math.degrees(math.atan2(pb[1], pb[0]))
        qa, qb = _ortho(*la), _ortho(*lb)
        if qa and qb:
            s.line(cx2 + qa[0] * R, cy2 - qa[1] * R, cx2 + qb[0] * R, cy2 - qb[1] * R,
                   stroke=AQUA, sw=1, opacity=0.95)
    s.text(cx2, cy2 + 128, "特別な「極の一点」も切れ目もない", size=11, fill=INK2, anchor="middle")

    s.text(cx1, 86, "緯度経度格子 ＋ CNN", size=13.5, fill=INK, anchor="middle", weight="700")
    s.text(cx2, 86, "正20面体メッシュ ＋ GNN", size=13.5, fill=INK, anchor="middle", weight="700")

    s.lines_of_text(24, 366, [
        "左：画像上では同じ 3×3 カーネルでも、覆う地面の広さが赤道と高緯度でまるで違う。CNN は格子の歪みを物理の歪みと",
        "　　取り違える。右：正20面体を細分して球面に投影すると、ほぼ一様な三角形になる。不規則な点の上での近傍のやり",
        "　　とりは、グラフのメッセージパッシング（GNN）として書ける。",
    ], size=11.5, lh=17)
    s.save("fig4-sphere-grid.svg")


# ---------------------------------------------------------------------------
# 図5　多重メッシュ（4-2）
# ---------------------------------------------------------------------------
def fig_multimesh():
    s = Svg(760, 352, "図5　多重メッシュ ── 遠距離をホップ数で律速させない",
            "隣接間隔 200 km のメッシュだけでは 3000 km 先の影響を届けるのに 15 ホップ（＝深いネット）が要る")
    n = 15
    x0, x1 = 96, 664
    step = (x1 - x0) / n

    def chain(y, label, color):
        s.text(24, y - 44, label, size=13, fill=INK, weight="700")
        for i in range(n + 1):
            x = x0 + i * step
            s.circle(x, y, 4.5, fill="#ffffff", stroke=INK3, sw=1.4)
        s.circle(x0, y, 7, fill=BLUE)
        s.circle(x1, y, 7, fill=ORANGE)
        s.text(x0, y + 26, "ここ", size=11, fill=BLUE, anchor="middle", weight="700")
        s.text(x1, y + 26, "3000 km 上流", size=11, fill=ORANGE, anchor="middle", weight="700")
        return step

    y1, y2 = 128, 254
    chain(y1, "細メッシュのみ（1辺 200 km）", BLUE)
    for i in range(n):
        xa = x0 + i * step
        s.arrow_path(f"M{xa + 6:.1f},{y1 - 6:.1f} Q{xa + step / 2:.1f},{y1 - 24:.1f} "
                     f"{xa + step - 7:.1f},{y1 - 6:.1f}", color=INK3, sw=1.2)
    s.text(x1 + 12, y1 - 20, "15 ホップ", size=12.5, fill=INK2, weight="700", anchor="end")
    s.text((x0 + x1) / 2, y1 - 34, "1 回のメッセージパッシングで 200 km しか進めない",
           size=11.5, fill=INK2, anchor="middle")

    chain(y2, "多重メッシュ（粗い辺を重ねる）", AQUA)
    for i in range(n):
        xa = x0 + i * step
        s.path(f"M{xa + 6:.1f},{y2 - 5:.1f} Q{xa + step / 2:.1f},{y2 - 16:.1f} "
               f"{xa + step - 6:.1f},{y2 - 5:.1f}", stroke=GRID, sw=1.2)
    mid = (x0 + x1) / 2
    s.arrow_path(f"M{x1 - 6:.1f},{y2 + 8:.1f} Q{(mid + x1) / 2:.1f},{y2 + 62:.1f} {mid + 6:.1f},{y2 + 8:.1f}",
                 color=AQUA, sw=2.2)
    s.arrow_path(f"M{mid - 6:.1f},{y2 + 8:.1f} Q{(x0 + mid) / 2:.1f},{y2 + 62:.1f} {x0 + 6:.1f},{y2 + 8:.1f}",
                 color=AQUA, sw=2.2)
    s.circle(mid, y2, 6, fill=AQUA)
    s.text(mid, y2 - 30, "粗い段の辺なら 2 ホップ", size=12.5, fill=AQUA, anchor="middle", weight="700")

    s.lines_of_text(24, 334, [
        "GraphCast は正20面体を 7 段階に細分し、粗い段から細かい段までの辺をすべて重ねて 1 つのグラフにする。",
    ], size=11.5, lh=17)
    s.save("fig5-multimesh.svg")


# ---------------------------------------------------------------------------
# 図6　MSEの罠（4-4）
# ---------------------------------------------------------------------------
def fig_mse_trap():
    s = Svg(760, 426, "図6　MSE の罠 ── 平均は「起こり得ない未来」になる",
            "前線が来れば12℃、来なければ22℃。MSE を最小にする単一予報は、確率ゼロの17℃")
    # 左：1地点の分布
    L, R, B, T = 76, 340, 288, 108
    tmin, tmax = 8.0, 26.0

    def X(t):
        return L + (t - tmin) / (tmax - tmin) * (R - L)

    s.line(L, B, R, B, stroke=INK3, sw=1)
    for t, color in ((12, BLUE), (22, ORANGE)):
        h = 150
        s.rect(X(t) - 17, B - h, 34, h, fill=color, rx=4, opacity=0.2)
        s.rect(X(t) - 17, B - h, 34, h, fill="none", stroke=color, rx=4, sw=1.8)
        s.text(X(t), B - h - 12, "50%", size=12.5, fill=color, anchor="middle", weight="700")
    s.line(X(17), B - 190, X(17), B, stroke=RED, sw=2, dash="6 4")
    s.text(X(17), B - 200, "MSE 最適解", size=12, fill=RED, anchor="middle", weight="700")
    s.text(X(17), B - 60, "確率 0", size=11.5, fill=RED, anchor="middle", weight="700")
    for t, color, lab in ((12, BLUE, "前線通過"), (17, RED, "起こり得ない"), (22, ORANGE, "前線来ず")):
        s.text(X(t), B + 19, f"{t}℃", size=11.5, fill=color, anchor="middle", weight="700")
        s.text(X(t), B + 36, lab, size=10.5, fill=color, anchor="middle")
    s.text(L - 44, B + 4, "確率", size=11, fill=INK2)
    s.text(24, 90, "① 1 地点の気温", size=13, fill=INK, weight="700")

    # 右：場全体
    s.text(400, 90, "② 場全体でやると ── 低気圧が二重にボケる", size=13, fill=INK, weight="700")

    def minimap(x, y, w, h, lows, title, color, ghost=False):
        s.rect(x, y, w, h, fill="#ffffff", stroke=CARD_EDGE, rx=6)
        for lx, depth in lows:
            for k, rr in enumerate((30, 21, 12)):
                s.circle(x + lx * w, y + h / 2, rr * (0.6 + 0.4 * depth),
                         fill="none", stroke=color, sw=1.4, opacity=0.35 + 0.2 * k,
                         dash="3 3" if ghost else None)
            s.text(x + lx * w, y + h / 2 + 5, "L", size=13 if depth > 0.7 else 11,
                   fill=color, anchor="middle", weight="700",
                   opacity=1.0 if depth > 0.7 else 0.55)
        s.text(x + w / 2, y + h + 17, title, size=11, fill=INK2, anchor="middle")

    mw, mh, my = 104, 96, 128
    minimap(400, my, mw, mh, [(0.34, 1.0)], "未来 A（50%）", BLUE)
    minimap(516, my, mw, mh, [(0.66, 1.0)], "未来 B（50%）", ORANGE)
    minimap(632, my, mw, mh, [(0.34, 0.5), (0.66, 0.5)], "MSE 最適解", RED, ghost=True)
    s.arrow(504, my + mh / 2, 512, my + mh / 2, color=INK3, sw=1.2)
    s.arrow(620, my + mh / 2, 628, my + mh / 2, color=INK3, sw=1.2)
    s.text(684, my + mh + 34, "半分の深さの低気圧が2つ", size=11, fill=RED, anchor="middle", weight="700")
    s.text(684, my + mh + 50, "＝実在しない場", size=11, fill=RED, anchor="middle", weight="700")

    s.lines_of_text(24, 362, [
        "MSE を最小化する予報は「あり得る未来たちの条件付き平均」。未来が多峰なら、平均はどの山にも当たらない谷底になる。",
        "鋭い前線を少しズレた位置に出すと有る所と無い所で二度罰せられる（double penalty）ので、モデルはぼかして両張りする。",
        "欲しいのは平均という 1 点ではなく、未来の分布そのもの ── これが「予報は決定論的な単一予報であってはいけない」理由。",
    ], size=11.5, lh=17)
    s.save("fig6-mse-trap.svg")


# ---------------------------------------------------------------------------
# 図7　ランクヒストグラム（4-5）
# ---------------------------------------------------------------------------
def fig_rank_histogram():
    s = Svg(760, 420, "図7　ランクヒストグラム ── アンサンブルが較正されているかの判定装置",
            "観測値が「小さい順に並べたアンサンブル」の何位に落ちたかを多数事例で集計する。理想は平ら")
    nb = 17
    base = 288
    top = 106

    def panel(x0, width, heights, color, title, note, uni_label=False):
        s.text(x0 + width / 2, 92, title, size=13, fill=INK, anchor="middle", weight="700")
        bw = width / nb
        hmax = max(heights)
        for i, hv in enumerate(heights):
            h = hv / hmax * (base - top) * 0.86
            s.rect(x0 + i * bw + 1.5, base - h, bw - 3, h, fill=color, rx=3, opacity=0.22)
            s.rect(x0 + i * bw + 1.5, base - h, bw - 3, h, fill="none", stroke=color, rx=3, sw=1.5)
        uni = sum(heights) / nb / hmax * (base - top) * 0.86
        s.line(x0, base - uni, x0 + width, base - uni, stroke=INK3, sw=1.4, dash="5 4")
        if uni_label:
            s.text(x0 + width / 2, base - uni - 8, "一様水準（理想）", size=10.5, fill=INK3, anchor="middle")
        s.line(x0, base, x0 + width, base, stroke=INK3, sw=1)
        s.text(x0 + width / 2, base + 19, "観測の順位（低 → 高）", size=11, fill=INK3, anchor="middle")
        s.lines_of_text(x0, base + 48, note, size=11.5, fill=color, lh=16, weight="700")

    u = [max(0.18, 1.55 * ((i - (nb - 1) / 2) / ((nb - 1) / 2)) ** 2 + 0.2) for i in range(nb)]
    flat = [0.92, 1.04, 0.97, 1.06, 0.99, 0.94, 1.05, 1.0, 0.96, 1.03, 0.98, 1.06, 0.95, 1.01, 0.99, 1.04, 0.97]
    panel(76, 300, u, ORANGE, "初期値を摂動しただけのアンサンブル",
          ["U 字＝過小分散（underdispersive）。束が細すぎて、", "観測が両端の外へこぼれる ── 自信過剰の印。"],
          uni_label=True)
    panel(432, 300, flat, AQUA, "分布そのものを学んでサンプルする",
          ["平ら＝較正済み（calibrated）。spread と error が", "釣り合い、五分五分を五分五分と言える。"])

    s.lines_of_text(24, 398, [
        "第1幕の「晴れ22℃か、前線通過で12℃か、五分五分」を、細い束で「ほぼ22℃です」と言い張るのが左。GenCast は右に近い。",
    ], size=11.5, lh=17)
    s.save("fig7-rank-histogram.svg")


# ---------------------------------------------------------------------------
# 図8　GraphCast / GenCast の全体像（第4幕まとめ・第5幕）
# ---------------------------------------------------------------------------
def fig_pipeline():
    s = Svg(760, 424, "図8　同じ器、違う損失 ── GraphCast と GenCast",
            "アーキテクチャはどちらも球面多重メッシュ GNN。決定論か確率かを分けたのは「何を最小化するか」")
    y = 118
    bh = 66
    boxes = [
        (44, 118, "状態 x(t)", "0.25°格子・2時刻"),
        (186, 108, "エンコーダ", "格子 → 球面メッシュ"),
        (318, 132, "プロセッサ", "多重メッシュ GNN"),
        (474, 108, "デコーダ", "メッシュ → 格子"),
        (606, 112, "x(t+6h)", "6時間後の場"),
    ]
    for x, w, lab, sub in boxes:
        s.box(x, y, w, bh, lab, sub, color=BLUE)
    for i in range(len(boxes) - 1):
        x, w, *_ = boxes[i]
        s.arrow(x + w + 4, y + bh / 2, boxes[i + 1][0] - 4, y + bh / 2, color=INK3, sw=1.6)
    s.text(24, 96, "共通の器（球面多重メッシュ GNN）", size=12, fill=BLUE, weight="700")

    # 自己回帰
    s.arrow_path(f"M{606 + 56:.1f},{y + bh + 6:.1f} Q{380:.1f},{y + bh + 74:.1f} {44 + 59:.1f},{y + bh + 6:.1f}",
                 color=INK2, sw=1.6)
    s.text(380, y + bh + 82, "自己回帰 ×40 ステップ ＝ 10 日先（多ステップ・ロールアウト訓練で安定化）",
           size=11.5, fill=INK2, anchor="middle", weight="700")

    # GenCast の拡散分岐
    dy = 322
    s.rect(24, dy - 22, 712, 96, fill="#ffffff", stroke=ORANGE, rx=8, sw=1.4, dash="5 4")
    s.text(38, dy - 4, "GenCast：出力を拡散サンプリングにする", size=12.5, fill=ORANGE, weight="700")
    stages = [(48, "砂嵐"), (168, "ほぼ砂嵐"), (288, "大気らしく"), (408, "鋭い場")]
    for i, (x, lab) in enumerate(stages):
        s.rect(x, dy + 6, 96, 40, fill=ORANGE, rx=6, opacity=0.10 + 0.06 * i)
        s.rect(x, dy + 6, 96, 40, fill="none", stroke=ORANGE, rx=6, sw=1.4)
        s.text(x + 48, dy + 31, lab, size=12, fill=INK, anchor="middle", weight="700")
        if i < len(stages) - 1:
            s.arrow(x + 100, dy + 26, x + 116, dy + 26, color=ORANGE, sw=1.5)
    s.text(276, dy + 66, "K 回のノイズ除去（各段で上のプロセッサを x(t) 条件つきで評価）",
           size=11, fill=ORANGE, anchor="middle")
    s.text(528, dy + 20, "毎回ちがう砂嵐から出発 →", size=11.5, fill=ORANGE, weight="700")
    s.text(528, dy + 40, "独立で鋭い 50 本のアンサンブル", size=11.5, fill=ORANGE, weight="700")

    s.text(24, 294, "GraphCast：この出力を MSE で訓練 → 条件付き平均 → 単一決定論予報（やや過平滑）",
           size=12, fill=BLUE, weight="700")
    s.save("fig8-pipeline.svg")


def main():
    fig_predictability()
    fig_richardson()
    fig_cost()
    fig_sphere()
    fig_multimesh()
    fig_mse_trap()
    fig_rank_histogram()
    fig_pipeline()


if __name__ == "__main__":
    main()
