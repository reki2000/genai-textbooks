#!/usr/bin/env python3
"""校正台（アーティファクト）で採用された提案を、@形式の正本へ反映する。

入力は校正台の共有 DB `proposals` を書き出した JSON（ArtifactData の list の
結果をそのまま保存したもの、または文書の配列）。発言の提案は ID で当て先を
決め、提案を作った時点の本文（before）と今の本文が一致するときだけ差し替える。
一致しなければ `conflict` にして人へ戻す。節の書き直し依頼（kind: section）は
本文を変えず、作業メモとして出力する。

    python3 scripts/apply_proposals.py proposals/                # ArtifactData の list に out_dir を渡した書き出し
    python3 scripts/apply_proposals.py proposals.json            # 反映して README.md を作り直す
    python3 scripts/apply_proposals.py proposals.json --dry-run  # 何が起きるかだけ見る

標準出力の末尾に、DB へ書き戻す状態（文書 ID → status / note）を JSON で出す。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaruo_script  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "docs" / "books"


def load_rows(path: Path) -> list[dict]:
    if path.is_dir():
        # ArtifactData の list に out_dir を渡した形（1文書1ファイル、ファイル名が文書 ID）
        rows = []
        for file in sorted(path.rglob("*.json")):
            row = json.loads(file.read_text(encoding="utf-8"))
            row["_id"] = file.stem
            rows.append(row)
        return rows
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("documents", "docs", "items", "results", "rows"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    rows = []
    for item in data:
        if isinstance(item.get("data"), dict):
            row = dict(item["data"])
            row["_id"] = item.get("id") or item.get("doc_id") or item.get("_id")
        else:
            row = dict(item)
            row["_id"] = row.get("_id") or row.get("id") or row.get("doc_id")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("proposals")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = sorted(load_rows(Path(args.proposals)), key=lambda r: str(r.get("createdAt", "")))
    updates: dict[str, dict] = {}
    touched: dict[str, list[yaruo_script.Act]] = {}
    sections: list[dict] = []

    for row in rows:
        if row.get("status") != "open":
            continue
        book = row.get("book", "")
        book_dir = BOOKS / book
        if not (book_dir / yaruo_script.SCRIPT_DIR_NAME).is_dir():
            updates[row["_id"]] = {"status": "conflict", "note": f"{book} は @形式ではない"}
            continue
        if row.get("kind") == "section":
            sections.append(row)
            continue
        acts = touched.setdefault(book, yaruo_script.load_script(book_dir))
        target = next((u for u in yaruo_script.all_utterances(acts) if u.id == row.get("uid")), None)
        if target is None:
            updates[row["_id"]] = {"status": "conflict", "note": "発言が見つからない（削除か書き直し済み）"}
        elif target.text != row.get("before"):
            updates[row["_id"]] = {"status": "conflict", "note": "提案の後に本文が変わった。今の本文で出し直す"}
        else:
            after = str(row.get("after", "")).strip("\n")
            target.lines = after.split("\n")
            updates[row["_id"]] = {"status": "applied", "note": ""}
            print(f"applied {book} {target.id} {target.speaker}: {row.get('label', '')}")

    for book, acts in touched.items():
        book_dir = BOOKS / book
        errors = yaruo_script.validate(acts, book_dir)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        if not args.dry_run:
            yaruo_script.write_script(book_dir, acts)
            (book_dir / "README.md").write_text(yaruo_script.render_markdown(acts), encoding="utf-8")
            print(f"rendered {book_dir / 'README.md'}")

    for row in sections:
        plan = row.get("plan") or {}
        print(f"\n節の書き直し依頼 [{row['_id']}] {row.get('book')} {row.get('section')}: {row.get('label')} — {row.get('direction')}")
        print(f"  案: {plan.get('title', '')}")
        for index, beat in enumerate(plan.get("beats", []), start=1):
            print(f"  {index}. {beat}")
        print(f"  残す: {plan.get('keeps', '')}\n  影響: {plan.get('risk', '')}")

    print("\nDB_UPDATES " + json.dumps(updates, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
