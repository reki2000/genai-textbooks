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

### 評価（ratings）

各教材の `catalog.yml` に、エンタメ学習コンテンツとしての評価を `ratings` で持たせる。トップページの一覧に総合評価・順位と3つの評価が表示される（サイドバーには出ない）。

```yaml
  ratings:
    knowledge: 4.75
    appeal: 5.0
    structure: 5.0
    overall: 4.92
```

| キー | 一覧での表示名 | 意味 |
|---|---|---|
| `knowledge` | 知識の充実 | 具体的な知識の量と、その分野の主要テーマの網羅、定着のしやすさ |
| `appeal` | 面白さ | 読ませる力 |
| `structure` | 物語の構成 | プロットと構成 |
| `overall` | 総合評価 | 3つの評価の平均 |

- 値はすべて1.0〜5.0。`overall` は3つの評価の平均（小数第2位まで）でなければならない。ずれていればビルドエラーになる
- `knowledge` は、もともと別軸だった「知識の量と定着のしやすさ」と「その分野の知識のカバレッジ」が重なっていたため統合した軸で、両者の平均を取る。そのため4.75のような0.25刻みの値になりうる
- 順位はカタログには持たせず、ビルド時に全教材の `overall` から自動計算する（同点は `knowledge`→`appeal`→`structure` の順に高い方を上位とし、最後は `id` 順）。1冊の評価を変えても、他の教材のカタログを直す必要はない
- `ratings` 自体は任意。無い教材は一覧に評価行が出ないだけで、ビルドは通る

### 改訂比較（revision_of）

改訂版の教材は、`catalog.yml` に `revision_of: <比較元のID>` を持たせることで、比較元との差分ページを持てる。

```yaml
  revision_of: electromagnetism
```

- ビルド時に `books/{id}/diff.md` が生成され、教材ページの冒頭とトップページの一覧からリンクされる（元の `README.md` 自体は変更しない。リンクはビルド成果物側にだけ付く）
- 差分ページは改訂版の全文をそのまま表示し、変わった所だけを目立たせる。変わっていない行は無色で出し、異なる行は最大5行ずつの塊に分けて、左右2ペインで旧（比較元・赤）を左、新（こちら・青）を右に並べる（狭い画面では上下に積む）。行内のハイライトは、塊の中で類似度により対応づいた行同士についてだけ、実際に異なる部分を同系の薄い色で付ける（対応づかない行には付けない。位置だけで対応づけると差分でない部分にハイライトが付くため）。削除された行は消えた位置に赤で差し込む。塊ごとに「旧／新」のラベルや説明は付けず、色だけで示す。塊に枠線や余分な余白は付けず、他の行と同じ行間で流す
- 差分ページは通常のMarkdownとして生成する（docsifyとKaTeXの描画を本文ページと壊さず揃えるため）。本文は原文のまま出し、色づけは変更箇所を包むコンテナと行内ハイライトだけで行う。数式（`$$`ブロック）、表、コードブロックは丸ごと1つの差分単位として扱い、内部にハイライトを入れない
- 差分判定は幕（`##` 見出し）と節（`###` 見出し）の単位で区切る。まず幕同士を対応づけ、幕の中では節同士をその幕の中だけで対応づける。行の対応づけは節も幕もまたがない。両版とも節を持つ幕だけを節に割り、どちらかに節がない幕は幕全体で判定する。幕の中での節の対応づけは見出し（節番号を除いて比較）・内容の同一行の重なりの順に行い、最後まで残った節同士は順番に対応づける（書き換えられた節を、節単位の差し替えとして扱うため）
- ただし幕・節の単位が丸ごと異なる場合は行同士を対応づけず、その単位で全文を並べる。単位の対応づけは見出し（番号を除いて比較し、改題された単位は内容の同一行の重なりでも対応づける）で行い、対応した単位同士で同一行の割合が2割未満なら「丸ごと異なる」と判定する。片側にしかない単位もその単位で表示し、長い単位は折りたたむ
- 空行・話者ラベルだけの行（`**やる夫**：`）・ラベルを除いて数文字しかない行（弱い行）だけの一致は、対応づけのアンカーにしない。これらは全書に何万回も現れるため、アンカーにすると全く別のやり取り同士が発言ごとに一致したことにされ、差し替わった範囲が発言単位の差分に見えてしまう。一致した範囲は、中身のある行を含む場合にだけ採用し、発言をまたいで差し替わった範囲は1つの差し替えとしてまとめて表示する（変わっていない会話の中の弱い行は、その範囲の一部として一致する）。同一行の割合（節の判定・対応づけ）も、弱い行を除いて数える
- `revision_of` の指すIDが存在しない場合と、自分自身を指す場合はビルドエラーになる
- 付けるのは小改訂のときだけ。全面書き直しは共通する行が少なく、行単位の差分が実態を表さないので付けない（例：`standard-model-v3`、`ultimate-detergent-v2`、`water-infrastructure-v3` は付けていない。新本文のうち旧と同一の行が34%以下しかない）

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

