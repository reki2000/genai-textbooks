# judge の判定の置き場所

`bench.py blind` が `packets/`（judge へ渡す）と `mapping.yml`（渡さない）を作る。
**`mapping.yml` を judge に見せない。** 見せた時点でその実行の blind は壊れる。
