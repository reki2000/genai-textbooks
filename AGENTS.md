# Repository instructions

## ディレクトリ構造と生成フロー

### ソース・ビルド分離

ソースファイルと生成ファイルを明確に分離します：

```
docs/                  ← ソースのみ（git 追跡対象）
├── catalog.yaml       ← 教材カタログ（構成定義）
├── README.md          ← トップページ（手書き部分のみ）
├── _footer.md         ← フッター
└── books/*/README.md  ← 各教材本文

build/                 ← 生成ファイル（git 除外）
├── index.html         ← トップページHTML（自動生成）
├── 404.html           ← エラーページ（自動生成）
├── _sidebar.md        ← サイドバー（自動生成）
├── README.md          ← カタログ付きREADME（自動生成）
├── sitemap.xml        ← サイトマップ（自動生成）
└── books/*/index.html ← 各教材SEOページ（自動生成）
```

### 生成ルール

- `docs/catalog.yaml` を正本として `scripts/generate_site.py` がビルド時に `build/` 全体を生成
- 生成対象：サイドバー・トップページ・教材SEOページ・サイトマップ
- 生成ファイルは直接編集したりコミットしたりしない（`.gitignore` で `build/` を除外）

### 開発時の確認手順

教材カタログ、カテゴリ、表示順、タイトル・URL・問い・プロット、または `docs/books/*/README.md` の追加・削除・改名を扱うときは `docs/catalog.yaml` を編集し、以下を実行：

```bash
python3 scripts/generate_site.py        # build/ を生成
npx docsify serve build                # ローカル確認
git add docs/                           # docs/ のみをステージ
git commit -m "..."
git push
```

**重要：`build/` は `.gitignore` で自動除外されるため、意識的にコミットする必要があります。**

### デプロイフロー

1. **PR時** → GitHub Actions が `generate_site.py` で `build/` を生成（確認のみ）
2. **メインブランチマージ時** → GitHub Actions が:
   - `generate_site.py` で `build/` を生成
   - `build/` 全体を GitHub Pages にデプロイ

### 文字数集計

教材の文字数は、簡便のためファイルサイズ ÷ 3 で概算する（換算規則の正本と正確な集計は yaruo-count スキル）。yaruo-count スキルは、`scripts/generate_site.py` の読了時間算出（内部で `count_document` を利用）か、規則に基づく正確な集計をユーザーが明示的に求めたときだけ使う。
