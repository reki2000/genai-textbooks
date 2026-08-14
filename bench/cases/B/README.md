# タスクB（コメント対応）の事例

事例は review corpus から作る。

```bash
python3 scripts/bench.py from-record <教材ID>/<コメントID> --case-id B-01 --task B
```

`input.md` のコメント欄へ、記録の「指摘」をそのまま貼る。`reference.md` には
**解消したと言える条件**を書く（人が実際に resolved にしたときの対応が手掛かりになる）。
主指標は first-pass resolve rate。
