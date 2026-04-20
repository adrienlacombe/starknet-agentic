#!/usr/bin/env python3
"""Asserts the bundle-generation step from workflows/default.md produces 4
non-empty per-agent bundle files when run on a fixture repo.

The orchestrator skill cannot spawn real Agent calls in CI, so this test
exercises the deterministic bash pipeline that builds the four bundle files
that each specialist later consumes.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"
FIXTURE = ROOT / "tests" / "fixtures" / "insecure_upgrade_controller"

REQUIRED_BUNDLE_MARKERS = (
    "### ",                                # at least one source-file header
    "```cairo",                            # fenced cairo code block
    "# Finding Validation (Cairo)",        # first heading of references/judging.md
    "# Report Formatting",                 # first heading of references/report-formatting.md
)


def build_bundles(fixture: Path, workdir: Path, bash_path: str) -> tuple[bool, str]:
    in_scope = workdir / "cairo-audit-files.txt"
    cairo_files = sorted(fixture.rglob("*.cairo"))
    if not cairo_files:
        return False, f"fixture {fixture} contained no .cairo files"
    in_scope.write_text("\n".join(str(p) for p in cairo_files) + "\n", encoding="utf-8")

    refs_q = shlex.quote(str(REFS))
    src_q = shlex.quote(str(fixture))
    workdir_q = shlex.quote(str(workdir))

    script = f"""set -euo pipefail
REFS={refs_q}
SRC={src_q}
WORKDIR={workdir_q}
IN_SCOPE="$WORKDIR/cairo-audit-files.txt"

build_code_block() {{
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    REL=$(echo "$f" | sed "s|$SRC/||")
    echo "### $REL"
    echo '```cairo'
    cat "$f"
    echo '```'
    echo ""
  done < "$IN_SCOPE"
}}

CODE=$(build_code_block)

for i in 1 2 3 4; do
  {{
    echo "$CODE"
    echo "---"
    cat "$REFS/judging.md"
    echo "---"
    cat "$REFS/report-formatting.md"
    echo "---"
    cat "$REFS/attack-vectors/attack-vectors-$i.md"
  }} > "$WORKDIR/cairo-audit-agent-$i-bundle.md"
  echo "Bundle $i: $(wc -l < "$WORKDIR/cairo-audit-agent-$i-bundle.md") lines"
done
"""
    proc = subprocess.run(
        [bash_path, "-c", script],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        return False, f"bundle script exited {proc.returncode}: {proc.stderr.strip()}"
    return True, proc.stdout.strip()


def validate_bundles(workdir: Path) -> tuple[bool, str]:
    for i in (1, 2, 3, 4):
        bundle = workdir / f"cairo-audit-agent-{i}-bundle.md"
        if not bundle.is_file():
            return False, f"missing bundle {bundle}"
        content = bundle.read_text(encoding="utf-8")
        if not content.strip():
            return False, f"bundle {bundle} is empty"
        if bundle.stat().st_size < 1024:
            return False, f"bundle {bundle} suspiciously small ({bundle.stat().st_size} bytes)"
        missing = [m for m in REQUIRED_BUNDLE_MARKERS if m not in content]
        if missing:
            return False, f"bundle {bundle} missing markers: {missing}"
        # The file is concatenated as raw text; verify the per-agent attack-vectors
        # partition is included by checking its first heading appears.
        partition_path = REFS / "attack-vectors" / f"attack-vectors-{i}.md"
        partition_first_line = partition_path.read_text(encoding="utf-8").splitlines()[0]
        if partition_first_line not in content:
            return (
                False,
                f"bundle {bundle} does not contain attack-vectors-{i} partition "
                f"(missing first line: {partition_first_line!r})",
            )
    return True, "all 4 bundles exist, are non-empty, and contain required sections"


def main(bash_path: str) -> int:
    if not FIXTURE.exists():
        print(f"missing fixture: {FIXTURE}", file=sys.stderr)
        return 1
    if not (REFS / "judging.md").is_file():
        print("missing references/judging.md", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="cairo-auditor-bundles-") as tmp:
        workdir = Path(tmp)
        ok, msg = build_bundles(FIXTURE, workdir, bash_path)
        print(msg)
        if not ok:
            print("\nbundle generation failed", file=sys.stderr)
            return 1

        ok, msg = validate_bundles(workdir)
        print(msg)
        if not ok:
            print("\nbundle validation failed", file=sys.stderr)
            return 1

    print("\nbundle generation validation passed")
    return 0


if __name__ == "__main__":
    resolved_bash = shutil.which("bash")
    if resolved_bash is None:
        print("bash not available; skipping", file=sys.stderr)
        raise SystemExit(0)
    raise SystemExit(main(resolved_bash))
