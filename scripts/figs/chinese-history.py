#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中国史教材の各「世界同時刻盤」を決定的に生成する。

配色：青＝各幕で追う中国の政体、橙＝比較の焦点となる転換、灰＝同時代の他地域。
帯の横幅は継続年数に比例する。地域ごとの時代区分を発展段階として揃えない。
"""
import filecmp
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, INK, SUB, MAIN, FOCUS, MUTED, TINT_MAIN, TINT_FOCUS, TINT_MUTED  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs/books/chinese-history/figs"

# filename, title, start, end, ticks, focus years, rows(label, periods(start,end,label))
SCENES = [
    ("fig1-zhou-world.svg", "周と同時代の国家形成は一つの型へ収束しない", -1100, -300,
     [-1000, -800, -600, -400], [-771, -550], [
        ("中国", [(-1046, -771, "西周"), (-770, -300, "東周")]),
        ("日本列島", [(-1100, -900, "縄文後期"), (-900, -300, "弥生への移行")]),
        ("西アジア", [(-911, -609, "新アッシリア"), (-550, -330, "アケメネス朝")]),
        ("南アジア", [(-1100, -600, "ヴェーダ期"), (-600, -300, "諸国形成")]),
        ("地中海", [(-800, -500, "ポリス形成"), (-509, -300, "共和政ローマ")]),
     ]),
    ("fig2-han-world.svg", "漢とローマの間には複数の中継世界がある", -220, 250,
     [-200, -100, 1, 100, 200], [-30, 220], [
        ("中国", [(-206, 9, "前漢"), (25, 220, "後漢")]),
        ("日本列島", [(-220, 250, "弥生・古墳への移行")]),
        ("中央・南アジア", [(-247, 224, "パルティア"), (30, 250, "クシャーナ朝")]),
        ("地中海", [(-27, 250, "ローマ帝国")]),
        ("海域アジア", [(-100, 250, "インド洋交易"), (50, 250, "扶南など")]),
     ]),
    ("fig3-division-world.svg", "帝国解体後も制度と宗教は別の政体へ継承される", 350, 650,
     [350, 450, 550, 650], [476, 589], [
        ("中国", [(350, 420, "東晋・十六国"), (420, 589, "南北朝"), (589, 618, "隋")]),
        ("日本・朝鮮", [(350, 538, "ヤマト王権"), (538, 650, "仏教受容・国家形成")]),
        ("西アジア", [(350, 651, "サーサーン朝")]),
        ("南アジア", [(350, 550, "グプタ朝"), (550, 650, "後継諸国")]),
        ("欧州・紅海", [(350, 476, "ローマ東西"), (476, 650, "東ローマ・諸王国"), (350, 570, "アクスム")]),
     ]),
    ("fig4-tang-world.svg", "唐・奈良・イスラム世界は交易と制度受容で結ばれる", 600, 900,
     [600, 700, 800, 900], [618, 755], [
        ("中国", [(618, 755, "唐前半"), (755, 907, "唐後半")]),
        ("日本・朝鮮", [(600, 710, "飛鳥"), (710, 794, "奈良"), (676, 900, "新羅・渤海")]),
        ("西アジア", [(600, 651, "サーサーン朝"), (661, 750, "ウマイヤ朝"), (750, 900, "アッバース朝")]),
        ("海域アジア", [(650, 900, "シュリーヴィジャヤ"), (600, 900, "インド洋交易")]),
        ("欧州", [(600, 800, "東ローマ"), (751, 888, "カロリング朝")]),
     ]),
    ("fig5-song-world.svg", "宋の技術発展は同時代の複数の商業圏の中にある", 950, 1250,
     [950, 1050, 1150, 1250], [960, 1127], [
        ("中国北南", [(960, 1127, "北宋・遼"), (1127, 1250, "南宋・金")]),
        ("日本", [(950, 1185, "平安後期"), (1185, 1250, "鎌倉")]),
        ("西アジア", [(950, 1055, "諸王朝"), (1037, 1194, "セルジューク朝")]),
        ("南・東南アジア", [(985, 1250, "チョーラ朝・交易"), (950, 1250, "アンコール・海港")]),
        ("欧州・西アフリカ", [(950, 1250, "都市・十字軍"), (950, 1235, "ガーナからマリへ")]),
     ]),
    ("fig6-yuan-world.svg", "モンゴル時代の移動網は双方向で費用負担も伴う", 1200, 1400,
     [1200, 1250, 1300, 1350, 1400], [1271, 1294], [
        ("中国", [(1206, 1271, "モンゴル征服"), (1271, 1368, "元")]),
        ("日本", [(1200, 1333, "鎌倉"), (1274, 1281, "襲来")]),
        ("西・南アジア", [(1256, 1335, "イル・ハン国"), (1250, 1400, "マムルーク・デリー")]),
        ("東南アジア", [(1200, 1287, "パガン"), (1238, 1400, "スコータイ・ジャワ")]),
        ("欧州・アフリカ", [(1200, 1400, "都市・王権"), (1235, 1400, "マリ・沿岸都市")]),
     ]),
    ("fig7-ming-world.svg", "銀の流れが明の税制を日本・米州・海域アジアへ結ぶ", 1400, 1650,
     [1400, 1450, 1500, 1550, 1600, 1650], [1492, 1571], [
        ("中国", [(1400, 1570, "明・銀納化"), (1570, 1644, "一条鞭法期")]),
        ("日本", [(1400, 1467, "室町"), (1467, 1600, "戦国・銀山"), (1600, 1650, "江戸初期")]),
        ("米州・太平洋", [(1492, 1545, "大西洋進出"), (1545, 1650, "銀山・マニラ航路")]),
        ("西・南アジア", [(1453, 1650, "オスマン"), (1501, 1650, "サファヴィー・ムガル")]),
        ("東南アジア", [(1400, 1511, "マラッカ"), (1511, 1650, "アユタヤ・バタヴィア")]),
     ]),
    ("fig8-qing-world.svg", "清と海洋帝国は異なる財政・軍事動員を発達させる", 1640, 1912,
     [1650, 1700, 1750, 1800, 1850, 1900], [1757, 1840], [
        ("中国", [(1644, 1796, "清前半・拡大"), (1796, 1912, "清後半・再編")]),
        ("日本", [(1640, 1868, "江戸"), (1868, 1912, "明治")]),
        ("欧州", [(1640, 1780, "財政軍事国家"), (1780, 1912, "工業化・国民国家")]),
        ("南・西アジア", [(1640, 1757, "ムガル・オスマン"), (1757, 1912, "英領化・カージャール")]),
        ("東南アジア・アフリカ", [(1640, 1800, "海域国家・交易"), (1800, 1912, "植民地化")]),
     ]),
    ("fig9-modern-world.svg", "旧帝国圏は世界大戦・独立・冷戦の中で国民国家へ再編される", 1912, 2025,
     [1912, 1945, 2025], [1949, 1978], [
        ("中国", [(1912, 1949, "中華民国"), (1949, 1978, "人民共和国・計画"), (1978, 2025, "改革開放期")]),
        ("日本", [(1912, 1945, "帝国・戦争"), (1945, 2025, "戦後")]),
        ("欧州", [(1914, 1945, "二つの世界大戦"), (1945, 1993, "冷戦・統合"), (1993, 2025, "EU期")]),
        ("アジア・中東", [(1912, 1945, "帝国解体"), (1945, 1975, "独立国家化"), (1975, 2025, "開発・地域秩序")]),
        ("アフリカ", [(1912, 1957, "植民地支配"), (1957, 1975, "独立"), (1975, 2025, "国家建設")]),
     ]),
]


def make_scene(title, start, end, ticks, focus, rows):
    """760×350。x=145+(year-start)*570/(end-start)、5地域行 y=70+52*n。"""
    s = SVG(760, 350, title)
    left, width = 145, 570
    x = lambda year: left + (year - start) * width / (end - start)
    for year in ticks:
        xx = x(year)
        s.line(xx, 35, xx, 320, stroke="#dedede", sw=1)
        label = f"前{-year}" if year < 0 else str(year)
        s.text(xx, 27, label, size=10, fill=SUB, anchor="middle")
    for year in focus:
        if start <= year <= end:
            s.line(x(year), 42, x(year), 320, stroke=FOCUS, sw=1.2, dash="4 4")
    for idx, (region, periods) in enumerate(rows):
        y = 58 + idx * 52
        s.text(132, y + 27, region, size=11, anchor="end", weight="700")
        for begin, finish, label in periods:
            begin, finish = max(begin, start), min(finish, end)
            if begin >= finish:
                continue
            main = idx == 0
            fill, stroke = (TINT_MAIN, MAIN) if main else (TINT_MUTED, MUTED)
            if any(begin <= f <= finish for f in focus) and not main:
                fill = TINT_FOCUS
            s.rect(x(begin), y + 8, max(1, x(finish) - x(begin)), 30, fill=fill, stroke=stroke, sw=1.2)
            if x(finish) - x(begin) >= max(42, len(label) * 9):
                s.text((x(begin) + x(finish)) / 2, y + 28, label, size=9, anchor="middle",
                       fill=INK, weight="700" if main else "400")
    return s


FIGURES = {
    filename: (lambda t=title, a=start, b=end, ticks=ticks, focus=focus, rows=rows:
               make_scene(t, a, b, ticks, focus, rows))
    for filename, title, start, end, ticks, focus, rows in SCENES
}


def write_all(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, make in FIGURES.items():
        make().save(out_dir / name)


def main():
    check = "--check" in sys.argv
    if check:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            write_all(temp)
            bad = [name for name in FIGURES
                   if not (OUT_DIR / name).exists() or
                   not filecmp.cmp(temp / name, OUT_DIR / name, shallow=False)]
        if bad:
            print("generated files differ: " + ", ".join(bad), file=sys.stderr)
            return 1
        print("all generated figures are up to date")
        return 0
    write_all(OUT_DIR)
    old = OUT_DIR / "fig1-world-timeline.svg"
    if old.exists():
        old.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
