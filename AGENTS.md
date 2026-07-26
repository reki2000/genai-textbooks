# Repository instructions

## このリポジトリについて

**genai-textbooks** は、生成 AI が執筆した短い教科書の集約サイトです。数学、物理、工学、経済学、哲学、社会科学などのトピックについて、「なんとなくの知識から、実際の理論体系までを学ぶ」ための教材を提供しています。

すべての教材は「やる夫」と「やらない夫」の対話形式で、学習者が理論を「自ら再発見」するストーリー仕立てで構成されています。

### サイト構成

- **公開サイト**: https://reki2000.github.io/genai-textbooks/
- **ホスティング**: GitHub Pages
- **対話形式**: やる夫式教材（.claude/skills/yaruo-rediscovery で設計・執筆）

## catalog.yaml と教材管理

教材の構成はすべて `docs/catalog.yaml` で定義されます。

### catalog.yaml の役割

```yaml
categories:              # カテゴリ定義（社会と制度、工学と産業など）
  - id: social          # カテゴリID
    title: 社会と制度    # 表示名
    order: 1             # 表示順

documents:              # 教材リスト
  - id: japan-food      # 教材ID
    title: やる夫と牛丼と食料政策
    path: /books/japan-food-policy/
    category: social
    order: 1
    question: 食料自給率を上げれば本当に安全なのか？
    plot: 深夜の牛丼屋で一杯の牛丼を分解しながら...
```

### 教材追加の手順

1. `docs/books/{教材ID}/README.md` を作成（本文）
2. `docs/catalog.yaml` に登録
3. `python3 scripts/generate_site.py` でビルド確認
4. git add docs/ でコミット

## yaruo-rediscovery スキル

対話形式教材の設計・執筆・改訂に使用するスキルです。

### 用途

- **新規教材作成** - ゼロからの執筆
- **続編・改訂** - 既存教材の拡張・修正
- **短編化・縮約** - 分量削減版の作成
- **別テーマ展開** - 関連トピックの新規教材

### 実行例

```bash
# 新しい教材を設計・執筆
/yaruo-rediscovery
# → やる夫とやらない夫の対話形式で教材を自動生成
```

### 教材の特徴

- **対話形式** - キャラクター（やる夫/やらない夫）による自然な会話
- **再発見型** - 学習者が理論を自ら導き出すストーリー構成
- **標準分量** - 読了時間が 10～60 分程度（スキルで自動計算）

## ビルドシステム

ソースと生成ファイルを明確に分離しています。テクニカルな詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照してください。

### 基本ルール

- **`docs/`**: ソースファイルのみ（`catalog.yaml`、各教材の `README.md` など）
- **`build/`**: 生成ファイル（`generate_site.py` の出力、`.gitignore` で除外）

### 開発時の手順

教材を追加・編集するときは `docs/catalog.yaml` を編集してから：

```bash
python3 scripts/generate_site.py        # build/ を生成
npx docsify serve build                # ローカル確認
git add docs/                           # docs/ のみをステージング
git commit -m "..."
```

### CI/CD

- **PR**: ビルドテストのみ
- **メインブランチマージ**: GitHub Pages にデプロイ

詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照。

## 教材の文字数・読了時間

教材の文字数は、簡便のためファイルサイズ ÷ 3 で概算する。

正確な集計が必要な場合は **yaruo-count スキル** を使用：

```bash
/yaruo-count
# → docs/books/*/README.md のすべての文字数・行数・読了時間を正確に集計
```

yaruo-count スキルは以下の場合に使用：
- `scripts/generate_site.py` の読了時間算出（内部で `count_document` を利用）
- ユーザーが規則に基づく正確な集計を明示的に求めたとき
