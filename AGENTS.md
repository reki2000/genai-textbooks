# Repository instructions

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
2. 同じディレクトリの `docs/books/{ID}/catalog.yml` に教材情報を登録
3. `python3 scripts/generate_site.py` でビルド確認
4. `git add docs/` でコミット

外部（別モデル・別セッション）で書かれた教材を受け入れるときは、2の前に `/yaruo-review` で品質を検査する。

## 検査・整形スクリプト

`scripts/yaruo_lint.py` が唯一の入口。`--check` / `--fix` / `--rules <id>` / `--verbose`、一覧は `--list-rules`。

```bash
python3 scripts/yaruo_lint.py docs/books/{ID}/README.md --check --verbose
```

- **error** は必ず解消する。**warning** は人が内容を見て判断する。**info は診断であって合否に使わない。**
- 話者行・非散文領域の判定は `scripts/yaruo_markdown.py` が正本。`yaruo_lint.py` と `count_textbooks.py` が共有する。
- ルールを変えたら `python3 scripts/tests/run_lint_tests.py` を実行する（fixture は `scripts/tests/fixtures/<ルールID>/`）。

## ビルドシステム

ソース・生成の分離詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照。

- **`docs/`**: ソースのみ
- **`build/`**: 生成ファイル（`.gitignore` で除外）

## 文字数集計

概算：ファイルサイズ ÷ 3

正確な集計が必要なら `/yaruo-count` スキルを使用。

## エージェント間の書面協議

このリポジトリでは Codex と Claude が共同作業する。設計方針の比較や合意形成は `/discussion/{yyyymmdd-hhmiss}-{topic}/` 配下のファイル交換で行う（`.gitignore` 済み、コミットしない）。

- ディレクトリ名は開始日時（`date +%Y%m%d-%H%M%S`）＋話題。例：`20260802-143012-sidebar-layout`。
- ファイル名は「通番＋宛先」。`1.to-claude.md` は Codex が書き Claude が読む。`2.to-codex.md` はその逆。通番は議論全体で1本の連番で、ファイル名順＝発言順になる。
- **進行中の議論は `discussion/CURRENT`（ディレクトリ名を1行）だけが指す。** 開始した側が書き、`conclusion.md` を書いた側が削除する。過去のディレクトリを更新時刻や日時で推測して読みに行かない。`CURRENT` が無ければ進行中の議論は無い。
- この仕組みにより、片側で議論を開始したあと、もう片側には「議論して」とだけ言えばよい。
- **自分が読む側のファイルを自分で書いてはならない**（相手の発言の捏造にあたる）。返信が来なければ待つか、ユーザーへ報告する。
- 双方が末尾に `合意` を明記したら、気づいた側が `conclusion.md` を書く。
- 詳細な作法は `.claude/skills/discuss/SKILL.md` にある。Claude 側は `/discuss` スキルとして起動する。
