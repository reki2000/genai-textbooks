#!/usr/bin/env python3
"""@形式の教材から、スマホで校正するためのページ（Claude のアーティファクト）を作る。

出力は `build/proof/{ID}/` に置く:

- `index.html` … `scripts/proof_template.html` そのもの（教材に依存しない）
- `book.json` … 本文（発言 ID・話者・Markdown・描画済み HTML）、登場人物欄、
  アウトライン、人物と面白味の規約（`yaruo-rediscovery` の SKILL.md から抜粋）
- `figs/` … 本文が参照する図版

ページは発言のタップ → Claude で直す方向の候補 → 方向を選んで改訂案3つ →
採用、と進み、採用した案をアーティファクトの共有 DB（`proposals`）へ保存する。
正本への反映は `scripts/apply_proposals.py` が行う。

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

import render_static  # noqa: E402
import yaruo_script  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "proof_template.html"
SKILL = ROOT / ".claude" / "skills" / "yaruo-rediscovery" / "SKILL.md"
ANTI_PATTERNS = ROOT / ".claude" / "skills" / "yaruo-rediscovery" / "references" / "anti-patterns.md"
RULE_SECTIONS = ("## 人物と書式", "## 面白味をつくる")
FIG_REF = re.compile(r"\((figs/[^)\s]+)\)")


def skill_rules() -> str:
    """規約の正本（SKILL.md）から、人物と面白味の節だけを抜く。"""
    text = SKILL.read_text(encoding="utf-8")
    parts: list[str] = []
    for heading in RULE_SECTIONS:
        start = text.index(heading)
        end = text.find("\n## ", start + len(heading))
        parts.append(text[start : end if end != -1 else len(text)].strip())
    anti = ANTI_PATTERNS.read_text(encoding="utf-8").strip()
    return "\n\n".join(parts + [anti])


def _block_markdown() -> object:
    md = render_static._markdown()
    md.disable("footnote_ref", ignoreInvalid=True)
    return md


def build(book_dir: Path, out_dir: Path) -> Path:
    acts = yaruo_script.load_script(book_dir)
    readme = (book_dir / "README.md").read_text(encoding="utf-8")
    title = readme.split("\n", 1)[0].lstrip("# ").strip()
    outline_path = book_dir / "outline.md"
    outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""
    md = _block_markdown()

    def to_html(text: str) -> str:
        return md.render(render_static._ruby(text))

    figs: set[str] = set()
    roster = ""
    out_acts = []
    for act in acts:
        blocks = []
        section = ""
        for item in act.items:
            if isinstance(item, yaruo_script.Raw):
                text = "\n".join(item.lines)
                figs.update(FIG_REF.findall(text))
                if act.name == "00":
                    roster += text + "\n"
                for line in item.lines:
                    if line.startswith("### "):
                        section = line[4:].strip()
                if text.strip() and text.strip() != "---":
                    blocks.append({"t": "raw", "html": to_html(text), "section": section})
            else:
                figs.update(FIG_REF.findall(item.text))
                blocks.append(
                    {
                        "t": "u",
                        "id": item.id,
                        "speaker": item.speaker,
                        "note": item.note,
                        "md": item.text,
                        "html": to_html(item.text),
                        "section": section,
                    }
                )
        out_acts.append({"name": act.name, "heading": act.heading or "前付け", "blocks": blocks})

    data = {
        "book": book_dir.name,
        "title": title,
        "rules": skill_rules(),
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
