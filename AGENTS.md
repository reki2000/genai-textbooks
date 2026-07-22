# Repository instructions

## Skills

- 教材カタログ、カテゴリ、分類、表示順、目次、サイドバー、トップページの教材一覧、または `docs/books/*.md` の追加・削除・改名を扱うときは、必ず `.claude/skills/yaruo-index/SKILL.md` の `yaruo-index` スキルを使うが、トークン節約のため、教材が完成したことをユーザーに確認してから行う。
- 教材の文字数は、簡便のためファイルサイズ / 3 で概算すること（換算規則の正本と正確な集計は yaruo-count スキル）。yaruo-count スキルは、yaruo-index の目次生成か、規則に基づく正確な集計をユーザーが明示的に求めたときだけ使う。
