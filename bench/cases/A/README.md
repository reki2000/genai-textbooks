# タスクA（問題発見）の事例

事例は review corpus から作る。人が resolved にした指摘だけが基準になる。

```bash
python3 scripts/bench.py from-record <教材ID>/<コメントID> --case-id A-01 --task A
```

作った後、`evaluates` を埋め、`reference.md` から**修正の内容**を落として
「人間が何を問題としたか」だけを残す（解き方を渡すとタスクにならない）。
