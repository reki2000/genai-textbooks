#!/usr/bin/env python3
"""docs/books/chinese-history/figs/*.svg を決定的に生成する。"""

from __future__ import annotations

import argparse
import sys
import tempfile
from functools import partial
from pathlib import Path

from svgkit import AQUA, BLUE, CARD_EDGE, GRID, INK, INK2, INK3, ORANGE, RED, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "chinese-history" / "figs"
Svg = partial(SvgDocument, out_dir=OUT_DIR)


def fig_command_translation():
    s = Svg(760, 390, "図1　皇帝の命令は、何段もの読み替えを経て村へ届く",
            "共通文書は広域をつなぐが、各段階で言語・行政慣行・地域の利害が命令の実施を変える")
    nodes = [
        (24, "中央", "詔書・法令", BLUE),
        (172, "地方官", "解釈・配分", AQUA),
        (320, "書記・通訳", "文書・現地語", ORANGE),
        (468, "村の有力者", "利害との調整", AQUA),
        (616, "住民", "口頭説明・実施", BLUE),
    ]
    for x, label, sub, color in nodes:
        s.box(x, 126, 120, 76, label, sub, color=color, size=12)
    for x in (144, 292, 440, 588):
        s.arrow(x + 4, 164, x + 24, 164, color=INK2, sw=2)
    s.text(380, 91, "同じ一文が、そのまま全員へ届くわけではない", size=17, anchor="middle", weight="700")
    labels = [(238, "行政慣行"), (386, "言語"), (534, "地域の利害")]
    for x, label in labels:
        s.line(x, 216, x, 254, stroke=ORANGE, sw=1.5, dash="4 3")
        s.text(x, 275, label, size=11.5, fill=ORANGE, anchor="middle", weight="700")
    s.rect(54, 305, 652, 48, fill="#ffffff", stroke=CARD_EDGE, rx=8)
    s.text(380, 326, "広域をつなぐ共通文書", size=12.5, fill=BLUE, anchor="middle", weight="700")
    s.text(380, 344, "＋　段階ごとの翻訳と交渉　＝　実際の統治", size=12.5, fill=INK, anchor="middle")
    s.save("fig1-command-translation.svg")


def fig_four_lines():
    s = Svg(760, 430, "図2　民族名の前後は、一本の系譜でなく4本の線で検査する",
            "女真→満洲は複数の線が重なるが、匈奴→モンゴルは同じ太さで直結できない")
    rows = [
        ("人", "子孫・移住集団", AQUA),
        ("言語", "同語族・近縁・別・不明", BLUE),
        ("政治", "制度・称号・組織の再編", ORANGE),
        ("名前", "自称・他称・名称変更", INK3),
    ]
    s.text(226, 86, "女真 → 満洲", size=15, anchor="middle", weight="700")
    s.text(566, 86, "匈奴 → モンゴル", size=15, anchor="middle", weight="700")
    for i, (label, sub, color) in enumerate(rows):
        y = 118 + i * 62
        s.box(24, y, 132, 46, label, sub, color=color, size=12)
        s.line(178, y + 23, 274, y + 23, stroke=color, sw=5)
        s.text(294, y + 27, "確認しやすい", size=11, fill=color)
        s.line(518, y + 23, 614, y + 23, stroke=color, sw=2, dash="8 7", opacity=.55)
        uncertainty = "一部不明" if label == "政治" else "直結不可"
        s.text(634, y + 27, uncertainty, size=11, fill=INK2)
    s.line(380, 102, 380, 364, stroke=GRID, sw=1.2)
    s.rect(54, 382, 652, 30, fill="#ffffff", stroke=CARD_EDGE, rx=7)
    s.text(380, 402, "名前が消えても他の線は残りうる／名前が似ても4本は自動でつながらない", size=12, anchor="middle", weight="700")
    s.save("fig2-four-lines.svg")


def fig_design_tensions():
    s = Svg(760, 470, "図3　歴代の『正解』は、同じつまみを逆向きに動かす",
            "一方を強めれば必ず失敗するのではなく、別の問題と負担が増えるため、永久に固定できる位置はない")
    tensions = [
        ("中央の直接把握", "現地の裁量", "統一・徴税", "対応速度・地域適合", BLUE),
        ("軍の財源を分離", "国境軍へ権限", "政変を抑える", "即応・兵站", ORANGE),
        ("一律の制度", "複数制度・仲介", "一貫性", "多言語・多生業を束ねる", AQUA),
    ]
    for i, (left, right, benefit_l, benefit_r, color) in enumerate(tensions):
        y = 102 + i * 104
        s.text(34, y, left, size=12.5, fill=INK, weight="700")
        s.text(726, y, right, size=12.5, fill=INK, anchor="end", weight="700")
        s.text(34, y + 20, benefit_l, size=11, fill=INK2)
        s.text(726, y + 20, benefit_r, size=11, fill=INK2, anchor="end")
        s.line(176, y + 8, 584, y + 8, stroke=GRID, sw=6)
        for x in (176, 380, 584):
            s.circle(x, y + 8, 5, fill="#ffffff", stroke=INK3, sw=1.3)
        knob_x = (302, 458, 356)[i]
        s.circle(knob_x, y + 8, 11, fill=color, stroke="#ffffff", sw=3)
        s.text(380, y + 53, "← 前提と負担に応じて動かす →", size=11, fill=color, anchor="middle", weight="700")
    s.rect(74, 410, 612, 38, fill="#ffffff", stroke=RED, rx=8, sw=1.5)
    s.text(380, 434, "九つの正解を全部『最大』にすることはできない", size=14, fill=RED, anchor="middle", weight="700")
    s.save("fig3-design-tensions.svg")


FIGURES = (fig_command_translation, fig_four_lines, fig_design_tensions)


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
    with tempfile.TemporaryDirectory(prefix="chinese-history-figs-") as tmp:
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
