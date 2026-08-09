#!/usr/bin/env python3
"""`scripts/comments.py` のアンカー解決・窓・状態遷移の検査。

アンカーは編集で動くことが前提なので、「動いても追随する」「見失ったら黙って
別の場所へ落ちない」の二つを重点的に見る。

    python3 scripts/tests/run_comment_tests.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import comments as C  # noqa: E402

SAMPLE = """# やる夫で学ぶ何か

## 第1幕　入口

### 1-1　最初の問い

**やる夫**：
　｜転移《てんい》は治療の障害ではないのかお。
　前は障害だと言っていたお。

**やらない夫**：
　**同じ言葉**でも、立場が変われば意味が変わる。

### 1-2　次の問い

**やる夫**：
　同じ言葉が出てきたお。
　前は障害だと言っていたお。

## 第2幕　出口

**やらない夫**：
　式は $x = 1$ で表される。
"""


def make_book(root: Path, body: str = SAMPLE) -> None:
    book = root / "docs" / "books" / "sample"
    book.mkdir(parents=True)
    (book / "README.md").write_text(body, encoding="utf-8")
    C.ROOT = root
    C.BOOKS_DIR = root / "docs" / "books"
    C.COMMENTS_DIR = root / "comments"


def anchor_comment(**kwargs) -> C.Comment:
    defaults = dict(
        id="0001",
        book="sample",
        part=1,
        kind="wording",
        unit="sentence",
        status="open",
        created="2026-01-01T00:00:00+09:00",
        body="指摘",
    )
    defaults.update(kwargs)
    return C.Comment(**defaults)  # type: ignore[arg-type]


FAILURES: list[str] = []


def check(name: str, actual, expected) -> None:
    if actual == expected:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name}: {actual!r} != {expected!r}")
        FAILURES.append(name)


def test_normalize() -> None:
    check("normalize: ルビは基底だけ", C.normalize("｜転移《てんい》は"), "転移は")
    check("normalize: 強調と空白を落とす", C.normalize("　**同じ言葉**でも"), "同じ言葉でも")
    check("normalize: 数式を落とす", C.normalize("式は $x = 1$ で"), "式はで")
    check("normalize: 全角英数を畳む", C.normalize("ＡＢ１"), "AB1")


def test_resolve_basic(root: Path) -> None:
    lines = C.read_lines(C.source_path("sample", 1))
    comment = anchor_comment(
        anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="転移は治療の障害ではないのかお。")
    )
    check("resolve: ルビ越しに引く", C.resolve(comment, lines), (7, 7))


def test_resolve_occurrence(root: Path) -> None:
    """同じ文が別の節にもあるとき、節で絞って正しい方を引く。"""
    lines = C.read_lines(C.source_path("sample", 1))
    first = anchor_comment(
        anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="前は障害だと言っていたお。")
    )
    second = anchor_comment(
        anchor=C.Anchor(heading="1-2　次の問い", heading_level=3, quote="前は障害だと言っていたお。")
    )
    check("resolve: 1-1 側", C.resolve(first, lines), (8, 8))
    check("resolve: 1-2 側", C.resolve(second, lines), (17, 17))


def test_resolve_after_edit(root: Path) -> None:
    """前の方を編集して行がずれても、引用で追随する。"""
    path = C.source_path("sample", 1)
    lines = C.read_lines(path)
    comment = anchor_comment(
        anchor=C.Anchor(heading="1-2　次の問い", heading_level=3, quote="同じ言葉が出てきたお。", line_hint=17)
    )
    before = C.resolve(comment, lines)
    edited = lines[:8] + ["　挿入された行その1。\n", "　挿入された行その2。\n"] + lines[8:]
    path.write_text("".join(edited), encoding="utf-8")
    after = C.resolve(comment, C.read_lines(path))
    check("resolve: 編集前", before, (16, 16))
    check("resolve: 編集後も同じ文へ追随", after, (18, 18))
    C.record_current_position(comment, edited, after)
    check("position: 編集後の現在行へ更新", comment.anchor.current_line, 19)
    check("position: 現在見出しも更新", comment.anchor.current_heading, "1-2　次の問い")
    path.write_text("".join(lines), encoding="utf-8")


def test_resolve_missing(root: Path) -> None:
    """引用が消えたら None。似た場所へ落とさない。"""
    lines = C.read_lines(C.source_path("sample", 1))
    comment = anchor_comment(
        anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="この文はどこにも無い。")
    )
    check("resolve: 見失ったら None", C.resolve(comment, lines), None)
    comment.anchor.current_line = 42
    comment.anchor.located_at = "2026-01-01T00:00:00+09:00"
    check("position: 解決失敗を報告", C.refresh_current_position(comment), False)
    check(
        "position: 解決失敗時は最後の位置を維持",
        (comment.anchor.current_line, comment.anchor.located_at),
        (42, "2026-01-01T00:00:00+09:00"),
    )


def test_resolve_section(root: Path) -> None:
    lines = C.read_lines(C.source_path("sample", 1))
    comment = anchor_comment(
        unit="section",
        anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="転移は"),
    )
    check("resolve: 節ぜんぶ", C.resolve(comment, lines), (4, 12))


def test_window(root: Path) -> None:
    lines = C.read_lines(C.source_path("sample", 1))
    wording = anchor_comment(
        kind="wording", anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="転移は治療の障害")
    )
    span = C.resolve(wording, lines)
    start, end = C.window_for(wording, lines, span)
    check("window: 軽微は段落の周りだけ", (start < span[0], end - start < 20), (True, True))

    substance = anchor_comment(
        kind="substance", anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="転移は治療の障害")
    )
    check("window: 内容は節ぜんぶ", C.window_for(substance, lines, span), (4, 13))


def test_outline_metadata(root: Path) -> None:
    path = C.source_path("sample", 1)
    timestamp = 1_786_233_600
    path.touch()
    os.utime(path, (timestamp, timestamp))
    check(
        "outline: 教材ディレクトリへ置く",
        C.outline_path("sample"),
        root / "docs" / "books" / "sample" / "outline.md",
    )
    check(
        "outline: README 更新日時を ISO 8601 で得る",
        C.readme_modified_at("sample"),
        "2026-08-09T00:00:00+00:00",
    )


def test_edit_anchor(root: Path) -> None:
    lines = C.read_lines(C.source_path("sample", 1))
    unique = C.edit_anchor(lines, (7, 7))
    check("edit_anchor: 一意なら1行", unique[1], True)
    # 「前は障害だと言っていたお。」は2箇所にあるので、前の行まで広げて一意にする
    duplicated = C.edit_anchor(lines, (8, 8))
    check("edit_anchor: 重複は広げて一意化", (duplicated[1], duplicated[0].count("\n")), (True, 2))

    section = C.edit_anchor(lines, (4, 12), unit="section")
    check("edit_anchor: section は候補を出さない", section, ("", False))

    thirteen_lines = [f"一意な行 {index}\n" for index in range(C.EDIT_ANCHOR_MAX_LINES + 1)]
    over_lines = C.edit_anchor(thirteen_lines, (0, len(thirteen_lines) - 1))
    check("edit_anchor: 行数上限を超えたら候補なし", over_lines, ("", False))

    long_line = ["長" * (C.EDIT_ANCHOR_MAX_CHARS + 1) + "\n"]
    over_chars = C.edit_anchor(long_line, (0, 0))
    check("edit_anchor: 文字数上限を超えたら候補なし", over_chars, ("", False))

    block = [f"共通行 {index}\n" for index in range(C.EDIT_ANCHOR_MAX_LINES)]
    needs_over_limit_extension = ["一つ目の前置き\n", *block, "区切り\n", "二つ目の前置き\n", *block]
    extended = C.edit_anchor(needs_over_limit_extension, (1, C.EDIT_ANCHOR_MAX_LINES))
    check("edit_anchor: 一意化後に上限超過なら候補なし", extended, ("", False))


def test_schema_revision_and_legacy_upgrade(root: Path) -> None:
    comment = C.create_comment(
        book="sample",
        part=1,
        kind="wording",
        unit="sentence",
        body="schema の検査",
        heading="1-1　最初の問い",
        heading_level=3,
        heading_path=[],
        quote="転移は治療の障害ではないのかお。",
        quote_tail="ないのかお。",
        occurrence=1,
    )
    check("schema: 新規は現行版", (comment.schema, comment.revision), (C.COMMENT_SCHEMA, 1))
    first_text = comment.path.read_text(encoding="utf-8")
    check("schema: frontmatter に版と revision", ("schema: comment/v1" in first_text, "revision: 1" in first_text), (True, True))

    legacy_text = first_text.replace("schema: comment/v1\nrevision: 1\n", "", 1)
    comment.path.write_text(legacy_text, encoding="utf-8")
    legacy = C.find_comment("sample", comment.id)
    check("schema: 欠落は legacy として読む", (legacy.schema, legacy.revision), (C.LEGACY_COMMENT_SCHEMA, 0))
    C.set_status(legacy, "stale")
    upgraded = C.find_comment("sample", comment.id)
    check("schema: 更新と同じ保存で現行版へ移行", (upgraded.schema, upgraded.revision), (C.COMMENT_SCHEMA, 1))

    unknown = upgraded.path.read_text(encoding="utf-8").replace("schema: comment/v1", "schema: comment/v999", 1)
    try:
        C.parse_comment(unknown)
    except C.CommentError:
        print("ok   schema: 未知の明示版を拒否")
    else:
        print("FAIL schema: 未知の明示版が通った")
        FAILURES.append("schema: unknown version")


def test_atomic_write_and_conflicts(root: Path) -> None:
    comment = C.create_comment(
        book="sample",
        part=1,
        kind="wording",
        unit="sentence",
        body="競合の検査",
        heading="1-1　最初の問い",
        heading_level=3,
        heading_path=[],
        quote="転移は治療の障害ではないのかお。",
        quote_tail="ないのかお。",
        occurrence=1,
    )
    C.set_status(comment, "answered", answer="最初の対応")
    before_followup = C.find_comment("sample", comment.id)
    stale_agent_copy = C.find_comment("sample", comment.id)
    C.add_followup(before_followup, "追加指摘を消さないで")
    try:
        C.set_status(stale_agent_copy, "answered", answer="古い版への対応")
    except C.CommentConflict:
        print("ok   conflict: stale な回答を拒否")
    else:
        print("FAIL conflict: stale な回答が上書きした")
        FAILURES.append("conflict: stale answer")
    preserved = C.find_comment("sample", comment.id)
    check(
        "conflict: 追加指摘と open 状態を保持",
        (preserved.status, preserved.body, [message.role for message in preserved.messages()]),
        ("open", "追加指摘を消さないで", ["user", "assistant", "user"]),
    )

    for target in ("resolved", "stale", "open"):
        first = C.find_comment("sample", comment.id)
        second = C.find_comment("sample", comment.id)
        C.set_status(first, target)
        try:
            C.set_status(second, target)
        except C.CommentConflict:
            print(f"ok   conflict: {target} の競合を拒否")
        else:
            print(f"FAIL conflict: {target} の競合が通った")
            FAILURES.append(f"conflict: {target}")

    fresh = C.find_comment("sample", comment.id)
    original = fresh.path.read_text(encoding="utf-8")
    with mock.patch("comments.os.replace", side_effect=OSError("置換失敗")):
        try:
            C.set_status(fresh, "stale")
        except OSError:
            print("ok   atomic: 置換失敗を呼び出し側へ返す")
        else:
            print("FAIL atomic: 置換失敗を握りつぶした")
            FAILURES.append("atomic: replace failure")
    check("atomic: 置換失敗時は元ファイルを保持", fresh.path.read_text(encoding="utf-8"), original)
    check(
        "atomic: 置換失敗時に一時ファイルを残さない",
        list(fresh.path.parent.glob(f".{fresh.path.name}.*")),
        [],
    )


def test_conflict_http_status() -> None:
    import dev_server

    handler = dev_server.PreviewHandler.__new__(dev_server.PreviewHandler)
    handler.path = f"{dev_server.COMMENT_API_PATH}/sample/0001/reopen"
    handler._check_origin = mock.Mock(return_value=True)
    handler._set_status = mock.Mock(side_effect=C.CommentConflict("競合"))
    handler._send_bytes = mock.Mock()
    handler.send_error = mock.Mock()
    handler.do_POST()
    check("conflict: HTTP は 409", handler._send_bytes.call_args.kwargs.get("status"), 409)

    with (
        mock.patch("comments.find_comment", return_value=anchor_comment(anchor=C.Anchor())),
        mock.patch("comments.set_status", side_effect=C.CommentConflict("競合")),
    ):
        exit_code = C.main(["reopen", "--book", "sample", "--id", "0001"])
    check("conflict: CLI は終了コード 2", exit_code, 2)


def test_create_and_status(root: Path) -> None:
    comment = C.create_comment(
        book="sample",
        part=1,
        kind="wording",
        unit="sentence",
        body="唐突に感じる",
        heading="1-1　最初の問い",
        heading_level=3,
        heading_path=[],
        quote="転移は治療の障害ではないのかお。",
        quote_tail="ないのかお。",
        occurrence=1,
    )
    check("create: id は連番", comment.id, "0001")
    check("create: 行番号を記録", comment.anchor.line_hint, 8)
    check("create: 現在行を記録", comment.anchor.current_line, 8)
    check("create: 現在見出しを記録", comment.anchor.current_heading, "1-1　最初の問い")
    check("create: 位置の確認日時を記録", bool(comment.anchor.located_at), True)
    check("create: 見出し経路を補う", comment.anchor.heading_path[-1], "1-1　最初の問い")

    reloaded = C.find_comment("sample", "0001")
    check("round-trip: 本文", reloaded.body, "唐突に感じる")
    check("round-trip: 現在位置", reloaded.anchor.current_line, 8)

    C.set_status(reloaded, "answered", answer="やる夫の台詞に理由を1文足した")
    again = C.find_comment("sample", "0001")
    check("answer: 状態", again.status, "answered")
    check("answer: revision を進める", again.revision, 2)
    check("answer: 対応の説明", again.answer, "やる夫の台詞に理由を1文足した")
    check("answer: 指摘は残る", again.body, "唐突に感じる")

    original_path = again.path
    C.add_followup(again, "理由ではなく、具体例も必要です")
    followed = C.find_comment("sample", "0001")
    check("follow-up: 同じファイルを使う", followed.path, original_path)
    check("follow-up: 再び処理対象へ戻す", followed.status, "open")
    check("follow-up: 往復の履歴を残す", [m.role for m in followed.messages()], ["user", "assistant", "user"])
    check("follow-up: 最新の指摘を本文にする", followed.body, "理由ではなく、具体例も必要です")
    check("follow-up: revision を進める", followed.revision, 3)

    C.set_status(followed, "answered", answer="具体例を一つ追加した")
    threaded = C.find_comment("sample", "0001")
    check("follow-up: 二度目の対応でも revision を進める", threaded.revision, 4)
    check(
        "follow-up: 二度目の対応も同じ履歴へ追加",
        [(m.role, m.body) for m in threaded.messages()],
        [
            ("user", "唐突に感じる"),
            ("assistant", "やる夫の台詞に理由を1文足した"),
            ("user", "理由ではなく、具体例も必要です"),
            ("assistant", "具体例を一つ追加した"),
        ],
    )
    rendered_thread = threaded.path.read_text(encoding="utf-8")
    check("follow-up: Markdown 内に追加指摘を残す", "## 追加指摘 [" in rendered_thread, True)

    second = C.create_comment(
        book="sample",
        part=1,
        kind="substance",
        unit="paragraph",
        body="二件目",
        heading="1-2　次の問い",
        heading_level=3,
        heading_path=[],
        quote="同じ言葉が出てきたお。",
        quote_tail="出てきたお。",
        occurrence=1,
    )
    check("create: 採番は続く", second.id, "0002")
    check("open_comments: answered は数えない", [c.id for c in C.open_comments("sample")], ["0002"])


def test_create_rejects_unresolvable(root: Path) -> None:
    try:
        C.create_comment(
            book="sample",
            part=1,
            kind="wording",
            unit="sentence",
            body="どこでもない",
            heading="1-1　最初の問い",
            heading_level=3,
            heading_path=[],
            quote="本文に存在しない文字列",
            quote_tail="文字列",
            occurrence=1,
        )
    except C.CommentError:
        print("ok   create: 特定できない選択はその場で拒否")
        return
    print("FAIL create: 特定できない選択が通ってしまった")
    FAILURES.append("create: 特定できない選択")


def test_browser_quote_parity(root: Path) -> None:
    """ブラウザが送ってくる正規形が、そのままソースへ当たること。

    ここに置いてある引用は `scripts/dev_comment_ui.js` を jsdom で動かして実際に
    採取した文字列。話者行と本文が `breaks: true` で1つの段落に描画され、ルビは
    <ruby> に、その両脇にゼロ幅非結合子が入り、`**` は太字要素になっている。
    それらを落とした結果がソース側の `normalize()` と一致していなければ、
    どんな選択もアンカーできない。
    """
    lines = C.read_lines(C.source_path("sample", 1))
    from_browser = "やる夫:転移は治療の障害ではないのかお。前は障害だと言っていたお。"
    comment = anchor_comment(
        unit="paragraph",
        anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote=from_browser),
    )
    check("parity: 描画結果の正規形がソースに当たる", C.resolve(comment, lines), (6, 8))

    partial = anchor_comment(anchor=C.Anchor(heading="1-1　最初の問い", heading_level=3, quote="治療の障害"))
    check("parity: 文の一部だけの選択", C.resolve(partial, lines), (7, 7))

    duplicated = "やる夫:同じ言葉が出てきたお。前は障害だと言っていたお。"
    second = anchor_comment(
        unit="paragraph",
        anchor=C.Anchor(heading="1-2　次の問い", heading_level=3, quote=duplicated),
    )
    check("parity: 節で絞って別の同文と混ざらない", C.resolve(second, lines), (15, 17))


def test_group_same_section(root: Path) -> None:
    head = anchor_comment(id="0001", anchor=C.Anchor(heading="1-1　最初の問い"))
    same = anchor_comment(id="0002", anchor=C.Anchor(heading="1-1　最初の問い"))
    other = anchor_comment(id="0003", anchor=C.Anchor(heading="1-2　次の問い"))
    check(
        "group: 同じ節だけまとめる",
        [c.id for c in C.group_with_same_section([head, same, other])],
        ["0001", "0002"],
    )


def test_waiter_registry(root: Path) -> None:
    """担当の在席は dev_server が接続で持つ。1教材に1つだけ。"""
    import dev_server

    registry = dev_server.WaiterRegistry(grace=0.5)
    registry.enter("sample", "AAA", "Claude Opus 5", "high")
    status = registry.status("sample")
    check(
        "waiter: 繋いでいる間は待機中",
        (status["state"], status["model"], status["effort"]),
        ("waiting", "Claude Opus 5", "high"),
    )

    try:
        registry.enter("sample", "BBB", "Sonnet 5", "medium")
    except C.WaiterBusy:
        print("ok   waiter: 二人目は弾かれる")
    else:
        print("FAIL waiter: 二人目が入れてしまった")
        FAILURES.append("waiter: 二人目")

    registry.enter("sample", "AAA", "Claude Opus 5", "high")
    registry.leave("sample")
    check("waiter: 同じ担当は繋ぎ直せる", registry.status("sample")["state"], "waiting")

    registry.leave("sample")
    check("waiter: 切れた直後は対応中とみなす", registry.status("sample")["state"], "working")

    time.sleep(0.6)
    check("waiter: 戻ってこなければ未接続", registry.status("sample")["state"], "disconnected")

    registry.enter("sample", "DDD", "落ちるモデル", "low")
    registry.drop("sample")
    check("waiter: 切断は猶予なしで未接続", registry.status("sample")["state"], "disconnected")

    registry.enter("", "GLOBAL", "Codex", "high")
    check("waiter: 教材未指定の担当を各教材に表示", registry.status("sample")["state"], "waiting")
    registry.assign("sample", "GLOBAL", "initializing")
    check("waiter: 割当後は初期化中", registry.status("sample")["state"], "initializing")
    registry.leave("sample")
    check("waiter: 接続の継ぎ目も初期化中を維持", registry.status("sample")["state"], "initializing")
    registry.enter("sample", "GLOBAL", "Codex", "high", "working")
    registry.leave("sample")
    check("waiter: 初期化後は対応中", registry.status("sample")["state"], "working")
    registry.drop("sample")

    registry.enter("sample", "CCC", "別モデル", "low")
    print("ok   waiter: 空いた枠は次の担当が取れる")
    registry.leave("sample")


def test_wait_connection_failure() -> None:
    """サーバ不達を握りつぶして、偽の「待機中」にならない。"""
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("到達不能")):
        try:
            C._long_poll(
                "http://127.0.0.1:3000",
                "sample",
                1.0,
                {"session": "AAA", "model": "test", "effort": "low"},
            )
        except C.CommentError as exc:
            if "dev_server に接続できない" in str(exc):
                print("ok   wait: サーバ不達を接続エラーにする")
                return
        print("FAIL wait: サーバ不達を握りつぶした")
        FAILURES.append("wait: server unavailable")


def test_wait_parser_needs_no_book() -> None:
    args = C.build_parser().parse_args(["wait"])
    check("wait: 教材指定は不要", hasattr(args, "book"), False)


def test_client_disconnect_during_response() -> None:
    """ブラウザが応答前に離れてもサーバスレッドから例外を漏らさない。"""
    import dev_server

    handler = dev_server.PreviewHandler.__new__(dev_server.PreviewHandler)
    handler.send_response = mock.Mock()
    handler.send_header = mock.Mock()
    handler.end_headers = mock.Mock()
    handler.wfile = mock.Mock()
    handler.wfile.write.side_effect = BrokenPipeError(32, "Broken pipe")
    try:
        handler._send_bytes(b"{}", "application/json", True)
    except BrokenPipeError:
        print("FAIL server: 切断時の BrokenPipeError が漏れた")
        FAILURES.append("server: broken pipe")
    else:
        print("ok   server: 切断時の BrokenPipeError を正常終了として扱う")


def test_book_id_guard(root: Path) -> None:
    for bad in ("../etc", "Book", "a/b", ""):
        try:
            C.check_book_id(bad)
        except C.CommentError:
            continue
        print(f"FAIL book id guard: {bad!r} が通った")
        FAILURES.append(f"book id guard {bad!r}")
    print("ok   book id: 経路をまたぐ id を拒否")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_book(root)
        test_normalize()
        test_resolve_basic(root)
        test_resolve_occurrence(root)
        test_resolve_after_edit(root)
        test_resolve_missing(root)
        test_resolve_section(root)
        test_window(root)
        test_outline_metadata(root)
        test_edit_anchor(root)
        test_create_and_status(root)
        test_schema_revision_and_legacy_upgrade(root)
        test_atomic_write_and_conflicts(root)
        test_create_rejects_unresolvable(root)
        test_browser_quote_parity(root)
        test_group_same_section(root)
        test_waiter_registry(root)
        test_wait_connection_failure()
        test_wait_parser_needs_no_book()
        test_client_disconnect_during_response()
        test_conflict_http_status()
        test_book_id_guard(root)

    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
