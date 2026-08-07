#!/usr/bin/env python3
"""教材図版（docs/books/{ID}/figs/*.svg）を組み立てる共通ヘルパ。

教材ごとの図は `scripts/figures/{ID}_figs.py` に置き、このモジュールを import して
`Svg` に描く。配色・書体・カード面の作りをここへ集約し、教材をまたいで図の
見た目を揃える。使い方は `.claude/skills/yaruo-figures/SKILL.md` が正本。

図は docsify のライト／ダーク両テーマの上に置かれる。テーマ切り替えは OS の
prefers-color-scheme と一致しないことがあるため、SVG 自身が明るいカード面を持ち、
どちらのテーマでも同じ配色で読めるようにしている。
"""

from __future__ import annotations

from pathlib import Path

# --- 配色（dataviz スキルの検証済みパレット。ライト面向けの値）-----------------
SURFACE = "#fcfcfb"     # カード面
CARD_EDGE = "#e2e4e3"   # カードの枠
INK = "#0b0b0b"         # 主要テキスト
INK2 = "#52514e"        # 副次テキスト・注記
INK3 = "#7b7a75"        # 軸・目盛・弱い要素
GRID = "#dcdedd"        # グリッド線
BLUE = "#2a78d6"        # 系列1
ORANGE = "#eb6834"      # 系列2
AQUA = "#1baf7a"        # 系列3
RED = "#e34948"         # 「これは駄目」を指す強調
VIOLET = "#4a3aa7"      # 補助

FONT = "'Hiragino Sans','Noto Sans JP','Yu Gothic',system-ui,sans-serif"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    """タイトル・副題つきのカード1枚。座標は左上原点、単位はユーザー単位（≒px）。

    幅は 760 を既定とする（docsify の本文幅にほぼ一致）。高さは中身に合わせる。
    """

    def __init__(self, width: float, height: float, title: str, subtitle: str = "",
                 out_dir: Path | None = None):
        self.w = width
        self.h = height
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.title = title
        self.out_dir = out_dir
        self.rect(0, 0, width, height, fill=SURFACE, stroke=CARD_EDGE, rx=10)
        self.text(24, 32, title, size=16, weight="700")
        if subtitle:
            self.text(24, 54, subtitle, size=12.5, fill=INK2)

    # --- primitives -----------------------------------------------------
    def rect(self, x, y, w, h, fill="none", stroke="none", rx=0, sw=1, opacity=None, dash=None):
        extra = f' opacity="{opacity}"' if opacity is not None else ""
        extra += f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'
        )

    def line(self, x1, y1, x2, y2, stroke=GRID, sw=1, dash=None, cap="round", opacity=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += f' opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"{extra}/>'
        )

    def path(self, d, stroke="none", fill="none", sw=2, dash=None, opacity=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += f' opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{extra}/>'
        )

    def circle(self, cx, cy, r, fill="none", stroke="none", sw=1, opacity=None, dash=None):
        extra = f' opacity="{opacity}"' if opacity is not None else ""
        extra += f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{extra}/>'
        )

    def text(self, x, y, s, size=12, fill=INK, weight="400", anchor="start", opacity=None):
        extra = f' opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{extra}>{esc(s)}</text>'
        )

    def lines_of_text(self, x, y, rows, size=12, fill=INK2, lh=16, anchor="start", weight="400"):
        for i, row in enumerate(rows):
            self.text(x, y + i * lh, row, size=size, fill=fill, anchor=anchor, weight=weight)

    def arrow_defs(self, name, color):
        self.defs.append(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
        )

    def arrow(self, x1, y1, x2, y2, color=INK2, sw=1.6, marker=None, dash=None):
        marker = marker or f"arw-{color.lstrip('#')}"
        if not any(f'id="{marker}"' in d for d in self.defs):
            self.arrow_defs(marker, color)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{marker})"{extra}/>'
        )

    def arrow_path(self, d, color=INK2, sw=1.6, dash=None):
        marker = f"arw-{color.lstrip('#')}"
        if not any(f'id="{marker}"' in dd for dd in self.defs):
            self.arrow_defs(marker, color)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" marker-end="url(#{marker})"{extra}/>'
        )

    def box(self, x, y, w, h, label, sub="", color=BLUE, size=12.5, fill="#ffffff"):
        """ラベル（＋小さい副題）つきの角丸ボックス。流れ図の節点に使う。"""
        self.rect(x, y, w, h, fill=fill, stroke=color, rx=8, sw=1.6)
        cy = y + h / 2 + (0 if not sub else -6)
        self.text(x + w / 2, cy + 4, label, size=size, anchor="middle", weight="700", fill=INK)
        if sub:
            self.text(x + w / 2, cy + 21, sub, size=11, anchor="middle", fill=INK2)

    def save(self, name: str, out_dir: Path | None = None):
        """viewBox だけを持つ SVG を書き出す。

        width/height 属性は付けない。付けると docsify 側の `max-width:100%` で
        縦横比が崩れる。viewBox だけなら閲覧幅にフィットする。
        """
        target = out_dir or self.out_dir
        if target is None:
            raise ValueError("out_dir を Svg() か save() で指定する")
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        body = "\n".join(self.parts)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" '
            f'role="img" aria-label="{esc(self.title)}">\n'
            f"<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n"
        )
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(svg, encoding="utf-8")
        print(f"wrote {target / name}")
