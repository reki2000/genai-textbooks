# review corpus

人間レビューを改善データとして蓄積する場所。プレビュー上のコメント（`comments/`）は
`.gitignore` 済みで機械ごとに消えるので、人が `resolved` にしたものだけをここへ凍結する。

```
review-corpus/
  records/{教材ID}/{コメントID}.md   人が確認して閉じた指摘と対応（凍結。手で編集しない）
  patterns/{パターンID}.md           再発防止ルールの候補（人が書く・承認する）
```

- 凍結・分類・ゲート判定は `scripts/review_corpus.py`（唯一の入口）。
- 判断（どれが同じ問題か、どこへ昇格させるか）と手順は `.claude/skills/yaruo-retrospect/SKILL.md` が正本。
- 昇格には **発生3件以上・2教材以上・`approved_by` が空でない**ことが要る。`approved_by` はエージェントが埋めない。

```bash
python3 scripts/review_corpus.py harvest   # resolved を取り込む
python3 scripts/review_corpus.py stats     # 未分類と発生回数
python3 scripts/review_corpus.py check     # 票の必須欄と昇格ゲート
```

記録は `patterns` 欄だけが後から変わる。指摘と対応の本文は凍結し、教材が改稿されても書き換えない
（「そのとき何を見て何と言われたか」が資料の価値なので）。
