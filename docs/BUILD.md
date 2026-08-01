# Build System

## ディレクトリ構造と生成フロー

### ソース・ビルド分離

```
docs/                  ← ソースのみ（git 追跡対象）
├── catalog.yml        ← カテゴリ定義
├── README.md          ← トップページ（手書き部分のみ）
├── _footer.md         ← フッター
└── books/*/
    ├── README.md      ← 各教材本文
    └── catalog.yml    ← 各教材のカタログ定義

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

- `docs/**/catalog.yml` を `scripts/generate_site.py` がビルド時に統合し、`docs/` のソースを `build/` にコピーして生成ファイルを追加・上書き
- カテゴリは `docs/catalog.yml`、教材情報は対応する `docs/books/{id}/catalog.yml` に置く
- 教材のタイトルは `catalog.yml` には書かず、本文 `README.md` の先頭行にある `# ` 見出しから取得する
- 教材の `created` には、旧 `docs/books/{id}.md` と現行パスを含む Git 履歴上の初出コミット日時をタイムゾーン付き ISO 8601 形式で記録し、カテゴリ内ではその昇順（同一日時は `id` の昇順）で表示する
- 教材の公開パスは `id` から `/books/{id}` として自動生成する
- 教材情報を `docs/books/{id}/catalog.yml` 以外に置いた場合や、IDが重複した場合はビルドエラー
- 生成対象：サイドバー・トップページ・教材SEOページ・サイトマップ
- 生成ファイルは直接編集したりコミットしたりしない（`.gitignore` で `build/` を除外）

### 複数パート教材（分冊）

長大な教材は `docs/books/{id}/` 内で複数ファイルに分割できる：

```
docs/books/{id}/
├── README.md      ← I部
├── README.2.md    ← II部
├── README.3.md    ← III部（以降 README.4.md ... と連番）
└── catalog.yml    ← パート分割してもエントリは1つのまま
```

- ファイル名は `README.md`（1部目）・`README.2.md`（2部目）・`README.3.md`（3部目）...の連番。1から始まり、欠番があるとビルドエラーになる
- `catalog.yml` のエントリはパート数によらず1教材1エントリ。`generate_site.py` がディレクトリ内の `README*.md` を自動検出してパート扱いするため、パート専用のカタログ登録は不要
- サイドバーには各パートが独立したエントリとして並び、タイトルを毎行繰り返した上でパート名と読了時間を付ける（例：`やる夫で学ぶ統計学 I部(20分)` `やる夫で学ぶ統計学 II部(53分)` ...）。パートごとに独立したリンクなので、docsify の `subMaxLevel` 設定により開いているパート内の見出し目次がそのリンクの下に自動表示される
- トップページ（教材一覧）では見出しをI部へのリンクのまま残し、その右にII部以降へのリンクを分数付きで並べる（例：`#### [やる夫で学ぶ統計学](...) (20分) ・ [II部(53分)](...) ・ [III部(24分)](...)`）。問い・プロットはシリーズ全体として1つだけ表示する
- 各パート本文の冒頭には手書きでパート間ナビ（例：`**I部** ／ [II部](./README.2.md) ／ [III部](./README.3.md)`）を置く。GitHub上でファイル単体を開いた読者や、サイトのパート個別URLへ直接来た読者が迷わないようにするため
- 本文中の相対リンク（`./README.2.md` など）は docsify の `relativePath: true`（`scripts/site_template.html`）により、現在開いているページのディレクトリを基準に解決される。この設定がないと相対リンクがサイトの basePath を失って404になるため、`docs/**/README*.md` 内で他ページへ相対リンクする際は素の相対パス（`./foo.md` や `../bar.md`）をそのまま使ってよい

## 開発時の手順

### 開発サーバ（推奨）

以下を実行し、表示された URL をブラウザで開く：

```bash
python3 scripts/dev_server.py
```

`docs/`、サイト生成スクリプト、テンプレートを監視し、変更すると自動的に再ビルドしてブラウザを再読み込みする。ビルドエラーが起きた場合は、ターミナルにエラーを表示したまま直前の正常なプレビューを維持し、次の変更時に再試行する。

標準では `127.0.0.1:3000` を使用する。変更する場合：

```bash
python3 scripts/dev_server.py --host 0.0.0.0 --port 8000
```

### 手動ビルド

教材ファイルを編集したら必ず実行：

```bash
python3 scripts/generate_site.py
```

### 手動でのローカル確認

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
- 同じディレクトリの `docs/books/{id}/catalog.yml` に登録済みか
- ファイルが実在するか：`ls docs/books/{id}/README.md`

## 設定ファイル

- **生成スクリプト：** `scripts/generate_site.py`
- **テンプレート：** `scripts/site_template.html`
- **カテゴリ定義：** `docs/catalog.yml`
- **教材カタログ定義：** `docs/books/*/catalog.yml`
- **デプロイ設定：** `.github/workflows/static.yml`
- **除外設定：** `.gitignore`（`/build/`）
