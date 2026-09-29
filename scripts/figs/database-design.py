#!/usr/bin/env python3
"""database-design の図。

色：青=いま有効な事実・正しい形／橙=照会（外から与える問い）／赤=矛盾・破綻。
灰は終わった事実・過去の認識・背景。
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/database-design/figs"


def months(d, origin):
    return (d.year - origin.year) * 12 + d.month - 1 - (origin.month - 1) + (d.day - 1) / 30


def band(s, x1, x2, y, h, label, color, open_end=False, sub=None):
    """期間の帯。青は有効な事実、灰は閉じた事実、赤は矛盾。open_end で右端へ矢印。"""
    s.rect(x1, y, x2 - x1, h, fill=TINT[color], stroke=color, sw=2 if color != MUTED else 1.2)
    s.text((x1 + x2) / 2, y + h / 2 + 5.5 if not sub else y + h / 2 - 1, label, size=15,
           anchor="middle", bold=color != MUTED, fill=INK if color != MUTED else SUB, halo=True)
    if sub:
        s.text((x1 + x2) / 2, y + h / 2 + 16, sub, size=13, anchor="middle", fill=SUB)
    if open_end:
        s.arrow(x2, y + h / 2, x2 + 18, y + h / 2, stroke=color, sw=2)


def valid_period():
    """3-4 旧行を閉じれば照会は1行、閉じ忘れると2行。対照の2枚、横長 M 600x330。

    時間 x = 40 + 月数*12（2024-04 → 40、2027-03 → 460）。照会 2026-12-01。
    上パネル 帯 y 56。下パネル 帯 y 170 / 210。注記 x 500。
    """
    o = date(2024, 4, 1)
    X = lambda d: 40 + months(d, o) * 12
    q = date(2026, 12, 1)
    ok = [(date(2024, 4, 1), date(2026, 4, 1), "250,000"), (date(2026, 4, 1), date(2026, 9, 1), "265,000"),
          (date(2026, 9, 1), None, "270,000")]
    ng = [ok[0], (date(2026, 4, 1), None, "265,000"), ok[2]]
    hits = lambda rows: [r for r in rows if r[0] <= q and (r[1] is None or q < r[1])]
    assert len(hits(ok)) == 1 and len(hits(ng)) == 2
    s = SVG(600, 330, "旧行を閉じれば照会日に当たるのは1行、閉じ忘れると同じ日に2行が当たる")
    end = X(date(2027, 3, 1))
    s.text(24, 40, "旧行を閉じた", size=15, bold=True)
    s.text(24, 154, "閉じ忘れた（265,000 の終わりが無期限）", size=15, bold=True, fill=WARN)
    for a, b, amt in ok:
        band(s, X(a), X(b) if b else end, 56, 32, amt, MUTED if b else MAIN, open_end=b is None)
    for k, (a, b, amt) in enumerate(ng):
        band(s, X(a), X(b) if b else end, 170 + 40 * max(0, k - 1), 32, amt,
             MUTED if b else WARN, open_end=b is None)
    s.line(X(q), 48, X(q), 256, stroke=FOCUS, sw=2.4, dash="6 4")
    s.text(X(q), 276, "照会：2026-12-01", size=15, fill=FOCUS, anchor="middle", bold=True)
    for d in (date(2024, 4, 1), date(2025, 4, 1), date(2026, 4, 1)):
        s.text(X(d), 310, f"{d.year}-{d.month:02d}", size=13, fill=SUB, anchor="middle")
    s.note(500, 78, "1行", color=MAIN)
    s.note(500, 212, "2行", color=WARN)
    return s


def bitemporal():
    """3-5 同じ「5月分の給与」でも、いつ聞いたかで答えが変わる。正方 M 520x500。

    x: 有効時間 2026-02 → 90 … 2026-08 → 480（1か月 65）
    y: システム時間 2026-05-01 → 400 … 2026-08-01 → 70（1か月 110、下ほど過去）
    """
    X = lambda m: 90 + (m - 2) * 65          # m は 2026 年の月（小数可）
    Y = lambda m: 400 - (m - 5) * 110
    known = 6 + 24 / 30                        # 6月25日
    s = SVG(520, 500, "6月25日より前に聞くと5月分は250,000円、後に聞くと265,000円")
    s.rect(X(2), Y(8), X(8) - X(2), Y(5) - Y(8), fill=TINT[MUTED], stroke="none")
    s.rect(X(4), Y(8), X(8) - X(4), Y(known) - Y(8), fill=TINT[MAIN], stroke="none")
    s.line(X(4), Y(8), X(4), Y(known), stroke=MAIN, sw=1.6)
    s.line(X(4), Y(known), X(8), Y(known), stroke=MAIN, sw=2.4)
    s.text(X(6.9), Y(7.6), "265,000円", size=18, fill=MAIN, anchor="middle", bold=True)
    s.text(X(6.9), Y(5.4), "250,000円", size=18, fill=SUB, anchor="middle", bold=True)
    s.text(X(2.9), Y(7.6), "250,000円", size=18, fill=SUB, anchor="middle", bold=True)
    s.text(X(8) - 4, Y(known) - 10, "6月25日：遡及を知る", size=14, fill=MAIN, anchor="end")
    s.line(X(2), Y(5), X(8), Y(5), stroke=MUTED)
    s.line(X(2), Y(5), X(2), Y(8), stroke=MUTED)
    for m in range(2, 9):
        s.text(X(m), Y(5) + 22, f"{m}月", size=14, fill=SUB, anchor="middle")
    for m in (5, 6, 7, 8):
        s.text(X(2) - 8, Y(m) + 5, f"{m}月", size=14, fill=SUB, anchor="end")
    s.text(X(5), 466, "有効時間（現実にいつ真実か）", size=15, fill=SUB, anchor="middle")
    s.text(24, 40, "システム時間（DBがいつそう信じたか）", size=15, fill=SUB)
    qx = X(5.5)
    s.line(qx, Y(5), qx, Y(8), stroke=FOCUS, sw=2.4, dash="6 4")
    for m, n in ((5 + 24 / 30, 1), (7.3, 2)):
        s.circle(qx, Y(m), 8, fill=FOCUS, stroke="#ffffff", sw=2)
        s.badge(qx - 26, Y(m), n)
    s.text(qx + 14, Y(5 + 24 / 30) + 5, "5月25日に聞く", size=14, fill=FOCUS, bold=True)
    s.text(qx + 14, Y(7.3) + 5, "いま聞く", size=14, fill=FOCUS, bold=True)
    s.note(X(2) + 12, Y(6.4) - 6, ["同じ5月分でも", "聞いた時点で答えが違う"])
    return s


def constraint_reach():
    """2-2 / 5-2 宣言的制約が届く範囲は入れ子で、比率の合計と円環はその外にある。正方 S 460x440。

    内側から：1行（CHECK）／条件を満たす行・列の一致（UNIQUE・部分一意）／2テーブル（外部キー）。
    太い青の枠が宣言的制約の限界。その外の2つを赤で。
    """
    s = SVG(460, 450, "宣言的制約が届くのは2テーブル間の参照まで。比率の合計と木の円環はその外にある")
    rings = [(24, 60, 412, 280, "外部キー：2テーブル間", "存在しない部署を指す"),
             (48, 120, 364, 200, "UNIQUE・部分一意：値の一致", "主務が2つある"),
             (72, 180, 316, 110, "CHECK：1行の中", "負の給与")]
    for k, (x, y, w, h, label, ex) in enumerate(rings):
        s.rect(x, y, w, h, rx=14, fill=TINT[MAIN] if k == 2 else "#ffffff",
               stroke=MAIN, sw=3.5 if k == 0 else 1.4)
        s.text(x + 14, y + 26, label, size=15, bold=k == 0)
        s.text(x + 14, y + 48, "防げる例：" + ex, size=14, fill=SUB)
    s.text(24, 44, "宣言だけで守れる範囲", size=16, fill=MAIN, bold=True)
    for y, label, sub in ((384, "行をまたぐ集計", "比率の合計 ＝ 1.0"),
                          (428, "経路をまたぐ", "部署の木に円環がない")):
        s.circle(40, y - 5, 7, fill=WARN, stroke="#ffffff", sw=2)
        s.text(58, y, label, size=15, bold=True, fill=WARN)
        s.text(200, y, sub, size=15)
    return s


NEST_BEFORE = [("営業本部", 0), ("第一営業部", 1), ("首都圏営業課", 2), ("東日本営業課", 2), ("第二営業部", 1)]


def nested_numbers(tree):
    """[(名前, 深さ)] の前順の並びから、入れ子集合の [lft, rgt] を振る。"""
    out, stack, n = {}, [], 0
    for name, d in tree:
        while stack and stack[-1][1] >= d:
            n += 1
            out[stack.pop()[0]][1] = n
        n += 1
        out[name] = [n, None]
        stack.append((name, d))
    while stack:
        n += 1
        out[stack.pop()[0]][1] = n
    return out


def nested_sets():
    """5-2 入れ子集合：包含が親子になる代わりに、1個の挿入で既存の番号が動く。
    対照の2枚、横長 L 760x560。1部署1行、数直線 x = 190 + 48*(n-1)（n=1..12）。
    上パネル 行 y = 72 + 28*k、下パネル 行 y = 330 + 28*k。名前は左端 x=176 に右寄せ。
    """
    before = nested_numbers(NEST_BEFORE)
    after_tree = NEST_BEFORE[:3] + [("営業一係", 3)] + NEST_BEFORE[3:]
    after = nested_numbers(after_tree)
    moved = [k for k in before if before[k] != after[k]]
    assert before["営業本部"] == [1, 10] and after["営業一係"] == [4, 5] and len(moved) == 5
    s = SVG(760, 560, "入れ子集合では区間の包含が親子関係になるが、営業一係を1個足すと既存5行すべての番号が動く")
    X = lambda n: 190 + 48 * (n - 1)

    def panel(y0, nums, tree, title, after_panel):
        s.text(24, y0 - 36, title, size=16, bold=True)
        for n in range(1, 13):
            s.text(X(n), y0 - 10, str(n), size=14, fill=SUB, anchor="middle")
        for k, (name, d) in enumerate(tree):
            a, b = nums[name]
            y = y0 + 28 * k
            new = name not in before
            ch = after_panel and not new
            col = FOCUS if new else (WARN if ch else MAIN)
            if ch:
                oa, ob = before[name]
                s.rect(X(oa) - 8, y, X(ob) - X(oa) + 16, 22, rx=5, stroke=MUTED, dash="4 3")
            s.rect(X(a) - 8, y, X(b) - X(a) + 16, 22, rx=5, fill=TINT[col], stroke=col,
                   sw=2 if (new or ch) else 1.4)
            s.text(176, y + 16, "　" * d + name, size=14, anchor="end", bold=new)

    panel(72, before, NEST_BEFORE, "挿入前", False)
    s.note(190, 244, "子孫 ＝ 区間に含まれる行（第一営業部は 2〜7）", color=MAIN)
    panel(330, after, after_tree, "営業一係を足した後（破線が元の位置）", True)
    s.note(190, 530, "1行足しただけで、既存の5行すべての番号が動く", color=WARN)
    return s


def org_tree_time():
    """5-3 departments の行を消さずに閉じると、改編の前後どちらの木も同じ表から出る。
    縦長 M 600x560。上に2本の木（改編前・後）、下に行の帯（時間 x = 250 + 月数*20）。
    """
    s = SVG(600, 580, "departments の行を消さずに閉じるだけで、改編前の木も改編後の木も同じ表から切り出せる")
    before = [("アホウドリ重工", 0), ("営業本部", 1), ("第一営業部", 2), ("第二営業部", 2),
              ("製造本部", 1), ("管理本部", 1), ("カモメ製作所", 2)]
    after = [("アホウドリ重工", 0), ("営業本部", 1), ("第一営業部", 2),
             ("製造本部", 1), ("カモメ事業部", 2), ("管理本部", 1)]

    def tree(x0, rows, title, changed):
        s.text(x0, 36, title, size=15, bold=True)
        for k, (name, d) in enumerate(rows):
            y = 64 + 28 * k
            if d:
                s.poly([(x0 + 18 * (d - 1) + 6, y - 22 if k else y), (x0 + 18 * (d - 1) + 6, y - 5),
                        (x0 + 18 * d, y - 5)], stroke=MUTED, sw=1.2)
            c = name in changed
            s.text(x0 + 18 * d + 4, y, name, size=15, bold=c, fill=FOCUS if c else INK)
    tree(24, before, "3月31日の木", {"第二営業部", "カモメ製作所"})
    tree(320, after, "4月1日の木", {"カモメ事業部"})
    s.line(24, 272, 576, 272, stroke=MUTED)
    s.text(24, 300, "departments の行（有効期間）", size=15, fill=SUB)
    X = lambda m: 250 + m * 20            # m: 2026-10 からの月数
    cut = X(6)
    rows = [("営業本部", "親：重工", 0, None, MAIN), ("第一営業部", "親：営業本部", 0, None, MAIN),
            ("第二営業部", "親：営業本部", 0, 6, MUTED), ("管理本部", "親：重工", 0, None, MAIN),
            ("カモメ製作所", "親：管理本部", 0, 6, MUTED), ("カモメ事業部", "親：製造本部", 6, None, MAIN)]
    for k, (name, par, a, b, col) in enumerate(rows):
        y = 318 + 36 * k
        s.text(24, y + 20, name, size=15, bold=col == MAIN and a > 0)
        s.text(236, y + 20, par, size=13, fill=SUB, anchor="end")
        band(s, X(a), X(b) if b else X(15), y, 28, "", col, open_end=b is None)
        if b:
            s.text(X(b) + 8, y + 19, "閉じた（消していない）", size=13, fill=SUB)
    s.line(cut, 306, cut, 540, stroke=FOCUS, sw=2.4, dash="6 4")
    s.text(cut, 562, "2027-04-01 改編", size=15, fill=FOCUS, anchor="middle", bold=True)
    return s


def person_employment():
    """6-1 番号1本だと前職の給与履歴が地続きになり、人と雇用を分けると雇用ごとに切れる。
    対照の2枚、横長 M 640x380。時間 x = 150 + (年-2016)*42。
    """
    X = lambda y: 120 + (y - 2016) * 40
    s = SVG(640, 380, "emp_id 1本では前職の給与履歴が今回の雇用と地続きに並ぶが、人と雇用を分けると雇用ごとに切れる")
    pay = [(2016.25, 2019.25, "旧給与1"), (2019.25, 2023.5, "旧給与2")]
    now = (2026.5, 2027.9, "今回")
    s.text(24, 40, "emp_id 1本", size=15, bold=True, fill=WARN)
    s.text(24, 80, "108", size=15)
    for a, b, lab in pay:
        band(s, X(a), X(b), 60, 30, lab, MUTED)
    band(s, X(now[0]), X(now[1]), 60, 30, now[2], MAIN)
    s.rect(X(2023.5), 60, X(2026.5) - X(2023.5), 30, fill=s.hatch(WARN), stroke="none")
    s.text((X(2023.5) + X(2026.5)) / 2, 112, "空白3年も同じ番号の履歴", size=14, fill=WARN, anchor="middle")
    s.text(24, 170, "人と雇用を分ける", size=15, bold=True, fill=MAIN)
    s.text(24, 210, "persons", size=15)
    band(s, X(2016.25), X(2027.9), 192, 28, "田中太郎（一生に1行）", MAIN)
    s.text(24, 260, "雇用 A", size=15)
    for a, b, lab in pay:
        band(s, X(a), X(b), 240, 30, lab, MUTED)
    s.text(24, 310, "雇用 B", size=15)
    band(s, X(now[0]), X(now[1]), 290, 30, now[2], MAIN)
    for y in range(2016, 2028, 2):
        s.text(X(y), 356, str(y), size=13, fill=SUB, anchor="middle")
    s.note(X(2023.5) + 6, 262, ["雇用ごとに切れる"], color=MAIN)
    return s


def frozen_payslip():
    """7-1 マスタから再計算すると答えが変わるが、凍結した明細は振込記録と一致したまま。
    横長 M 640x360。時間 x = 120 + 日数*2.6（2026-12-01 → 120）。
    """
    o = date(2026, 12, 1)
    X = lambda d: 120 + (d - o).days * 2.6
    paid, fix, feb = date(2026, 12, 25), date(2027, 1, 29), date(2027, 2, 25)
    assert 265000 - 263660 == 1340
    s = SVG(640, 360, "マスタからの再計算は1月末の訂正で答えが変わるが、凍結した明細は振込額のまま動かない")
    s.text(24, 34, "「12月の明細を出せ」への答え", size=15, fill=SUB)
    s.text(24, 88, "マスタから", size=15, bold=True)
    s.text(24, 108, "再計算", size=15, bold=True)
    band(s, X(paid), X(fix), 76, 34, "263,660", MUTED)
    band(s, X(fix), X(date(2027, 3, 20)), 76, 34, "265,000", WARN, open_end=True)
    s.text(X(fix) + 6, 130, "1月末の遡及訂正で答えが変わる", size=14, fill=WARN)
    s.text(24, 208, "凍結した", size=15, bold=True)
    s.text(24, 228, "明細", size=15, bold=True)
    band(s, X(paid), X(date(2027, 3, 20)), 196, 34, "263,660（振込額と一致）", MAIN, open_end=True)
    s.rect(X(feb) - 4, 250, 132, 30, rx=4, fill=TINT[FOCUS], stroke=FOCUS, sw=1.6)
    s.text(X(feb) + 62, 270, "2月明細に +1,340", size=14, anchor="middle", bold=True)
    s.line(24, 300, 616, 300, stroke=MUTED)
    for d, lab in ((paid, "12/25 振込"), (fix, "1月末 訂正"), (feb, "2/25")):
        s.line(X(d), 296, X(d), 304, stroke=MUTED)
        s.text(X(d), 324, lab, size=14, fill=SUB, anchor="middle")
    s.note(X(feb) + 146, 270, "訂正は追記する", color=FOCUS)
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig1-valid-period.svg": valid_period,
        OUT / "fig2-bitemporal.svg": bitemporal,
        OUT / "fig3-constraint-reach.svg": constraint_reach,
        OUT / "fig4-nested-sets.svg": nested_sets,
        OUT / "fig5-org-tree-time.svg": org_tree_time,
        OUT / "fig6-person-employment.svg": person_employment,
        OUT / "fig7-frozen-payslip.svg": frozen_payslip,
    }))
