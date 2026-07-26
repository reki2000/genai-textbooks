# Build System

## ディレクトリ構造と生成フロー

### ソース・ビルド分離

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
├── _footer.md         ← docs/ からコピー
├── assets/            ← docs/ からコピー
├── sitemap.xml        ← サイトマップ（自動生成）
├── books/*/README.md  ← docs/ からコピー
└── books/*/index.html ← 各教材SEOページ（自動生成）
```

### 生成ルール

- `docs/catalog.yaml` を正本として `scripts/generate_site.py` が `docs/` のソースを `build/` にコピーし、生成ファイルを追加・上書き
- 生成対象：サイドバー・トップページ・教材SEOページ・サイトマップ
- 生成ファイルは直接編集したりコミットしたりしない（`.gitignore` で `build/` を除外）

## 開発時の手順

### ローカルビルド

教材ファイルを編集したら必ず実行：

```bash
python3 scripts/generate_site.py
```

### ローカル確認

```bash
npx docsify serve build
```

### コミット時の注意

**絶対禁止：** `build/` ディレクトリを含める

```bash
# ✅ 正しい
git add docs/
git commit -m "..."

# ❌ 間違い
git add -A                    # build/ を含む可能性
git add docs/ build/          # build/ を明示的に追加
```

**確認方法：**
```bash
git diff --cached | grep build/
# 出力がなければOK
```

## CI/CD フロー

### PR時（テスト）

1. GitHub Actions が `generate_site.py` で `build/` を生成
2. ビルド成功を確認
3. デプロイはしない（確認のみ）

### メインブランチプッシュ時（本番）

1. GitHub Actions が `generate_site.py` で `build/` を生成
2. `build/` 全体を GitHub Pages にデプロイ（`.github/workflows/static.yml` で定義）

## トラブルシューティング

### 「build が git に含まれた」エラー

問題：既にコミットしてしまった場合

解決方法：
```bash
# build/ をトラッキングから削除
git rm -r --cached build/
git commit -m "Remove build/ from tracking"
```

### `generate_site.py` エラー

確認事項：
```bash
# 構文チェック（実行しない）
python3 scripts/generate_site.py --check

# PyYAML のインストール確認
python3 -m pip install -r requirements-dev.txt
```

### 教材ファイルが認識されない

確認事項：
- ファイルパス：`docs/books/{id}/README.md` の形式
- `docs/catalog.yaml` に登録済みか
- ファイルが実在するか：`ls docs/books/{id}/README.md`

## 設定ファイル

- **生成スクリプト：** `scripts/generate_site.py`
- **テンプレート：** `scripts/site_template.html`
- **カタログ定義：** `docs/catalog.yaml`
- **デプロイ設定：** `.github/workflows/static.yml`
- **除外設定：** `.gitignore`（`/build/`）
