#!/usr/bin/env python3
"""プレビュー上の推敲：選択 → 候補 → 選んで採用。

LLM には本文を編集させず、差分の候補だけを返させる。書き換えは人が選んだ
候補をここで決定的に適用する。仕様は REVISE.md。

- 対象の特定は `comments.py` のアンカー解決（見出し＋引用＋出現順）を流用する。
- 候補は JSONL で1案1行。届いた行から順に検証（置換元の一意性・lint）して返す。
- 依頼・候補・採否・採用後の手直しを `revisions/log/YYYY-MM.jsonl` に残す。
  次の依頼のお手本（few-shot）と、定期の分析（`stats`）の材料になる。

    python3 scripts/revise.py try --book {ID} --quote '選んだ文' --action shorten
    python3 scripts/revise.py stats
"""

from __future__ import annotations

import argparse
import difflib
import re
import hashlib
import json
import secrets
import shutil
import sys
import threading
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comments  # noqa: E402
import revise_backends as backends  # noqa: E402
import yaruo_lint  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "scripts" / "revise.toml"
CARD_PATH = ROOT / "scripts" / "revise_card.md"
LOG_DIR = ROOT / "revisions" / "log"

TIERS = ("light", "heavy")
MAX_TARGET_LINES = 120
MAX_INSTRUCTION_CHARS = 2000
FEWSHOT_LIMIT = 3
FEWSHOT_MAX_CHARS = 600
# 採用後にこの秒数以内の手直しを「採用後の手直し」として記録する。
POST_EDIT_WINDOW = 30 * 60
CONTEXT_CHARS = 80


# 直後の台詞が受けている語を探す範囲（空行・話者行を除いた行数）。
FOLLOWING_LINES = 6
_TERM_RE = re.compile(
    r"[0-9０-９][0-9０-９,，.．]*[万億兆千百十]*[円%％倍年月日人個回歳件点]?"
    r"|[一-龥々〆ヵヶ]{2,}"
    r"|[ァ-ヴ][ァ-ヴー]+"
    r"|[A-Za-zＡ-Ｚａ-ｚ][A-Za-zＡ-Ｚａ-ｚ0-9]+"
)


class ReviseError(ValueError):
    pass


# --------------------------------------------------------------------------
# 設定
# --------------------------------------------------------------------------


@dataclass
class Action:
    id: str
    label: str
    key: str = ""
    tier: str = "light"
    instruction: str = ""


@dataclass
class Config:
    default_backend: str = "claude"
    candidates: int = 3
    pool_sizes: dict[str, int] = field(default_factory=lambda: {"light": 1, "heavy": 1})
    idle_ttl: float = 600.0
    heavy_lines: int = 12
    heavy_chars: int = 1200
    heavy_instruction_chars: int = 60
    context_utterances: int = 6
    tiers: dict[str, dict[str, backends.TierSpec]] = field(default_factory=dict)
    actions: list[Action] = field(default_factory=list)

    def action(self, action_id: str) -> Action:
        for action in self.actions:
            if action.id == action_id:
                return action
        if action_id == "free":
            return Action("free", "自由指示", tier="light")
        raise ReviseError(f"未知のアクション: {action_id!r}")

    def spec(self, tier: str, backend: str) -> backends.TierSpec:
        try:
            return self.tiers[tier][backend]
        except KeyError as exc:
            raise ReviseError(f"revise.toml に tiers.{tier}.{backend} が無い") from exc


def load_config(path: Path = CONFIG_PATH) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    pool = data.get("pool", {})
    routing = data.get("routing", {})
    tiers: dict[str, dict[str, backends.TierSpec]] = {}
    for tier, by_backend in (data.get("tiers") or {}).items():
        for backend, spec in (by_backend or {}).items():
            if backend not in backends.BACKENDS:
                raise ReviseError(f"未知のバックエンド: {backend}")
            tiers.setdefault(tier, {})[backend] = backends.TierSpec(
                backend=backend,
                model=str(spec.get("model", "")),
                effort=str(spec.get("effort", "")),
                thinking=bool(spec.get("thinking", tier == "heavy")),
            )
    actions = [
        Action(
            id=str(item["id"]),
            label=str(item.get("label", item["id"])),
            key=str(item.get("key", "")),
            tier=str(item.get("tier", "light")),
            instruction=str(item.get("instruction", "")),
        )
        for item in data.get("actions", [])
    ]
    return Config(
        default_backend=str(data.get("default_backend", "claude")),
        candidates=int(data.get("candidates", 3)),
        pool_sizes={tier: int(pool.get(tier, 1)) for tier in TIERS},
        idle_ttl=float(pool.get("idle_ttl", 600)),
        heavy_lines=int(routing.get("heavy_lines", 12)),
        heavy_chars=int(routing.get("heavy_chars", 1200)),
        heavy_instruction_chars=int(routing.get("heavy_instruction_chars", 60)),
        context_utterances=int((data.get("context") or {}).get("utterances", 6)),
        tiers=tiers,
        actions=actions,
    )


# --------------------------------------------------------------------------
# 対象の特定
# --------------------------------------------------------------------------


@dataclass
class Target:
    book: str
    unit: str
    quote: str
    heading_path: list[str]
    start: int  # 0-indexed 行（包含）
    end: int  # 0-indexed 行（包含）
    offset: int  # 本文中の文字位置
    text: str
    source_hash: str

    @property
    def line_count(self) -> int:
        return self.end - self.start + 1


