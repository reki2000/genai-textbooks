#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/books/memory-chip/figs/*.svg を決定的に生成する。

この教材の他の図はChatGPTの画像生成で作った（記録は scripts/figs/memory-chip.md）。
本ファイルが受け持つのは、座標そのものが主張になっていて生成では再現できなかった図だけ。

配色の割り当て（この教材での意味づけ。作図規約の3系統に対応させる）
  青 #1f6fd0 : いま追いかけている信号・電荷・データの本流
  橙 #e07b1f : いま操作している場所（この図では未使用）
  赤 #cf3b2d : 破綻・無駄・成立しない構成（この図では未使用）
  灰 #8d8d8d : 動かない構造。基板、接点、筐体
形でも必ず区別する（実線／破線、塗り／白抜き）。
"""
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import MAIN, MUTED, SUB, TINT_MUTED, SVG  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "memory-chip" / "figs"


# ---------------------------------------------------------------- fig10
def fig10():
    """7-1 SIMMとDIMMの違いは両面実装ではなく、表裏の接点が同じ信号かどうか。

    上下で基板・接点の座標を完全に固定し、基板内部の結線だけを変える。
    SIMMは表裏を1本の縦線が貫いて短絡するので独立信号は4本、DIMMは表側と裏側が
    別の高さを走るので8本になる。読者が数えられることが、この図の主張そのもの。

    グリッド（先に宣言し、この座標だけを使う）
      基板    x = 150..690（幅540）、高さ 70
              パネルA(SIMM) y = 78..148 / パネルB(DIMM) y = 268..338
      接点    幅44・高さ14、中心 x = 250, 360, 470, 580（間隔110）
              A 表 y=64..78 / A 裏 y=148..162 / B 表 y=254..268 / B 裏 y=338..352
      配線    水平線の長さ 60（左向き）
              A: 縦線 x=中心, y=78..148（表裏を貫く）／水平線 y=113
              B: 表 縦線 x=中心,    y=268..291 ／水平線 y=291
                 裏 縦線 x=中心+14, y=315..338 ／水平線 y=315
              B の2本の水平線の間隔 24 = 基板高さの約1/3（表裏が別配線である余白）
      文字    A 34 題／58 表の接点／176 裏の接点・注記
              B 224 題／248 表の接点／366 裏の接点・注記
              基板ラベルは基板内の左下 x=162, y=138 / 328（信号線の左端 x=190 と離す）
    """
    BOARD_X0, BOARD_X1, BOARD_H = 150, 690, 70
    CONTACT_W, CONTACT_H, LEAD = 44, 14, 60
    CENTERS = (250, 360, 470, 580)
    BACK_DX = 14

    s = SVG(760, 400,
            "SIMMは表裏の接点が同じ信号へ短絡し、DIMMは表裏が別の信号線へ出る")

    def contact(cx, y):
        s.rect(cx - CONTACT_W / 2, y, CONTACT_W, CONTACT_H,
               fill=TINT_MUTED, stroke=MUTED, sw=1.3)

    def panel(title, ty, board_y, label_top, label_bottom, note, simm):
        top_y = board_y - CONTACT_H
        bot_y = board_y + BOARD_H
        s.text(BOARD_X0 - 90, ty, title, size=15, weight="700")
        s.rect(BOARD_X0, board_y, BOARD_X1 - BOARD_X0, BOARD_H,
               fill=TINT_MUTED, stroke=MUTED, sw=1.4)
        s.text(BOARD_X0 + 12, board_y + BOARD_H - 10, "基板", size=12, fill=SUB)
        for cx in CENTERS:
            contact(cx, top_y)
            contact(cx, bot_y)
        s.text(CENTERS[0], label_top, "表の接点", size=12, anchor="middle")
        s.text(CENTERS[0], label_bottom, "裏の接点", size=12, anchor="middle")
        s.text(BOARD_X1, label_bottom, note, size=13, fill=MAIN,
               anchor="end", weight="700")

        for cx in CENTERS:
            if simm:
                # 表裏を1本の縦線が貫く。その中点から1本だけ信号が出る
                mid = board_y + BOARD_H / 2
                s.line(cx, board_y, cx, bot_y, stroke=MAIN, sw=2.4, role="connector")
                s.line(cx - LEAD, mid, cx, mid, stroke=MAIN, sw=2.4, role="connector")
            else:
                # 表と裏で縦線の x も水平線の y も分ける。両者は決して接しない
                y_front = board_y + BOARD_H / 3
                y_back = bot_y - BOARD_H / 3
                s.line(cx, board_y, cx, y_front, stroke=MAIN, sw=2.4, role="connector")
                s.line(cx - LEAD, y_front, cx, y_front, stroke=MAIN, sw=2.4,
                       role="connector")
                bx = cx + BACK_DX
                s.line(bx, y_back, bx, bot_y, stroke=MAIN, sw=2.4, role="connector")
                s.line(bx - LEAD, y_back, bx, y_back, stroke=MAIN, sw=2.4,
                       role="connector")

    panel("SIMM", 34, 78, 58, 176, "表裏が同じ信号", simm=True)
    panel("DIMM", 224, 268, 248, 366, "表裏が別の信号", simm=False)
    return s


FIGS = {
    "fig10-simm-vs-dimm": fig10,
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
