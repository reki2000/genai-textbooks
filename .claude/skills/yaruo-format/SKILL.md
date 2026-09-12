---
name: yaruo-format
description: やる夫式教材のMarkdownを scripts/yaruo_lint.py で検査・整形する。lint、強調・表の表示崩れ、カギカッコ・句点・丸囲み数字・単位表記の修正で使う。
---

# やる夫式教材 書式整形スキル

対象は `docs/books/*/README.md`。書式の正本は [format.md](../yaruo-rediscovery/references/format.md)。自動修正できる項目はスクリプトで処理し、warning は本文を確認して判断する。

## 手順

```bash
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check
# error があれば適用し、再検査する
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --fix
python3 scripts/yaruo_lint.py docs/books/<id>/README.md --check
```

ルールの適用順は `--fix` の内部で固定されている（会話表記を確定させてから強調・表・句点）。個別に回したいときだけ `--rules <id>` を使う。`--list-rules` で一覧。

| ルールID | 直すもの |
|---|---|
| `dialogue-frame` | 発言外枠のカギカッコ、行頭の全角空白 |
| `emphasis-flanking` | 約物に隣接して壊れた `**` |
| `table-delimiter` | GFM 表の区切り行、表の行頭空白 |
| `dialogue-period` | 発言末の句点（`〜〜 翌朝 〜〜` 等の場面転換カードは発言境界として除外） |
| `circled-numbers` | 丸囲み数字（①②③…⑳）を半角の `(1)(2)(3)…` に書き換え |
| `unit-notation` | メートル・グラム系単位のカタカナ表記を `m` `km` `g` `kg` 等へ書き換え |
| `heading-level` | 幕見出しを `##`、節見出しを `###` に統一（`####` 以下を禁止） |
| `structure-delimiter` | `##` / `###` の直前は空行1行＋`---`、直後は `---` なしの空行1行に統一 |

再検査で error が0件になることを確認する。warning は下表で判断し、info は合否に使わない。`git diff` で修正件数との整合と意図しない本文変更がないことを確認する。

## warning への対応

自動修正せず報告するものは、該当行を目視して手で直す。

| warning | 対応 |
|---|---|
| 壊れた発言外枠（対応する `」` が無い） | 先頭の `「` だけ削除済み。閉じ位置を手で確認する |
| `**` の直後（直前）が空白 | `** 重要**` 型の書き間違い。空白を内側から外側へ移す |
| 区切り行の列数がヘッダと不一致 | GFM では表にならない。区切り行の列数をヘッダに合わせる |
| 表の直前が空行でない | 段落の続きと解釈される。空行を1行入れる |
| 直前の行に `|` が含まれる | ヘッダ行が別の文と融合している可能性。そのブロックは自動修正していない |
| 読点・コロン・セミコロンで終わる発言 | 句点を自動補完していない。文が途中で切れていないか確認する |

コードブロック・インラインコード・TeX数式内は対象外。表示崩れの原因と予防は [format.md](../yaruo-rediscovery/references/format.md) を参照する。

## 回帰

ルールを変更したら必ず実行する。fixture は `scripts/tests/fixtures/<ルールID>/` に input と expected の対で置く。

```bash
python3 scripts/tests/run_lint_tests.py
```

## 完了報告

ファイルごとに、ルール別の修正件数、warning の一覧と各々への対応（手で直した／問題なしと判断した）、`git diff --stat` との整合を報告する。
