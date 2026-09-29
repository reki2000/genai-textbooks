# このリポジトリでの配置と検査

Phase 2 に入ったら読む。作図の判断は `conventions.md`・`layout.md`・`recipes.md`、置き場所とビルドはここ。

## 生成元と生成先

教材IDを `<id>` として固定する。

```text
scripts/figs/<id>.py             # 図の生成元（SVG直書き・自力描画・matplotlib）
scripts/figs/<id>.md             # 図版選定の記録、作画資料と引用写真の出典、検査メモ
scripts/figs/svgkit.py           # 共通の描画ヘルパ
docs/books/<id>/figs/<name>.svg  # 本文が参照する生成物
docs/books/<id>/figs/<name>.png  # matplotlib などで PNG にした生成物
```

決定的な描画コードを作る場合は、**骨格を `scripts/figs/database-design.py` から写す。** 決定的な出力、`--check`、出力先の解決、座標の丸めはそこに実装済みなので、図ごとの関数だけ足す。

決定的な描画コードでは、コードの形そのものではなく次の約束を守る。

- 1教材につき、描画は1個の `.py`、記録は1個の `.md` にまとめる。複数教材で再利用する部品だけ `scripts/figs/` 配下の共通モジュールへ切り出す。ただし `follows` でつながるシリーズは、先頭巻のIDの `.py` 1本で全巻の図を描き、図ごとに該当する巻の `figs/` へ振り分けてよい（例 `scripts/figs/statistics.py` の `fig_out_dir`）。
- `--check` が差分ゼロで通ること。生成物も一緒にコミットし、**手で編集しない。**
- 冒頭の docstring で、その教材の色3系統が何を指すかを宣言する（`conventions.md`）。
- 座標・曲線・尺度・数値は本文の式や入力値から計算する。目分量で結果らしい形を作らない。**本文の数値は `assert` で突き合わせてから描く。** 図と本文がずれたら、どちらが誤りかを検査が教えてくれる（本文側の誤りが見つかることもある）。
- 各図の関数の docstring に、キャンバス寸法と要素の座標を先に書き出す。書いていない要素を描かない。

外部引用画像（参考写真）は `docs/books/<id>/figs/` へコピーせず、生成対象にも含めない。ファイルページの表示用 URL を本文から直接参照する。

## 記録（`scripts/figs/<id>.md`）

- Phase 1 の採用スロットと却下候補（理由つき）。
- 色3系統の割り当て（`.py` の docstring と同じもの）。
- **作画資料**：自力描画で形・比率・配置を確かめるのに見た資料の URL と、そこから取った事実（「スパインの頭は直径約1マイクロメートル、首より太い」など）。本文に表示しない資料もここへ残す。
- **引用写真**：ファイルページ URL、作者、ライセンス、確認日。
- 検査結果（下の表でよい）。

| ファイル | 形・表示幅 | 機械検査 | 原寸 | 360px | 説明力（layout.md 4） | 本文整合 |
|---|---|---|---|---|---|---|
| fig1-….svg | 縦長 480×680・M | pass | pass | pass | pass | pass |

`scripts/figs/memory-engram.md` とその PNG は、外部の画像生成に依頼していた旧方式の記録である。図を作り直すときは Phase 1 からやり直し、この方式に置き換える。

## SVG の書き出し

`svgkit.SVG.save()` が docsify 向けの処理を済ませてある（理由は svgkit.py の docstring）。図を設計するときに効くのは次の2点だけ。

- 幅は表示幅に近づける（S 320〜420、M 480〜600、L 760。`layout.md`）。760 は本文幅いっぱいの L 区分であって既定ではない。
- KaTeX は SVG 内で動かない。長い数式は本文へ残し、図には計算結果と必要最小限の記号だけを置く。

## 本文への埋め込み

単独行の画像＋一文のキャプション。代替テキストは「概念図」ではなく図が示す結論を書く。細部を持つ図は画像自身へのリンクで包み、狭い画面からタップして原寸表示できるようにする。

表示幅は docsify の表示指定 `':size=<幅>'` で決める。S・M 区分の図には必ず付け、L（本文幅いっぱい）だけ省く。スマホでは本文幅に収まるよう自動で縮む。

```markdown
[![二段階の標本と短い残りを足してrankを求める図](figs/rank-two-level.svg ':size=560')](figs/rank-two-level.svg)

図2-1：`rank_1(14)=3+2+1=6`。大区画、小区画、残りの実測を足す（タップ／クリックで原寸表示）。
```

