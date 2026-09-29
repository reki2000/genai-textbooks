# -*- coding: utf-8 -*-
"""最小限のSVG組み立てヘルパ。

教材ごとの図は `scripts/figs/{ID}.py` に置き、このモジュールを import して描き、
`docs/books/{ID}/figs/*.svg` へ書き出す。使い方は `.claude/skills/zuhan/` が正本
（配置と検査は `references/repo.md`、作図規約は `references/conventions.md`）。

作図規約:
  - キャンバスの形と大きさは内容から決める（`references/layout.md`）。760 幅を既定にしない
  - 座標は先に決める（自動レイアウトを使わない）
  - 意味を持つ色は3系統まで。役割で選ぶ（MAIN / FOCUS / WARN、補助は MUTED）
  - 接続線は直線、または直角1回まで。形態そのもの（膜・輪郭・流路）は曲線でよい

自力で描く挿絵風の模式図（細胞・装置・地形など）は、プリミティブに加えて
`blob`（点列を通る滑らかな閉曲線）、`curve` / `curve_arrow`（滑らかな開曲線）、
`zoom`（全体＋拡大の枠と案内線）、`badge`（読み順の番号）、`note`（結論の注記）、
`hatch`（色に頼らない塗り分け）で組み立てる。

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

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="400", style="",
             halo=False):
        """halo=True で文字の周りを地色で縁取る。線や塗りの上に直接ラベルを置くときに使う。"""
        st = f' font-style="{style}"' if style else ""
        s = esc(s)
        if halo:
            # paint-order は SVG2 なので使わず、地色で太らせた同じ文字を下に敷く
            self.parts.append(
                f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                f'fill="#ffffff" stroke="#ffffff" stroke-width="4" stroke-linejoin="round" '
                f'text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    def lines(self, x, y, rows, size=15, lh=None, **kw):
        """複数行の文字。<tspan> を使わず1行1個の <text> にする（検査器が数えられるように）。
        戻り値は最終行の下端の y。"""
        lh = lh or round(size * 1.4)
        for i, row in enumerate(rows):
            self.text(x, y + i * lh, row, size=size, **kw)
        return y + (len(rows) - 1) * lh + round(size * 0.3)

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
        ty = y - (size - 4) if up else y + size + 4   # size=11 で従来の -7 / +15
        self.text((x1 + x2) / 2, ty, label, size=size, fill=color, anchor="middle")

    def cross(self, cx, cy, r=5, stroke=WARN, sw=2):
        self.line(cx - r, cy - r, cx + r, cy + r, stroke=stroke, sw=sw, role="glyph")
        self.line(cx + r, cy - r, cx - r, cy + r, stroke=stroke, sw=sw, role="glyph")

    # ---- 自力描画の部品 ----
    @staticmethod
    def _smooth(pts, closed, k=1.0):
        """点列を通る Catmull-Rom 曲線を3次ベジェの path d へ変換する。
        k は張り（0 で折れ線、1 で標準）。座標は点列が決めるので、形は宣言した点から外れない。"""
        n = len(pts)
        if n < 2:
            raise ValueError("点が2個以上要る")
        def P(i):
            if closed:
                return pts[i % n]
            return pts[max(0, min(n - 1, i))]
        f = lambda v: f"{round(v, 1):g}"
        d = [f"M {f(pts[0][0])} {f(pts[0][1])}"]
        last = n if closed else n - 1
        for i in range(last):
            p0, p1, p2, p3 = P(i - 1), P(i), P(i + 1), P(i + 2)
            c1 = (p1[0] + (p2[0] - p0[0]) * k / 6, p1[1] + (p2[1] - p0[1]) * k / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) * k / 6, p2[1] - (p3[1] - p1[1]) * k / 6)
            d.append(f"C {f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
        if closed:
            d.append("Z")
        return " ".join(d)

    def blob(self, pts, fill=TINT_MUTED, stroke=INK, sw=1.6, k=1.0, dash=None, op=1):
        """点列を通る滑らかな閉曲線。細胞・器官・島・液滴など、輪郭そのものが対象の形。"""
        self.path(self._smooth(pts, True, k), stroke=stroke, sw=sw, fill=fill, dash=dash, op=op)

    def curve(self, pts, stroke=INK, sw=1.6, k=1.0, dash=None, op=1):
        """点列を通る滑らかな開曲線。膜・流路・境界線など。"""
        self.path(self._smooth(pts, False, k), stroke=stroke, sw=sw, dash=dash, op=op)

    def curve_arrow(self, pts, stroke=INK, sw=2.0, k=1.0, dash=None):
        """点列を通る曲がった矢印。移動の経路が曲がっていること自体に意味があるときだけ使う。"""
        m = self._arrowhead(stroke, sw)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{self._smooth(pts, False, k)}" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"{da}/>')

    def badge(self, cx, cy, n, color=FOCUS, r=13, size=15):
        """読み順の番号。図の中で「どこから見るか」を指定する。1図に5個まで。"""
        self.circle(cx, cy, r, fill=color, stroke="#ffffff", sw=2)
        self.text(cx, cy + size * 0.36, str(n), size=size, fill="#ffffff",
                  anchor="middle", weight="700")

    def note(self, x, y, rows, color=FOCUS, size=15, bar=True, weight="700"):
        """結論の注記。図が答える問いへの答えを、該当箇所のすぐ横に置く。
        左に色の縦棒を付けて本文ラベルと区別する。1図に1個が原則。"""
        if isinstance(rows, str):
            rows = [rows]
        lh = round(size * 1.4)
        if bar:
            self.rect(x, y - size, 4, lh * len(rows) - lh + size * 1.3, fill=color,
                      stroke="none", sw=0)
        self.lines(x + (12 if bar else 0), y, rows, size=size, lh=lh, fill=INK,
                   weight=weight)

    def zoom(self, src, dst, stroke=MUTED, sw=1.2):
        """全体＋拡大。src=(x,y,w,h) の破線枠から dst の実線枠へ案内線を2本引く。
        案内線は枠の外側の角どうしを結ぶので、交差しない。拡大側の中身は呼び出し側が描く。"""
        sx, sy, sw_, sh = src
        dx, dy, dw, dh = dst
        self.rect(sx, sy, sw_, sh, stroke=stroke, sw=sw, dash="4 3")
        self.rect(dx, dy, dw, dh, fill="#ffffff", stroke=stroke, sw=sw)
        # 中心どうしの変位で、横に出すか縦に出すかを決める
        ddx = (dx + dw / 2) - (sx + sw_ / 2)
        ddy = (dy + dh / 2) - (sy + sh / 2)
        if abs(ddx) >= abs(ddy):
            if ddx > 0:             # 右に拡大
                pairs = [((sx + sw_, sy), (dx, dy)), ((sx + sw_, sy + sh), (dx, dy + dh))]
            else:                   # 左に拡大
                pairs = [((sx, sy), (dx + dw, dy)), ((sx, sy + sh), (dx + dw, dy + dh))]
        elif ddy > 0:               # 下に拡大
            pairs = [((sx, sy + sh), (dx, dy)), ((sx + sw_, sy + sh), (dx + dw, dy))]
        else:                       # 上に拡大
            pairs = [((sx, sy), (dx, dy + dh)), ((sx + sw_, sy), (dx + dw, dy + dh))]
        for (a, b) in pairs:
            self.line(a[0], a[1], b[0], b[1], stroke=stroke, sw=sw, dash="4 3")

    def hatch(self, color=MUTED, gap=7, sw=1.2, angle=45):
        """斜線の塗りを定義して fill 値（url(#...)）を返す。色に頼らず領域を区別する。"""
        key = f"h{color.replace('#', '')}{gap}{angle}".replace(".", "_")
        if not any(f'id="{key}"' in d for d in self.defs):
            self.defs.append(
                f'<pattern id="{key}" width="{gap}" height="{gap}" '
                f'patternUnits="userSpaceOnUse" patternTransform="rotate({angle})">'
                f'<line x1="0" y1="0" x2="0" y2="{gap}" stroke="{color}" '
                f'stroke-width="{sw}"/></pattern>')
        return f"url(#{key})"

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
