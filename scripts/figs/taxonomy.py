#!/usr/bin/env python3
"""taxonomy の図。

色：青=本当のまとまり（単系統群、受け継いだ骨、交配できるつながり）／橙=その図で見る1か所／
赤=やる夫の誤ったまとめ方（穴あきの棚、完全な時計）。灰は外群・補助・背景。
系統樹は根を左、枝先を右に描く（遺伝子の木と種の木の図だけは時間を上から下）。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, WARN, MUTED, INK, SUB, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/taxonomy/figs"


def clade(s, x, ys, xs, stroke=INK, sw=2):
    """内部節 x から子（枝先の x, y）へ、縦線1本と横線を引く。子の位置を返す節の y は中央。"""
    s.line(x, min(ys), x, max(ys), stroke=stroke, sw=sw)
    for cx, cy in zip(xs, ys):
        s.line(x, cy, cx, cy, stroke=stroke, sw=sw)
    return (min(ys) + max(ys)) / 2


def ring():
    """2-3 隣どうしはみな交配できるのに、輪の両端だけはできない。縦長 M 480x550（模式の地図）。

    谷：中心 (240, 305)、横 100・縦 160 の楕円。集団は外側の楕円（横 175、縦 205）の上に並べる。
    北の祖先 90°、東回り 60→-70°、西回り 120→250°。南で出会う両端の間は赤の破線。
    """
    cx, cy, rx, ry = 240, 305, 175, 205
    P = lambda d: (cx + rx * math.cos(math.radians(d)), cy - ry * math.sin(math.radians(d)))
    east = [90, 58, 26, -6, -38, -68]
    west = [90, 122, 154, 186, 218, 248]
    s = SVG(480, 550, "谷を囲む輪の上では隣どうしの集団はみな交配できるが、南で出会う両端の集団はほとんど交配しない")
    s.poly([(cx + 100 * math.cos(t), cy - 160 * math.sin(t)) for t in (2 * math.pi * k / 80 for k in range(80))],
           closed=True, fill=TINT[FOCUS], stroke=MUTED, sw=1)
    s.text(cx, cy - 6, "乾いた谷", size=16, anchor="middle", bold=True)
    s.text(cx, cy + 16, "（住めない）", size=14, fill=SUB, anchor="middle")
    for arm in (east, west):
        for a, b in zip(arm, arm[1:]):
            s.line(*P(a), *P(b), stroke=MAIN, sw=4)
    for d in east[1:] + west[1:]:
        s.circle(*P(d), 9, fill=MAIN, stroke="#ffffff", sw=2)
    s.circle(*P(90), 11, fill=INK, stroke="#ffffff", sw=2)
    s.text(P(90)[0], P(90)[1] - 18, "北の祖先", size=15, anchor="middle", bold=True)
    s.text(P(26)[0] + 16, P(26)[1], "東回り", size=15, fill=MAIN, bold=True)
    s.text(P(154)[0] - 16, P(154)[1], "西回り", size=15, fill=MAIN, bold=True, anchor="end")
    a, z = P(-68), P(248)
    s.line(*a, *z, stroke=WARN, sw=3, dash="6 5")
    for p, lab in ((a, "A"), (z, "Z")):
        s.circle(*p, 12, fill=FOCUS, stroke="#ffffff", sw=2)
        s.text(p[0], p[1] + 5, lab, size=15, fill="#ffffff", anchor="middle", bold=True)
    s.text(cx, a[1] + 34, "ほとんど交配しない", size=15, fill=WARN, anchor="middle", bold=True)
    s.text(456, 536, "模式図", size=14, fill=SUB, anchor="end")
    s.note(24, 40, ["隣どうしはつながるのに", "両端はつながらない"])
    return s


def wing():
    """4-1 骨の並びは同じ（相同）、飛ぶ面の作り方は別々（相似）。対照の2枚 M 640x330（模式）。

    左：コウモリ（肩 (40,150)）、右：ハト（肩 (360,150)）。骨は同じ色・同じ順に描く。
    上腕骨 → 前腕の2本 → 手首と指。コウモリは指の間の膜、ハトは腕に並ぶ羽毛。
    """
    s = SVG(640, 330, "コウモリとハトの翼は、肩から指先へ骨の並びが同じで、飛ぶ面の作り方だけが違う")
    # コウモリ
    sh, el, wr = (40, 150), (120, 112), (220, 96)
    tips = [(250, 70), (300, 44), (310, 140), (268, 220), (196, 250)]
    s.poly([sh, el, wr, tips[1], tips[2], tips[3], tips[4], (60, 250)], closed=True, fill=TINT[MUTED],
           stroke=MUTED, sw=1.4, smooth=False)
    s.line(*sh, *el, stroke=MAIN, sw=6)
    s.line(el[0], el[1] - 3, wr[0], wr[1] - 3, stroke=MAIN, sw=3)
    s.line(el[0], el[1] + 3, wr[0], wr[1] + 3, stroke=MAIN, sw=3)
    for t in tips:
        s.line(*wr, *t, stroke=MAIN, sw=2.4)
    s.text(150, 290, "コウモリ：指の間に膜", size=16, anchor="middle", bold=True)
    # ハト
    sh2, el2, wr2, tip2 = (360, 150), (430, 124), (520, 116), (590, 108)
    for k in range(10):
        base = (430 + k * 16, 124 - k * 1.3) if k < 6 else (530 + (k - 6) * 18, 114 - (k - 6) * 2)
        L = 90 + (k - 5) * 8 if k >= 5 else 80
        ang = math.radians(100 - k * 5)
        tip = (base[0] + L * math.cos(ang) * 0.6 + 12, base[1] + L * math.sin(ang))
        s.poly([base, (base[0] + 6, base[1] + L * 0.5), tip, (base[0] - 4, base[1] + L * 0.4)], closed=True,
               fill="#ffffff", stroke=MUTED, sw=1.2, smooth=True)
    s.line(*sh2, *el2, stroke=MAIN, sw=6)
    s.line(el2[0], el2[1] - 3, wr2[0], wr2[1] - 3, stroke=MAIN, sw=3)
    s.line(el2[0], el2[1] + 3, wr2[0], wr2[1] + 3, stroke=MAIN, sw=3)
    s.line(*wr2, *tip2, stroke=MAIN, sw=3)
    s.text(470, 290, "ハト：腕に並ぶ羽毛", size=16, anchor="middle", bold=True)
    for (x, y, lab) in ((sh[0] + 20, sh[1] - 26, "上腕骨"), (170, 76, "前腕の2本"), (282, 176, "指")):
        s.text(x, y, lab, size=14, fill=MAIN, anchor="middle", halo=True)
    for (x, y, lab) in ((392, 124, "上腕骨"), (476, 104, "前腕の2本"), (560, 96, "手首と指")):
        s.text(x, y, lab, size=14, fill=MAIN, anchor="middle", halo=True)
    s.text(616, 322, "模式図", size=14, fill=SUB, anchor="end")
    s.note(24, 36, "青の骨の並びは同じ（相同）、面は別々の発明（相似）", size=15)
    return s


def paraphyly():
    """4-2 爬虫類の棚は、鳥を抜いた穴あきのまとまり。横長 M 560x300。

    枝先 x 330、y = 70, 130, 190, 250（トカゲ・ヘビ、カメ、ワニ、鳥）。
    節 x：根 60、（カメ・ワニ・鳥）140、（ワニ・鳥）230。
    """
    s = SVG(560, 300, "ワニは鳥とトカゲより近いので、鳥を抜いた爬虫類の棚は祖先の子孫の一部だけの穴あきグループになる")
    tips = [(330, 70, "トカゲ・ヘビ"), (330, 130, "カメ"), (330, 190, "ワニ"), (330, 250, "鳥")]
    s.rect(300, 44, 240, 234, rx=10, fill=TINT[MAIN], stroke=MAIN, sw=2)
    s.text(530, 274 - 8, "単系統群", size=14, fill=MAIN, anchor="end", bold=True)
    s.rect(308, 50, 150, 164, rx=8, stroke=WARN, sw=2.4, dash="6 4")
    s.text(466, 134, ["爬虫類", "の棚"], size=15, fill=WARN, bold=True)
    y_wb = clade(s, 230, [190, 250], [320, 320])
    y_twb = clade(s, 140, [130, y_wb], [320, 230])
    clade(s, 60, [70, y_twb], [320, 140])
    for x, y, lab in tips:
        s.text(x, y + 5, lab, size=16, bold=lab == "鳥", fill=INK)
    s.circle(60, (70 + y_twb) / 2, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(52, (70 + y_twb) / 2 - 14, "共通祖先", size=14, fill=FOCUS, anchor="start", bold=True)
    s.note(24, 30, "鳥を抜くと、子孫の一部が棚の外に漏れる", size=15)
    return s


def parsimony():
    """4-4 変化の回数を枝に刻むと、木Bは4回、木Aは6回。対照の2枚 M 640x320。

    各パネル：枝先 x = x0+230、y = 70（カエル）, 130, 190, 250。根 x0+30。
    刻み：羊=羊膜、窓=前眼窩窓、心=二つに分かれた心室、羽=羽毛。
    """
    s = SVG(640, 330, "同じ形質の表でも、ワニとハトを束ねる木Bは変化4回、トカゲとワニを束ねる木Aは6回で済む")

    def tick(x, y, lab, col=FOCUS):
        s.line(x, y - 9, x, y + 9, stroke=col, sw=3)
        s.text(x, y - 13, lab, size=14, fill=col, anchor="middle", bold=True)

    for x0, name, order, pairs in ((0, "木A", ["カエル", "トカゲ", "ワニ", "ハト"], "A"),
                                   (320, "木B", ["カエル", "トカゲ", "ワニ", "ハト"], "B")):
        tx = x0 + 230
        ys = [70, 130, 190, 250]
        for y, lab in zip(ys, order):
            s.text(tx + 10, y + 5, lab, size=15)
        if pairs == "A":      # ((トカゲ, ワニ), ハト)
            y1 = clade(s, x0 + 150, [130, 190], [tx, tx])
            y2 = clade(s, x0 + 100, [y1, 250], [x0 + 150, tx])
            y3 = clade(s, x0 + 30, [70, y2], [tx, x0 + 100])
            tick(x0 + 65, y2, "羊")
            tick(tx - 40, 190, "窓"); tick(tx - 20, 190, "心")
            tick(tx - 60, 250, "窓"); tick(tx - 40, 250, "心"); tick(tx - 20, 250, "羽")
            n, col = 6, WARN
        else:                 # (トカゲ, (ワニ, ハト))
            y1 = clade(s, x0 + 150, [190, 250], [tx, tx])
            y2 = clade(s, x0 + 100, [130, y1], [tx, x0 + 150])
            y3 = clade(s, x0 + 30, [70, y2], [tx, x0 + 100])
            tick(x0 + 65, y2, "羊")
            tick(x0 + 115, y1, "窓"); tick(x0 + 135, y1, "心")
            tick(tx - 20, 250, "羽")
            n, col = 4, MAIN
        s.text(x0 + 30, 36, name, size=17, bold=True)
        s.text(x0 + 130, 300, f"変化 {n} 回", size=17, fill=col, anchor="middle", bold=True)
    s.note(24, 324, "羊=羊膜　窓=前眼窩窓　心=心室　羽=羽毛", color=MUTED, size=14)
    return s


def saturation():
    """5-2 同じ場所が何度も変わると、数えた違いは頭打ちになる。正方 S 460x380。

    横：本当の変化の回数（1文字あたり）0〜3、x = 70 + d*120。縦：数えた違いの割合 0〜1、y = 320 - p*260。
    模型：4種の文字が等しく入れ替わる最も単純な模型、p = 3/4 (1 - exp(-4d/3))。
    """
    X = lambda d: 70 + d * 120
    Y = lambda p: 320 - p * 260
    jc = lambda d: 0.75 * (1 - math.exp(-4 * d / 3))
    assert abs(jc(3) - 0.736) < 0.01
    s = SVG(460, 380, "同じ場所で何度も変わると、並べて数えた違いは本当の変化より少なくなり、0.75で頭打ちになる")
    s.line(70, Y(0), 430, Y(0), stroke=INK)
    s.line(70, Y(0), 70, Y(1), stroke=INK)
    for d in (1, 2, 3):
        s.text(X(d), Y(0) + 22, str(d), size=14, fill=SUB, anchor="middle")
    for p in (0.25, 0.5, 0.75, 1):
        s.text(62, Y(p) + 5, f"{p:g}", size=14, fill=SUB, anchor="end")
    s.text(430, 368, "本当の変化の回数（1文字あたり）", size=14, fill=SUB, anchor="end")
    s.text(74, Y(1) - 10, "並べて数えた違いの割合", size=14, fill=SUB)
    s.poly([(X(d), Y(d)) for d in (0, 1)], stroke=WARN, sw=2.4, dash="6 4")
    s.text(X(1) - 4, Y(1) + 20, "完全な時計", size=15, fill=WARN, anchor="end", bold=True)
    s.poly([(X(k / 40), Y(jc(k / 40))) for k in range(121)], stroke=MAIN, sw=3.5)
    s.line(70, Y(0.75), 430, Y(0.75), stroke=MUTED, dash="3 3")
    s.rect(X(0), Y(0.12), X(0.12) - X(0), Y(0) - Y(0.12), fill=TINT[FOCUS], stroke=FOCUS, sw=1.4)
    s.text(X(0.14) + 4, Y(0.06), "池のドジョウ", size=14, fill=FOCUS, bold=True)
    s.note(X(1.2), Y(0.45), ["遠い親戚ほど", "数えた違いが足りない"])
    return s


def whale():
    """5-3 クジラは偶蹄類の内側、カバの隣に入る。横長 M 580x330。

    枝先 x 330、y = 60, 110, 170, 230, 290（ラクダ、ブタ、ウシ・シカ、カバ、クジラ）。
    節：根 50、（ウシ・シカ、（カバ、クジラ））150、（カバ、クジラ）240。
    """
    s = SVG(580, 330, "DNAと化石の両方で、クジラは偶蹄類の内側に入り、カバと姉妹になる")
    tips = ["ラクダ", "ブタ", "ウシ・シカ", "カバ", "クジラ"]
    ys = [60, 110, 170, 230, 290]
    s.rect(310, 36, 250, 276, rx=10, fill=TINT[MAIN], stroke=MAIN, sw=2)
    s.text(552, 304 - 6, "鯨偶蹄目", size=15, fill=MAIN, anchor="end", bold=True)
    s.rect(316, 42, 150, 212, rx=8, stroke=WARN, sw=2.4, dash="6 4")
    s.text(474, 110, ["クジラを", "外した", "偶蹄目"], size=14, fill=WARN, bold=True)
    y_hw = clade(s, 240, [230, 290], [320, 320], sw=2)
    y_r = clade(s, 150, [170, y_hw], [320, 240])
    s.line(50, 60, 50, y_r, stroke=INK, sw=2)
    for y in (60, 110):
        s.line(50, y, 320, y, stroke=INK, sw=2)
    s.line(50, y_r, 150, y_r, stroke=INK, sw=2)
    for y, lab in zip(ys, tips):
        s.text(330, y + 5, lab, size=16, bold=lab in ("カバ", "クジラ"))
    s.line(195, y_hw - 10, 195, y_hw + 10, stroke=FOCUS, sw=4)
    s.text(195, y_hw + 30, "共有する挿入", size=14, fill=FOCUS, anchor="middle", bold=True)
    s.line(30, 175, 50, 175, stroke=INK, sw=2)
    s.line(38, 165, 38, 185, stroke=FOCUS, sw=4)
    s.text(24, 208, ["両端が滑車", "の距骨"], size=14, fill=FOCUS, bold=True)
    s.note(24, 30, "外に置くと偶蹄目が穴あきになる", size=15)
    return s


def gene_tree():
    """5-4 遺伝子の木は種の木と食い違うことがある。縦長 M 520x460（模式、時間は上が昔）。

    種の木：太い管。祖先の管 y 60〜180、C が y 180 で分かれ、A と B が y 230 で分かれる。枝先 y 400。
    遺伝子：A(表)・B(裏)・C(表)。A と B の系統は短い区間で合流せず、祖先の管で A と C が先に合流。
    """
    s = SVG(520, 460, "種はAとBが近いのに、ある遺伝子ではAとCが同じ型で近く見える。祖先の集団に型が混じっていたため")
    tube = lambda pts: s.poly(pts, closed=True, fill=TINT[MUTED], stroke=MUTED, sw=1.6)
    tube([(180, 50), (340, 50), (340, 170), (430, 250), (430, 400), (370, 400), (370, 250), (260, 190),
          (260, 400), (200, 400), (200, 250), (165, 235), (130, 250), (130, 400), (70, 400), (70, 250),
          (180, 170)])
    s.text(260, 36, "祖先の集団", size=15, anchor="middle", fill=SUB)
    for x, lab, face in ((100, "A", "表"), (230, "B", "裏"), (400, "C", "表")):
        s.text(x, 426, lab, size=18, anchor="middle", bold=True)
        s.text(x, 448, face, size=15, anchor="middle", fill=FOCUS if face == "表" else MAIN, bold=True)
    s.poly([(100, 400), (100, 250), (150, 205), (205, 160), (250, 110)], stroke=FOCUS, sw=3, smooth=True)
    s.poly([(400, 400), (400, 250), (320, 195), (290, 150), (250, 110)], stroke=FOCUS, sw=3, smooth=True)
    s.poly([(230, 400), (230, 250), (232, 190), (240, 130), (250, 75)], stroke=MAIN, sw=3, smooth=True)
    s.poly([(250, 110), (250, 75)], stroke=FOCUS, sw=3)
    s.circle(250, 110, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.circle(250, 75, 7, fill=INK, stroke="#ffffff", sw=2)
    s.text(268, 116, "A と C の遺伝子が合流", size=14, fill=FOCUS, bold=True, halo=True)
    s.text(440, 190, ["C が", "分かれる"], size=14, fill=SUB)
    s.text(24, 236, ["A と B", "が分かれる"], size=14, fill=SUB)
    s.note(350, 300, ["種の木：A と B", "遺伝子の木", "：A と C"], size=15)
    return s


def rooting():
    """6-3 重複でできたもう一方のコピーを外群にすると、根は細菌の側に落ちる。横長 M 560x380。

    重複の節 (40, 190)。コピー1 の木 y 50〜150、コピー2 の木 y 230〜330。枝先 x 320。
    各コピーの中は（細菌、（古細菌、真核生物））。
    """
    s = SVG(560, 380, "全生物の共通祖先より前に重複した遺伝子の2コピーは互いの外群になり、根は細菌の側に落ちる")
    labs = ["細菌", "古細菌", "真核生物"]
    for k, (y0, name, col) in enumerate(((50, "コピー1", MAIN), (230, "コピー2", MUTED))):
        ys = [y0, y0 + 50, y0 + 100]
        y_ae = clade(s, 230, ys[1:], [320, 320], stroke=col, sw=2.6 if k == 0 else 1.8)
        y_r = clade(s, 150, [ys[0], y_ae], [320, 230], stroke=col, sw=2.6 if k == 0 else 1.8)
        for y, lab in zip(ys, labs):
            s.text(330, y + 5, lab, size=15, fill=INK if k == 0 else SUB, bold=k == 0 and lab == "細菌")
        s.text(500, y0 + 55, name, size=15, fill=col, bold=True, anchor="middle")
        if k == 0:
            y_root1 = y_r
        else:
            y_root2 = y_r
    y_dup = clade(s, 50, [y_root1, y_root2], [150, 150], stroke=INK, sw=2.6)
    s.circle(50, y_dup, 8, fill=FOCUS, stroke="#ffffff", sw=2)
    s.text(58, y_dup + 28, ["遺伝子", "重複"], size=14, fill=FOCUS, bold=True)
    s.rect(140, 214, 290, 136, rx=8, stroke=MUTED, dash="5 4")
    s.text(424, 364, "コピー1 の木から見た外群", size=14, fill=SUB, anchor="end")
    s.circle(150, y_root1, 7, fill=FOCUS, stroke="#ffffff", sw=2)
    s.note(360, 190, ["根は細菌の側", "古細菌と真核生物が姉妹"], size=15)
    return s


def web():
    """終幕 生命の樹は横でもつながる。横長 L 760x480（模式）。

    根 (40, 230)。細菌 y 60〜170、古細菌 y 250、真核生物 y 310〜410。枝先 x 560。
    横線：細菌どうしの水平伝播（灰）、細菌→真核生物の根元（ミトコンドリア）、シアノバクテリア→植物（葉緑体）、
    ウイルス→哺乳類（シンシチン、橙）。
    """
    s = SVG(760, 480, "生命の樹は枝分かれだけでなく、水平伝播と細胞内共生とウイルスの書き込みで横にもつながる")
    tx = 560
    bac = {"ミトコンドリアの祖先": 60, "ほかの細菌": 110, "シアノバクテリア": 160}
    euk = {"植物": 310, "菌": 360, "哺乳類": 410}
    y_b = clade(s, 150, list(bac.values()), [tx] * 3, stroke=INK, sw=2.4)
    y_e = clade(s, 300, list(euk.values()), [tx] * 3, stroke=INK, sw=2.4)
    y_ae = clade(s, 150, [250, y_e], [tx, 300], stroke=INK, sw=2.4)
    y_root = clade(s, 40, [y_b, y_ae], [150, 150], stroke=INK, sw=2.4)
    for lab, y in list(bac.items()) + [("古細菌", 250)] + list(euk.items()):
        s.text(tx + 10, y + 5, lab, size=15, bold=lab in ("哺乳類",))
    s.text(48, y_b - 10, "細菌", size=15, bold=True)
    s.text(48, y_ae + 24, ["古細菌と", "真核生物"], size=15, bold=True)
    s.text(308, 340, "真核生物", size=15, bold=True)
    s.line(420, 60, 440, 110, stroke=MUTED, sw=2, dash="4 3")
    s.line(470, 110, 490, 160, stroke=MUTED, sw=2, dash="4 3")
    s.text(470, 86, "水平伝播", size=14, fill=SUB)
    s.poly([(250, 60), (270, 200), (300, y_e - 4)], stroke=MAIN, sw=3, smooth=True, arrow=True)
    s.text(262, 196, "ミトコンドリア", size=14, fill=MAIN, bold=True, halo=True, anchor="end")
    s.poly([(380, 160), (400, 240), (420, 306)], stroke=MAIN, sw=3, smooth=True, arrow=True)
    s.text(410, 236, "葉緑体", size=14, fill=MAIN, bold=True, halo=True)
    s.circle(430, 455, 9, fill="#ffffff", stroke=FOCUS, sw=2.4)
    s.text(446, 461, "ウイルス（シンシチン）", size=14, fill=FOCUS, bold=True)
    s.poly([(436, 447), (452, 430), (466, 414)], stroke=FOCUS, sw=3, smooth=True, arrow=True)
    s.text(736, 30, "模式図", size=14, fill=SUB, anchor="end")
    s.note(24, 30, "枝は横でもつながる")
    return s


if __name__ == "__main__":
    sys.exit(build({
        OUT / "fig2-3-ring.svg": ring,
        OUT / "fig4-1-wing.svg": wing,
        OUT / "fig4-2-paraphyly.svg": paraphyly,
        OUT / "fig4-4-parsimony.svg": parsimony,
        OUT / "fig5-2-saturation.svg": saturation,
        OUT / "fig5-3-whale.svg": whale,
        OUT / "fig5-4-gene-tree.svg": gene_tree,
        OUT / "fig6-3-rooting.svg": rooting,
        OUT / "fig8-web.svg": web,
    }))
