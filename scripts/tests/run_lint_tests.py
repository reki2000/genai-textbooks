#!/usr/bin/env python3
"""scripts/yaruo_lint.py の golden fixture 回帰。

`fixtures/<rule-id>/<case>.md` を、そのルールだけ有効にして `--fix` した結果が
`<case>.expected` とバイト一致することを確認する。さらに2回目の `--fix` で
変化しないこと（冪等性）と、直後の `--check` が fixable な error を残さないこと
を確認する。

    python3 scripts/tests/run_lint_tests.py

fixture は rule ごとの小さな input / expected 対にする。大きな1ファイルへ詰めると
失敗原因を特定できなくなる。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT = ROOT / "scripts" / "yaruo_lint.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT), *args], capture_output=True, text=True
    )


def main() -> int:
    failures: list[str] = []
    cases = 0
    with tempfile.TemporaryDirectory() as tmp:
        work_root = Path(tmp)
        for rule_dir in sorted(FIXTURES.iterdir()):
            if not rule_dir.is_dir():
                continue
            rule = rule_dir.name
            for source in sorted(rule_dir.glob("*.md")):
                expected_path = source.with_suffix(".expected")
                if not expected_path.exists():
                    failures.append(f"{rule}/{source.name}: .expected が無い")
                    continue
                cases += 1
                work = work_root / f"{rule}__{source.name}"
                shutil.copy(source, work)

                run(str(work), "--fix", "--rules", rule)
                produced = work.read_bytes()
                expected = expected_path.read_bytes()
                if produced != expected:
                    failures.append(
                        f"{rule}/{source.name}: 出力が expected と不一致\n"
                        f"  produced: {produced!r}\n  expected: {expected!r}"
                    )
                    continue

                run(str(work), "--fix", "--rules", rule)
                if work.read_bytes() != produced:
                    failures.append(f"{rule}/{source.name}: --fix が冪等でない")
                    continue

                check = run(str(work), "--check", "--rules", rule)
                if check.returncode != 0:
                    failures.append(
                        f"{rule}/{source.name}: 修正後の --check が error を残す\n"
                        f"  {check.stdout.strip()}"
                    )

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{cases - len(failures)}/{cases} 件が一致")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
