#!/usr/bin/env python3
"""`scripts/revise.py`・`revise_backends.py` と dev_server の推敲 API の検査。

LLM は呼ばない。偽バックエンド（`revise_backends.py --fake-child`）を子プロセスと
して起動し、プール・標準入出力・逐次表示の経路は本物と同じものを通す。

    python3 scripts/tests/run_revise_tests.py
"""

from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import comments as C  # noqa: E402
import revise as R  # noqa: E402
import revise_backends as B  # noqa: E402

SAMPLE = """# やる夫で学ぶ何か

---
## 第1幕　入口

---
### 1-1　最初の問い

**やる夫**：
｜転移《てんい》は治療の障害ではないのかお。
前は障害だと言っていたお。

**やらない夫**：
**同じ言葉**でも、立場が変われば意味が変わる。

---
### 1-2　次の問い

**やる夫**：
同じ言葉が出てきたお。
前は障害だと言っていたお。
"""

FAILURES: list[str] = []


def check(name: str, actual, expected) -> None:
    if actual == expected:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name}: {actual!r} != {expected!r}")
        FAILURES.append(name)


def make_book(root: Path) -> None:
    book = root / "docs" / "books" / "sample"
    book.mkdir(parents=True, exist_ok=True)
    (book / "README.md").write_text(SAMPLE, encoding="utf-8")
    C.ROOT = root
    C.BOOKS_DIR = root / "docs" / "books"
    C.COMMENTS_DIR = root / "comments"


def anchor(quote: str, heading: str = "1-1　最初の問い") -> dict:
    return {"heading": heading, "heading_level": 3, "quote": quote, "quote_tail": quote[-40:], "occurrence": 1}


def service(root: Path) -> R.Service:
    config = R.load_config()
    config.default_backend = "fake"
    return R.Service(config, log_dir=root / "revisions" / "log")


def source() -> str:
    return C.source_path("sample").read_text(encoding="utf-8")


# --------------------------------------------------------------------------


def test_parser() -> None:
    parser = R.CandidateParser()
    got = parser.feed('```json\n{"new": "あ", "wh')
    got += parser.feed('y": "短く"}\n前置きの文\n{"new": null, "why": "不要"}\n{"new": "い"}')
    got += parser.flush()
    check("parser: 分割された行を組み立てる", [item["new"] for item in got], ["あ", None, "い"])
    check("parser: 壊れた行は読み飛ばす", R.CandidateParser().feed('{"new": "x"\n{broken}\n'), [])


def test_locate_and_validate(root: Path) -> None:
    target, lines = R.locate("sample", "sentence", anchor("前は障害だと言っていたお。"))
    check("locate: 節で絞って1-1側の行", (target.start, target.end), (10, 10))
    check("locate: target は行全体", target.text, "前は障害だと言っていたお。\n")
    check("locate: 見出し経路", target.heading_path[-1], "1-1　最初の問い")

    text = "".join(lines)
    baseline = R.lint_errors(text)
    ok = R.validate({"new": "前は障害だと言ってたお。", "why": "縮めた"}, 0, text, target, baseline)
    check("validate: 行末の改行を補う", ok.new, "前は障害だと言ってたお。\n")
    check("validate: 通る候補", (ok.ok, ok.problems, ok.lint), (True, [], []))

    same = R.validate({"new": target.text, "why": ""}, 1, text, target, baseline)
    check("validate: 変更なしは採用不可", same.problems, ["変更なし"])

    none = R.validate({"new": None, "why": "直す必要なし"}, 2, text, target, baseline)
    check("validate: 直す必要なし", (none.ok, none.new), (False, None))

    dup = R.validate({"old": "前は障害だと言っていたお。", "new": "x", "why": ""}, 3, text, target, baseline)
    check("validate: 一意でない置換元を拒む", dup.problems, ["置換元が本文で一意でない"])

    missing = R.validate({"old": "どこにも無い", "new": "x", "why": ""}, 4, text, target, baseline)
    check("validate: 無い置換元を拒む", missing.problems, ["置換元が本文に見つからない"])

    other = R.validate({"old": "同じ言葉が出てきたお。\n", "new": "また同じ言葉だお。\n", "why": ""},
                       5, text, target, baseline)
    check("validate: target の外も一意なら使える", (other.ok, other.offset), (True, text.find("同じ言葉が出てきたお。")))

    lint = R.validate({"new": "前は障害だと言っていたお", "why": ""}, 6, text, target, baseline)
    check("validate: lint の新しい error を拾う", any("dialogue-period" in item for item in lint.lint), True)


