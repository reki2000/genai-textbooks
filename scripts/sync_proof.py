#!/usr/bin/env python3
"""校正台（アーティファクト）の修正と指摘を、正本と指摘ログへ取り込む。

入力は校正台の共有 DB を ArtifactData の list（`out_dir` 付き）で書き出したディレクトリ。
`<dir>/edits/*.json`（ブロックごとの上書き）と `<dir>/feedback/*.json`（指摘と採否）を読む。

- edits: 発言・地の文の差し替え、削除、追加を `docs/books/{ID}/script/` へ反映し、
  README.md を作り直す。上書きを作った時点の本文（base）と今の本文が違うブロックは
  反映せず conflict として残す。
- feedback: 取り込んでいないものを `editorial/feedback.jsonl` へ追記する。採用された
  直し方は examples として残し、次の校正台・執筆・レビューが読む。

    python3 scripts/sync_proof.py <書き出し先> [--dry-run]

標準出力の末尾に、DB へ書き戻す操作を JSON で出す（反映した edits の削除と、
feedback の synced）。書き戻した後、校正台を作り直して公開し直す。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaruo_script  # noqa: E402
from build_proof_page import paragraphs, raw_id  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "docs" / "books"
FEEDBACK_LOG = ROOT / "editorial" / "feedback.jsonl"


def read_docs(directory: Path) -> list[dict]:
    rows = []
    if directory.is_dir():
        for file in sorted(directory.glob("*.json")):
            row = json.loads(file.read_text(encoding="utf-8"))
            row["_id"] = file.stem
            rows.append(row)
    return rows


def locate(acts: list[yaruo_script.Act], block_id: str):
    """ブロック ID から (幕, 幕内の位置, 項目, 段落の行範囲) を返す。発言の段落範囲は None。"""
    for act in acts:
        raw_index = 0
        for position, item in enumerate(act.items):
            if isinstance(item, yaruo_script.Raw):
                for k, span in enumerate(paragraphs(item.lines)):
                    if raw_id(act.name, raw_index, k) == block_id:
                        return act, position, item, span
                raw_index += 1
            elif item.id == block_id:
                return act, position, item, None
    return None


def text_of(item, span) -> str:
    lines = item.lines if span is None else item.lines[span[0] : span[1]]
    return "\n".join(lines)


def apply_edits(book: str, edits: list[dict]) -> tuple[list[yaruo_script.Act], dict[str, str]]:
    book_dir = BOOKS / book
    acts = yaruo_script.load_script(book_dir)
    result: dict[str, str] = {}
    # 位置がずれないよう、地の文の差し替え → 発言の差し替え・削除 → 追加 の順に当てる。
    # 地の文の ID は幕内の通し番号なので、発言の追加より先に解決しておく。
    resolved = []
    for edit in edits:
        if edit.get("insertAfter") and edit.get("base") is None:
            continue
        found = locate(acts, edit["_id"])
        if found is None:
            result[edit["_id"]] = "conflict: ブロックが見つからない"
            continue
        _, _, item, span = found
        if text_of(item, span) != (edit.get("base") or ""):
            result[edit["_id"]] = "conflict: 校正台で直した後に正本が変わった"
            continue
        resolved.append((edit, item, span))
    # 同じ素通し部分の段落は後ろから当てて、前の段落の行範囲をずらさない
    resolved.sort(key=lambda r: -(r[2][0] if r[2] else 0))
    for edit, item, span in resolved:
        new_lines = [] if edit.get("deleted") else str(edit.get("md", "")).split("\n")
        if span is None:
            item.lines = None if edit.get("deleted") else new_lines  # None は後で取り除く印
        else:
            start, end = span
            if not new_lines and end < len(item.lines) and item.lines[end] == "":
                end += 1  # 段落を消したら、後ろの空行も1つ詰める
            item.lines[start:end] = new_lines
        result[edit["_id"]] = "applied"

    inserts = [e for e in edits if e.get("insertAfter") and e.get("base") is None]
    pending = sorted(inserts, key=lambda e: str(e.get("createdAt", "")))
    progress = True
    while pending and progress:
        progress = False
        for edit in list(pending):
            found = locate(acts, edit["insertAfter"])
            if found is None:
                continue
            act, position, _, _ = found
            pending.remove(edit)
            progress = True
            if edit.get("deleted"):
                result[edit["_id"]] = "applied"
                continue
            new = yaruo_script.Utterance(edit["_id"], edit.get("speaker", ""), "", str(edit.get("md", "")).split("\n"))
            act.items[position + 1 : position + 1] = [yaruo_script.Raw([""]), new]
            result[edit["_id"]] = "applied"
    for edit in pending:
        result[edit["_id"]] = "conflict: 追加先のブロックが見つからない"

    for act in acts:
        items = []
        for item in act.items:
            if item.lines is None:
                # 削除した発言の直後の空行を1つ詰める
                continue
            items.append(item)
        cleaned: list = []
        for item in items:
            if (
                isinstance(item, yaruo_script.Raw)
                and cleaned
                and isinstance(cleaned[-1], yaruo_script.Raw)
            ):
                merged = cleaned[-1].lines + item.lines
                while len(merged) >= 2 and merged[-1] == "" and merged[-2] == "":
                    merged.pop()
                cleaned[-1] = yaruo_script.Raw(merged)
            else:
                cleaned.append(item)
        act.items = [i for i in cleaned if not (isinstance(i, yaruo_script.Raw) and not i.lines)]
    return acts, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("export")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    export = Path(args.export)
    edits = read_docs(export / "edits")
    feedback = read_docs(export / "feedback")

    ops: list[dict] = []
    for book in sorted({e.get("book", "") for e in edits}):
        book_edits = [e for e in edits if e.get("book") == book]
        acts, result = apply_edits(book, book_edits)
        errors = yaruo_script.validate(acts, BOOKS / book)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        markdown = yaruo_script.render_markdown(acts)
        reparsed = yaruo_script.acts_from_markdown(markdown)
        if yaruo_script.render_markdown(reparsed) != markdown:
            print(f"{book}: 反映後の本文が @形式として往復しない", file=sys.stderr)
            return 1
        for edit_id, status in sorted(result.items()):
            print(f"{book} {edit_id}: {status}")
            if status == "applied":
                ops.append({"op": "delete", "collection": "edits", "doc_id": edit_id})
        if not args.dry_run:
            yaruo_script.write_script(BOOKS / book, acts)
            (BOOKS / book / "README.md").write_text(markdown, encoding="utf-8")
            print(f"rendered {BOOKS / book / 'README.md'}")

    lines = []
    for row in sorted(feedback, key=lambda r: str(r.get("createdAt", ""))):
        if row.get("synced"):
            continue
        accepted = [p for p in row.get("patches", []) if p.get("accepted")] + list(row.get("propagated", []))
        rejected = [p for p in row.get("patches", []) if not p.get("accepted")]
        lines.append(
            {
                "book": row.get("book"),
                "act": row.get("act"),
                "target": row.get("target"),
                "text": row.get("text"),
                "scope": row.get("scope"),
                "source": row.get("source"),
                "offered": row.get("offered", []),
                "summary": row.get("summary", ""),
                "accepted": len(accepted),
                "rejected": len(rejected),
                "edited": sum(1 for p in accepted if p.get("final") and p.get("final") != p.get("proposed")),
                "doneActs": row.get("doneActs", []),
                "skippedActs": row.get("skippedActs", []),
                "examples": [
                    {"before": p.get("before", ""), "after": p.get("final", ""), "proposed": p.get("proposed", "")}
                    for p in accepted[:3]
                ],
                "status": "accepted" if accepted else "rejected",
                "createdAt": row.get("createdAt"),
            }
        )
        ops.append({"op": "update", "collection": "feedback", "doc_id": row["_id"], "data": {"synced": True}})
    if lines and not args.dry_run:
        with FEEDBACK_LOG.open("a", encoding="utf-8") as log:
            for line in lines:
                log.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"feedback: {len(lines)}件を {FEEDBACK_LOG.relative_to(ROOT)} へ{'追記する予定' if args.dry_run else '追記した'}")
    print("\nDB_OPS " + json.dumps(ops, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
