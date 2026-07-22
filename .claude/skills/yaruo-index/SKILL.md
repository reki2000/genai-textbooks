---
name: yaruo-index
description: やる夫式教材集のカタログと公開目次を `docs/catalog.yaml` で一元管理し、`docs/_sidebar.md` とトップページ `docs/README.md` の教材一覧を再生成・検証するスキル。教材（`docs/books/*.md`）の追加・削除・改名、目次・教材一覧・索引の更新、カテゴリ・分類・表示順・タイトル・URL・問い・プロットの変更、sidebarやトップページへの反映、カタログ生成エラーの修正を依頼された場合は必ず使うこと。yaruo-rediscovery（教材作成）、yaruo-format（書式整形）、yaruo-proofread（校正）とは独立しており、該当する作業では併用する。読了時間の算出には yaruo-count の集計スクリプトを内部利用する。
---

# やる夫教材目次管理

教材カタログを唯一の正本として更新し、公開用Markdownを決定的に再生成する。生成ファイルを手作業で同期しない。

## 管理対象

- 正本：`docs/catalog.yaml`
- 全体を生成：`docs/_sidebar.md`
- 生成マーカー内だけを生成：`docs/README.md`
- 生成スクリプト：`.claude/skills/yaruo-index/scripts/generate_catalog.py`

生成時に `yaruo-count` スキルの集計スクリプトを使って各教材の読了時間を自動計算し、サイドバーとトップページの各教材リンクの後ろへ `(0分)` 形式で付与する。計算規則や実装をこのスキルやカタログへ重複して持たせない。

`docs/README.md` の生成マーカー外にあるサイト説明は手動管理とし、このスキルでは変更しない。

## YAML構造

トップレベルにカテゴリ一覧と文書一覧を並べる。文書をカテゴリ配下へネストしない。

```yaml
categories:
  - id: category-id
    title: 表示名
    order: 10

documents:
  - id: document-id
    title: 教材名
    path: /books/document-id
    category: category-id
    order: 10
    question: 教材を貫く問い。
    plot: 教材のプロット。
```

- `documents[].category` から `categories[].id` を参照する。
- `categories[].order` でカテゴリ順、`documents[].order` でカテゴリ内の文書順を指定する。
- `id` と `path` は文書ごとに一意にする。`order` は同じ階層内で一意にする。
- `path: /books/foo` は `docs/books/foo.md` と対応させる。
- 意図的なURL移行でない限り、既存文書の `path` を変更しない。

## 更新手順

1. `git status --short` と `docs/catalog.yaml` を確認し、既存の未コミット変更を保護する。
2. 依頼内容に応じて `docs/catalog.yaml` を更新する。教材の追加・削除・改名では、対応する `docs/books/*.md` も同じ変更内で整合させる。
3. 次のコマンドで公開目次を生成する。

   ```bash
   python3 .claude/skills/yaruo-index/scripts/generate_catalog.py
   ```

4. 次のコマンドで再生成差分がないことを確認する。

   ```bash
   python3 .claude/skills/yaruo-index/scripts/generate_catalog.py --check
   ```

5. `git diff --check` と対象ファイルの差分を確認する。`docs/catalog.yaml`、`docs/_sidebar.md`、`docs/README.md` の生成範囲が同じ内容になっていることを確認する。

PyYAMLが無い場合だけ、リポジトリルートで次を実行する。

```bash
python3 -m pip install -r requirements-dev.txt
```

## 検証仕様

生成スクリプトに次を検証させる。検証を回避するために生成物を直接編集しない。

- カテゴリID・カテゴリ順の重複
- 文書ID・URL・カテゴリ内順の重複
- 未定義カテゴリへの参照
- 不正なURLまたは存在しない教材ファイル
- `docs/books/*.md` にある未登録教材
- 文書が一つもないカテゴリ
- トップページの生成マーカー欠落
- 各教材から算出した読了時間がサイドバーとトップページに反映されていること
- YAMLと生成済みMarkdownの不一致（`--check`）

## 完了報告

変更したカテゴリまたは教材、再生成したファイル、`--check` の結果を簡潔に報告する。
