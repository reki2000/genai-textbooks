# Repository instructions

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

### コミットルール

**`build/` をコミットに含めない。** `.gitignore` で自動除外されます。

```bash
# 確認
git diff --cached | grep build/
# 出力がなければOK
```

### CI/CD

- **PR**: ビルドテストのみ
- **メインブランチマージ**: GitHub Pages にデプロイ

詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照。

### 文字数集計

教材の文字数は、簡便のためファイルサイズ ÷ 3 で概算する（換算規則の正本と正確な集計は yaruo-count スキル）。yaruo-count スキルは、`scripts/generate_site.py` の読了時間算出（内部で `count_document` を利用）か、規則に基づく正確な集計をユーザーが明示的に求めたときだけ使う。
