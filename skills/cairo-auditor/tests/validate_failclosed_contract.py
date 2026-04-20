#!/usr/bin/env python3
"""Asserts the documented fail-closed contract for deep mode.

The skill cannot actually spawn agents in CI, so this test pins the *contract*
that the orchestrator must honor: when specialist agents are unavailable and
`--allow-degraded` is not present, deep mode emits CAUD-006 and stops before
findings. Same fail-closed semantics for CAUD-007 (preflight) and CAUD-009
(strict-models). When `--allow-degraded` is present, the report must carry the
documented `degraded-deep` warning lines.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DOC = ROOT / "SKILL.md"
DEEP_WORKFLOW = ROOT / "workflows" / "deep.md"
DEFAULT_WORKFLOW = ROOT / "workflows" / "default.md"
REPORT_FORMAT = ROOT / "references" / "report-formatting.md"


def must_contain(path: Path, needles: tuple[str, ...]) -> tuple[bool, str]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"unable to read {path}: {exc}"
    missing = [n for n in needles if n not in content]
    if missing:
        return False, f"{path.relative_to(ROOT)} missing: {missing}"
    return True, f"{path.relative_to(ROOT)} contains required fail-closed markers"


def main() -> int:
    checks: list[tuple[bool, str]] = []

    # SKILL.md owns the error-code contract and the single-source-of-truth
    # fail-closed semantics block that both workflows reference.
    checks.append(
        must_contain(
            SKILL_DOC,
            (
                "CAUD-006",
                "CAUD-007",
                "CAUD-009",
                "--allow-degraded",
                "--strict-models",
                "--proven-only",
                "Fail-closed semantics for deep mode",
                "do not publish findings",
            ),
        )
    )

    # workflows/deep.md owns the Integrity Gate and the explicit warning lines
    # required when --allow-degraded is honored.
    checks.append(
        must_contain(
            DEEP_WORKFLOW,
            (
                "Integrity gate",
                "CAUD-006",
                "CAUD-007",
                "CAUD-009",
                "--allow-degraded",
                "WARNING: degraded execution (specialist agents unavailable)",
                "WARNING: degraded execution may omit exploitable paths",
                "Execution Integrity: DEGRADED",
                "degraded-deep",
            ),
        )
    )

    # workflows/default.md must NOT silently re-implement deep-mode fail-closed
    # logic — that is the deep workflow's responsibility. Verify none of the
    # deep-only markers leaked into default.
    default_content = DEFAULT_WORKFLOW.read_text(encoding="utf-8")
    forbidden_in_default = (
        "CAUD-006",
        "CAUD-007",
        "CAUD-009",
        "--allow-degraded",
        "degraded-deep",
        "WARNING: degraded execution (specialist agents unavailable)",
        "WARNING: degraded execution may omit exploitable paths",
    )
    leaked = [m for m in forbidden_in_default if m in default_content]
    if leaked:
        checks.append(
            (
                False,
                f"workflows/default.md leaked deep-only fail-closed markers: {leaked}",
            )
        )
    else:
        checks.append(
            (True, "workflows/default.md does not duplicate deep-only fail-closed markers")
        )

    # references/report-formatting.md must enumerate the Execution Integrity
    # tri-state value the report carries when degraded.
    checks.append(
        must_contain(
            REPORT_FORMAT,
            (
                "Execution Integrity: <FULL|DEGRADED|FAILED>",
                "## Execution Trace",
            ),
        )
    )

    failures: list[str] = []
    for ok, msg in checks:
        print(msg)
        if not ok:
            failures.append(msg)

    if failures:
        print("\nfail-closed contract validation failed", file=sys.stderr)
        return 1

    print("\nfail-closed contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