def _transient_comment(book: str, unit: str, anchor: dict, kind: str) -> comments.Comment:
    return comments.Comment(
        id="0000",
        book=book,
        kind=kind,
        unit=unit if unit in comments.UNITS else "sentence",
        status="open",
        created="",
        anchor=comments.Anchor(
            heading=str(anchor.get("heading", "")),
            heading_level=int(anchor.get("heading_level", 0) or 0),
            heading_path=[str(item) for item in anchor.get("heading_path", []) or []],
            quote=str(anchor.get("quote", ""))[: comments.MAX_QUOTE_CHARS],
            quote_tail=str(anchor.get("quote_tail", ""))[-comments.MAX_QUOTE_CHARS :],
            occurrence=int(anchor.get("occurrence", 1) or 1),
        ),
        body="",
    )


def locate(book: str, unit: str, anchor: dict) -> tuple[Target, list[str]]:
    """選択を今の本文の行範囲へ引き直す。見つからなければ例外（推測で別の場所へ落とさない）。"""
    comments.check_book_id(book)
    path = comments.source_path(book)
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    comment = _transient_comment(book, unit, anchor, "wording")
    span = comments.resolve(comment, lines)
    if span is None:
        raise ReviseError("選択範囲を本文から特定できなかった。数式や図の内側を避けて選び直してほしい")
    start, end = span
    if comment.unit != "section":
        start, end = sentence_bounds(lines, start, end)
    if end - start + 1 > MAX_TARGET_LINES:
        raise ReviseError(f"範囲が大きすぎる（{end - start + 1}行）。{MAX_TARGET_LINES}行以内で選び直してほしい")
    offset = sum(len(line) for line in lines[:start])
    text = "".join(lines[start : end + 1])
    target = Target(
        book=book,
        unit=comment.unit,
        quote=comment.anchor.quote,
        heading_path=comments.heading_path_at(lines, start),
        start=start,
        end=end,
        offset=offset,
        text=text,
        source_hash=_hash(source),
    )
    return target, lines


_SPEAKER_RE = re.compile(r"\*\*[^*]+\*\*(（[^）]*）)?[：:]")
_SENTENCE_END = ("。", "？", "！", "?", "!", "…", "」", "』", "）", ")", "──", "$$")
SENTENCE_EXTEND_LIMIT = 6


def _is_prose(line: str) -> bool:
    body = line.strip()
    if not body or body == "---" or body.startswith(("#", "|", "$$", "![", "```")):
        return False
    return not _SPEAKER_RE.fullmatch(body)


def _ends_sentence(line: str) -> bool:
    # 強調やコードの閉じ記号の内側で文が終わっていれば、文の終わりとみなす。
    return line.rstrip().rstrip("*_`").endswith(_SENTENCE_END)


def sentence_bounds(lines: list[str], start: int, end: int) -> tuple[int, int]:
    """行の途中で切れている文を、同じ発言の中で文の切れ目まで広げる。

    行単位の target が文の途中で終わっていると、モデルは続きの行まで書き換えて
    返し、採用すると本文が重複する。
    """
    for _ in range(SENTENCE_EXTEND_LIMIT):
        if _ends_sentence(lines[end]) or end + 1 >= len(lines) or not _is_prose(lines[end + 1]):
            break
        end += 1
    for _ in range(SENTENCE_EXTEND_LIMIT):
        if start == 0 or not _is_prose(lines[start - 1]) or _ends_sentence(lines[start - 1]):
            break
        start -= 1
    return start, end


def context_lines(target: Target, lines: list[str], window: tuple[int, int]) -> tuple[list[str], list[str]]:
    """target の直前・直後の窓の行。"""
    start = min(window[0], target.start)
    end = max(window[1], target.end + 1)
    return lines[start : target.start], lines[target.end + 1 : end]


CONTEXT_LINE_LIMIT = 120


def utterance_window(lines: list[str], start: int, end: int, utterances: int) -> tuple[int, int]:
    """target の前後に、発言を `utterances` 個ずつ含む範囲。

    文や段落だけでは、誰が何を受けて話しているかが見えず、書き換えで会話の
    つながりが壊れる。話者行を数えて前後のやり取りごと渡す。
    """
    # 前：target を含む発言自身の話者行に加えて、さらに `utterances` 個さかのぼる。
    window_start, found = start, 0
    for index in range(start - 1, max(start - CONTEXT_LINE_LIMIT, 0) - 1, -1):
        window_start = index
        if _SPEAKER_RE.fullmatch(lines[index].strip()):
            found += 1
            if found > utterances:
                break
    # 後：`utterances` 個の発言の終わり（次の話者行の手前）まで。
    window_end, found = end + 1, 0
    for index in range(end + 1, min(end + 1 + CONTEXT_LINE_LIMIT, len(lines))):
        if _SPEAKER_RE.fullmatch(lines[index].strip()):
            found += 1
            if found > utterances:
                break
        window_end = index + 1
    while window_end > end + 1 and not lines[window_end - 1].strip():
        window_end -= 1
    return window_start, window_end


