#!/usr/bin/env python3
"""@形式の教材から、スマホで校正するためのページ（Claude のアーティファクト）を作る。

出力は `build/proof/{ID}/` に置く:

- `index.html` … `scripts/proof_template.html` そのもの（教材に依存しない）
- `book.json` … 本文（ブロック ID・話者・Markdown）、登場人物欄、アウトライン、
  規約（`yaruo-rediscovery` の SKILL.md の抜粋と `editorial/rules.md`）、
  過去の指摘（`editorial/feedback.jsonl`）
- `figs/` … 本文が参照する図版

ブロック ID は、発言は台本の ID（`u7f3a`）、地の文・見出し・登場人物欄は
`r{幕}-{幕内の素通し部分の通し番号}-{その中の段落番号}`。ページは修正を共有 DB の `edits` に上書きとして
持ち、`scripts/sync_proof.py` が正本へ取り込む。

    python3 scripts/build_proof_page.py docs/books/statistics
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
import yaruo_script  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "proof_template.html"
SKILL = ROOT / ".claude" / "skills" / "yaruo-rediscovery" / "SKILL.md"
ANTI_PATTERNS = ROOT / ".claude" / "skills" / "yaruo-rediscovery" / "references" / "anti-patterns.md"
EDITORIAL = ROOT / "editorial"
RULE_SECTIONS = ("## 人物と書式", "## 面白味をつくる")
FIG_REF = re.compile(r"\((figs/[^)\s]+)\)")
HISTORY_LIMIT = 80


def raw_id(act_name: str, index: int, paragraph: int) -> str:
    return f"r{act_name}-{index}-{paragraph}"


def paragraphs(lines: list[str]) -> list[tuple[int, int]]:
    """空行で区切った段落の [開始, 終了) 行範囲。地の文は段落ごとにタップできるようにする。"""
    spans: list[tuple[int, int]] = []
    start = None
    for index, line in enumerate(lines + [""]):
        if line.strip() and start is None:
            start = index
        elif not line.strip() and start is not None:
            spans.append((start, index))
            start = None
    return spans


def skill_rules() -> str:
    """規約の正本（SKILL.md）から、人物と面白味の節だけを抜く。"""
    text = SKILL.read_text(encoding="utf-8")
    parts: list[str] = []
    for heading in RULE_SECTIONS:
        start = text.index(heading)
        end = text.find("\n## ", start + len(heading))
        parts.append(text[start : end if end != -1 else len(text)].strip())
    parts.append(ANTI_PATTERNS.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def editorial_rules() -> str:
    path = EDITORIAL / "rules.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def history(book: str) -> list[dict]:
    """過去の指摘。この教材のものを優先し、新しい順に並べる。"""
    path = EDITORIAL / "feedback.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda r: (r.get("book") == book, r.get("createdAt", "")), reverse=True)
    out = []
    for row in rows[:HISTORY_LIMIT]:
        out.append(
            {
                "book": row.get("book", ""),
                "text": row.get("text", ""),
                "scope": row.get("scope", ""),
                "speaker": row.get("speaker", ""),
                "status": row.get("status", ""),
                "examples": row.get("examples", [])[:2],
            }
        )
    return out


def series_outline(book_dir: Path) -> str:
    """教材の outline.md。無ければ catalog.yml の follows をたどり、前の巻の骨格を使う
    （シリーズの骨格は先頭巻にまとめて置く慣例。BUILD.md「シリーズ」）。"""
    seen = set()
    current = book_dir
    while current.name not in seen:
        seen.add(current.name)
        path = current / "outline.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        catalog = current / "catalog.yml"
        if not catalog.exists():
            break
        documents = (yaml.safe_load(catalog.read_text(encoding="utf-8")) or {}).get("documents", [])
        previous = next((d.get("follows") for d in documents if d.get("id") == current.name and d.get("follows")), None)
        if not previous:
            break
        current = current.parent / previous
    return ""


def build(book_dir: Path, out_dir: Path) -> Path:
    acts = yaruo_script.load_script(book_dir)
    readme = (book_dir / "README.md").read_text(encoding="utf-8")
    title = readme.split("\n", 1)[0].lstrip("# ").strip()
    outline = series_outline(book_dir)

    figs: set[str] = set()
    roster = ""
    out_acts = []
    for act in acts:
        blocks = []
        section = ""
        raw_index = 0
        for item in act.items:
            if isinstance(item, yaruo_script.Raw):
                text = "\n".join(item.lines)
                figs.update(FIG_REF.findall(text))
                if act.name == "00":
                    roster += text + "\n"
                for k, (start, end) in enumerate(paragraphs(item.lines)):
                    para = item.lines[start:end]
                    for line in para:
                        if line.startswith("### "):
                            section = line[4:].strip()
                    body = "\n".join(para)
                    if body.strip() != "---":
                        blocks.append({"t": "raw", "id": raw_id(act.name, raw_index, k), "md": body, "section": section})
                raw_index += 1
            else:
                figs.update(FIG_REF.findall(item.text))
                blocks.append(
                    {"t": "u", "id": item.id, "speaker": item.speaker, "note": item.note, "md": item.text, "section": section}
                )
        out_acts.append({"name": act.name, "heading": act.heading or "前付け", "blocks": blocks})

    data = {
        "book": book_dir.name,
        "title": title,
        "rules": skill_rules(),
        "editorialRules": editorial_rules(),
        "history": history(book_dir.name),
        "roster": roster.strip(),
        "outline": outline,
        "speakers": sorted({u.speaker for u in yaruo_script.all_utterances(acts)}),
        "acts": out_acts,
    }
    target = out_dir / book_dir.name
    if target.exists():
        shutil.rmtree(target)
    (target / "figs").mkdir(parents=True)
    (target / "book.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8").replace("{{TITLE}}", html.escape(title.split(" ── ")[0]))
    (target / "index.html").write_text(page, encoding="utf-8")
    for fig in sorted(figs):
        source = book_dir / fig
        if source.exists():
            shutil.copy2(source, target / fig)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("book")
    parser.add_argument("--out", default=str(ROOT / "build" / "proof"))
    args = parser.parse_args()
    target = build(Path(args.book), Path(args.out))
    files = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    print(f"built {target}: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
