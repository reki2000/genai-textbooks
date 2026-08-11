# このリポジトリでの配置と検査

Phase 2 に入ったら読む。作図の判断は `conventions.md` と `recipes.md`、置き場所とビルドはここ。

## 生成元と生成先

教材IDを `<id>` として固定する。

```text
scripts/figs/<id>.py              # その教材の全図を生成する唯一のコード
scripts/figs/svgkit.py            # 共通の描画ヘルパ
docs/books/<id>/figs/<name>.svg   # 本文が参照する生成物
```

```python
#!/usr/bin/env python3
"""docs/books/<id>/figs/*.svg を決定的に生成する。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, E_BLUE, INK, N_TINT   # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "books" / "<id>" / "figs"
```

- 同じ教材の図を別のPythonファイルへ分散させない。複数教材で再利用する部品だけ `scripts/figs/` 配下の共通モジュールへ切り出す。
- **生成物を手で編集しない。** SVGも生成コードと一緒にコミットする。
- リポジトリ直下以外から呼ばれても出力先を解決し、出力順・数値表記を決定的にする。`--check` で既存図と再生成結果を比較できるようにする（差分があれば非ゼロ終了）。
- 座標・曲線・尺度・数値は本文の式や入力値から計算する。目分量で結果らしい形を作らない。
- 外部引用画像は `docs/books/<id>/figs/` へコピーせず、生成対象にも含めない。

## 生成画像

画像生成で作った図（Codex から使うときの第一候補）も置き場所は同じ `docs/books/<id>/figs/` で、ラスタ画像のままコミットする。`docs/` は丸ごとサイトへコピーされるので、ここに置けばそのまま公開される。

- ファイル名は SVG と同じ規則（`figN-<内容>.png` など）。
- **採用した画像の最終プロンプトと生成手段を `scripts/figs/<id>.py` へコメントか定数として残す。** 生成物そのものは再現できなくても、何をどう頼んだかは追えるようにする。スクリプト側では存在確認・寸法・ファイル名を検証対象に含める。
- 外部サイトの画像を貼り込んだ場合は、キャプションの直下へ引用元のサイト名とURLを併記し、そのサイトの引用ルールに従った帰属表記を書く（`references/recipes.md`）。
- `check_figure.py` は SVG を解析する検査なのでラスタ画像には効かない。**PNG の目視だけが検査**になるので、デスクトップ幅と約360px幅の両方で必ず見る。

## SVG の書き出し

`svgkit.SVG.save()` が処理済みだが、理由を知っておく。

- `width` / `height` 属性を付けない。docsify 側の `max-width:100%` と噛み合って縦横比が崩れる。`viewBox` だけなら閲覧幅にフィットする。
- `SVG(w, h, title)` で `<title>` / `<desc>` が入る。title は図が示す結論を一文で書く。
- 図はライト／ダーク両テーマの上に置かれ、テーマ切り替えは OS の `prefers-color-scheme` と一致しないことがある。**SVG 自身が明るい地色を持つ**ことで、どちらでも同じ配色で読める。
- 幅は 760 前後が本文幅にほぼ一致する。
- KaTeX は SVG 内で動かない。長い数式は本文へ残し、図には計算結果と必要最小限の記号だけを置く。

## 本文への埋め込み

単独行の画像＋一文のキャプション。代替テキストは「概念図」ではなく図が示す結論を書く。細部を持つ図は画像自身へのリンクで包み、狭い画面からタップして原寸表示できるようにする。

```markdown
[![二段階の標本と短い残りを足してrankを求める図](figs/rank-two-level.svg)](figs/rank-two-level.svg)

図2-1：`rank_1(14)=3+2+1=6`。大区画、小区画、残りの実測を足す（タップ／クリックで原寸表示）。
```

単独行の画像は `yaruo_markdown.py` が非散文領域として扱う。直後の `図N：…` キャプションは表記の検査は受けるが、発言長の集計からは図版ブロックとして除外される。

## 検査

```bash
python3 scripts/figs/<id>.py
python3 scripts/figs/<id>.py --check
python3 .claude/skills/zuhan/scripts/check_figure.py "docs/books/<id>/figs/*.svg" --png-dir /tmp/figpng
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check --verbose
python3 scripts/generate_site.py
git diff --check
```

`generate_site.py` が不足パッケージだけを理由に停止し、`uv` が使えるなら、グローバル環境へ入れずに次で検証する。

```bash
uv run --with-requirements requirements-dev.txt python scripts/generate_site.py
```

`check_figure.py` の豆腐検査と PNG 書き出しには `fonttools` と `cairosvg` が要る（`requirements-dev.txt` に入っている）。

## PNG の目視

**必ず実画像を見る。** ソースを読み返す自己レビューは、ラベルの重なり・矢印の頭の肥大・図形の食い違いを1つも捕まえない。

`check_figure.py --png-dir` が cairosvg で書き出す。ただし cairosvg は SVG の `font-family` に一致する日本語フォントが無い環境では**日本語をすべて豆腐で描く**。そのPNGで文字が四角になっていても図の欠陥ではない。レイアウトの確認には使えるが、文字の確認には次の resvg を使う。

`@resvg/resvg-js` はフォントを直接渡せる。狭い画面幅の確認もこちらで行う。

```bash
mkdir -p /tmp/svgshot && cd /tmp/svgshot && npm install @resvg/resvg-js
cd - >/dev/null
node .claude/skills/zuhan/scripts/render_svg.js docs/books/<id>/figs /tmp/svgshot/out
SVG_RENDER_WIDTH=360 node .claude/skills/zuhan/scripts/render_svg.js docs/books/<id>/figs /tmp/svgshot/out-360
```

日本語フォントが無い環境では、`SVG_FONT_FILES=/path/to/font.ttf`（複数はOSのパス区切り文字で連結）で一時フォントを渡してから判定する。

見るのはデスクトップ幅と約360px幅の2つ。**360px ではタイトル・主経路・結論が分かることを必須**とし、細部は原寸リンクへ逃がす。全ての細字を縮小状態で読ませようとして情報を削らない。図を開かなくても結論が残るキャプションを付ける。