def window_of(target: Target, lines: list[str], tier: str, anchor: dict,
              utterances: int = 6) -> tuple[int, int]:
    """light は前後のやり取り、heavy は節ぜんぶ（と前後のやり取りの広い方）。"""
    around = utterance_window(lines, target.start, target.end, utterances)
    if tier != "heavy":
        return around
    comment = _transient_comment(target.book, target.unit, anchor, "substance")
    section = comments.window_for(comment, lines, (target.start, target.end))
    return min(section[0], around[0]), max(section[1], around[1])


def choose_tier(requested: str, action: Action, target: Target, instruction: str, config: Config) -> str:
    """ティアの自動の振り分けは規則で決める（LLM に決めさせると遅延が増えるだけ）。"""
    if requested in TIERS:
        return requested
    if target.unit == "section":
        return "heavy"
    if target.line_count > config.heavy_lines or len(target.text) > config.heavy_chars:
        return "heavy"
    if len(instruction) > config.heavy_instruction_chars:
        return "heavy"
    return action.tier if action.tier in TIERS else "light"


def _speech_lines(lines: list[str]) -> list[str]:
    """空行・区切り・話者行を除いた本文の行。"""
    kept = []
    for line in lines:
        body = line.strip()
        if not body or body == "---" or body.startswith("#"):
            continue
        if re.fullmatch(r"\*\*[^*]+\*\*(（[^）]*）)?[：:]", body):
            continue
        kept.append(body)
    return kept


def terms_of(text: str) -> list[str]:
    """漢字・カタカナの2字以上の連なり、数（単位付き）、英単語。"""
    seen: list[str] = []
    for match in _TERM_RE.finditer(comments.normalize(text)):
        term = match.group(0)
        if len(term) < 2 and not term[0].isdigit():
            continue
        if term not in seen:
            seen.append(term)
    return seen


def following_terms(target: Target, lines: list[str]) -> list[str]:
    """target に出て、直後の台詞でも使われている語。

    直後の相手はその語を受けて話しているので、書き換えで消すと会話が
    つながらなくなる（light が特に落としやすい）。語の同定は決定的に行い、
    プロンプトで「残す語」として渡すと同時に、候補の検査にも使う。
    """
    after = "".join(_speech_lines(lines[target.end + 1 :])[:FOLLOWING_LINES])
    after_norm = comments.normalize(after)
    found = []
    for term in terms_of(target.text):
        if term in after_norm and not any(term in other and term != other for other in found):
            found = [other for other in found if other not in term]
            found.append(term)
    return found


_NUMBER_RE = re.compile(r"[0-9][0-9,.]*")


def added_numbers(new: str, known: str) -> list[str]:
    """候補に出てきた数のうち、target にも前後の本文にも無いもの（作られた数値の疑い）。"""
    known_numbers = {match.group(0).replace(",", "") for match in _NUMBER_RE.finditer(comments.normalize(known))}
    added = []
    for match in _NUMBER_RE.finditer(comments.normalize(new)):
        number = match.group(0).replace(",", "").rstrip(".")
        if number and number not in known_numbers and number not in added:
            added.append(number)
    return added


def lost_terms(new: str, terms: list[str]) -> list[str]:
    normalized = comments.normalize(new)
    return [term for term in terms if term not in normalized]


# --------------------------------------------------------------------------
# プロンプト
# --------------------------------------------------------------------------


def card_text() -> str:
    return CARD_PATH.read_text(encoding="utf-8").strip()


def card_version() -> str:
    return _hash(card_text())[:8]


def outline_text(book: str) -> str:
    path = comments.outline_path(book)
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            text = text[end + 4 :]
    return text.strip()


def system_prompt(book: str) -> str:
    """変わりにくいものほど前に置く（先頭一致のキャッシュを効かせるため）。

    作法カード → 教材の骨格。骨格を変えると system ごとキャッシュから外れるので、
    骨格の更新は採用のたびではなくまとめて行う（REVISE.md）。
    """
    parts = [card_text()]
    outline = outline_text(book)
    if outline:
        parts.append("# この教材の骨格\n\n" + outline)
    return "\n\n".join(parts) + "\n"


def user_prompt(
    target: Target,
    lines: list[str],
    window: tuple[int, int],
    action: Action,
    instruction: str,
    count: int,
    examples: list[dict],
    keep: list[str] | None = None,
) -> str:
    before_lines, after_lines = context_lines(target, lines, window)
    before = "".join(before_lines)
    after = "".join(after_lines)
    parts: list[str] = []
    if examples:
        shots = []
        for example in examples:
            shots.append(
                f"依頼: {example['request']}\n元:\n{example['before']}\n採用された形:\n{example['after']}"
            )
        parts.append("# お手本（この教材の書き手が過去に採用した書き換え）\n\n" + "\n\n---\n\n".join(shots))
    # 前後は参考として別の区画に置き、書き換える部分だけを <target> に入れる。窓の中に
    # target を埋め込むと、軽いモデルは窓ごと書き直して返しやすい。
    parts.append(
        "# 前後の本文（参考。書き換えない）\n\n"
        "<before>\n" + before + "</before>\n\n<after>\n" + after + "</after>"
    )
    parts.append("# 書き換える部分\n\n<target>\n" + target.text + "</target>")
    request = action.instruction
    if instruction:
        request = (request + "\n" if request else "") + "書き手からの指示: " + instruction
    parts.append(
        "# 依頼\n\n"
        f"見出し: {' > '.join(target.heading_path)}\n"
        f"選択箇所（表示上の文字列）: 「{target.quote}」\n"
        + (f"直後の台詞が受けている語（どの案でも残す）: {'、'.join(keep)}\n" if keep else "")
        + f"依頼: {request}\n"
        f"案を{count}個、1行1案の JSON で。"
    )
    return "\n\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# 候補
