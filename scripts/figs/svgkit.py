# -*- coding: utf-8 -*-
"""教材図版の SVG 組み立てヘルパ。

教材ごとの図は `scripts/figs/{ID}.py` に置き、`build()` へ図の関数を渡して
`docs/books/{ID}/figs/*.svg` へ書き出す。作図の規約は `.claude/skills/zuhan/` が正本。

    s = SVG(560, 320, "図が示す結論を一文で")
    s.rect(...); s.text(...); s.note(x, y, ["結論の注記"])
    return s

書き出す SVG は viewBox だけを持つ（width/height を付けると docsify の
max-width:100% と噛み合わず縦横比が崩れる）。地色は白で固定する。
SVG1.1 の範囲だけを使う（検査用レンダラが SVG2 を解釈しないため）。
"""

import sys
from pathlib import Path

FONT = "Noto Sans CJK JP, Hiragino Sans, Yu Gothic, sans-serif"

# 役割の色。意味の割り当ては教材ごとに scripts/figs/{ID}.py の docstring で宣言する。
MAIN = "#1f6fd0"    # 主役
FOCUS = "#e07b1f"   # いま注目している箇所（1図に1か所）
WARN = "#cf3b2d"    # 破綻・失敗・注意
MUTED = "#8d8d8d"   # 背景・目盛・補助
INK = "#1c1c1c"
SUB = "#6b6b6b"
TINT = {MAIN: "#e6eefb", FOCUS: "#f6e6b8", WARN: "#fbeae8", MUTED: "#f2f2f2"}


def _f(v):
    return f"{round(v, 1):g}"


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _smooth(pts, closed):
    """点列を通る Catmull-Rom 曲線を3次ベジェの path にする。"""
    n = len(pts)
    at = (lambda i: pts[i % n]) if closed else (lambda i: pts[max(0, min(n - 1, i))])
    d = [f"M {_f(pts[0][0])} {_f(pts[0][1])}"]
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append("C " + " ".join(_f(v) for v in (*c1, *c2, *p2)))
    return " ".join(d) + (" Z" if closed else "")


