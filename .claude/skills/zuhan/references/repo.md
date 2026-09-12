# このリポジトリでの配置と検査

Phase 2 に入ったら読む。作図の判断は `conventions.md` と `recipes.md`、置き場所とビルドはここ。

## 生成元と生成先

教材IDを `<id>` として固定する。

```text
scripts/figs/<id>.py                    # 決定的に描画する図の生成元
scripts/figs/<id>.md                    # 生成手段・図版選定・検査メモ（プロンプト全文は置かない）
scripts/figs/<id>-prompt.txt            # ChatGPTへ渡す初回プロンプトの全文
scripts/figs/<id>-prompt-fix-<連番>.txt  # ChatGPTへ渡す修正プロンプトの全文
scripts/figs/svgkit.py                  # 共通の描画ヘルパ
docs/books/<id>/figs/<name>.svg         # 本文が参照する生成物
docs/books/<id>/figs/<name>.png         # 本文が参照する生成画像
```

決定的な描画コードを作る場合は、**骨格を `scripts/figs/database-design.py` から写す。** 決定的な出力、`--check`、出力先の解決、座標の丸めはそこに実装済みなので、図ごとの関数だけ足す。

決定的な描画コードでは、コードの形そのものではなく次の約束を守る。

- 1教材につき、決定的な描画は1個の `.py`、画像生成の記録は1個の `.md` にまとめる。両方の手段を使う教材では両方あってよい。複数教材で再利用する部品だけ `scripts/figs/` 配下の共通モジュールへ切り出す。
- `--check` が差分ゼロで通ること。生成物も一緒にコミットし、**手で編集しない。**
- 冒頭の docstring で、その教材の色3系統が何を指すかを宣言する（`conventions.md`）。
- 座標・曲線・尺度・数値は本文の式や入力値から計算する。目分量で結果らしい形を作らない。**本文の数値は `assert` で突き合わせてから描く。** 図と本文がずれたら、どちらが誤りかを検査が教えてくれる（本文側の誤りが見つかることもある）。
- 各図の関数の docstring に、キャンバス寸法と要素の座標を先に書き出す。書いていない要素を描かない。

外部引用画像は `docs/books/<id>/figs/` へコピーせず、生成対象にも含めない。

## 生成画像とZIP受領

生成画像は `figN-<内容>.png` などの名で生成先へ置き、コミットする。記録用 `.md` には生成手段・期待ファイル名と寸法・選定理由・検査結果を残し、プロンプト全文は上表の `.txt` を参照する。画像生成だけなら `.py` は不要。

ChatGPTへの依頼・不合格時の再生成は [chatgpt-image-prompt.md](chatgpt-image-prompt.md)。受領時は次の順に処理する。

1. ユーザーにZIPをリポジトリルートの `tmp/` へ置いてもらう。原本は変更せず、`docs/` へ直接展開しない。
2. 下の検査器で `<id>/<filename>.png` の期待一覧、余分なファイル、PNG署名、寸法を確認し、一時ディレクトリへ展開する。総覧画像や追加資料は不可。
3. 全PNGを原寸と約360px幅で見て、ラベル・経路・方向・本文整合・禁止事項を確認する。ZIP検査は内容の正しさを保証しない。
4. 合格画像だけを `docs/books/<id>/figs/` へコピーし、判定を記録する。不合格図は再生成を依頼する。

```bash
python3 .claude/skills/zuhan/scripts/check_image_zip.py tmp/<id>-figures.zip \
  --id <id> --expect fig1-<内容>.png --expect fig2-<内容>.png \
  --width 1536 --height 1024 --extract-to /tmp/zuhan-<id>
```

修正ZIPは `<id>-figures-fix-<連番>.zip`。`--expect` は不合格図だけにし、別の一時ディレクトリで検査する。合格した修正版だけを差分適用する。

## SVG の書き出し

`svgkit.SVG.save()` が docsify 向けの処理を済ませてある（理由は svgkit.py の docstring）。図を設計するときに効くのは次の2点だけ。

- 幅は 760 前後が本文幅にほぼ一致する。
- KaTeX は SVG 内で動かない。長い数式は本文へ残し、図には計算結果と必要最小限の記号だけを置く。

## 本文への埋め込み

単独行の画像＋一文のキャプション。代替テキストは「概念図」ではなく図が示す結論を書く。細部を持つ図は画像自身へのリンクで包み、狭い画面からタップして原寸表示できるようにする。

```markdown
[![二段階の標本と短い残りを足してrankを求める図](figs/rank-two-level.svg)](figs/rank-two-level.svg)

図2-1：`rank_1(14)=3+2+1=6`。大区画、小区画、残りの実測を足す（タップ／クリックで原寸表示）。
```

単独行の画像は `yaruo_markdown.py` が非散文領域として扱う。直後の `図N：…` キャプションは表記の検査は受けるが、発言長の集計からは図版ブロックとして除外される（`yaruo_markdown.figure_block_lines`）。

キャプションにも `dialogue-period` が適用されるため、末尾に括弧があっても `。` で閉じる。

図を挿す位置は、直前の発言の末尾に**その図を指す一文を足してから**、発言ブロックの外に置く。発言の中へ画像を差し込まない。

## 検査

```bash
# 決定的な描画コードがある場合
python3 scripts/figs/<id>.py
python3 scripts/figs/<id>.py --check

# ZIPは上記の受領手順で検査済みとする。次はSVGがある場合だけ。
python3 .claude/skills/zuhan/scripts/check_figure.py "docs/books/<id>/figs/*.svg" --png-dir /tmp/figpng
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check --verbose
python3 scripts/generate_site.py
git diff --check
```

`yaruo_lint.py` は**図を足す前にも一度走らせて warning の数を控えておく**。図の追加で増えていないことを比べられる。

`check_figure.py` のラベル上限（22個）は「2文字以上の `<text>` を、同一文字列は1個として」数える。1文字のラベル（`0` `1` などのセルの中身、目盛の数字）は数えない。設計中に見積もりたいときは `--labels` を付ける。超過したときは自動で一覧が出るので、どれを削るか見て決める。

依存（`fonttools` / `cairosvg`）の入れ方とビルド環境は [`BUILD.md`](../../../../BUILD.md)。

## PNG の目視

実画像でラベルの重なり・矢印・図形の配置を確認する。matplotlib のSVGでは文字がパスになり、`check_figure.py` の文字検査が効かないため、文字も目視する。

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