# --------------------------------------------------------------------------


class CandidateParser:
    """逐次届く本文から、完成した JSON 行を順に取り出す。"""

    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, text: str) -> list[dict]:
        self.buffer += text
        found: list[dict] = []
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            parsed = self._parse(line)
            if parsed is not None:
                found.append(parsed)
        return found

    def flush(self) -> list[dict]:
        line, self.buffer = self.buffer, ""
        parsed = self._parse(line)
        return [parsed] if parsed is not None else []

    @staticmethod
    def _parse(line: str) -> dict | None:
        line = line.strip()
        if not line.startswith("{"):
            return None  # コードフェンスや前置きは読み飛ばす
        try:
            data = json.loads(line)
        except ValueError:
            return None
        if not isinstance(data, dict) or "new" not in data:
            return None
        return data


@dataclass
class Candidate:
    index: int
    old: str
    new: str | None
    why: str
    offset: int  # 生成時点の本文での old の位置（-1 は不明）
    problems: list[str] = field(default_factory=list)
    lint: list[str] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    trimmed: bool = False

    @property
    def ok(self) -> bool:
        return self.new is not None and not self.problems

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "old": self.old,
            "new": self.new,
            "why": self.why,
            "ok": self.ok,
            "problems": self.problems,
            "lint": self.lint,
            "lost": self.lost,
            "added": self.added,
            "trimmed": self.trimmed,
        }


def lint_errors(text: str) -> dict[tuple[str, str], int]:
    """error の件数を (ルール, 行番号を除いた文言) ごとに数える。行は編集でずれるため。"""
    lines = text.splitlines(keepends=True)
    result = yaruo_lint.Result(list(lines))
    for rule in yaruo_lint.REGISTRY:
        rule.run(list(lines), result)
    counts: dict[tuple[str, str], int] = {}
    for finding in result.findings:
        if finding.level != "error":
            continue
        key = (finding.rule, finding.message)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _bare(line: str) -> str:
    return line.rstrip("\n")


def trim_context(new: str, before: list[str], after: list[str]) -> tuple[str, bool]:
    """候補の先頭・末尾に写し込まれた前後の行を落とす。

    先頭が直前の行の末尾側と、末尾が直後の行の先頭側と一字一句一致する分だけ
    削る。書き換えた行は一致しないので残る。
    """
    rows = new.splitlines(keepends=True)
    head = 0
    for k in range(min(len(rows) - 1, len(before)), 0, -1):
        if [_bare(row) for row in rows[:k]] == [_bare(row) for row in before[-k:]]:
            head = k
            break
    rows = rows[head:]
    tail = 0
    for m in range(min(len(rows) - 1, len(after)), 0, -1):
        if [_bare(row) for row in rows[-m:]] == [_bare(row) for row in after[:m]]:
            tail = m
            break
    if tail:
        rows = rows[:-tail]
    return "".join(rows), bool(head or tail)


def overlap_problems(new: str, target_text: str, before: list[str], after: list[str]) -> list[str]:
    problems = []
    context = {comments.normalize(line) for line in before + after}
    context.discard("")
    for row in new.splitlines():
        normalized = comments.normalize(row)
        if len(normalized) >= 8 and normalized in context and normalized not in comments.normalize(target_text):
            problems.append("前後の行と重複する")
            break
    if not any(_SPEAKER_RE.fullmatch(row.strip()) or row.strip() == "---" or row.startswith("#")
               for row in target_text.splitlines()):
        if any(_SPEAKER_RE.fullmatch(row.strip()) or row.strip() == "---" or row.startswith("#")
               for row in new.splitlines()):
            problems.append("話者や見出しをまたいでいる")
    return problems


def validate(raw: dict, index: int, source: str, target: Target,
             baseline: dict[tuple[str, str], int] | None, keep: list[str] | None = None,
             context: tuple[list[str], list[str]] | None = None) -> Candidate:
    old = raw.get("old")
    new = raw.get("new")
    why = str(raw.get("why", ""))[:200]
    if new is None:
        return Candidate(index, target.text, None, why or "直す必要なし", target.offset)
    new = str(new)
    if old is None or old == "":
        old = target.text
        offset = target.offset
    else:
        old = str(old)
        occurrences = source.count(old)
        if occurrences != 1:
            candidate = Candidate(index, old, new, why, -1)
            candidate.problems.append("置換元が本文に見つからない" if occurrences == 0 else "置換元が本文で一意でない")
            return candidate
        offset = source.find(old)
    # 行末の改行の有無は元に合わせる（モデルが落としがち）。
    if old.endswith("\n") and not new.endswith("\n"):
        new += "\n"
    trimmed = False
    if context is not None and old == target.text:
        new, trimmed = trim_context(new, *context)
    candidate = Candidate(index, old, new, why, offset, trimmed=trimmed)
    if context is not None and old == target.text:
        candidate.problems.extend(overlap_problems(new, old, *context))
        if not new.strip():
            candidate.problems.append("空になった")
            return candidate
    if new == old:
        candidate.problems.append("変更なし")
        return candidate
    if keep and old == target.text:
        candidate.lost = lost_terms(new, keep)
    known = old + "".join(context[0] + context[1]) if context is not None else old
    candidate.added = added_numbers(new, known)
    if baseline is not None:
        after = source[:offset] + new + source[offset + len(old) :]
        for (rule, message), count in lint_errors(after).items():
            added = count - baseline.get((rule, message), 0)
            if added > 0:
                candidate.lint.append(f"{rule}: {message}")
    return candidate