実物＋模式図は、引用写真と自作図を続けて置き、キャプションは1つにまとめて対応関係を書く。

```markdown
![海馬の錐体細胞の顕微鏡像。細胞体から樹状突起が伸び、表面に多数の突起が並ぶ](https://upload.wikimedia.org/…/file.jpg ':size=420')

[![写真と同じ向きで、細胞体・樹状突起・スパインを描き分けた模式図](figs/fig1-neuron.svg ':size=420')](figs/fig1-neuron.svg)

図1：上が実物、下が同じ向きの模式図。下の図の橙の枠が、上の写真で樹状突起の表面に並ぶ小さな突起（スパイン）にあたる。*出典（上）：作者「資料名」[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:…)。CC BY-SA 4.0。*
```

単独行の画像は `yaruo_markdown.py` が非散文領域として扱う。直後の `図N：…` キャプションは表記の検査は受けるが、発言長の集計からは図版ブロックとして除外される（`yaruo_markdown.figure_block_lines`）。

キャプションにも `dialogue-period` が適用されるため、末尾に括弧があっても `。` で閉じる。

図を挿す位置は、直前の発言の末尾に**その図を指す一文を足してから**、発言ブロックの外に置く。発言の中へ画像を差し込まない。

## 検査

```bash
python3 scripts/figs/<id>.py
python3 scripts/figs/<id>.py --check
python3 .claude/skills/zuhan/scripts/check_figure.py "docs/books/<id>/figs/*.svg" --png-dir /tmp/figpng
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check --verbose
python3 scripts/generate_site.py
git diff --check
```

`yaruo_lint.py` は**図を足す前にも一度走らせて warning の数を控えておく**。図の追加で増えていないことを比べられる。

`check_figure.py` は、スマホ本文幅（340px）へ縮めたときに実効6px未満になる文字を NG にし、4枚以上を渡して全部が同じ幅・似た縦横比なら「形が一様」と注意を出す（注意は合否に使わないが、`layout.md` で形を選び直すきっかけにする）。

ラベル上限（22個）は「2文字以上の `<text>` を、同一文字列は1個として」数える。1文字のラベル（`0` `1` などのセルの中身、目盛の数字）は数えない。設計中に見積もりたいときは `--labels` を付ける。超過したときは自動で一覧が出るので、どれを削るか見て決める。

依存（`fonttools` / `cairosvg`）の入れ方とビルド環境は [`BUILD.md`](../../../../BUILD.md)。

## PNG の目視

実画像でラベルの重なり・矢印・図形の配置を確認し、`layout.md` の「説明力の確認」6項目を順に見る。原寸と約360px幅の2つを見る。matplotlib のSVGでは文字がパスになり、`check_figure.py` の文字検査が効かないため、文字も目視する。

`cairosvg` が無い環境では `scripts/render_svg.js`（resvg）で PNG にする。`SVG_RENDER_WIDTH=360` で縮小版も出せる。

見るのは**デスクトップ幅と約360px幅の2つ**。360px ではタイトル・主経路・結論が分かることを必須とし、細部は原寸リンクへ逃がす。全ての細字を縮小状態で読ませようとして情報を削らない。

道具は2つあり、用途が違う。

| 道具 | 用途 | 注意 |
|---|---|---|
| `check_figure.py --png-dir`（cairosvg） | レイアウトの確認 | 日本語フォントが無い環境では**文字をすべて豆腐で描く**。それは図の欠陥ではない |
| `render_svg.js`（`@resvg/resvg-js`） | 文字の確認、狭い幅の確認 | フォントを直接渡せる。**SVG2 未対応**なので、SVG2 限定の機能を使うと壊れて見える |

```bash
mkdir -p /tmp/svgshot && cd /tmp/svgshot && npm install @resvg/resvg-js
cd - >/dev/null
node .claude/skills/zuhan/scripts/render_svg.js docs/books/<id>/figs /tmp/svgshot/out
SVG_RENDER_WIDTH=360 node .claude/skills/zuhan/scripts/render_svg.js docs/books/<id>/figs /tmp/svgshot/out-360
```

日本語フォントが無い環境では、`SVG_FONT_FILES=/path/to/font.ttf`（複数はOSのパス区切り文字で連結）で一時フォントを渡してから判定する。svgkit は SVG1.1 の範囲だけで描くので resvg で正しく出る。生成コードでも SVG2 限定の機能を足さない。