def test_locate_errors(root: Path) -> None:
    try:
        R.locate("sample", "sentence", anchor("この文はどこにも無い。"))
    except R.ReviseError:
        print("ok   locate: 見失ったら例外（似た場所へ落とさない）")
    else:
        FAILURES.append("locate missing")
        print("FAIL locate: 見失ったのに例外にならない")


def test_light_guards() -> None:
    """light が前後の行を写し込む・直後が受ける語を消す・数値を作る、への備え。"""
    lines = [
        "**やる夫**：\n",
        "地道に貯めたお。\n",
        "正確には、賞与と、今月の家賃を\n",
        "一つに集めたお。\n",
        "\n",
        "**やらない夫**：\n",
        "やれやれ、家賃まで元手に混ぜたのか。\n",
    ]
    check("sentence: 文の途中で切れた行を続きまで広げる", R.sentence_bounds(lines, 2, 2), (2, 3))
    check("sentence: 続きの行から前へ広げる", R.sentence_bounds(lines, 3, 3), (2, 3))
    check("sentence: 文で終わる行はそのまま", R.sentence_bounds(lines, 1, 1), (1, 1))
    check("sentence: 強調の内側で終わる文は区切り",
          R.sentence_bounds(["**約2週間だお！**\n", "次の文だお。\n"], 1, 1), (1, 1))

    target = R.Target("sample", "sentence", "", [], 2, 3, 0, "".join(lines[2:4]), "")
    check("keep: 直後の台詞が受ける語", R.following_terms(target, lines), ["家賃"])
    check("keep: 消えた語", R.lost_terms("正確には賞与を集めたお。", ["家賃"]), ["家賃"])

    before, after = lines[:2], lines[4:]
    copied = "".join(lines[:2]) + "賞与と家賃を集めたお。\n" + "".join(lines[4:6])
    trimmed, did = R.trim_context(copied, before, after)
    check("trim: 写し込まれた前後の行を落とす", (trimmed, did), ("賞与と家賃を集めたお。\n", True))
    check("trim: 写し込みが無ければそのまま", R.trim_context("家賃を集めたお。\n", before, after),
          ("家賃を集めたお。\n", False))
    check("overlap: 一致しない形で残った重複を拒む",
          R.overlap_problems("家賃を集めたお。\nやれやれ、家賃まで元手に混ぜたのか。\n", target.text, before, after),
          ["前後の行と重複する"])
    check("overlap: 話者をまたぐ案を拒む",
          R.overlap_problems("集めたお。\n\n**やらない夫**：\nふむ。\n", target.text, before, after),
          ["話者や見出しをまたいでいる"])
    check("added: 本文に無い数値", R.added_numbers("年2%の利息で100万円", "預けた100万円"), ["2"])
    check("added: 桁区切りの揺れは同じ数", R.added_numbers("1,000円", "1000円"), [])


def test_utterance_window() -> None:
    lines = []
    for number in range(10):
        lines += [f"**{'やる夫' if number % 2 == 0 else 'やらない夫'}**：\n", f"発言{number}の一文目。\n",
                  f"発言{number}の二文目。\n", "\n"]
    target_line = 5 * 4 + 2  # 発言5の二文目
    start, end = R.utterance_window(lines, target_line, target_line, 2)
    check("context: 前は自分の発言に加えて2発言", lines[start], "**やらない夫**：\n")
    check("context: 前の起点は発言3", lines[start + 1], "発言3の一文目。\n")
    check("context: 後ろは2発言の終わりまで", lines[end - 1], "発言7の二文目。\n")