### 台本形式（@形式、試行中）

`docs/books/{id}/script/` を持つ教材は、そこにある幕ごとのファイル（`00.txt` が前付け、`01.txt` 以降が `## ` 見出しごとの幕）が正本で、`README.md` はそこから生成する。現在は `statistics`・`statistics-2`・`statistics-3`・`fluid-mechanics`。

```
@u7f3a やる夫
任せるお！ どれも二回分だから、…
@end
```

- `@<ID> <話者>[注記]` で発言を開き、`@end` で閉じる。発言の始まり・終わり・話者が記法に書かれているので、空行や `$$` 数式・表・図を挟んでも誰の発言かが曖昧にならない。ブロックの外は素通しの Markdown（見出し・区切り・図・参考文献）。`@` で始まる本文行は `@@` と重ねる
- ID は教材の中で一意の `u` ＋16進4桁。発言を書き直しても変えない。ID を省いた `@ やる夫` は `render` / `fmt` が採番する
- `generate_site.py` は `script/` から生成した内容と `README.md` が一致しなければビルドを止める。`script/` 自体は `build/` へコピーしない
- `README.md` を読む既存の道具（lint・字数集計・差分ページ・コメント・docsify）はそのまま使える。`README.md` を直接直したときは `absorb` で `script/` へ戻す。発言は前後の並びと本文の近さで対応づけ、同じ発言の書き換えなら ID を保つ

```bash
python3 scripts/yaruo_script.py render docs/books/{id}     # script/ → README.md
python3 scripts/yaruo_script.py absorb docs/books/{id}     # README.md の手直し → script/（ID を保つ）
python3 scripts/yaruo_script.py check  docs/books/*        # 構文・ID・同期の検査
python3 scripts/yaruo_script.py roundtrip docs/books/*     # README.md → @ → README.md の往復検査（変換前の確認）
python3 scripts/yaruo_script.py convert docs/books/{id}    # README.md から script/ を作る（移行）
```

`script/` を持つ教材には、docsify を使わない静的ページ `books/{id}/static.html` も生成する（`scripts/render_static.py`）。発言は `data-uid` 付きの要素になり、`#u7f3a` で発言へ直接飛べる。一覧からはまだリンクしない。

#### 校正台（アーティファクト）

`python3 scripts/build_proof_page.py` が `script/` を持つ全教材をまとめた校正台を `build/proof/all/` に作る（`index.html` は教材に依存しない `scripts/proof_template.html`、教材の一覧は `books.json`、本文・登場人物欄・アウトライン・規約・過去の指摘は教材ごとの `books/{id}.json`、図版は `books/{id}/figs/`）。`outline.md` が無い巻は `follows` をたどって前の巻の骨格を使う。Claude Code の Artifact ツールで、`index.html` 以外の全ファイルを `files` に付け、capabilities `sample`・`db`・`user` で公開する。ヘッダーで教材を切り替える