# --------------------------------------------------------------------------
# 適用・取り消し
# --------------------------------------------------------------------------


@dataclass
class Applied:
    request_id: str
    book: str
    index: int
    old: str
    new: str
    offset: int
    before_ctx: str
    after_ctx: str
    at: float
    last_final: str = ""


def apply_replacement(book: str, old: str, new: str, offset: int) -> tuple[int, str, str]:
    """old を new へ置き換える。生成時の位置で一致すればそこ、ずれていれば一意な出現を使う。"""
    path = comments.source_path(book)
    source = path.read_text(encoding="utf-8")
    if not (0 <= offset and source[offset : offset + len(old)] == old):
        occurrences = source.count(old)
        if occurrences != 1:
            raise ReviseError("候補を作った後に本文が変わり、置換元を特定できない。候補を作り直してほしい")
        offset = source.find(old)
    updated = source[:offset] + new + source[offset + len(old) :]
    comments._atomic_replace_text(path, updated)
    before_ctx = source[max(0, offset - CONTEXT_CHARS) : offset]
    after_ctx = source[offset + len(old) : offset + len(old) + CONTEXT_CHARS]
    return offset, before_ctx, after_ctx


# --------------------------------------------------------------------------
# ログ
# --------------------------------------------------------------------------

_LOG_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_log(event: dict, log_dir: Path | None = None) -> None:
    log_dir = log_dir or LOG_DIR
    event = {"ts": now_iso(), **event}
    with _LOG_LOCK:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / (datetime.now().strftime("%Y-%m") + ".jsonl")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_log(log_dir: Path | None = None) -> list[dict]:
    log_dir = log_dir or LOG_DIR
    events: list[dict] = []
    if not log_dir.is_dir():
        return events
    for path in sorted(log_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def examples_for(action_id: str, book: str, log_dir: Path | None = None,
                 limit: int = FEWSHOT_LIMIT) -> list[dict]:
    """過去に採用された書き換えを、同じアクション・同じ教材を優先して返す。

    採用後に人が手直ししていれば、その最終形をお手本にする（「その中ではまし」
    だった候補より、人が仕上げた形のほうが好みを正しく表すため）。
    """
    events = read_log(log_dir)
    requests = {event["id"]: event for event in events if event.get("type") == "request"}
    finals: dict[str, str] = {}
    undone: set[str] = set()
    for event in events:
        if event.get("type") == "post_edit":
            finals[event["id"]] = event.get("final", "")
        elif event.get("type") == "undo":
            undone.add(event["id"])
    picked: list[tuple[int, dict]] = []
    for event in reversed(events):
        if event.get("type") != "decision" or event.get("result") != "adopted":
            continue
        request = requests.get(event["id"])
        if not request or event["id"] in undone or request.get("action") != action_id:
            continue
        before = event.get("old", "")
        after = finals.get(event["id"], event.get("new", ""))
        if not before or not after or len(before) + len(after) > FEWSHOT_MAX_CHARS * 2:
            continue
        rank = 0 if request.get("book") == book else 1
        picked.append((rank, {
            "id": event["id"],
            "request": request.get("request", ""),
            "before": before[:FEWSHOT_MAX_CHARS],
            "after": after[:FEWSHOT_MAX_CHARS],
        }))
    picked.sort(key=lambda item: item[0])  # 安定ソートなので新しい順は保たれる
    return [example for _, example in picked[:limit]]


# --------------------------------------------------------------------------
# サービス（dev_server から使う）
# --------------------------------------------------------------------------


@dataclass
class RequestRecord:
    id: str
    book: str
    action: str
    tier: str
    backend: str
    target: Target
    keep: list[str] = field(default_factory=list)
    context: tuple[list[str], list[str]] = field(default_factory=lambda: ([], []))
    candidates: list[Candidate] = field(default_factory=list)
    shown_at: float = 0.0
    decided: bool = False


class Service:
    def __init__(self, config: Config | None = None, log_dir: Path | None = None) -> None:
        self.config = config or load_config()
        self.log_dir = log_dir
        self.pool = backends.Pool(self.config.pool_sizes, self.config.idle_ttl)
        self.lock = threading.Lock()
        self.requests: dict[str, RequestRecord] = {}
        self.applied: dict[str, list[Applied]] = {}
        # 直後が受ける語をプロンプトで渡すか（評価で渡さない条件と比べるため）。
        self.keep_hint = True

    # -- 設定と待機 ----------------------------------------------------------

    def describe(self) -> dict:
        available = {
            name: (name == "fake" or shutil.which(name) is not None) for name in backends.BACKENDS
        }
        tiers = {
            tier: {backend: {"model": spec.model, "effort": spec.effort, "thinking": spec.thinking}
                   for backend, spec in by_backend.items()}
            for tier, by_backend in self.config.tiers.items()
        }
        return {
            "default_backend": self.config.default_backend,
            "backends": available,
            "tiers": tiers,
            "actions": [action.__dict__ for action in self.config.actions],
            "card_version": card_version(),
        }

    def prewarm(self, book: str, backend: str) -> None:
        if backend != "fake" and shutil.which(backend) is None:
            return
        system = system_prompt(book)
        for tier in TIERS:
            try:
                spec = self.config.spec(tier, backend)
            except ReviseError:
                continue
            try:
                self.pool.prewarm(spec, system, tier)
            except backends.BackendError:
                return

    # -- 生成 ----------------------------------------------------------------

    def generate(self, payload: dict) -> Iterator[dict]:
        """依頼を1件処理し、画面へ送るイベントを順に返す。"""
        started = time.monotonic()
        book = str(payload.get("book", ""))
        action = self.config.action(str(payload.get("action", "")))
        instruction = str(payload.get("instruction", "")).strip()[:MAX_INSTRUCTION_CHARS]
        if action.id == "free" and not instruction:
            raise ReviseError("自由指示が空")
        backend_name = str(payload.get("backend") or self.config.default_backend)
        if backend_name not in backends.BACKENDS:
            raise ReviseError(f"未知のバックエンド: {backend_name}")
        anchor = payload.get("anchor") or {}
        target, lines = locate(book, str(payload.get("unit", "sentence")), anchor)
        tier = choose_tier(str(payload.get("tier", "auto")), action, target, instruction, self.config)
        spec = self.config.spec(tier, backend_name)
        window = window_of(target, lines, tier, anchor, self.config.context_utterances)
        examples = examples_for(action.id, book, self.log_dir)
        count = max(1, min(int(payload.get("count") or self.config.candidates), 5))
        system = system_prompt(book)
        keep = following_terms(target, lines)
        context = context_lines(target, lines, window)
        user = user_prompt(target, lines, window, action, instruction, count, examples,
                           keep if self.keep_hint else None)
        source = "".join(lines)
        baseline = lint_errors(source)

        request_id = "r" + datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(2)
        record = RequestRecord(request_id, book, action.id, tier, backend_name, target, keep, context)
        with self.lock:
            self.requests[request_id] = record
            self._prune_requests()
        parent = str(payload.get("parent") or "")
        if parent:
            self._decide_implicit(parent, "escalated" if payload.get("escalate") else "regenerated")

        yield {
            "event": "meta",
            "id": request_id,
            "tier": tier,
            "backend": backend_name,
            "model": spec.model or "(既定)",
            "effort": spec.effort,
            "lines": [target.start + 1, target.end + 1],
            "old": target.text,
        }

        process = self.pool.acquire(spec, system, tier)
        parser = CandidateParser()
        usage: dict = {}
        first_token: float | None = None
        error = ""
        raw_text: list[str] = []
        try:
            for event in backends.run(process, backends.BACKENDS[backend_name], system, user):
                if event.kind == "delta":
                    if first_token is None:
                        first_token = time.monotonic() - started
                    raw_text.append(event.text)
                    yield {"event": "delta", "text": event.text}
                    for raw in parser.feed(event.text):
                        yield self._add_candidate(record, raw, source, baseline)
                elif event.kind == "done":
                    usage = compact_usage(event.usage)
            for raw in parser.flush():
                yield self._add_candidate(record, raw, source, baseline)
        except backends.BackendError as exc:
            error = str(exc)
            yield {"event": "error", "message": error}
        finally:
            elapsed = time.monotonic() - started
            record.shown_at = time.monotonic()
            append_log({
                "type": "request",
                "id": request_id,
                "book": book,
                "action": action.id,
                "request": (action.instruction + (" / " + instruction if instruction else "")).strip(" /"),
                "instruction": instruction,
                "tier": tier,
                "tier_requested": str(payload.get("tier", "auto")),
                "backend": backend_name,
                "model": spec.model,
                "effort": spec.effort,
                "thinking": spec.thinking,
                "card_version": card_version(),
                "system_hash": _hash(system)[:16],
                "parent": parent,
                "heading_path": target.heading_path,
                "quote": target.quote,
                "unit": target.unit,
                "target": target.text,
                "window": list(window),
                "fewshot": [example["id"] for example in examples],
                "keep": keep,
                "candidates": [
                    {"new": c.new, "old": c.old if c.old != target.text else None, "why": c.why,
                     "order": c.index, "ok": c.ok, "problems": c.problems, "lint": c.lint,
                     "lost": c.lost, "added": c.added, "trimmed": c.trimmed}
                    for c in record.candidates
                ],
                "raw": "".join(raw_text) if not record.candidates else "",
                "usage": usage,
                "ttft_ms": round(first_token * 1000) if first_token is not None else None,
                "ms": round(elapsed * 1000),
                "error": error,
            }, self.log_dir)
        if not error:
            yield {"event": "done", "id": request_id, "usage": usage,
                   "ms": round((time.monotonic() - started) * 1000),
                   "ttft_ms": round(first_token * 1000) if first_token is not None else None}

    def _add_candidate(self, record: RequestRecord, raw: dict, source: str,
                       baseline: dict[tuple[str, str], int]) -> dict:
        candidate = validate(raw, len(record.candidates), source, record.target, baseline, record.keep,
                             record.context)
        record.candidates.append(candidate)
        return {"event": "candidate", **candidate.to_dict()}

    def _prune_requests(self) -> None:
        if len(self.requests) <= 200:
            return
        for request_id in sorted(self.requests)[:-200]:
            del self.requests[request_id]

    # -- 採否 ----------------------------------------------------------------

    def _record(self, request_id: str) -> RequestRecord:
        with self.lock:
            record = self.requests.get(request_id)
        if record is None:
            raise ReviseError("候補の記録が無い（サーバを再起動した？）。作り直してほしい")
        return record

    def _decide_implicit(self, request_id: str, result: str) -> None:
        with self.lock:
            record = self.requests.get(request_id)
            if record is None or record.decided:
                return
            record.decided = True
            shown = record.shown_at
        append_log({"type": "decision", "id": request_id, "result": result,
                    "decision_ms": round((time.monotonic() - shown) * 1000) if shown else None},
                   self.log_dir)

    def adopt(self, request_id: str, index: int) -> dict:
        record = self._record(request_id)
        if not 0 <= index < len(record.candidates):
            raise ReviseError("候補の番号が不正")
        candidate = record.candidates[index]
        if candidate.new is None:
            raise ReviseError("この候補は書き換えを含まない")
        if candidate.problems:
            raise ReviseError("この候補は適用できない: " + "、".join(candidate.problems))
        with self.lock:
            offset, before_ctx, after_ctx = apply_replacement(
                record.book, candidate.old, candidate.new, candidate.offset
            )
            self.applied.setdefault(record.book, []).append(Applied(
                request_id, record.book, index, candidate.old, candidate.new, offset,
                before_ctx, after_ctx, time.time(),
            ))
            del self.applied[record.book][:-50]
            record.decided = True
        append_log({
            "type": "decision", "id": request_id, "result": "adopted", "candidate": index,
            "old": candidate.old, "new": candidate.new, "lint": candidate.lint,
            "decision_ms": round((time.monotonic() - record.shown_at) * 1000) if record.shown_at else None,
        }, self.log_dir)
        return {"ok": True, "line": _line_of(record.book, offset)}

    def reject(self, request_id: str, reason: str = "") -> dict:
        record = self._record(request_id)
        with self.lock:
            record.decided = True
        append_log({
            "type": "decision", "id": request_id, "result": "rejected", "reason": reason[:200],
            "decision_ms": round((time.monotonic() - record.shown_at) * 1000) if record.shown_at else None,
        }, self.log_dir)
        return {"ok": True}

    def undo(self, book: str) -> dict:
        with self.lock:
            stack = self.applied.get(book) or []
            if not stack:
                raise ReviseError("取り消せる採用が無い")
            applied = stack[-1]
            path = comments.source_path(book)
            source = path.read_text(encoding="utf-8")
            offset = applied.offset
            if source[offset : offset + len(applied.new)] != applied.new:
                if source.count(applied.new) != 1:
                    raise ReviseError("採用後に本文が変わったので取り消せない")
                offset = source.find(applied.new)
            updated = source[:offset] + applied.old + source[offset + len(applied.new) :]
            comments._atomic_replace_text(path, updated)
            stack.pop()
        append_log({"type": "undo", "id": applied.request_id}, self.log_dir)
        return {"ok": True, "id": applied.request_id}

    # -- 採用後の手直し --------------------------------------------------------

    def observe(self, book: str) -> list[dict]:
        """本文が変わったら、直近の採用箇所を人が手直ししたかを調べて記録する。

        採用した文が本文にそのまま残っていれば手直しは無い。消えていれば、採用時に
        控えた前後の文脈で挟まれた部分を「人が仕上げた形」として記録する。
        """
        recorded: list[dict] = []
        with self.lock:
            stack = list(self.applied.get(book) or [])
        if not stack:
            return recorded
        try:
            source = comments.source_path(book).read_text(encoding="utf-8")
        except (comments.CommentError, OSError):
            return recorded
        now = time.time()
        for applied in stack:
            if now - applied.at > POST_EDIT_WINDOW:
                continue
            if applied.new in source and not applied.last_final:
                continue
            final = _between(source, applied.before_ctx, applied.after_ctx)
            if final is None or final == applied.last_final:
                continue
            if final == applied.new and not applied.last_final:
                continue
            applied.last_final = final
            event = {"type": "post_edit", "id": applied.request_id, "final": final,
                     "similarity": round(difflib.SequenceMatcher(None, applied.new, final).ratio(), 3)}
            append_log(event, self.log_dir)
            recorded.append(event)
        return recorded

    def reap(self) -> None:
        self.pool.reap()

    def close(self) -> None:
        self.pool.close()


def _between(source: str, before: str, after: str) -> str | None:
    start = source.find(before) if before else 0
    if start < 0 or (before and source.count(before) != 1):
        return None
    start += len(before)
    end = source.find(after, start) if after else len(source)
    if end < 0:
        return None
    return source[start:end]


def _line_of(book: str, offset: int) -> int:
    source = comments.source_path(book).read_text(encoding="utf-8")
    return source.count("\n", 0, offset) + 1


USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
              "output_tokens", "cost_usd", "api_ms")


