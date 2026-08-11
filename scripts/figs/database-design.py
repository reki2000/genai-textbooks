#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/database-design/figs/*.svg を決定的に生成する。

配色の割り当て（この教材での意味づけ。作図規約の3系統に対応させる）
  青 #1f6fd0 : いま有効な事実・宣言的制約が届く範囲・分離後の正しい形
  赤 #cf3b2d : 矛盾・破綻・更新の波及（注意喚起）
  灰 #8d8d8d : 終わった事実・過去の認識・非該当（破線の輪郭）
  橙 #e07b1f : 照会（外から与える問い）
形でも必ず区別する（実線／破線、塗り／白抜き、×印）。
"""
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import (  # noqa: E402
    SVG, INK, SUB, ACCENT, E_BLUE, H_RED, FIX_GRAY, N_TINT, P_TINT, DEP_TINT,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "database-design" / "figs"


# ---------------------------------------------------------------- fig1
def fig1():
    """3-4 有効期間：半開区間で隣接させる／旧行を閉じ忘れる。

    同じ3つの事実（250,000 / 265,000 / 270,000）を上下で描き分ける。
    変えるのは「旧行を閉じたか」だけで、時間軸の座標はパネル間で固定する。

    グリッド（先に宣言し、この座標だけを使う）
      時間軸  x = 70 + 月数*26.25   (2025-04 = 0 か月 → 70、2027-04 = 24 か月 → 700)
              2026-04 → 385 / 2026-09 → 516 / 照会 2026-12 → 595 / 無期限の端 → 690
      y  32 照会ラベル / 58 パネルA名・境界注記 / 72..106 帯（2段書き）/ 132 結果
         162 重なり注記 / 160 パネルB名 / 174..208 帯1段目 / 216..250 帯2段目 / 280 結果
         310 日付軸 / 330 目盛ラベル
      色  灰＝終端が閉じた行（終わった事実） / 青＝終端が infinity の行
    """
    def tx(month):
        return 70 + month * 26.25

    s = SVG(760, 356,
            "半開区間で隣接させれば照会は1行、旧行を閉じ忘れると同じ時点に2行が当たる")
    x0, x_apr, x_sep, x_q, x_inf = tx(0), tx(12), tx(17), tx(20), tx(23.62)

    def band(x1, x2, y, amount, span, open_end):
        fill, stroke = ((N_TINT, E_BLUE) if open_end else (DEP_TINT, FIX_GRAY))
        s.rect(x1, y, x2 - x1, 34, fill=fill, stroke=stroke, sw=1.6 if open_end else 1.3)
        s.text((x1 + x2) / 2, y + 16, amount, size=13, anchor="middle",
               fill=E_BLUE if open_end else INK, weight="700" if open_end else "400")
        s.text((x1 + x2) / 2, y + 29, span, size=10, fill=SUB, anchor="middle")
        if open_end:
            s.arrow(x2, y + 17, x2 + 16, y + 17, stroke=E_BLUE, sw=1.6)

    # 照会（橙）: 2パネルを同じ日付で貫く。結果ラベルの位置で線を切る
    s.text(x_q, 32, "照会：2026-12-01 の給与は", size=13, fill=ACCENT,
           anchor="middle", weight="700")
    s.line(x_q, 40, x_q, 126, stroke=ACCENT, sw=1.6, dash="6 4")
    s.line(x_q, 154, x_q, 266, stroke=ACCENT, sw=1.6, dash="6 4")

    # --- パネルA：閉じてから次を足す
    s.text(70, 58, "A　旧行を閉じて隣接させる", size=13, weight="700")
    s.text(x_apr, 58, "終点＝次の始点", size=11, fill=SUB, anchor="middle")
    s.line(x_apr, 64, x_apr, 72, stroke=SUB, sw=1)
    band(x0, x_apr, 72, "250,000円", "[2023-10-01, 2026-04-01)", False)
    band(x_apr, x_sep, 72, "265,000円", "[2026-04-01, 2026-09-01)", False)
    band(x_sep, x_inf, 72, "270,000円", "[2026-09-01, infinity)", True)
    s.text(x_q, 140, "当たる行 1本", size=13, anchor="middle", fill=E_BLUE,
           weight="700")

    # --- パネルB：旧行を閉じ忘れる
    s.text(70, 160, "B　旧行を閉じ忘れる", size=13, weight="700")
    s.text(x_sep + 10, 160, "期間が重なる", size=12, fill=H_RED, weight="700")
    band(x0, x_apr, 174, "250,000円", "[2023-10-01, 2026-04-01)", False)
    band(x_apr, x_inf, 174, "265,000円", "[2026-04-01, infinity)", True)
    band(x_sep, x_inf, 216, "270,000円", "[2026-09-01, infinity)", True)
    s.rect(x_sep, 168, x_inf - x_sep, 88, fill="none", stroke=H_RED, sw=1.8,
           dash="5 4")
    s.cross(x_q - 82, 283, r=6, stroke=H_RED, sw=2.2)
    s.text(x_q, 288, "当たる行 2本（矛盾）", size=13, fill=H_RED,
           anchor="middle", weight="700")

    # --- 共有の日付軸
    s.line(x0, 310, 706, 310, stroke=INK, sw=1.2)
    for m, lab in ((0, "2025-04"), (12, "2026-04"), (17, "2026-09"), (24, "2027-04")):
        s.line(tx(m), 306, tx(m), 314, stroke=INK, sw=1.2)
        s.text(tx(m), 330, lab, size=11, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- fig2
def fig2():
    """3-5 バイテンポラル：同じ5月分でも、いつ聞いたかで答えが変わる。

    グリッド
      x（有効時間）  x = 120 + 月数*14.6  (2023-10 = 0 → 120、2027-01 = 39 → 690)
                     2026-04 → 558 / 照会する 2026-05 → 578
      y（システム時間、上ほど新しい） y = 340 - 月数*17.9 (2026-01 = 0 → 340)
                     2026-05-25 → 254 / 2026-06-25 → 236 / 現在 2026-12 → 144
      枠  R1 250,000（6/25以前の認識） x 120..690, y 236..340
          R2 250,000（現在の認識・4/1まで） x 120..558, y 90..236
          R3 265,000（現在の認識・4/1以降） x 558..690, y 90..236
    """
    s = SVG(760, 400,
            "有効時間とシステム時間の2軸。同じ5月分の給与でも、いつ聞いたかで答えが変わる")
    L, R, B, T = 120, 690, 340, 90
    x_apr, x_q = 558, 578
    y_know, y_may, y_now = 236, 254, 144

    # 認識の領域。問いの点が落ちた領域のラベルがそのまま答えになる
    s.rect(L, y_know, R - L, B - y_know, fill=DEP_TINT, stroke=FIX_GRAY,
           sw=1.3, dash="5 4")
    s.rect(L, T, x_apr - L, y_know - T, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.3)
    s.rect(x_apr, T, R - x_apr, y_know - T, fill=N_TINT, stroke=E_BLUE, sw=1.6)
    s.text(480, 290, "250,000円", size=13, anchor="middle")
    s.text(480, 306, "6月25日以前の認識", size=11, fill=SUB, anchor="middle")
    s.text((L + x_apr) / 2, 170, "250,000円", size=13, anchor="middle")
    s.text((x_apr + R) / 2, 170, "265,000円", size=13, anchor="middle",
           fill=E_BLUE, weight="700")

    # DBが知った瞬間
    s.line(L, y_know, R, y_know, stroke=INK, sw=1.6)
    s.text(L - 8, y_know - 4, "2026-06-25", size=11, fill=INK, anchor="end",
           weight="700")
    s.text(L - 8, y_know + 12, "遡及を知る", size=11, fill=SUB, anchor="end")

    # 照会（橙）。2つの点は同じ有効時間、違うシステム時間
    s.line(x_q, T - 10, x_q, B + 14, stroke=ACCENT, sw=1.6, dash="6 4")
    s.text(x_q, 386, "照会：2026年5月分の給与", size=12, fill=ACCENT,
           anchor="middle", weight="700")
    s.circle(x_q, y_may, 5.5, fill=ACCENT, stroke=ACCENT, sw=0)
    s.text(x_q + 12, y_may + 4, "5月25日に聞く", size=12, fill=INK)
    s.circle(x_q, y_now, 5.5, fill=ACCENT, stroke=ACCENT, sw=0)
    s.text(x_q + 12, y_now + 4, "いま聞く", size=12, fill=INK)

    # 軸
    s.arrow(L, B, 710, B, stroke=INK, sw=1.4)
    s.arrow(L, B, L, T - 22, stroke=INK, sw=1.4)
    s.text(128, T - 28, "システム時間（DBがそう信じた期間）", size=12, fill=SUB)
    s.text(L, 386, "有効時間（現実に真実だった期間）", size=12, fill=SUB)
    s.arrow(R, 288, R + 16, 288, stroke=FIX_GRAY, sw=1.4)
    s.arrow(R, 163, R + 16, 163, stroke=E_BLUE, sw=1.6)
    for m, lab in ((6, "2024-04"), (18, "2025-04"), (30, "2026-04-01")):
        x = 120 + m * 14.6
        s.line(x, B, x, B + 5, stroke=INK, sw=1.2)
        s.text(x, B + 20, lab, size=11, fill=SUB, anchor="middle")
    s.line(L - 5, y_now, L, y_now, stroke=INK, sw=1.2)
    s.text(L - 8, y_now + 4, "現在", size=11, fill=SUB, anchor="end")
    return s


# ---------------------------------------------------------------- fig3
def fig3():
    """5-2 宣言的制約の射程：1回の検査が見る範囲と、その限界。

    グリッド
      射程の目盛 x = 230 + 段*88 （段1..5 → 318, 406, 494, 582, 670）
      目盛ラベル y = 44（段1,3,5） / 62（段2,4）  ※交互にずらして重なりを避ける
      帯   y = 100,136,172,208,244（届く・青） / 282,318（届かない・灰破線）
      限界線 x = 596（外部キーの端 582 と、届かない側の帯の途中）
    """
    def rx(step):
        return 230 + step * 88.0

    s = SVG(760, 380,
            "宣言的制約は1回の検査で見る範囲が広がるほど強く、行またぎ・経路またぎには届かない")
    x0, limit = 230, 596

    for step, lab, y in ((1, "1行の中", 44), (2, "同じ表の行どうし", 62),
                         (3, "行の組（期間の重なり）", 44), (4, "2つの表のあいだ", 62),
                         (5, "表全体・経路全体", 44)):
        s.text(rx(step), y, lab, size=11, fill=SUB, anchor="middle")
        s.line(rx(step), 70, rx(step), 76, stroke=SUB, sw=1)
    s.arrow(x0, 76, 706, 76, stroke=SUB, sw=1.2)

    rows = (
        (100, 1, "CHECK・NOT NULL", None),
        (136, 2, "主キー・UNIQUE", None),
        (172, 2, "部分一意インデックス", "条件を満たす行だけ"),
        (208, 3, "排他制約", None),
        (244, 4, "外部キー", None),
    )
    for y, step, name, note in rows:
        s.rect(x0, y - 13, rx(step) - x0, 26, fill=N_TINT, stroke=E_BLUE, sw=1.6)
        s.text(222, y + 5, name, size=13, anchor="end")
        if note:
            s.text(rx(step) + 10, y + 5, note, size=11, fill=SUB)

    for y, name in ((282, "行またぎの集計（比率の合計）"), (318, "経路またぎ（木に円環がない）")):
        s.rect(x0, y - 13, rx(5) - x0, 26, fill=DEP_TINT, stroke=FIX_GRAY,
               sw=1.4, dash="5 4")
        s.text(222, y + 5, name, size=13, fill=SUB, anchor="end")
        s.cross(limit, y, r=7, stroke=H_RED, sw=2.4)

    s.line(limit, 88, limit, 340, stroke=H_RED, sw=1.8, dash="6 4")
    s.text(limit, 358, "宣言的制約の限界", size=12, fill=H_RED, anchor="middle",
           weight="700")
    return s


# ---------------------------------------------------------------- fig4
def fig4():
    """5-2 入れ子集合：区間の包含が親子関係。その代金は挿入時の番号の書き換え。

    区間は木を深さ優先で辿った通し番号（本文の営業本部の部分木から計算）
      挿入前 営業本部[1,10] 第一営業部[2,7] 首都圏[3,4] 東日本[5,6] 第二営業部[8,9]
      挿入後 営業本部[1,12] 第一営業部[2,9] 首都圏[3,6] 営業一係[4,5]
             東日本[7,8] 第二営業部[10,11]
    グリッド
      数直線 x = 80 + (番号-1)*50  (1 → 80、12 → 630)  ※上下のパネルで共通
      A y=70,100,130（深さ0,1,2）/ 数直線 165 / 目盛 182
      B y=222,252,282,312（深さ0..3）/ 数直線 345 / 目盛 362
    """
    def nx(n):
        return 80 + (n - 1) * 50.0

    s = SVG(760, 464,
            "入れ子集合は木を数直線の区間に写す。子孫の照会は包含1発だが、1行の挿入で既存の全行の番号が動く")

    def span(lft, rgt, y, label, mode):
        """y はラベルのベースライン。帯はその 6px 下から 20px。"""
        fill, stroke = {"plain": (DEP_TINT, FIX_GRAY),
                        "moved": (P_TINT, H_RED),
                        "new": (N_TINT, E_BLUE)}[mode]
        s.text(nx(lft) + 2, y, label, size=11,
               fill=H_RED if mode == "moved" else INK,
               weight="700" if mode == "new" else "400")
        s.rect(nx(lft), y + 6, nx(rgt) - nx(lft), 20, fill=fill, stroke=stroke,
               sw=1.6, dash="5 4" if mode == "moved" else None)

    def numline(y, last):
        s.line(nx(1), y, nx(last), y, stroke=INK, sw=1.2)
        for n in range(1, last + 1):
            s.line(nx(n), y, nx(n), y + 5, stroke=INK, sw=1.2)
            s.text(nx(n), y + 22, str(n), size=11, fill=SUB, anchor="middle")

    # --- A 挿入前
    s.text(80, 50, "A　挿入前　区間に含まれる＝子孫", size=13, weight="700")
    span(1, 10, 68, "営業本部 [1,10]", "plain")
    span(2, 7, 108, "第一営業部 [2,7]", "plain")
    span(8, 9, 108, "第二営業部 [8,9]", "plain")
    span(3, 4, 148, "首都圏営業課 [3,4]", "plain")
    span(5, 6, 148, "東日本営業課 [5,6]", "plain")
    numline(190, 10)

    # --- B 挿入後（営業一係を首都圏営業課の下に1個足す）
    s.text(80, 250, "B　挿入後　営業一係を1個足す", size=13, weight="700")
    s.text(390, 250, "既存5行すべての番号が動く", size=12, fill=H_RED, weight="700")
    span(1, 12, 268, "営業本部 [1,12]", "moved")
    span(2, 9, 308, "第一営業部 [2,9]", "moved")
    span(10, 11, 308, "第二営業部 [10,11]", "moved")
    span(3, 6, 348, "首都圏営業課 [3,6]", "moved")
    span(7, 8, 348, "東日本営業課 [7,8]", "moved")
    span(4, 5, 388, "営業一係 [4,5]", "new")
    numline(430, 12)
    return s


# ---------------------------------------------------------------- fig5
def fig5():
    """5-3 木 × 時間：行に有効期間を持たせると、時点で切るたびに当時の木が出る。

    グリッド
      左＝改編前の木（x0=70）／右＝改編後の木（x0=400）。行は y = 86 + i*26
      仕切り x = 380 は、下の時間軸では 2027-04-01 にあたる
      時間軸 x = 60 + 月数*26.67 (2026-04 → 60、2027-04 → 380、2028-04 → 700)
      帯 y = 296, 328, 360, 392 / 軸 424 / 目盛 442
    """
    def tx(month):
        return 60 + month * 26.667

    s = SVG(760, 460,
            "部署の行に有効期間を持たせると、改編前の木と改編後の木が同じ表から切り出せる")
    IND = (0, 16, 34)

    def tree(x0, rows, links):
        for i, (d, label, mode) in enumerate(rows):
            y = 86 + i * 26
            col = {"plain": INK, "gone": FIX_GRAY, "moved": H_RED}[mode]
            s.text(x0 + IND[d], y, label, size=12, fill=col,
                   weight="700" if mode == "moved" else "400")
            if mode == "gone":
                s.line(x0 + IND[d] - 2, y - 5, x0 + IND[d] + len(label) * 12 + 2,
                       y - 5, stroke=FIX_GRAY, sw=1.2, role="glyph")
        for parent, children in links:
            xv = x0 + IND[rows[parent][0]] + 8
            for c in children:
                yc = 86 + c * 26
                s.line(xv, yc - 4, x0 + IND[rows[c][0]] - 4, yc - 4,
                       stroke=SUB, sw=1.1)
            s.line(xv, 86 + parent * 26 + 6, xv, 86 + max(children) * 26 - 4,
                   stroke=SUB, sw=1.1)

    s.text(70, 62, "2027年3月31日時点の木", size=13, weight="700")
    tree(70, [(0, "アホウドリ重工", "plain"), (1, "営業本部", "plain"),
              (2, "第一営業部", "plain"), (2, "第二営業部", "plain"),
              (1, "製造本部", "plain"), (1, "管理本部", "plain"),
              (2, "カモメ事業部", "plain")],
         [(0, [1, 4, 5]), (1, [2, 3]), (5, [6])])

    s.text(400, 62, "2027年4月1日時点の木", size=13, weight="700")
    tree(400, [(0, "アホウドリ重工", "plain"), (1, "営業本部", "plain"),
               (2, "第一営業部", "plain"), (2, "第二営業部", "gone"),
               (1, "製造本部", "plain"), (2, "カモメ事業部", "moved"),
               (1, "管理本部", "plain")],
         [(0, [1, 4, 6]), (1, [2, 3]), (4, [5])])

    # 仕切り＝改編日
    s.text(380, 44, "2027-04-01　組織改編", size=13, anchor="middle", weight="700")
    s.line(380, 52, 380, 424, stroke=INK, sw=1.4, dash="6 4")

    # departments の行（有効期間つき）
    def band(x1, x2, y, label, live):
        fill, stroke = ((N_TINT, E_BLUE) if live else (DEP_TINT, FIX_GRAY))
        s.rect(x1, y, x2 - x1, 26, fill=fill, stroke=stroke, sw=1.5)
        s.text(x1 + 8, y + 17, label, size=12,
               fill=E_BLUE if live else SUB)
        if live:
            s.arrow(x2, y + 13, x2 + 16, y + 13, stroke=E_BLUE, sw=1.6)

    band(tx(0), tx(24), 296, "変更なし：営業本部・製造本部・管理本部", True)
    band(tx(0), tx(12), 328, "第二営業部（親＝営業本部）", False)
    band(tx(0), tx(12), 360, "カモメ事業部（親＝管理本部）", False)
    band(tx(12), tx(24), 392, "カモメ事業部（親＝製造本部）", True)

    s.line(tx(0), 424, 722, 424, stroke=INK, sw=1.2)
    for m, lab in ((0, "2026-04"), (12, "2027-04"), (24, "2028-04")):
        s.line(tx(m), 420, tx(m), 428, stroke=INK, sw=1.2)
        s.text(tx(m), 444, lab, size=11, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- fig6
def fig6():
    """6-1 田中の再入社：番号1本で背負う形と、人と雇用に分けた形。

    グリッド
      時間軸 x = 70 + 年数*52.5 (2016-04 → 70、2028-04 → 700)
             2023-06 退職 → 446 / 2026-07 再入社 → 608
      A y=68..96（在籍の行）/ 106..126（給与履歴）/ 154 注記
      B y=196..222（persons）/ 232..258（employments）/ 268..288（salaries）
      軸 330 / 目盛 348
    """
    def tx(year):
        return 70 + year * 52.5

    s = SVG(760, 376,
            "番号1本では前職と今回の雇用が地続きになり、人と雇用に分けると雇用ごとに切れる")
    x_in, x_out, x_re, x_end = tx(0), tx(7.17), tx(10.25), tx(12)

    # --- A 番号1本
    s.text(70, 54, "A　emp_id 1本で人も雇用も背負う", size=13, weight="700")
    s.rect(x_in, 68, x_end - x_in, 28, fill=N_TINT, stroke=E_BLUE, sw=1.6)
    s.text(x_in + 8, 86, "emp_id 108（田中）", size=12, fill=E_BLUE, weight="700")
    s.rect(x_in, 106, x_out - x_in, 20, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.3)
    s.rect(x_re, 106, x_end - x_re, 20, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.3)
    s.text(x_in + 8, 120, "給与履歴", size=11, fill=SUB)
    s.rect(x_out, 62, x_re - x_out, 70, fill="none", stroke=FIX_GRAY, sw=1.3,
           dash="4 4")
    s.text((x_out + x_re) / 2, 58, "3年の空白", size=11, fill=SUB, anchor="middle")
    s.arrow(x_re - 4, 116, x_out + 6, 116, stroke=ACCENT, sw=2.0)
    s.text((x_out + x_re) / 2, 148, "『直近の昇給』が前職に届く", size=12,
           fill=ACCENT, anchor="middle", weight="700")
    s.cross(x_in + 6, 153, r=6, stroke=H_RED, sw=2.2)
    s.text(x_in + 18, 158, "入社日も勤続も列が1つしかない", size=12, fill=H_RED)

    # --- B 人と雇用を分ける
    s.text(70, 182, "B　人と雇用に分ける", size=13, weight="700")
    s.rect(x_in, 196, x_end - x_in, 26, fill=N_TINT, stroke=E_BLUE, sw=1.6)
    s.text(x_in + 8, 213, "persons　person_id=7（田中太郎）", size=12,
           fill=E_BLUE, weight="700")
    s.arrow(x_end, 209, x_end + 16, 209, stroke=E_BLUE, sw=1.6)
    s.rect(x_in, 232, x_out - x_in, 26, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.5)
    s.text(x_in + 8, 249, "employments　雇用1（終了）", size=12, fill=SUB)
    s.rect(x_re, 232, x_end - x_re, 26, fill=N_TINT, stroke=E_BLUE, sw=1.6)
    s.text(x_re + 8, 249, "雇用2", size=12, fill=E_BLUE, weight="700")
    s.arrow(x_end, 245, x_end + 16, 245, stroke=E_BLUE, sw=1.6)
    s.rect(x_in, 268, x_out - x_in, 20, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.3)
    s.rect(x_re, 268, x_end - x_re, 20, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.3)
    s.text(x_in + 8, 282, "給与履歴", size=11, fill=SUB)
    s.text(x_in, 308, "入社日・勤続・社会保険は雇用ごとに切れる", size=12, fill=INK)

    # --- 共有の日付軸
    s.line(x_in, 330, 722, 330, stroke=INK, sw=1.2)
    for yr, lab in ((0, "2016-04 入社"), (4, "2020-04"), (7.17, "2023-06 退職"),
                    (10.25, "2026-07 再入社")):
        s.line(tx(yr), 326, tx(yr), 334, stroke=INK, sw=1.2)
        s.text(tx(yr), 348, lab, size=11, fill=SUB, anchor="middle")
    return s


# ---------------------------------------------------------------- fig7
def fig7():
    """7-1 確定の凍結：マスタの答えは後から変わり、明細の答えは変わらない。

    グリッド
      暦の軸 x = 80 + 月数*110 (2026-11 → 80、2027-03 → 520)
             12/25 の支給 → 272 / 1月末の訂正 → 410 / 2月の明細 → 415..600
      マスタの帯 y = 72..102 / 明細の箱 y = 156..212 / 答えの欄 x = 620..750
      軸 268 / 目盛 286
    """
    def tx(month):
        return 80 + month * 110.0

    s = SVG(760, 320,
            "マスタは訂正で答えが変わり、凍結した明細は振込記録と一致したまま動かない")
    x_pay, x_fix, x_feb = 272, tx(3), 415

    s.text(685, 44, "問い：12月の明細を出せ", size=12, anchor="middle",
           weight="700")

    s.text(80, 54, "マスタが答える『12月分の通勤手当』", size=12, weight="700")
    s.rect(tx(0), 72, x_fix - tx(0), 30, fill=DEP_TINT, stroke=FIX_GRAY, sw=1.4)
    s.text(tx(0) + 8, 92, "訂正前の額", size=12, fill=SUB)
    s.rect(x_fix, 72, 600 - x_fix, 30, fill=P_TINT, stroke=H_RED, sw=1.6)
    s.text(x_fix + 8, 92, "訂正後の額（+1,340円）", size=12, fill=H_RED)
    s.text(x_fix, 64, "1月末に遡及訂正", size=11, fill=H_RED, anchor="middle")

    s.text(80, 138, "確定した明細（凍結：二度と更新しない）", size=12, weight="700")
    s.rect(x_pay - 50, 156, 130, 56, fill=N_TINT, stroke=E_BLUE, sw=1.8)
    s.text(x_pay + 15, 176, "2026年12月の明細", size=11, fill=E_BLUE,
           anchor="middle", weight="700")
    s.text(x_pay + 15, 194, "手取り 263,660円", size=11, anchor="middle")
    s.rect(x_feb, 156, 185, 56, fill=N_TINT, stroke=E_BLUE, sw=1.8)
    s.text(x_feb + 92, 176, "2027年2月の明細", size=11, fill=E_BLUE,
           anchor="middle", weight="700")
    s.text(x_feb + 92, 194, "12月分 通勤手当差額 +1,340円", size=11, anchor="middle")

    # 同じ問いへの2つの答え方
    s.arrow(600, 87, 616, 87, stroke=SUB, sw=1.6)
    s.rect(620, 72, 130, 30, fill=P_TINT, stroke=H_RED, sw=1.6)
    s.text(685, 92, "再計算はズレる", size=11, fill=H_RED, anchor="middle",
           weight="700")
    s.arrow(600, 184, 616, 184, stroke=SUB, sw=1.6)
    s.rect(620, 169, 130, 30, fill=N_TINT, stroke=E_BLUE, sw=1.6)
    s.text(685, 189, "振込記録と一致", size=11, fill=E_BLUE, anchor="middle",
           weight="700")

    s.line(tx(0), 268, 606, 268, stroke=INK, sw=1.2)
    for m, lab in ((1, "2026-12"), (2, "2027-01"), (3, "2027-02"), (4, "2027-03")):
        s.line(tx(m), 264, tx(m), 272, stroke=INK, sw=1.2)
        s.text(tx(m), 286, lab, size=11, fill=SUB, anchor="middle")
    s.line(x_pay, 212, x_pay, 264, stroke=SUB, sw=1.1, dash="4 3")
    s.text(x_pay - 6, 240, "12月25日 振込", size=11, fill=SUB, anchor="end")
    s.line(x_feb + 92, 212, x_feb + 92, 264, stroke=SUB, sw=1.1, dash="4 3")
    s.text(x_feb + 98, 240, "2月25日 支給", size=11, fill=SUB)
    return s


FIGS = {
    "fig1-valid-period": fig1,
    "fig2-bitemporal": fig2,
    "fig3-constraint-reach": fig3,
    "fig4-nested-sets": fig4,
    "fig5-org-tree-time": fig5,
    "fig6-person-employment": fig6,
    "fig7-frozen-payslip": fig7,
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