def test_routing(root: Path) -> None:
    config = R.load_config()
    target, _ = R.locate("sample", "sentence", anchor("前は障害だと言っていたお。"))
    shorten = config.action("shorten")
    connect = config.action("connect")
    check("routing: 既定はアクションのティア", R.choose_tier("auto", shorten, target, "", config), "light")
    check("routing: heavy のアクション", R.choose_tier("auto", connect, target, "", config), "heavy")
    check("routing: 明示は優先", R.choose_tier("light", connect, target, "", config), "light")
    check("routing: 長い自由指示は heavy",
          R.choose_tier("auto", config.action("free"), target, "あ" * 100, config), "heavy")
    section, _ = R.locate("sample", "section", anchor(""))
    check("routing: 節の選択は heavy", R.choose_tier("auto", shorten, section, "", config), "heavy")


def test_prompts(root: Path) -> None:
    first = R.system_prompt("sample")
    outline = C.outline_path("sample")
    outline.write_text("---\ntype: outline\nbook: sample\n---\n\n# 骨格\n- 1-1 転移の誤解\n", encoding="utf-8")
    second = R.system_prompt("sample")
    check("system: 作法カードが先頭", second.startswith(R.card_text()), True)
    check("system: 骨格を含み frontmatter は落とす", ("1-1 転移の誤解" in second, "type: outline" in second),
          (True, False))
    check("system: 骨格が変わると変わる", first != second, True)
    check("system: 同じ入力なら同一（キャッシュのため）", R.system_prompt("sample"), second)
    outline.unlink()

    target, lines = R.locate("sample", "sentence", anchor("前は障害だと言っていたお。"))
    config = R.load_config()
    user = R.user_prompt(target, lines, (5, 14), config.action("shorten"), "語尾は残す", 3,
                         [{"id": "x", "request": "短く", "before": "元の文", "after": "直した文"}])
    check("user: target を印で囲む", "<target>\n前は障害だと言っていたお。\n</target>" in user, True)
    check("user: 自由指示を添える", "書き手からの指示: 語尾は残す" in user, True)
    check("user: お手本が窓より前", user.index("お手本") < user.index("# 前後の本文"), True)
    check("user: 案の数", "案を3個" in user, True)


