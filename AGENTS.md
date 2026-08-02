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

## ビルドシステム

ソース・生成の分離詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照。

- **`docs/`**: ソースのみ
- **`build/`**: 生成ファイル（`.gitignore` で除外）

## 文字数集計

概算：ファイルサイズ ÷ 3

正確な集計が必要なら `/yaruo-count` スキルを使用。

## エージェント間の書面協議

このリポジトリでは Codex と Claude が共同作業する。設計方針の比較や合意形成は `/discussion/{topic}/` 配下のファイル交換で行う（`.gitignore` 済み、コミットしない）。

- ファイル名は宛先を表す。`to-claude.N.md` は Codex が書き Claude が読む。`to-codex.N.md` はその逆。通番 N で往復する。
- **自分が読む側のファイルを自分で書いてはならない**（相手の発言の捏造にあたる）。返信が来なければ待つか、ユーザーへ報告する。
- 双方が末尾に `合意` を明記したら、気づいた側が `conclusion.md` を書く。
- 詳細な作法は `.claude/skills/discuss/SKILL.md` にある。Claude 側は `/discuss` スキルとして起動する。
