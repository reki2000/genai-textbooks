# Repository instructions

## Skills

- 教材カタログ、カテゴリ、分類、表示順、目次、サイドバー、トップページの教材一覧、または `docs/books/*.md` の追加・削除・改名を扱うときは、必ず `.claude/skills/yaruo-index/SKILL.md` の `yaruo-index` スキルを使う。
- 目次管理の正本・生成手順・検証方法は `yaruo-index` スキルに集約する。ここへ重複して記載しない。
- 教材の文字数・行数・UTF-8バイト数・数式量・読了時間を集計するとき、またはその集計処理を他の生成処理へ組み込むときは、必ず `.claude/skills/yaruo-count/SKILL.md` の `yaruo-count` スキルを使う。
- 集計規則と実装は `yaruo-count` スキルに集約する。ここへ重複して記載しない。