def test_service_flow(root: Path) -> None:
    svc = service(root)
    original = source()
    try:
        events = list(svc.generate({
            "book": "sample", "unit": "sentence", "action": "shorten", "backend": "fake",
            "anchor": anchor("前は障害だと言っていたお。"),
        }))
        kinds = [event["event"] for event in events]
        check("generate: meta → delta… → candidate… → done", (kinds[0], kinds[-1], "candidate" in kinds),
              ("meta", "done", True))
        request_id = events[0]["id"]
        candidates = [event for event in events if event["event"] == "candidate"]
        check("generate: 候補数", len(candidates), 3)
        check("generate: 1案目", candidates[0]["new"], "前は障害だと言っていたお！\n")

        svc.adopt(request_id, 0)
        check("adopt: 本文へ適用", "前は障害だと言っていたお！\n同じ言葉" not in source()
              and source().count("前は障害だと言っていたお！") == 1, True)
        check("adopt: 他の同文は触らない", source().count("前は障害だと言っていたお。"), 1)

        svc.undo("sample")
        check("undo: 元に戻る", source(), original)
        try:
            svc.undo("sample")
        except R.ReviseError:
            print("ok   undo: 取り消せる採用が無ければ例外")
        else:
            FAILURES.append("undo empty")

        # 採用 → 人が手直し → observe で最終形を記録 → 次のお手本に使う
        events = list(svc.generate({
            "book": "sample", "unit": "sentence", "action": "shorten", "backend": "fake",
            "anchor": anchor("前は障害だと言っていたお。"),
        }))
        request_id = events[0]["id"]
        svc.adopt(request_id, 0)
        check("observe: 手直しが無ければ記録しない", svc.observe("sample"), [])
        path = C.source_path("sample")
        path.write_text(source().replace("前は障害だと言っていたお！", "前は障害だって言ってたお！"), encoding="utf-8")
        recorded = svc.observe("sample")
        check("observe: 手直しの最終形", [event["final"] for event in recorded], ["前は障害だって言ってたお！\n"])
        check("observe: 同じ状態は二重に記録しない", svc.observe("sample"), [])
        examples = R.examples_for("shorten", "sample", root / "revisions" / "log")
        check("fewshot: 人の最終形をお手本にする", examples[0]["after"], "前は障害だって言ってたお！\n")
        check("fewshot: 取り消した採用は除く", len(examples), 1)

        # 却下・作り直し・もっと考えて
        events = list(svc.generate({
            "book": "sample", "unit": "sentence", "action": "tempo", "backend": "fake",
            "anchor": anchor("同じ言葉が出てきたお。", "1-2　次の問い"),
        }))
        first_id = events[0]["id"]
        events = list(svc.generate({
            "book": "sample", "unit": "sentence", "action": "tempo", "backend": "fake", "tier": "heavy",
            "parent": first_id, "escalate": True, "anchor": anchor("同じ言葉が出てきたお。", "1-2　次の問い"),
        }))
        check("escalate: heavy で作り直す", events[0]["tier"], "heavy")
        svc.reject(events[0]["id"], "verbose")

        rows = {row["action"]: row for row in R.stats(R.read_log(root / "revisions" / "log"))}
        check("stats: 採用数", rows["shorten"]["adopted"], 2)
        check("stats: 取り消し数", rows["shorten"]["undone"], 1)
        check("stats: 手直し数", rows["shorten"]["post_edited"], 1)
        tempo = [row for row in R.stats(R.read_log(root / "revisions" / "log")) if row["action"] == "tempo"]
        check("stats: もっと考えて・却下", sorted((row["tier"], row["escalated"], row["rejected"]) for row in tempo),
              [("heavy", 0, 1), ("light", 1, 0)])
    finally:
        svc.close()
        C.source_path("sample").write_text(original, encoding="utf-8")


def test_adopt_after_shift(root: Path) -> None:
    """候補を作った後に前の行が増えても、一意なら適用できる。"""
    svc = service(root)
    original = source()
    try:
        events = list(svc.generate({
            "book": "sample", "unit": "sentence", "action": "shorten", "backend": "fake",
            "anchor": anchor("同じ言葉が出てきたお。", "1-2　次の問い"),
        }))
        path = C.source_path("sample")
        path.write_text(source().replace("## 第1幕　入口\n", "## 第1幕　入口\n\n追加された行。\n"), encoding="utf-8")
        svc.adopt(events[0]["id"], 0)
        check("adopt: 行がずれても一意な置換元へ", "同じ言葉が出てきたお！" in source(), True)
    finally:
        svc.close()
        C.source_path("sample").write_text(original, encoding="utf-8")


def test_pool() -> None:
    pool = B.Pool({"light": 2}, idle_ttl=60)
    spec = B.TierSpec("fake")
    try:
        pool.prewarm(spec, "system", "light")
        check("pool: 指定数を待たせる", pool.count(), 2)
        process = pool.acquire(spec, "system", "light")
        check("pool: 取り出したら補充", pool.count(), 2)
        events = list(B.run(process, B.BACKENDS["fake"], "system", "<target>\nあ。\n</target>\n案を1個"))
        check("pool: 取り出したプロセスで1件処理", events[-1].kind, "done")
        pool.acquire(spec, "other system", "light")
        check("pool: system が変わると別キー", len(pool.warm), 2)
        check("pool: 期限切れを落とす", pool.reap(now=time.monotonic() + 3600), 4)
        check("pool: 空になる", pool.count(), 0)
    finally:
        pool.close()