def compact_usage(usage: dict) -> dict:
    """ログに残す使用量。バックエンドごとの細目は落とし、比較に要る数だけ残す。"""
    compact = {key: usage[key] for key in USAGE_KEYS if usage.get(key) is not None}
    thinking = (usage.get("output_tokens_details") or {}).get("thinking_tokens")
    if thinking:
        compact["thinking_tokens"] = thinking
    for key, value in usage.items():  # codex など、上の名前を持たない形はそのまま残す
        if key not in compact and isinstance(value, (int, float)) and key not in {"iterations"}:
            compact.setdefault(key, value)
    return compact


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# 集計
# --------------------------------------------------------------------------


def stats(events: list[dict]) -> list[dict]:
    """アクション×ティア×モデルごとの採用率など。定期の分析の入口。"""
    requests = {event["id"]: event for event in events if event.get("type") == "request"}
    decisions: dict[str, dict] = {}
    undone: set[str] = set()
    post_edited: set[str] = set()
    for event in events:
        if event.get("type") == "decision":
            decisions[event["id"]] = event
        elif event.get("type") == "undo":
            undone.add(event["id"])
        elif event.get("type") == "post_edit":
            post_edited.add(event["id"])
    rows: dict[tuple, dict] = {}
    for request_id, request in requests.items():
        key = (request.get("action"), request.get("tier"), request.get("backend"), request.get("model"))
        row = rows.setdefault(key, {
            "action": key[0], "tier": key[1], "backend": key[2], "model": key[3],
            "requests": 0, "adopted": 0, "first": 0, "rejected": 0, "regenerated": 0,
            "escalated": 0, "undone": 0, "post_edited": 0, "errors": 0, "ms": [], "ttft_ms": [],
        })
        row["requests"] += 1
        if request.get("error"):
            row["errors"] += 1
        if request.get("ms") is not None:
            row["ms"].append(request["ms"])
        if request.get("ttft_ms") is not None:
            row["ttft_ms"].append(request["ttft_ms"])
        decision = decisions.get(request_id)
        if decision:
            result = decision.get("result")
            if result == "adopted":
                row["adopted"] += 1
                if decision.get("candidate") == 0:
                    row["first"] += 1
            elif result in {"rejected", "regenerated", "escalated"}:
                row[result] += 1
        if request_id in undone:
            row["undone"] += 1
        if request_id in post_edited:
            row["post_edited"] += 1
    output = []
    for row in rows.values():
        ms, ttft = row.pop("ms"), row.pop("ttft_ms")
        row["median_ms"] = sorted(ms)[len(ms) // 2] if ms else None
        row["median_ttft_ms"] = sorted(ttft)[len(ttft) // 2] if ttft else None
        output.append(row)
    output.sort(key=lambda row: (-row["requests"], str(row["action"])))
    return output


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def cmd_try(args: argparse.Namespace) -> int:
    """端末から1件試す。本文は書き換えない（候補を表示するだけ）。"""
    service = Service()
    lines = comments.source_path(args.book).read_text(encoding="utf-8").splitlines()
    heading = ""
    quote_norm = comments.normalize(args.quote)
    for index, line in enumerate(lines):
        if quote_norm and quote_norm in comments.normalize(line):
            path = comments.heading_path_at([item + "\n" for item in lines], index)
            heading = path[-1] if path else ""
            break
    payload = {
        "book": args.book, "unit": "sentence", "action": args.action, "instruction": args.instruction,
        "tier": args.tier, "backend": args.backend or service.config.default_backend,
        "anchor": {"heading": heading, "quote": quote_norm, "quote_tail": quote_norm[-40:], "occurrence": 1},
    }
    try:
        for event in service.generate(payload):
            kind = event["event"]
            if kind == "meta":
                print(f"# {event['id']} tier={event['tier']} {event['backend']}:{event['model']} "
                      f"lines={event['lines']}", flush=True)
                print(event["old"], end="", flush=True)
            elif kind == "candidate":
                mark = "OK" if event["ok"] else "NG " + "、".join(event["problems"])
                lint = (" lint: " + "; ".join(event["lint"])) if event["lint"] else ""
                print(f"\n--- 案{event['index'] + 1} [{mark}]{lint} {event['why']}\n{event['new']}", end="", flush=True)
            elif kind == "error":
                print("\nERROR " + event["message"], file=sys.stderr)
                return 1
            elif kind == "done":
                print(f"\n# done {event['ms']}ms ttft={event['ttft_ms']}ms usage={json.dumps(event['usage'])}")
    except (ReviseError, comments.CommentError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    finally:
        service.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    rows = stats(read_log())
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("ログが無い: " + str(LOG_DIR.relative_to(ROOT)))
        return 0
    header = ["action", "tier", "backend", "model", "requests", "adopted", "first", "rejected",
              "regenerated", "escalated", "undone", "post_edited", "errors", "median_ms", "median_ttft_ms"]
    print("\t".join(header))
    for row in rows:
        print("\t".join(str(row.get(name, "")) for name in header))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    trial = sub.add_parser("try", help="端末から候補を1回作る（本文は変えない）")
    trial.add_argument("--book", required=True)
    trial.add_argument("--quote", required=True, help="対象にする本文の文字列（表示上の文字列でよい）")
    trial.add_argument("--action", default="shorten")
    trial.add_argument("--instruction", default="")
    trial.add_argument("--tier", default="auto", choices=["auto", *TIERS])
    trial.add_argument("--backend", default="")
    trial.set_defaults(func=cmd_try)
    summary = sub.add_parser("stats", help="採用率などを集計する")
    summary.add_argument("--json", action="store_true")
    summary.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
