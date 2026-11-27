#!/usr/bin/env python3
"""@形式（`docs/books/{ID}/script/`）の教材を、docsify を使わない静的 HTML にする。

発言は `<div class="u" data-uid="…" data-speaker="…">` で包む。発言の ID で
本文の位置を一意に指せるので、タップした発言をそのまま校正の対象にできる。
数式は KaTeX の auto-render、ルビは `generate_site.convert_ruby_to_html` と同じ変換。

    python3 scripts/render_static.py docs/books/statistics -o /tmp/statistics.html
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from markdown_it import MarkdownIt
    from mdit_py_plugins.anchors import anchors_plugin
    from mdit_py_plugins.dollarmath import dollarmath_plugin
    from mdit_py_plugins.footnote import footnote_plugin
except ImportError:
    sys.exit(
        "markdown-it-py と mdit-py-plugins が要る。"
        "`python3 -m pip install -r requirements-dev.txt` を実行する。"
    )

import yaruo_script  # noqa: E402

STATIC_PAGE_NAME = "static.html"
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"
SPEAKER_CLASS = {
    "やる夫": "yaruo",
    "やらない夫": "yaranai",
    "できる夫": "dekiruo",
    "できる子": "dekiruko",
}
README_LINK = re.compile(r'href="(\.\./[a-z0-9-]+/)README\.md(#[^"]*)?"')


def _slug(text: str) -> str:
    return re.sub(r"\s+", "-", text.strip())


def _markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "linkify": False, "typographer": False, "breaks": True})
    md.enable("table").enable("strikethrough")
    md.use(footnote_plugin)
    md.use(
        dollarmath_plugin,
        allow_space=True,
        allow_digits=True,
        double_inline=True,
        renderer=lambda content, opts: html.escape(content),
    )
    md.use(anchors_plugin, min_level=2, max_level=3, slug_func=_slug)
    md.add_render_rule(
        "math_inline",
        lambda self, tokens, idx, options, env: f'<span class="math">\\({html.escape(tokens[idx].content)}\\)</span>',
    )
    md.add_render_rule(
        "math_inline_double",
        lambda self, tokens, idx, options, env: f'<div class="math">\\[{html.escape(tokens[idx].content)}\\]</div>',
    )
    md.add_render_rule(
        "math_block",
        lambda self, tokens, idx, options, env: f'<div class="math">\\[{html.escape(tokens[idx].content)}\\]</div>\n',
    )
    return md


def _ruby(text: str) -> str:
    # generate_site を読み込むとそちらが本モジュールを読み込むので、使う時点で読む。
    from generate_site import convert_ruby_to_html

    return convert_ruby_to_html(text)


def wrapped_markdown(acts: list[yaruo_script.Act]) -> str:
    """発言を HTML ブロックで包んだ Markdown。脚注を全体で解決するため一度に描画する。"""
    out: list[str] = []
    for act in acts:
        for item in act.items:
            if isinstance(item, yaruo_script.Raw):
                out.extend(item.lines)
                continue
            css = SPEAKER_CLASS.get(item.speaker, "other")
            note = f'<span class="note">{html.escape(item.note)}</span>' if item.note else ""
            out.append(
                f'<div class="u {css}" id="{item.id}" data-uid="{item.id}" data-speaker="{html.escape(item.speaker)}">'
                f'<div class="spk">{html.escape(item.speaker)}{note}</div>'
            )
            out.append("")
            out.extend(item.lines)
            out.append("")
            out.append("</div>")
    return "\n".join(out) + "\n"


def _toc_label(title: str) -> str:
    return re.sub(r"\$([^$]+)\$", r"\\(\1\\)", html.escape(title, quote=False))


def toc(acts: list[yaruo_script.Act]) -> str:
    items: list[str] = []
    for act in acts:
        for item in act.items:
            if not isinstance(item, yaruo_script.Raw):
                continue
            for line in item.lines:
                for prefix, level in (("## ", 2), ("### ", 3)):
                    if line.startswith(prefix):
                        title = line[len(prefix) :].strip()
                        items.append(
                            f'<li class="l{level}"><a href="#{html.escape(_slug(title))}">{_toc_label(title)}</a></li>'
                        )
    return "<ul>" + "".join(items) + "</ul>"


def render_body(book_dir: Path) -> tuple[str, str]:
    acts = yaruo_script.load_script(book_dir)
    body = _markdown().render(_ruby(wrapped_markdown(acts)))
    return README_LINK.sub(lambda m: f'href="{m.group(1)}{m.group(2) or ""}"', body), toc(acts)


PAGE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="{katex}/katex.min.css">
<style>
:root {{
  --bg: #fbfaf7; --fg: #1f2328; --muted: #6a737d; --line: #e4e1da; --card: #ffffff;
  --yaruo: #1f6feb; --yaranai: #2f855a; --dekiruo: #b7791f; --dekiruko: #b83280; --other: #6a737d;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #15171a; --fg: #e6e6e6; --muted: #9aa4ae; --line: #2c3036; --card: #1c1f23;
    --yaruo: #79a8ff; --yaranai: #6fcf97; --dekiruo: #f2c46d; --dekiruko: #f48fc7; --other: #9aa4ae;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #15171a; --fg: #e6e6e6; --muted: #9aa4ae; --line: #2c3036; --card: #1c1f23;
  --yaruo: #79a8ff; --yaranai: #6fcf97; --dekiruo: #f2c46d; --dekiruko: #f48fc7; --other: #9aa4ae;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.85 "Hiragino Sans", "Noto Sans JP", system-ui, sans-serif; }}
.wrap {{ display: grid; grid-template-columns: 17rem minmax(0, 46rem); gap: 2.5rem; justify-content: center; padding: 0 16px; }}
nav {{ position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 1.5rem 0; font-size: 13px; line-height: 1.5; }}
nav ul {{ list-style: none; margin: 0; padding: 0; }}
nav li.l2 {{ margin-top: .8rem; font-weight: 600; }}
nav li.l3 {{ padding-left: .8rem; color: var(--muted); }}
nav a {{ color: inherit; text-decoration: none; }}
main {{ padding: 1.5rem 0 6rem; min-width: 0; }}
h1 {{ font-size: 1.6rem; line-height: 1.4; }}
h2 {{ margin-top: 3rem; padding-bottom: .3rem; border-bottom: 2px solid var(--line); font-size: 1.35rem; }}
h3 {{ margin-top: 2.2rem; font-size: 1.1rem; }}
hr {{ border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }}
a {{ color: var(--yaruo); }}
img {{ max-width: 100%; height: auto; }}
table {{ border-collapse: collapse; display: block; overflow-x: auto; font-size: 14px; }}
th, td {{ border: 1px solid var(--line); padding: .3rem .6rem; }}
pre {{ overflow-x: auto; background: var(--card); border: 1px solid var(--line); padding: .8rem; font-size: 13px; }}
.math {{ overflow-x: auto; overflow-y: hidden; }}
.u {{ margin: .9rem 0; padding: .1rem 0 .1rem .9rem; border-left: 3px solid var(--c, var(--other)); }}
.u > p {{ margin: .2rem 0; }}
.u .spk {{ font-weight: 700; font-size: 14px; color: var(--c, var(--other)); }}
.u .note {{ font-weight: 400; color: var(--muted); }}
.u.yaruo {{ --c: var(--yaruo); }} .u.yaranai {{ --c: var(--yaranai); }}
.u.dekiruo {{ --c: var(--dekiruo); }} .u.dekiruko {{ --c: var(--dekiruko); }}
.u:target {{ background: color-mix(in srgb, var(--c) 10%, transparent); }}
.footnotes {{ font-size: 14px; }}
@media (max-width: 900px) {{
  .wrap {{ display: block; }}
  nav {{ position: static; height: auto; padding: 1rem 0 0; }}
  nav > details > ul {{ max-height: 50vh; overflow-y: auto; }}
}}
</style>
</head>
<body>
<div class="wrap">
<nav><details open><summary>目次</summary>{toc}</details></nav>
<main>
{body}
</main>
</div>
<script defer src="{katex}/katex.min.js"></script>
<script defer src="{katex}/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{{delimiters:[{{left:'\\\\[',right:'\\\\]',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}}],throwOnError:false}})"></script>
<script>
if (matchMedia('(max-width: 900px)').matches) document.querySelector('nav details').removeAttribute('open');
</script>
</body>
</html>
"""


def render_book_page(book_dir: Path, title: str, description: str) -> str:
    body, nav = render_body(book_dir)
    return PAGE.format(
        title=html.escape(title),
        description=html.escape(description),
        katex=KATEX,
        toc=nav,
        body=body,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    book_dir = Path(args.book)
    readme = (book_dir / "README.md").read_text(encoding="utf-8")
    title = readme.split("\n", 1)[0].lstrip("# ").strip()
    Path(args.output).write_text(render_book_page(book_dir, title, ""), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