def test_claude_parse() -> None:
    lines = [
        json.dumps({"type": "system", "subtype": "init"}),
        json.dumps({"type": "stream_event", "event": {"type": "content_block_delta",
                                                      "delta": {"type": "text_delta", "text": "{\"new\""}}}),
        json.dumps({"type": "stream_event", "event": {"type": "content_block_delta",
                                                      "delta": {"type": "thinking_delta", "thinking": "…"}}}),
        json.dumps({"type": "result", "usage": {"input_tokens": 3}, "total_cost_usd": 0.1}),
    ]
    events = list(B.ClaudeBackend().parse(iter(lines)))
    check("claude: 本文の差分と完了だけ拾う", [(event.kind, event.text) for event in events],
          [("delta", "{\"new\""), ("done", "")])
    command = B.ClaudeBackend().command(B.TierSpec("claude", "m", "high", False), "SYS")
    check("claude: 既定のツール・設定・MCP を外す",
          all(flag in command for flag in ["--tools", "--setting-sources", "--strict-mcp-config", "--system-prompt"]),
          True)
    check("claude: 思考を切る", B.ClaudeBackend().env(B.TierSpec("claude", thinking=False))["MAX_THINKING_TOKENS"], "0")


def test_http(root: Path) -> None:
    import dev_server

    server = dev_server.PreviewServer(("127.0.0.1", 0))
    server._revise = service(root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = source()
    port = server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("GET", dev_server.REVISE_API_PATH + "/config?book=sample&backend=fake")
        config = json.loads(connection.getresponse().read())
        check("http: 設定を返す", [action["id"] for action in config["actions"]][:2], ["shorten", "plain"])
        check("http: 教材を開いたら待機プロセスを起こす", server._revise.pool.count() > 0, True)

        body = json.dumps({"book": "sample", "unit": "sentence", "action": "shorten", "backend": "fake",
                           "anchor": anchor("前は障害だと言っていたお。")})
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("POST", dev_server.REVISE_API_PATH, body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        check("http: SSE で返す", response.getheader("Content-Type"), "text/event-stream; charset=utf-8")
        events = [json.loads(line[6:]) for line in response.read().decode("utf-8").split("\n")
                  if line.startswith("data: ")]
        check("http: 候補が届く", sum(1 for event in events if event["event"] == "candidate"), 3)

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("POST", f"{dev_server.REVISE_API_PATH}/{events[0]['id']}/adopt",
                           json.dumps({"index": 0}), {"Content-Type": "application/json"})
        check("http: 採用", json.loads(connection.getresponse().read())["ok"], True)
        check("http: 本文に反映", "前は障害だと言っていたお！" in source(), True)

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        bad = json.dumps({"book": "sample", "unit": "sentence", "action": "shorten", "backend": "fake",
                          "anchor": anchor("どこにも無い文。")})
        connection.request("POST", dev_server.REVISE_API_PATH, bad, {"Content-Type": "application/json"})
        check("http: 特定できない選択は 400", connection.getresponse().status, 400)

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("POST", dev_server.REVISE_API_PATH + "/undo", json.dumps({"book": "sample"}),
                           {"Content-Type": "application/json", "Origin": "http://evil.example"})
        check("http: 他オリジンの書き込みを拒む", connection.getresponse().status, 403)
    finally:
        server.shutdown()
        server._revise.close()
        server.server_close()
        C.source_path("sample").write_text(original, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_book(root)
        test_parser()
        test_locate_and_validate(root)
        test_locate_errors(root)
        test_light_guards()
        test_utterance_window()
        test_routing(root)
        test_prompts(root)
        test_service_flow(root)
        test_adopt_after_shift(root)
        test_pool()
        test_claude_parse()
        test_http(root)

    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