class SVG:
    def __init__(self, w, h, title):
        """title は図が示す結論を一文で書く（スクリーンリーダが読む）。"""
        self.w, self.h, self.title = w, h, title
        self.defs, self.parts = {}, []

    def _add(self, tag, attrs, body=None):
        a = " ".join(f'{k.rstrip("_").replace("_", "-")}="{v}"'
                     for k, v in attrs.items() if v is not None)
        self.parts.append(f"<{tag} {a}/>" if body is None else f"<{tag} {a}>{body}</{tag}>")

    def _marker(self, color):
        key = "a" + color.lstrip("#")
        self.defs[key] = (
            f'<marker id="{key}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" '
            f'markerHeight="10" markerUnits="userSpaceOnUse" orient="auto">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
        return f"url(#{key})"

    # ---- 基本形 ----
    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None):
        self._add("rect", dict(x=_f(x), y=_f(y), width=_f(w), height=_f(h), rx=rx or None,
                               fill=fill, stroke=stroke, stroke_width=sw,
                               stroke_dasharray=dash))

    def circle(self, cx, cy, r, fill="none", stroke=INK, sw=1.2, dash=None):
        self._add("circle", dict(cx=_f(cx), cy=_f(cy), r=_f(r), fill=fill, stroke=stroke,
                                 stroke_width=sw, stroke_dasharray=dash))

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.2, dash=None, arrow=False):
        """arrow=True で終点に矢じりを付ける。矢印は移動・方向・変化にだけ使う。"""
        self._add("line", dict(x1=_f(x1), y1=_f(y1), x2=_f(x2), y2=_f(y2), stroke=stroke,
                               stroke_width=sw, stroke_dasharray=dash,
                               stroke_linecap="round",
                               marker_end=self._marker(stroke) if arrow else None))

    def arrow(self, x1, y1, x2, y2, stroke=INK, sw=2, dash=None):
        self.line(x1, y1, x2, y2, stroke, sw, dash, arrow=True)

    def poly(self, pts, stroke=INK, sw=1.6, fill="none", closed=False, smooth=False,
             dash=None, arrow=False):
        """点列を結ぶ。smooth=True で点を通る滑らかな曲線（輪郭・膜・流路）にする。"""
        if smooth:
            d = _smooth(pts, closed)
        else:
            d = "M " + " L ".join(f"{_f(x)} {_f(y)}" for x, y in pts) + (" Z" if closed else "")
        self._add("path", dict(d=d, fill=fill, stroke=stroke, stroke_width=sw,
                               stroke_dasharray=dash, stroke_linejoin="round",
                               stroke_linecap="round",
                               marker_end=self._marker(stroke) if arrow else None))

    def text(self, x, y, s, size=15, fill=INK, anchor="start", bold=False, halo=False):
        """s にリストを渡すと複数行。halo=True で地色の縁取りを下に敷く（線の上の文字用）。"""
        rows = [s] if isinstance(s, str) else list(s)
        for i, row in enumerate(rows):
            yy = y + i * round(size * 1.4)
            base = dict(x=_f(x), y=_f(yy), font_family=FONT, font_size=size,
                        text_anchor=anchor, font_weight="700" if bold else None)
            if halo:
                self._add("text", dict(base, fill="#ffffff", stroke="#ffffff",
                                       stroke_width=4, stroke_linejoin="round"), _esc(row))
            self._add("text", dict(base, fill=fill), _esc(row))

    # ---- 読ませるための部品 ----
    def note(self, x, y, rows, color=FOCUS, size=16):
        """結論の注記。答えが見える場所の隣に1個だけ置く。左の色棒で本文ラベルと区別する。"""
        rows = [rows] if isinstance(rows, str) else rows
        lh = round(size * 1.4)
        self.rect(x, y - size, 4, lh * (len(rows) - 1) + size * 1.3, fill=color, stroke="none")
        self.text(x + 12, y, rows, size=size, bold=True)

    def badge(self, cx, cy, n, color=FOCUS):
        """読み順の番号。1図に5個まで。"""
        self.circle(cx, cy, 13, fill=color, stroke="#ffffff", sw=2)
        self.text(cx, cy + 5.5, str(n), size=15, fill="#ffffff", anchor="middle", bold=True)

    def zoom(self, src, dst, color=MUTED):
        """全体＋拡大。src=(x,y,w,h) の破線枠と dst の枠を案内線2本で結ぶ。中身は呼び出し側が描く。"""
        (sx, sy, sw, sh), (dx, dy, dw, dh) = src, dst
        self.rect(sx, sy, sw, sh, stroke=color, dash="4 3")
        self.rect(dx, dy, dw, dh, fill="#ffffff", stroke=color)
        ddx, ddy = dx + dw / 2 - sx - sw / 2, dy + dh / 2 - sy - sh / 2
        if abs(ddx) >= abs(ddy):   # 横へ出す：向き合う縦の辺どうしを結ぶ
            ax, bx = (sx + sw, dx) if ddx > 0 else (sx, dx + dw)
            pairs = [((ax, sy), (bx, dy)), ((ax, sy + sh), (bx, dy + dh))]
        else:                      # 縦へ出す：向き合う横の辺どうしを結ぶ
            ay, by = (sy + sh, dy) if ddy > 0 else (sy, dy + dh)
            pairs = [((sx, ay), (dx, by)), ((sx + sw, ay), (dx + dw, by))]
        for (x1, y1), (x2, y2) in pairs:
            self.line(x1, y1, x2, y2, stroke=color, dash="4 3")

    def hatch(self, color=MUTED):
        """斜線の塗り。fill に渡す。色に頼らず領域を区別する。"""
        key = "h" + color.lstrip("#")
        self.defs[key] = (
            f'<pattern id="{key}" width="7" height="7" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" '
            f'stroke="{color}" stroke-width="1.2"/></pattern>')
        return f"url(#{key})"

    def svg(self):
        defs = "<defs>" + "".join(self.defs[k] for k in sorted(self.defs)) + "</defs>" \
            if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'role="img" aria-labelledby="title"><title id="title">{_esc(self.title)}'
                f'</title>{defs}<rect x="0" y="0" width="{self.w}" height="{self.h}" '
                f'fill="#ffffff"/>' + "".join(self.parts) + "</svg>\n")


def build(figures):
    """figures は {出力パス: SVG を返す関数}。

    引数なしで書き出す。`--check` を付けると書き出さずに比べ、差分があれば 1 を返す。
    """
    check = "--check" in sys.argv[1:]
    stale = []
    for path, fn in figures.items():
        path = Path(path)
        text = fn().svg()
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    if check:
        print("差分あり: " + ", ".join(stale) if stale else f"{len(figures)} 枚とも一致")
    return 1 if stale else 0
