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
    ├── catalog.yml    ← 各教材のカタログ定義
    └── figs/*.{svg,png} ← 説明図の原本（描画コードまたは画像生成。任意）

build/                 ← 生成ファイル（git 除外）
├── index.html         ← トップページHTML（自動生成）
├── 404.html           ← エラーページ（自動生成）
├── _sidebar.md        ← サイドバー（自動生成）
├── README.md          ← カタログ付きREADME（自動生成）
├── _sidebar.draft.md  ← 下書き込みサイドバー（自動生成）
├── README.draft.md    ← 下書き込みトップページ（自動生成）
├── _footer.md         ← docs/ からコピー
├── assets/            ← docs/ からコピー
├── sitemap.xml        ← サイトマップ（自動生成）
├── books/*/README.md  ← docs/ からコピー
├── books/*/figs/      ← SVGはコピー、PNG原本は公開用WebPへ変換
└── books/*/index.html ← 各教材SEOページ（自動生成）
```

### 生成ルール

- `docs/**/catalog.yml` を `scripts/generate_site.py` がビルド時に統合し、`docs/` のソースを `build/` にコピーして生成ファイルを追加・上書き
- `docs/books/**` のPNG図版は原本として維持する。ビルド時に長辺1600px以下・200KiB以下のWebPへ変換し、公開Markdownの表示画像と原寸リンクをWebPへ差し替える。文字・細線を守るため圧縮を先に試し、必要な場合だけ縮小する。faviconなど `docs/books/` 外のPNGは対象外。開発時の継続ビルドでは、既存WebPがPNG原本と変換コードより新しく、容量上限内なら再圧縮せずに再利用する
- カテゴリは `docs/catalog.yml`、教材情報は対応する `docs/books/{id}/catalog.yml` に置く
- 教材のタイトルは `catalog.yml` には書かず、本文 `README.md` の先頭行にある `# ` 見出しから取得する
- 教材の `created` には、旧 `docs/books/{id}.md` と現行パスを含む Git 履歴上の初出コミット日時をタイムゾーン付き ISO 8601 形式で記録し、カテゴリ内ではその昇順（同一日時は `id` の昇順）で表示する
- 教材の公開パスは `id` から `/books/{id}` として自動生成する
- 教材情報を `docs/books/{id}/catalog.yml` 以外に置いた場合や、IDが重複した場合はビルドエラー
- 生成対象：サイドバー・トップページ・教材SEOページ・サイトマップ
- `follows: <ID>` を持つ教材は `created` の順ではなく、その教材の直後に並ぶ。詳細は下の「シリーズ（連続する教材）」を参照
- `draft: true` の教材は一覧から外す。詳細は下の「下書き（draft）」を参照
- 生成ファイルは直接編集したりコミットしたりしない（`.gitignore` で `build/` を除外）

### 下書き（draft）

`docs/books/{id}/catalog.yml` の教材エントリに `draft: true` を付けると、その教材は**公開の一覧に出ないまま本番と同じ経路でビルド・デプロイ**される。図版・スライド・ルビ変換・SEOページはすべて通常どおり生成されるので、公開後とまったく同じ表示で読める。

| 生成物 | 通常の教材 | `draft: true` |
|---|---|---|
| `README.md`（トップ一覧）・`_sidebar.md`・`sitemap.xml` | 載る | 載らない |
| `README.draft.md`・`_sidebar.draft.md` | 載る | 載る（`【下書き】` 付き） |
| `books/{id}/` の本文・図版・スライド・`index.html` | 生成する | 生成する（`noindex` 付き） |

- 下書きしか持たないカテゴリは、公開側の一覧から見出しごと消える。「カテゴリに教材が1つも無い」ビルドエラーは下書きを含む全体で判定するので、これには当たらない
- `draft` は真偽値のみ。省略時は `false`
- 公開するときは `draft: true` の1行を消すだけ。URLも `created` も変わらない

閲覧側の切り替えは、サイトを `?draft=1` 付きで開くと下書き込みの一覧に、`?draft=0` で通常に戻る。選択は `localStorage` に残る（history モードのリンク遷移でクエリ文字列が落ちるため、クエリだけでは1クリックで解ける）。下書き表示中は右下に「下書き表示中 ✕」のバッジが出て、タップで解除できる。切り替えは `scripts/site_template.html` の draft-mode ブロックが docsify の設定を組み立てる前に決めるので、一覧が二度描画されることはない。

なお下書きの教材ページ自体は、下書き表示が off でもURL直打ちで読める。隠しているのは一覧とサイトマップだけで、認証ではない。

### シリーズ（連続する教材）

1冊に収まらない教材は、巻ごとに独立した教材として書き、`follows` で前の巻につなぐ。1つの教材ディレクトリに本文を複数置く分冊（`README.2.md` など）は廃止した。`docs/books/{id}/` に `README.<数字>.md` があるとビルドエラーになる。

```
docs/books/statistics/     ← I巻（README.md, catalog.yml, figs/）
docs/books/statistics-2/   ← II巻。catalog.yml に follows: statistics
docs/books/statistics-3/   ← III巻。catalog.yml に follows: statistics-2
```

```yaml
documents:
- id: statistics-2
  category: math-information
  created: '2026-07-29T00:12:20+09:00'
  follows: statistics
  question: ...
  plot: ...
```

- 各巻は普通の教材と同じく、ID・`README.md`・`catalog.yml`（`question` と `plot` はその巻の内容）・`figs/`・URL・読了時間・サイトマップ項目をそれぞれ持つ。サイドバーとトップページにも1巻1項目で出る
- `follows` が変えるのは並び順だけ。`follows: <前の巻のID>` を持つ教材は、自分の `created` にかかわらず前の巻の直後に並ぶ。連鎖はそのまま続くので、I巻→II巻→III巻と途切れずに並ぶ。同じ巻の直後に複数の教材が続く場合は、その間を `created` と `id` の昇順で並べる
- `follows` の先は存在するIDで、同じカテゴリでなければならない。循環もビルドエラー
- 巻のIDは先頭巻のIDに `-2`・`-3` … を付ける（改訂版の `-v2` とは別物）。タイトルは各巻の `README.md` の `# ` 見出しで、`やる夫で学ぶ統計学 II ── …` のように巻番号を入れる
- 下書きは巻ごとに付けられる。前の巻が下書きで一覧から消えても、後の巻は前後の位置を保ったまま表示される
- 巻の冒頭と末尾には手書きで巻間ナビ（例：`**I部** ／ [II部](../statistics-2/README.md) ／ [III部](../statistics-3/README.md)`）を置く。GitHub上でファイル単体を開いた読者や、途中の巻へ直接来た読者が迷わないようにするため
- 本文中の相対リンクは docsify の `relativePath: true`（`scripts/site_template.html`）により、現在開いているページのディレクトリを基準に解決される。この設定がないと相対リンクがサイトの basePath を失って404になるため、`docs/**/README.md` 内で他の教材へリンクする際は素の相対パス（`../statistics-2/README.md`）をそのまま使ってよい

## 開発時の手順

### 依存関係のセットアップ

Python の開発・ビルド依存は `requirements-dev.txt` にまとめる。Pillow は公開画像の変換に使うため、本文だけを編集した場合も全体ビルドに必要。

初回はリポジトリルートで仮想環境を作る。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

`No module named pip` や `ensurepip is not available` が出る Debian・Ubuntu 環境では、先に OS 側のパッケージを導入してから上の手順を実行する。

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv
```

