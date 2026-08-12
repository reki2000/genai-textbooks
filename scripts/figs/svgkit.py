# -*- coding: utf-8 -*-
"""最小限のSVG組み立てヘルパ。

教材ごとの図は `scripts/figs/{ID}.py` に置き、このモジュールを import して描き、
`docs/books/{ID}/figs/*.svg` へ書き出す。使い方は `.claude/skills/zuhan/` が正本
（配置と検査は `references/repo.md`、作図規約は `references/conventions.md`）。

作図規約:
  - 座標は先に決める（自動レイアウトを使わない）
  - 意味を持つ色は3系統まで。役割で選ぶ（MAIN / FOCUS / WARN、補助は MUTED）
  - 接続線は直線、または直角1回まで

書き出しは docsify に合わせてある。`width` / `height` 属性を付けると閲覧側の
`max-width:100%` と噛み合って縦横比が崩れるため、`viewBox` だけを持たせる。
図はライト／ダーク両テーマの上に置かれるので、SVG 自身が明るい地色を持つ。
"""

from pathlib import Path

FONT = "Noto Sans CJK JP, Hiragino Sans, Noto Sans JP, Yu Gothic, sans-serif"

# 意味は役割で決める。分野固有の対象（電子・正孔など）に固定しない。
# その教材で各色が何を指すかは scripts/figs/{ID}.py の冒頭で宣言する。
MAIN = "#1f6fd0"        # その教材が追いかける主役
FOCUS = "#e07b1f"       # いま注目している箇所
WARN = "#cf3b2d"        # 注意喚起・破綻
MUTED = "#8d8d8d"       # 動かないもの・補助
INK = "#1c1c1c"
SUB = "#6b6b6b"
TINT_MAIN = "#e6eefb"
TINT_FOCUS = "#f6e6b8"
TINT_WARN = "#fbeae8"
TINT_MUTED = "#f2f2f2"

# 旧名（半導体教材由来）。既存の図が参照しているので別名として残す。
E_BLUE, ACCENT, H_RED, FIX_GRAY = MAIN, FOCUS, WARN, MUTED
N_TINT, OX_TINT, P_TINT, DEP_TINT = TINT_MAIN, TINT_FOCUS, TINT_WARN, TINT_MUTED


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    def __init__(self, w, h, title="", desc="", bg="#ffffff"):
        """title / desc はスクリーンリーダ用。title は図が何を示すかを一文で書く。"""
        self.w, self.h = w, h
        self.parts = []
        self.defs = []
        self.title = title
        self.desc = desc or title
        self._arrowheads = set()
        self.parts.append(
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>')

    # ---- primitives ----
    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1.4, rx=0, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.4, dash=None, cap="round",
             op=1, role=None):
        """role="connector" を付けた線どうしの交差だけを check_figure.py が咎める。
        領域の境界や×印など、交差して当然の線には role を付けない。"""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        r = f' data-role="{role}"' if role else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="{cap}" opacity="{op}"{d}{r}/>')

    def path(self, d, stroke=INK, sw=1.4, fill="none", dash=None, op=1):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{op}"{da}/>')

    def circle(self, cx, cy, r, fill="none", stroke=INK, sw=1.2, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" opacity="{op}"{d}/>')

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="400", style=""):
        st = f' font-style="{style}"' if style else ""
        s = esc(s)
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    # ---- composites ----
    def _arrowhead(self, color, sw, back=False):
        """矢印の頭を1つ定義して id を返す。

        `orient="auto-start-reverse"` は SVG2 で、resvg のような検査用レンダラが
        未対応だと頭が回らず、目視で矢印の向きを確かめられなくなる。SVG1.1 の
        `orient="auto"` だけを使い、marker-start 用には向きを反転した図形を
        別マーカーとして持つ（`back=True`）。
        """
        # 頭の実寸を約 3.4*sw に固定し、太い矢印で頭が肥大するのを防ぐ
        mw = round(max(2.4, min(20.0 / sw, 9.0)), 2)
        key = ("b" if back else "f") + color.replace("#", "") + str(mw).replace(".", "_")
        if key not in self._arrowheads:
            self._arrowheads.add(key)
            d = "M 10 0 L 0 5 L 10 10 z" if back else "M 0 0 L 10 5 L 0 10 z"
            refx = 1.5 if back else 8.5
            self.defs.append(
                f'<marker id="ah{key}" viewBox="0 0 10 10" refX="{refx}" refY="5" '
                f'markerWidth="{mw}" markerHeight="{mw}" orient="auto">'
                f'<path d="{d}" fill="{color}"/></marker>')
        return f"ah{key}"

    def arrow(self, x1, y1, x2, y2, stroke=INK, sw=2.0, dash=None):
        m = self._arrowhead(stroke, sw)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"{d}/>')

    def dim(self, x1, x2, y, label, color=SUB, size=11, up=False):
        """水平方向の寸法線（両矢印）"""
        ms = self._arrowhead(color, 1, back=True)
        me = self._arrowhead(color, 1)
        self.parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" '
            f'stroke-width="1" marker-start="url(#{ms})" marker-end="url(#{me})"/>')
        self.line(x1, y - 5, x1, y + 5, stroke=color, sw=1)
        self.line(x2, y - 5, x2, y + 5, stroke=color, sw=1)
        ty = y - 7 if up else y + 15
        self.text((x1 + x2) / 2, ty, label, size=size, fill=color, anchor="middle")

    def cross(self, cx, cy, r=5, stroke=WARN, sw=2):
        self.line(cx - r, cy - r, cx + r, cy + r, stroke=stroke, sw=sw, role="glyph")
        self.line(cx + r, cy - r, cx - r, cy + r, stroke=stroke, sw=sw, role="glyph")

    def save(self, path):
        """viewBox だけを持つSVGを書き出す（width/height は付けない）。"""
        path = Path(path)
        defs = ("<defs>" + "".join(self.defs) + "</defs>") if self.defs else ""
        head = ""
        if self.title:
            head = (f'<title id="title">{esc(self.title)}</title>'
                    f'<desc id="desc">{esc(self.desc)}</desc>')
            label = ' role="img" aria-labelledby="title desc"'
        else:
            label = ""
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 0 {self.w} {self.h}"{label}>'
               + head + defs + "".join(self.parts) + "</svg>\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path}")
        return path
