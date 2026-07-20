# genai-textbooks

AI-Generated Japanese Short Textbooks: "Yaruo"-Style Dialogue Collection and AI Text Generation Skill Definitions

[公開サイト](https://reki2000.github.io/genai-textbooks/#/)

- GitHub Pages で公開されるテキスト本体（`docs/books/*.md`）
- 「やる夫で学ぶ」形式の教材を作成・整形・校正し、公開目次を管理するための Claude Code / Codex 用スキル 4 種（`.claude/skills/`、`.codex/skills/`）

## Claude Code / Codex 用スキル

やる夫（生徒）とやらない夫（教師）の対話で理論を「再発見」していく教材を、作成 → 整形 → 校正の工程と公開目次の管理に分けて扱う。各スキルはユーザーが該当キーワード（「対話形式の教材」「整形」「校正」「目次」など）に言及すると自動で起動する。Codex では `.codex/skills` から `.claude/skills` へのディレクトリシンボリックリンクを辿って、同じ `SKILL.md` と付属スクリプトを参照する。

| スキル | 役割 | 主な起動キーワード |
|---|---|---|
| `yaruo-rediscovery` | 対話形式教材の**作成**。生徒が素朴案→反例→修正のサイクルで概念を自ら再発見する物語を書く | やる夫形式／対話形式の教材／再発見／続編・改訂 |
| `yaruo-format` | 教材の**書式整形**（機械的）。台詞継続行の全角空白インデント、約物に隣接して壊れる強調記号 `**` の修正、区切り行の無い表の修正。スクリプトで冪等に実行 | 整形／フォーマット／インデント／太字が効かない／表が崩れる |
| `yaruo-proofread` | 教材の**校正・検証**。(1) 事実・理論のファクトチェックと参考文献（脚注）の付与、(2) 数式と会話の整合性検証 | 校正／ファクトチェック／出典／数式チェック／検証 |
| `yaruo-index` | 教材カタログの**目次管理**。YAMLを正本としてサイドバーとトップページの教材一覧を生成・検証 | 目次／教材一覧／カテゴリ／分類／表示順／教材の追加・削除・改名 |