次回以降も作業開始時に `source .venv/bin/activate` を実行する。`git pull` で `requirements-dev.txt` が更新された場合は、仮想環境を有効にして `python3 -m pip install -r requirements-dev.txt` を再実行する。ビルドも同じ環境の `python3` で実行する。

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

本文 Markdown（`docs/books/*/README.md`）だけが変わったときは、全体ビルドを回さずにそのファイルだけをルビ変換して差し替える。ブラウザ側は更新種別にかかわらずページ全体を再読み込みせず、現在開いている Markdown を取り直す。内容が変わっていれば docsify の本文だけを描画し直し、スクロール位置を保ったまま更新する（`/__dev/revision` を更新通知として使う）。

### プレビュー上のコメント

プレビューでは本文を選んでコメントを付け、常駐したエージェントにその場で直させられる。使い方と仕様は [`COMMENTS.md`](./COMMENTS.md) を参照。

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

不足パッケージだけを理由に停止し、グローバル環境を汚したくないなら `uv` で検証する。

```bash
uv run --with-requirements requirements-dev.txt python scripts/generate_site.py
```

`requirements-dev.txt` はバージョンを範囲で書いてある。完全一致で固定すると、OS のパッケージ管理が入れた同名パッケージ（`python3-yaml` など）を pip が消せず、install 全体が落ちるため。**新しい依存を足すときも `==` を使わない。**

図版の検査に使う `fonttools`（豆腐検査）と `cairosvg`（PNG 書き出し）も同じファイルに入っている。

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
