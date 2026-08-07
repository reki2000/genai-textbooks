---
name: yaruo-figures
description: やる夫式教材（docs/books/*/README*.md）に、理解を助ける説明図（SVG）を設計・生成して本文へ組み込むスキル。図は Python スクリプトで生成し docs/books/{ID}/figs/ に置く。「図」「図解」「イラスト」「グラフを入れて」「図版」「ダイアグラム」「可視化」に言及し、対象がやる夫式教材なら使う。
---

# やる夫式教材 図版スキル

対話教材に**説明図**を足す。図は手で SVG を書かず、`scripts/figures/{ID}_figs.py` が生成し、`docs/books/{ID}/figs/*.svg` に出力する。生成物も本文と同じくソース扱いでコミットする。

参考実装は `scripts/figures/weather_forecasting_figs.py`（8図）。描画ヘルパは `scripts/figures/svgkit.py` が正本。

## 1. 何を図にするか決める

やる夫式教材は「素朴案 → 反例で死ぬ → 直す」の連鎖でできている。図にすべきは**その死ぬ瞬間と、直したあとの形**であって、教材の要約ではない。

図にする候補：

- **数で殺した箇所**（$10^{30}$ 年、16倍、$(1.1)^{40}$ など）。桁の差は文字より図が速い。
- **やる夫が「あーーー」と気づく壁**。ボケ・過小分散・極の潰れなど、絵にすると一撃で分かるもの。
- **幾何・空間の話**（球面、格子、メッシュ、経路）。文章がいちばん不利な領域。
- **前後の対比**（駄目な方式 ／ 直した方式）。1枚に並置する。
- **全体の流れ**（パイプライン、分岐）。第4幕までに組んだ道具を1枚へ束ねる位置に置く。

図にしない：

- 会話の言い換え、登場人物、教材の目次・まとめ。
- 本文を読めば1行で済むこと。図が本文の代替になっているなら、その図は要らない。

**着手前に、図の一覧（何を・どの位置に・何が読み取れるか）をユーザーへ提示して合意を取る。** 教材1本あたり6〜10枚が目安。1つの節に2枚以上は置かない。

## 2. 生成スクリプトを書く

`scripts/figures/{ID}_figs.py`（ID の `-` は `_` に）を作り、`svgkit` を import する。

```python
from pathlib import Path
from functools import partial
from svgkit import Svg, BLUE, ORANGE, AQUA, RED, INK, INK2, INK3, GRID

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "{ID}" / "figs"
Svg = partial(Svg, out_dir=OUT_DIR)


def fig_something():
    s = Svg(760, 400, "図1　<結論を書いた題>", "<1行の副題：図が示す事実>")
    ...
    s.lines_of_text(24, 360, ["<2〜3行の説明。図だけ見ても分かるようにする>"], size=11.5, lh=17)
    s.save("fig1-<slug>.svg")
```

規約：

- **幅は 760 固定**。高さは中身に合わせる。`svgkit.Svg` が `viewBox` だけを書き、`width`/`height` 属性は付けない（付けると docsify の `max-width:100%` で縦横比が崩れる）。
- ファイル名は `fig{n}-{英小文字スラッグ}.svg`。本文の登場順に番号を振る。
- 図の中に**題・副題・2〜3行の説明**を必ず入れる。本文と切り離して読んでも意味が通る単位にする。
- 座標・曲線・数値は**式で計算する**。目分量の数値を並べない（図3の 8/16 倍、図1の倍加時間など、本文の数値と一致させる）。
- 色は `svgkit` の定数だけを使う。1枚に3系列まで。系列色は凡例ではなく**直接ラベル**で示す。「これは駄目」を指す線・注記は `RED` に寄せ、系列色として使わない。
- 数式は SVG に持ち込まない（KaTeX が効かない）。式は本文に置き、図は結果の形だけを見せる。上付きが要るなら Unicode（`10⁻³`）を使う。
- 明るいカード面は `svgkit` が描く。ダークテーマでもカードだけ明るく浮く前提で、テーマ非依存の配色にしてある。個別の図で背景色を変えない。

## 3. 画像にして必ず目視する

**行数やテキスト幅の目算は当てにならない。** 日本語ラベルは容易に重なり、はみ出す。全図を PNG 化して Read ツールで1枚ずつ見る。

初回だけ環境を用意する（この2つが無いと描画できない）。

```bash
# 日本語フォント（WSL なら Windows から借りる）。fc-list :lang=ja が空でなければ不要
mkdir -p ~/.local/share/fonts && cp /mnt/c/Windows/Fonts/{YuGothR.ttc,YuGothB.ttc,meiryo.ttc} ~/.local/share/fonts/ && fc-cache -f

# ラスタライザ（システム依存の共有ライブラリが要らないものを使う。
# rsvg-convert / chromium は sudo が必要になり、この環境では入らない）
mkdir -p /tmp/svgshot && cd /tmp/svgshot && npm install @resvg/resvg-js
```

描画：

```bash
python3 scripts/figures/{ID}_figs.py
node .claude/skills/yaruo-figures/scripts/render_svg.js docs/books/{ID}/figs /tmp/svgshot/out
```

見る点：

- ラベル同士、ラベルと線・棒・図形の**重なり**。
- カード外へのはみ出し、下端の注記と本体の衝突。
- 逆に**空きすぎた帯**（高さを詰める）。
- 曲線の極値やマーカーが、指したい場所に本当に付いているか。

直したらスクリプトを直して再生成し、**もう一度見る**。1回で通ることはまずない。

## 4. 本文へ挿入する

```markdown
（発言の最終行。）

![図1　<題>。<何が読み取れるか>](./figs/fig1-<slug>.svg)

**やらない夫**：
```

- **単独行**で置き、前後に空行を1行ずつ。`docs/**/README*.md` の相対リンクは docsify の `relativePath: true` が解決するので `./figs/...` でよい。
- 挿入位置は、**その図が答えになっている気づきの直後**。やる夫が結論に達した発言の後ろに置き、次の話者行の前で切る。節の冒頭に先回りして置かない（図が答えを先出しすると再発見が壊れる）。
- alt テキストには題だけでなく**読み取れる内容**まで書く。図の代わりに読まれる文になる。
- 図番号は本文中で参照しない（「図3のとおり」と書かない）。教材は音読しても成立する会話文なので、図は黙って添える。

単独行の画像は `scripts/yaruo_markdown.py` の `IMAGE_LINE` により非散文領域として扱われ、`dialogue-period` などの検査対象から外れる。ここを変えたら `python3 scripts/tests/run_lint_tests.py` を回す。

## 5. 検査とビルド

```bash
python3 scripts/yaruo_lint.py docs/books/{ID}/README.md --check   # error 0件
python3 scripts/generate_site.py                                  # ビルド成功
ls build/books/{ID}/figs/                                         # SVG がコピーされている
```

`generate_site.py` は `docs/` を丸ごと `build/` へコピーするため、図の配置に追加設定は要らない。

コミットは `git add docs/ scripts/`。`build/` は絶対に含めない。

## 6. 完了報告

- 図の一覧（番号・題・挿入した節・何を示すか）
- 生成スクリプトのパスと実行コマンド
- lint と build の結果
- 図にしなかった候補と、その理由（本文で足りる／絵にしても読み取れない、など）

## チェックリスト

- [ ] 図の案をユーザーに提示して合意を取ったか
- [ ] 全図を PNG 化して1枚ずつ目視したか（重なり・はみ出し・空き）
- [ ] 図の数値が本文の数値と一致しているか
- [ ] 挿入位置が「気づきの直後」で、答えの先出しになっていないか
- [ ] `yaruo_lint.py --check` が error 0件、`generate_site.py` が成功したか
