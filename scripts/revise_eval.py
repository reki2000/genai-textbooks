#!/usr/bin/env python3
"""推敲の候補の質を、実際の教材から抜いた事例で測る（LLM を呼ぶので費用がかかる）。

直後の台詞が受けている語を持つ行を教材ごとに1つずつ決定的に選び、指定の
アクションで候補を作らせて、機械的に分かる不具合の件数を数える。

- lost：直後の台詞が受けている語を消した案
- added：target にも前後にも無い数値を持ち込んだ案
- blocked：前後の行との重複・話者またぎなどで採用できない案
- trimmed：写し込まれた前後の行を削った案
- clean：上のどれにも当たらない案

作法カード・アクションの指示文・モデルを変えたら、変更前後でこれを比べる。

    python3 scripts/revise_eval.py --cases 10 --actions shorten,plain --tier light
    python3 scripts/revise_eval.py --compare-hint     # 残す語のヒントの有無を比べる
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comments  # noqa: E402
import revise  # noqa: E402


def pick_cases(count: int, seed: int) -> list[tuple[str, dict]]:
    books = sorted(path.name for path in comments.BOOKS_DIR.iterdir() if (path / "README.md").is_file())
    random.Random(seed).shuffle(books)
    cases: list[tuple[str, dict]] = []
    for book in books:
        lines = comments.read_lines(comments.source_path(book))
        for index in range(120, len(lines)):
            body = lines[index].strip()
            if not 25 <= len(body) <= 90 or body.startswith(("#", "**", "|", "$", "!", "-", ">")):
                continue
            path = comments.heading_path_at(lines, index)
            if not path:
                continue
            quote = comments.normalize(body)
            anchor = {"heading": path[-1], "heading_level": 3, "quote": quote,
                      "quote_tail": quote[-40:], "occurrence": 1}
            try:
                target, located = revise.locate(book, "sentence", anchor)
            except (revise.ReviseError, comments.CommentError):
                continue
            if not target.start <= index <= target.end or not revise.following_terms(target, located):
                continue
            cases.append((book, anchor))
            break
        if len(cases) >= count:
            break
    return cases


def run_one(service: revise.Service, book: str, anchor: dict, action: str, backend: str, tier: str) -> dict:
    candidates, request_id, error = [], "", ""
    for event in service.generate({"book": book, "unit": "sentence", "action": action,
                                   "backend": backend, "tier": tier, "anchor": anchor}):
        if event["event"] == "meta":
            request_id = event["id"]
        elif event["event"] == "candidate":
            candidates.append(event)
        elif event["event"] == "error":
            error = event["message"]
    record = service.requests[request_id]
    return {"book": book, "action": action, "keep": record.keep, "old": record.target.text,
            "candidates": candidates, "error": error}


def summarize(results: list[dict]) -> dict:
    counts = {"total": 0, "lost": 0, "added": 0, "blocked": 0, "trimmed": 0, "clean": 0, "errors": 0}
    for result in results:
        counts["errors"] += bool(result["error"])
        for candidate in result["candidates"]:
            if candidate["new"] is None:
                continue
            counts["total"] += 1
            counts["lost"] += bool(candidate["lost"])
            counts["added"] += bool(candidate["added"])
            counts["blocked"] += bool(candidate["problems"])
            counts["trimmed"] += bool(candidate["trimmed"])
            counts["clean"] += candidate["ok"] and not candidate["lost"] and not candidate["added"]
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--actions", default="shorten,plain")
    parser.add_argument("--backend", default="claude")
    parser.add_argument("--tier", default="light", choices=["light", "heavy"])
    parser.add_argument("--compare-hint", action="store_true", help="残す語のヒントを渡さない条件とも比べる")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="", help="候補を含む結果を JSON で書き出す先")
    args = parser.parse_args()

    cases = pick_cases(args.cases, args.seed)
    jobs = [(book, anchor, action) for book, anchor in cases for action in args.actions.split(",")]
    output = {}
    for hint in ([False, True] if args.compare_hint else [True]):
        with tempfile.TemporaryDirectory() as log_dir:
            service = revise.Service(log_dir=Path(log_dir))  # 評価の依頼は推敲ログに混ぜない
            service.keep_hint = hint
            try:
                with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
                    results = list(pool.map(
                        lambda job: run_one(service, job[0], job[1], job[2], args.backend, args.tier), jobs))
            finally:
                service.close()
        counts = summarize(results)
        label = f"hint={'on' if hint else 'off'}"
        print(label + " " + " ".join(f"{key}={value}" for key, value in counts.items()), flush=True)
        output[label] = {"counts": counts, "results": results}
    if args.out:
        Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
