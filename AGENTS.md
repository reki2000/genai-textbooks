# Repository instructions

## コマンドラインツール

- `ripgrep` (`rg`) が利用可能なら、ファイル内検索には `grep` より `rg`、ファイル一覧の取得には `find` より `rg --files` を積極的に使う。
- [`rtk`](https://github.com/rtk-ai/rtk) が利用可能なら、対応するコマンド（`rtk git`、`rtk test`、`rtk lint`、`rtk rg` など）を積極的に使い、出力を必要十分な内容に絞る。未対応の操作や、生の完全な出力が必要な場合は通常のコマンドを使う。

## catalog.yml 構造

カテゴリはトップページの隣の `docs/catalog.yml` で定義：

```yaml
categories:
  - id: social
    title: 社会と制度
    order: 1
```

教材情報は本文の隣の `docs/books/{ID}/catalog.yml` で定義：

```yaml
documents:
  - id: japan-food
    category: social
    created: '2026-07-16T12:10:45+00:00'
    question: 食料自給率を上げれば本当に安全なのか？
    plot: 深夜の牛丼屋で一杯の牛丼を分解しながら...
```

教材の公開パスは `id` から `/books/{ID}` として自動生成される。
教材タイトルは `catalog.yml` ではなく、`README.md` の先頭行にある `# ` 見出しを用いる。

`created` には、旧 `docs/books/{ID}.md` と現行の本文パスを含む Git 履歴上の初出コミット日時を設定する。教材はカテゴリ内で `created` の昇順に表示し、同一日時の場合は `id` の昇順。

## 教材追加手順

1. `/yaruo-rediscovery` で教材を執筆 → `docs/books/{ID}/README.md`
2. `/yaruo-checkpoint` で到達目標を確定 → `docs/books/{ID}/checkpoints.yml`
3. 同じディレクトリの `docs/books/{ID}/catalog.yml` に教材情報を登録
4. `python3 scripts/generate_site.py` でビルド確認
5. `git add docs/` でコミット

外部（別モデル・別セッション）で書かれた教材を受け入れるときは、3の前に `/yaruo-review` で品質を検査する。判定基準と二者レビューの手順はスキルの `SKILL.md` を正本とする。

## 学習成果

本文は改訂され続けるので、「何幕まで読んだ」を学習成果の正本にしない。正本は概念で、`docs/books/{ID}/checkpoints.yml` に 5〜15 個の到達目標（「〜を説明できる」）と、読了直後・翌日・数日後の想起練習（説明・予測・転移）を置く。書式と個数の正本は `scripts/checkpoints.py`、作り方は `/yaruo-checkpoint`。

```bash
python3 scripts/checkpoints.py docs/books/{ID}/checkpoints.yml --check --verbose
python3 scripts/checkpoints.py docs/books/{ID}/checkpoints.yml --quiz 翌日
```

id は学習記録の宛先なので振り直さない。概念が消えたら行を消さず `retired: true` にする。

## レビューの資産化

プレビューのコメント（`comments/`）は `.gitignore` 済みで消える。**人が resolved にした指摘だけ**を `review-corpus/` へ凍結し、類似の指摘を束ねてから再発防止ルールへ昇格させる。**1件の指摘を直接スキルのルールへ書き足さない。** 入口は `scripts/review_corpus.py`、判断と昇格の手順は `/yaruo-retrospect`。昇格には発生3件以上・2教材以上・人の承認が要る。

## モデルと effort

工程ごとの使い分けは [`MODELS.md`](./MODELS.md)。**一つの最強モデルを決めない。** 仮説と実測を分けて書き、実測は `bench/` の結果でのみ書き換える。

## 制作工程ベンチマーク

モデル選定用の評価セットは実際の制作物から作る（6タスク：問題発見・コメント対応・再発見化・難所説明・構成改善・新規執筆）。設計の正本は [`bench/README.md`](./bench/README.md)、道具は `scripts/bench.py`。**単一スコアで順位を決めず、能力プロファイルを出す。**

## 図版

説明図は `/zuhan` で追加する。選定・手段の使い分け・作図規約・機械検査・本文への埋め込み方まで、すべてスキルが正本（このリポジトリ固有の配置と検査は `.claude/skills/zuhan/references/repo.md`）。

図は手書きしない。決定的に描画できる図は `scripts/figs/{ID}.py` で生成し、画像生成を使う図は最終プロンプト・生成手段・検査メモを `scripts/figs/{ID}.md` に残す。生成物は `docs/books/{ID}/figs/` へ置いてコミットする。再利用できる描画ヘルパと配色は `scripts/figs/svgkit.py`。

旧スキルで描いた図は作図規約が違うためすべて破棄した。図を戻すときは `/zuhan` の Phase 1（選定）からやり直す。

## ルビ

ルビは青空文庫式 `｜基底《よみ》` で書く（区切りは全角の `｜` `《` `》`、`｜` は省略しない）。表のセル区切り `|` やTeXの `{}` と衝突せず、変換されない場所でもそのまま読める。`scripts/generate_site.py` がビルド時に `<ruby>` HTML へ変換し、コードスパン・フェンス・`$…$` / `$$…$$` の中は素通しする。`｜《》` は Unicode の約物なので `**｜台詞《せりふ》**` のように隣接すると CommonMark の flanking 規則で太字が壊れるため、変換後の `<ruby>` はゼロ幅文字（U+200C）で挟む。marp スライドはこの変換を通らないので `slide.md` では使わない。

読みは注記であって散文ではないので、字数の集計では基底だけを数える（`yaruo_markdown.strip_ruby` を `yaruo_lint.py` の発言長と `count_textbooks.py` の文字数・読了時間が共有する）。バイト数だけはファイル実寸なのでルビを含む。

## 検査・整形スクリプト

書式・数値制約の検査は `scripts/yaruo_lint.py` が唯一の入口。`--check` / `--fix` / `--rules <id>` / `--verbose` / `--stats`、一覧は `--list-rules`。

```bash
python3 scripts/yaruo_lint.py docs/books/{ID}/README.md --check --verbose
```

- **error** は必ず解消する。**warning** は人が内容を見て判断する。**info は診断であって合否に使わない。**
- 話者行・非散文領域の判定は `scripts/yaruo_markdown.py` が正本。`yaruo_lint.py` と `count_textbooks.py` が共有する。
- ルールを変えたら `python3 scripts/tests/run_lint_tests.py` を実行する（fixture は `scripts/tests/fixtures/<ルールID>/`）。

スクリプトを変えたら、対応する回帰を走らせる。

| 変えたもの | 走らせるもの |
|---|---|
| `yaruo_lint.py` | `scripts/tests/run_lint_tests.py` |
| `comments.py` / `dev_server.py` | `scripts/tests/run_comment_tests.py` |
| `yaruo_review_eval.py` | `scripts/tests/run_review_eval_tests.py` |
| `checkpoints.py` | `scripts/tests/run_checkpoint_tests.py` |
| `review_corpus.py` | `scripts/tests/run_corpus_tests.py` |
| `bench.py` | `scripts/tests/run_bench_tests.py` |

会話の同型反復は `scripts/yaruo_beat_repetition.py`（`--show` / `--beats` / `--units`）。lint とは別系統で、**合否ではなくレビュー時の候補区間の絞り込み**に使う。ラベル体系と指標の正本は `.claude/skills/yaruo-review/references/beat-labels.md`。

## プレビュー上のコメント

開発サーバのプレビューで本文にコメントを付け、常駐したエージェント（`/comment-eater`）がその場で直す経路がある。ファイル形式・アンカー解決・状態遷移の詳細は [`COMMENTS.md`](./COMMENTS.md) を参照。

## ビルドシステム

ソース・生成の分離詳細は [`BUILD.md`](./BUILD.md) を参照。

- **`docs/`**: ソースのみ
- **`build/`**: 生成ファイル（`.gitignore` で除外）

## 文字数集計

概算：ファイルサイズ ÷ 3

正確な集計が必要なら `/yaruo-count` スキルを使用。

## エージェント間の書面協議

Codex と Claude の設計比較・レビュー照合・合意形成には `/discuss` を使う。進行中の議論は `discussion/CURRENT` だけから特定し、自分宛ての発言ファイルは作成・編集しない。ファイル形式、待機、合意、終了処理の正本は `.claude/skills/discuss/SKILL.md` とする（`discussion/` はコミットしない）。
