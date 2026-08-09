# genai-textbooks

AI-Generated Japanese Short Textbooks: "Yaruo"-Style Dialogue Collection and AI Text Generation Skill Definitions

[公開サイト](https://reki2000.github.io/genai-textbooks/)

- GitHub Pages で公開されるテキスト本体（`docs/books/*/README.md`）。公開用の目次・サイドバー・各教材ページ（SEO用meta含む）は各 `README.md` の隣にある `catalog.yml` を `scripts/generate_site.py` がビルド時に統合して自動生成する（`scripts/site_template.html` 参照）
- 「やる夫で学ぶ」形式の教材を執筆・検査・公開するための Claude Code / Codex 用スキル 9 種（`.claude/skills/`、`.codex/skills/`）

## Claude Code / Codex 用スキル

やる夫（生徒）とやらない夫（教師）の対話で、理論を「再発見」していく教材を扱う。各スキルは依頼内容に応じて自動で起動する。Codex は `.codex/skills` から `.claude/skills` へのシンボリックリンクを通じ、Claude Code と同じ定義を参照する。

| スキル | 役割 | 主な起動キーワード |
|---|---|---|
| `yaruo-rediscovery` | 対話形式教材の**作成**。生徒が素朴案→反例→修正のサイクルで概念を自ら再発見する物語を書く | やる夫形式／対話形式の教材／再発見／続編・改訂 |
| `yaruo-review` | 外部で書かれた教材の**受け入れ検査**。物語性、学習内容、再発見の過程を証拠つきで評価する | レビュー／受け入れ検査／品質チェック |
| `yaruo-format` | 教材の**書式整形**。Markdown の強調、表、会話表記などを lint・修正する | 整形／フォーマット／lint／太字や表の崩れ |
| `yaruo-proofread` | 教材の**校正・検証**。事実、出典、論理展開、数式と会話の整合性を確認する | 校正／ファクトチェック／出典／数式チェック |
| `yaruo-count` | 教材の文字数、行数、数式量、推定読了時間を統一ルールで正確に集計する | 正確な文字数／行数／読了時間 |
| `textbook-figures` | 教材本文へ説明図を追加。Python生成SVGや出典明記の外部画像から適切な媒体を選び組み込む | 図を追加／図解／可視化／概念図 |
| `yaruo-slide` | 教材から物語を除き学習内容だけを圧縮した marp スライド `slide.md` を作成・更新する | スライド／marp／要約スライド／発表資料 |
| `comment-eater` | 開発サーバのプレビューに投稿されたコメントを1件ずつ拾い、該当箇所だけを読んで直す | コメント対応／コメントを待って／プレビューのコメント |
| `discuss` | Codex と Claude がファイルを介して設計案やレビューを照合し、合意を残す | 議論して／Claude・Codex と相談／合意を取って |

## この執筆環境の使い方

Claude Code または Codex をリポジトリルートで起動し、自然文で作業を依頼する。たとえば「○○をやる夫形式の教材にして」で新規執筆、「この教材をレビューして直して」で受け入れ検査と修正、「整形して」「校正して」で各工程を個別に実行できる。二者で方針を詰める場合は一方に「Claude（または Codex）と議論して」と依頼し、もう一方に `/discuss` で参加するよう伝える。

初回だけ開発用依存関係を導入する。

```bash
python3 -m pip install -r requirements-dev.txt
```

新しい教材の基本フローは次のとおり。

1. `yaruo-rediscovery` で `docs/books/{ID}/README.md` を執筆する。
2. `docs/books/{ID}/catalog.yml` にカテゴリ、作成日時、問い、プロットを登録する。タイトルは本文先頭の `# ` 見出しから取得される。
3. lint を実行し、`error` を解消する。

   ```bash
   python3 scripts/yaruo_lint.py docs/books/{ID}/README.md --check --verbose
   ```

4. サイトをビルドして確認する。継続して編集する場合は、自動再ビルドされる開発サーバーが便利。

   ```bash
   python3 scripts/generate_site.py
   python3 scripts/dev_server.py
   ```

5. ソースである `docs/` だけをステージする。生成先の `build/` はコミットしない。

   ```bash
   git add docs/
   ```

外部のモデルや別セッションが書いた教材は、カタログ登録前に `yaruo-review` で検査する。詳しいカタログ仕様、分冊、プレビュー、デプロイ手順は [`BUILD.md`](BUILD.md) を参照。プレビュー上のコメント機能は [`COMMENTS.md`](COMMENTS.md)。
