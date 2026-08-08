#!/usr/bin/env python3
"""軌道力学教材のSVGを決定的に生成する。"""
from __future__ import annotations
import argparse, filecmp, sys, tempfile
from functools import partial
from pathlib import Path
from svgkit import AQUA, BLUE, CARD_EDGE, INK, INK2, INK3, RED, Svg as SvgDocument

OUT_DIR = Path(__file__).resolve().parents[2] / "docs/books/orbital-mechanics-moon/figs"

def ellipse(cx, cy, rx, ry):
    return f"M{cx-rx},{cy} A{rx},{ry} 0 1,0 {cx+rx},{cy} A{rx},{ry} 0 1,0 {cx-rx},{cy}"

def figures(out_dir: Path):
    Svg = partial(SvgDocument, out_dir=out_dir)
    s = Svg(760, 400, "図1　前へ追いつくには、まず後ろ向きに噴射する", "減速して低い軌道へ入ると、短い周期で内側から先回りできる")
    cx, cy = 270, 230
    s.circle(cx, cy, 58, fill="#eaf4ff", stroke=BLUE, sw=2); s.text(cx, cy+5, "地球", 14, BLUE, "700", "middle")
    s.circle(cx, cy, 132, stroke=INK3, sw=1.8, dash="6 5"); s.path(ellipse(cx, 214, 110, 116), stroke=AQUA, sw=3)
    s.circle(300, 102, 7, fill="#eb6834", stroke="#fff", sw=2); s.text(300, 82, "100 m前の仲間", 11.5, "#eb6834", "700", "middle")
    s.circle(270, 98, 7, fill=BLUE, stroke="#fff", sw=2); s.arrow(260, 98, 218, 98, RED, 2.5); s.text(208, 90, "減速", 11.5, RED, "700", "end")
    s.arrow_path("M277,99 C368,128 363,258 296,326", AQUA, 2.5)
    s.lines_of_text(438,174,["低い軌道", "半長軸が小さい", "→ 周期が短い", "→ 内側から先回り"], 12, INK2, 21, weight="700")
    s.box(430, 270, 270, 66, "その場の速度ではなく", "噴射後の軌道全体で考える", AQUA)
    s.text(380,378,"軌道は模式表示（高度差は強調）",10.5,INK3,anchor="middle"); s.save("fig1-rendezvous-slow-down.svg")

    s = Svg(760, 430, "図2　同じΔvでも、噴射方向で届く距離が24倍違う", "LEOで3.09 km/s：外向きは地球へ衝突、進行方向なら月距離へ届く")
    for px,title,color,aval,line1,line2 in [(28,"外向きに噴射",RED,"8,080","遠地点 < 16,160 km","近地点 ≈ 4,800 km（地球内部）"),(392,"進行方向に噴射",AQUA,"195,000","長半径 ≈ 195,000 km","遠地点 ≈ 月の距離")]:
        s.rect(px,80,340,288,"#fff",CARD_EDGE,8); s.text(px+170,108,title,14,color,"700","middle")
        ex,ey=px+92,218; s.circle(ex,ey,34,"#eaf4ff",BLUE,1.8); s.text(ex,ey+4,"地球",11,BLUE,"700","middle"); s.circle(ex,ey,48,stroke=INK3,dash="4 4"); s.circle(ex,ey-48,5,INK)
        s.arrow(ex,ey-53,ex+66,ey-53,color,2.5)
        if color==RED:
            s.path(f"M{ex},{ey-48} C{ex+100},{ey-82} {ex+164},{ey-22} {ex+40},{ey+27}",RED,sw=2.8); s.text(px+244,205,"衝突",11.5,RED,"700","middle")
        else:
            s.path(f"M{ex},{ey-48} C{ex+226},{ey-85} {ex+226},{ey+85} {ex},{ey+48}",AQUA,sw=2.8); s.text(px+270,218,"月距離",11.5,AQUA,"700","middle")
        s.text(px+170,298,line1,12,INK,"700","middle"); s.text(px+170,320,line2,11.5,color,"700","middle"); s.text(px+170,348,f"a = {aval} km",11,INK2,anchor="middle")
    s.text(380,397,"速度ベクトルと同じ向きなら、Δvが運動エネルギー増加へ最も効く",13,INK,"700","middle"); s.text(380,417,"軌道形状は模式化（数値は本文のvis-viva計算）",10.5,INK3,anchor="middle"); s.save("fig2-burn-direction.svg")

    s = Svg(760, 430, "図3　LORは「月面まで運ぶ質量」を切り離す", "帰還機を月周回に残し、軽い着陸機だけが2.0 + 1.9 km/sを払う")
    for px,title,color in [(28,"直接上昇",RED),(392,"月周回ランデブー（LOR）",AQUA)]:
        s.rect(px,82,340,286,"#fff",CARD_EDGE,8); s.text(px+170,111,title,13.5,color,"700","middle"); s.circle(px+170,292,58,"#f3f3f1",INK3,1.5); s.text(px+170,300,"月面",12,INK2,"700","middle")
        if color==RED:
            s.box(px+91,150,158,66,"宇宙船まるごと","帰還機＋燃料＋熱盾",RED); s.arrow(px+170,222,px+170,256,RED,2.5); s.arrow(px+184,256,px+184,222,RED,2.5); s.text(px+170,347,"重い全質量が降下・上昇",11.5,RED,"700","middle")
        else:
            s.path(ellipse(px+170,254,126,48),INK3,sw=1.4,dash="5 4"); s.box(px+36,142,146,58,"母船","帰還機・熱盾は待機",BLUE); s.box(px+208,202,100,58,"着陸機","小さく軽い",AQUA); s.arrow(px+255,266,px+207,291,AQUA,2.5); s.arrow(px+198,291,px+246,266,AQUA,2.5); s.text(px+170,347,"月面往復は着陸機だけ",11.5,AQUA,"700","middle")
    s.arrow(354,225,390,225,INK2,2); s.text(380,397,"指数で増える燃料連鎖を、月周回で機体を分けて断ち切る",13,INK,"700","middle"); s.save("fig3-lor-mass-separation.svg")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--check",action="store_true"); args=p.parse_args()
    if not args.check: figures(OUT_DIR); return 0
    with tempfile.TemporaryDirectory() as tmp:
        candidate=Path(tmp); figures(candidate); expected=sorted(p.name for p in candidate.glob("*.svg")); actual=sorted(p.name for p in OUT_DIR.glob("*.svg")) if OUT_DIR.exists() else []
        if expected!=actual: print(f"figure set differs: expected {expected}, actual {actual}",file=sys.stderr); return 1
        changed=[n for n in expected if not filecmp.cmp(candidate/n,OUT_DIR/n,shallow=False)]
        if changed: print("outdated figures: "+", ".join(changed),file=sys.stderr); return 1
    print("all orbital-mechanics-moon figures are up to date"); return 0
if __name__=="__main__": raise SystemExit(main())
