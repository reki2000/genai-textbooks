# Repository instructions

## catalog.yaml 構造

教材の構成はすべて `docs/catalog.yaml` で定義：

```yaml
categories:
  - id: social
    title: 社会と制度
    order: 1

documents:
  - id: japan-food
    title: やる夫と牛丼と食料政策
    path: /books/japan-food-policy/
    category: social
    order: 1
    question: 食料自給率を上げれば本当に安全なのか？
    plot: 深夜の牛丼屋で一杯の牛丼を分解しながら...
```

## 教材追加手順

1. `/yaruo-rediscovery` で教材を執筆 → `docs/books/{ID}/README.md`
2. `docs/catalog.yaml` に登録
3. `python3 scripts/generate_site.py` でビルド確認
4. `git add docs/` でコミット

## ビルドシステム

ソース・生成の分離詳細は [`docs/BUILD.md`](./docs/BUILD.md) を参照。

- **`docs/`**: ソースのみ
- **`build/`**: 生成ファイル（`.gitignore` で除外）

## 文字数集計

概算：ファイルサイズ ÷ 3

正確な集計が必要なら `/yaruo-count` スキルを使用。
