# genai-textbooks

AI-Generated Japanese Short Textbooks: "Yaruo"-Style Dialogue Collection and AI Text Generation Skill Definitions

[公開サイト](https://reki2000.github.io/genai-textbooks/)

- GitHub Pages で公開されるテキスト本体（`docs/books/*/README.md`）。公開用の目次・サイドバー・各教材ページ（SEO用meta含む）は `docs/catalog.yaml` を正本として `scripts/generate_site.py` がビルド時に自動生成する（`scripts/site_template.html` 参照）
- 「やる夫で学ぶ」形式の教材を作成・整形・校正するための Claude Code / Codex 用スキル 3 種（`.claude/skills/`、`.codex/skills/`）

## Claude Code / Codex 用スキル

やる夫（生徒）とやらない夫（教師）の対話で理論を「再発見」していく教材を、作成 → 整形 → 校正の工程で扱う。各スキルはユーザーが該当キーワード（「対話形式の教材」「整形」「校正」など）に言及すると自動で起動する。Codex では `.codex/skills` から `.claude/skills` へのディレクトリシンボリックリンクを辿って、同じ `SKILL.md` と付属スクリプトを参照する。

| スキル | 役割 | 主な起動キーワード |
|---|---|---|
| `yaruo-rediscovery` | 対話形式教材の**作成**。生徒が素朴案→反例→修正のサイクルで概念を自ら再発見する物語を書く | やる夫形式／対話形式の教材／再発見／続編・改訂 |
| `yaruo-format` | 教材の**書式整形**（機械的）。発言外枠のカギカッコと行頭の全角空白の削除（行末以外で閉じる引用語は保持）、約物に隣接して壊れる強調記号 `**` の修正、区切り行の無い表の修正。スクリプトで冪等に実行 | 整形／フォーマット／会話表記／カギカッコ／インデント／太字が効かない／表が崩れる |
| `yaruo-proofread` | 教材の**校正・検証**。(1) 事実・理論のファクトチェックと参考文献（脚注）の付与、(2) 数式と会話の整合性検証 | 校正／ファクトチェック／出典／数式チェック／検証 |