- 常に指摘の工程の中にいる（モードの出入りは無い）。下に小さな帯が出ていて、本文をタップすればすぐ①に入る。①範囲を選ぶ: タップで文節、同じ所をもう一度で 文 → 発言（地の文なら段落）。指で選んでもよい。この段階では下に小さな帯が出るだけで、候補は裏で推測しておく。「範囲なしで指摘」で幕全体への指摘にもできる。②指摘を決める: 上に自由記述・範囲（ここだけ／この幕）・「回答開始」、下に候補。候補は複数選べ、自由記述と組み合わせられる。候補は選んだ範囲と過去の指摘（採否・直し方・案へのコメント）から推測する。③修正案を確かめる: 回答開始で処理中の表示に切り替わり、終わると差分を左右2ペイン（左=今の本文、右=修正案）で出す。空白だけの違いは差分にしない。案ごとに採否・手直し・コメント、全体へのコメントを付けられ、「コメントして作り直す」で作り直させられる。「適用」で今の幕に即時反映する
- ヘッダーに AI の処理状態（何をしていて何秒経ったか）と、料金の目安（今回／累計）を常に出す。料金は送受信した文字数から推定した API 換算（quick=Haiku 5.5、default=Sonnet 5.5 の単価、1ドル150円）で、思考に使った分は含まない。実際には閲覧者の Claude の利用枠から引かれる
- 他の幕へ広げるのは「履歴」から。修正案を作るとき Claude が、方針についての指摘（口調・台詞の長さ・比喩の使い方など）を「全体向き」と判定し、履歴の上に並べる。広げたい指摘にチェックを付け（複数可）、「他の幕へ広げる」を押すと、まだ当てていない幕（発言のある幕）の修正案を幕ごとの確認なしで順に作る。終わると見本3件の差分を出し（残りは開けば見られる）、「すべて承認して適用」するか、追加の指示を書いて同じ幕について作り直す。追加の指示は指摘のコメントとして残る。履歴の「規則にする」で、取り込み時に `editorial/rules.md` へ足す候補として印を付ける
- 修正は共有 DB の `edits`（ブロックごとの上書き。文書 ID は `{教材ID}__{ブロックID}`、作った時点の本文を `base` に持つ）、指摘は `feedback`（指摘文・出した候補・範囲・提案・最終形・採否・適用済みの幕）に残る。問い合わせは閲覧者自身の Claude の利用枠で行う
- ブロック ID は、発言は台本の ID、地の文は `r{幕}-{素通し部分の番号}-{段落番号}`

正本への取り込みは Claude Code が行う。

1. `ArtifactData` の list を `out_dir` 付きで `edits` と `feedback` に対して実行し、書き出す
2. `python3 scripts/sync_proof.py <書き出し先>`。`base` と今の本文が一致するブロックだけを `script/` へ反映して README.md を作り直し、指摘を `editorial/feedback.jsonl` へ追記する。ずれていれば conflict として残す
3. 末尾の `DB_OPS` を `ArtifactData` の batch で書き戻し（反映した edits の削除、feedback の synced）、校正台を作り直して公開し直す

## 校正で蓄積する規則（editorial/）

- `editorial/feedback.jsonl` … 指摘ログ（追記のみ）。指摘文・範囲・採用数・却下数・手直し数・採用された直し方の例
- `editorial/rules.md` … 繰り返し効かせる規則。似た指摘がログに溜まったら Claude が規則の案を作り、人が承認してから書き足す。機械で判定できるもの（語・長さ）は `yaruo_lint.py` のルールにもする
- 校正台は両方を `book.json` に入れて候補の推測と修正に使い、`yaruo-rediscovery`（執筆）と `yaruo-review`（レビュー）は `rules.md` を読む

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
