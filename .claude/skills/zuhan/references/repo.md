# このリポジトリでの配置と検査

Phase 2 に入ったら読む。作図の判断は `conventions.md`・`layout.md`・`recipes.md`、置き場所とビルドはここ。

## ファイル

```text
scripts/figs/svgkit.py           # 共通の描画ヘルパ（SVG / build）
scripts/figs/<id>.py             # その教材の全図の生成元
scripts/figs/<id>.md             # 選定の記録、作画資料と引用写真の出典、検査メモ
docs/books/<id>/figs/<name>.svg  # 生成物。手で編集しない
```

- 1教材に `.py` と `.md` を1個ずつ。`follows` でつながるシリーズは先頭巻の `<id>.py` 1本で全巻を描き、出力パスで巻の `figs/` へ振り分ける。
- 外部の参考写真は `figs/` へ複製しない。ファイルページの表示用 URL を本文から直接参照する。

## `<id>.py` の形

```python
#!/usr/bin/env python3
"""<id> の図。

色：青=…（主役）／橙=…（注目点）／赤=…（破綻）。灰は背景と目盛。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import SVG, MAIN, FOCUS, MUTED, TINT, build  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/books/<id>/figs"


def rank():
    """2-1 rank は表を2回引いて残りだけ数える。M 560x300。

    x: 32 大区画の左端 / 282 右端 / 330 注記
    y: 60 帯の上端 / 150 下端 / 90 注記
    """
    s = SVG(560, 300, "大区画・小区画・残りの実測を足して rank を求める")
    ...
    return s


if __name__ == "__main__":
    sys.exit(build({OUT / "fig2-1-rank.svg": rank}))
```

- 図ごとの関数の docstring に、節番号・問い・形と表示幅、使う座標を先に書く。書いていない座標を使わない。
- 座標・曲線・数値は本文の式や入力値から計算する。本文の数値は `assert` で突き合わせてから描く。
- `python3 scripts/figs/<id>.py` で書き出し、`--check` で生成物との一致を確かめる。

## `<id>.md` の中身

- Phase 1 の採用スロットと却下候補（理由つき）。
- 作画資料：形・比率・配置を確かめるのに見た資料の URL と、取り出した事実。
- 引用写真：ファイルページ URL・作者・ライセンス・確認日。
- 検査結果の表。

| ファイル | 形・表示幅 | 機械検査 | 原寸 | 360px | 説明力 | 本文整合 |
|---|---|---|---|---|---|---|
| fig2-1-rank.svg | 横長 560x300・M | pass | pass | pass | pass | pass |

## 本文への埋め込み

単独行の画像＋一文のキャプション。画像は原寸へのリンクで包む。代替テキストには図が示す結論を書く。表示幅は `':size=<幅>'` で指定し、L（本文幅いっぱい）のときだけ省く。

```markdown
[![表を2回引き、残りだけ数えてrankを求める図](figs/fig2-1-rank.svg ':size=560')](figs/fig2-1-rank.svg)

図2-1：`rank_1(14)=3+2+1=6`。大区画、小区画、残りの実測を足す。
```

実物＋模式図は、引用写真と自作図を続けて置き、キャプションを1つにまとめて対応を書く。

```markdown
![海馬の錐体細胞の顕微鏡像](https://upload.wikimedia.org/…/file.jpg ':size=420')

[![写真と同じ向きで細胞体・樹状突起・スパインを描いた模式図](figs/fig1-neuron.svg ':size=420')](figs/fig1-neuron.svg)

図1：上が実物、下が同じ向きの模式図。*出典（上）：作者「資料名」[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:…)。CC BY-SA 4.0。*
```

- 直前の発言の末尾に、その図を指す一文を足す。画像は発言ブロックの外に置く。
- キャプションは `。` で閉じる（`dialogue-period`）。画像行とその直後のキャプションは、発言長の集計から外れる（`yaruo_markdown.figure_block_lines`）。
- KaTeX は SVG 内で動かない。数式は本文へ残す。

## 検査

```bash
python3 scripts/figs/<id>.py && python3 scripts/figs/<id>.py --check
python3 .claude/skills/zuhan/scripts/check_figure.py "docs/books/<id>/figs/*.svg" --png-dir /tmp/figpng
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check --verbose
python3 scripts/generate_site.py
git diff --check
```

- `check_figure.py` の NG はすべて直す。依存は `requirements-dev.txt`（`fonttools` / `cairosvg`）と日本語フォント `fonts-noto-cjk`。
- `--png-dir` の `*.png`（原寸）と `*.360.png`（スマホ幅）を両方開き、`layout.md` の「説明力の確認」6項目を見る。
- `yaruo_lint.py` は図を足す前にも走らせ、warning が増えていないことを比べる。
