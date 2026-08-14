#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中国史教材の比較年表を決定的に生成する。

配色：青＝中国の政体、橙＝同時代を読む同期点、灰＝他地域の政体・時代区分。
帯の横幅は継続年数に比例し、境界が概数の区分はキャプションでその旨を示す。
"""
import filecmp
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, INK, SUB, MAIN, FOCUS, MUTED, TINT_MAIN, TINT_MUTED  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs/books/chinese-history/figs"

START, END = -1200, 2025


def timeline():
    """中国と世界の比較年表。

    グリッド：760×370。年代 x=125+(year+1200)*590/3225。
    地域行の上端 y=72,142,212,282、各行の帯 y+22..y+50。
    同期点は前221、618、1271、1644、1912、1949年。
    """
    s = SVG(760, 370, "共通の年代軸で中国、日本、中央・西アジア、欧州を並べた比較年表")
    left, span = 125, 590

    def x(year):
        assert START <= year <= END
        return left + (year - START) * span / (END - START)

    rows = {
        "中国": (72, [(-1046, -256, "周"), (-221, 220, "秦・漢"), (220, 589, "分裂期"),
                     (618, 907, "唐"), (960, 1279, "宋・遼・金"), (1271, 1368, "元"),
                     (1368, 1644, "明"), (1644, 1912, "清"), (1912, 2025, "民国・人民共和国")]),
        "日本列島": (142, [(-900, 250, "縄文後期・弥生"), (250, 710, "古墳・飛鳥"),
                           (710, 1185, ""), (1185, 1600, "武家政権"),
                           (1600, 1868, ""), (1868, 2025, "近現代")]),
        "中央・西アジア": (212, [(-911, -550, "古代帝国"), (-550, -330, ""),
                                  (-247, 224, ""), (224, 651, ""),
                                  (661, 1258, "カリフ諸王朝"), (1258, 1500, ""),
                                  (1500, 1922, ""), (1922, 2025, "")]),
        "欧州・地中海": (282, [(-800, -146, "古代地中海"), (-146, 476, ""),
                                 (476, 1000, ""), (1000, 1500, "中世"),
                                 (1500, 1789, ""), (1789, 1914, ""),
                                 (1914, 2025, "")]),
    }

    ticks = [-1000, 1, 1000, 2000]
    for year in ticks:
        xx = x(year)
        s.line(xx, 42, xx, 350, stroke="#dedede", sw=1)
        s.text(xx, 32, f"紀元前{-year}" if year < 0 else str(year), size=10, fill=SUB, anchor="middle")

    sync = [-221, 618, 1271, 1644, 1912, 1949]
    for year in sync:
        s.line(x(year), 52, x(year), 350, stroke=FOCUS, sw=1, dash="4 5", op=.7)

    for label, (y, periods) in rows.items():
        s.text(112, y + 41, label, size=12, anchor="end", weight="700")
        for begin, finish, name in periods:
            begin, finish = max(begin, START), min(finish, END)
            fill, stroke = (TINT_MAIN, MAIN) if label == "中国" else (TINT_MUTED, MUTED)
            s.rect(x(begin), y + 22, max(1, x(finish) - x(begin)), 28, fill=fill, stroke=stroke, sw=1)
            if name and x(finish) - x(begin) > 28:
                s.text((x(begin) + x(finish)) / 2, y + 41, name, size=9, anchor="middle",
                       fill=INK, weight="700" if label == "中国" else "400")

    return s


FIGURES = {"fig1-world-timeline.svg": timeline}


def write_all(out_dir):
    for name, make in FIGURES.items():
        make().save(out_dir / name)


def main():
    check = "--check" in sys.argv
    if check:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            write_all(temp)
            bad = [n for n in FIGURES if not filecmp.cmp(temp / n, OUT_DIR / n, shallow=False)]
        if bad:
            print("generated files differ: " + ", ".join(bad), file=sys.stderr)
            return 1
        print("all generated figures are up to date")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_all(OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
