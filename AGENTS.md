# Repository instructions

## サイドバー・トップページ・教材ページの生成

`docs/_sidebar.md`、`docs/README.md` の教材一覧ブロック、`docs/index.html`・`docs/404.html`、`docs/books/*/index.html`（各教材のSEO用ページ。教材本文は同じフォルダの `README.md`）、`docs/sitemap.xml` は `docs/catalog.yaml` を正本として `scripts/generate_site.py` がビルド時（GitHub Actions）に自動生成する。これらは生成物であり、直接編集したりコミットしたりしない（`.gitignore` 参照）。

- 教材カタログ、カテゴリ、分類、表示順、タイトル・URL・問い・プロット、または `docs/books/*/README.md` の追加・削除・改名を扱うときは、`docs/catalog.yaml` を編集する（対応する `docs/books/*/README.md` があれば同じ変更内で整合させる）。手元で確認する場合は `python3 scripts/generate_site.py` を実行する。
- 教材の文字数は、簡便のためファイルサイズ / 3 で概算すること（換算規則の正本と正確な集計は yaruo-count スキル）。yaruo-count スキルは、`scripts/generate_site.py` の読了時間算出（内部で `count_document` を利用）か、規則に基づく正確な集計をユーザーが明示的に求めたときだけ使う。
