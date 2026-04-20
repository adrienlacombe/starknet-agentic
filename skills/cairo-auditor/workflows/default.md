# Default Workflow

Standard 4-agent parallel scan. Orchestrated by [SKILL.md](../SKILL.md).

This workflow is also the canonical orchestration base. Deep mode ([deep.md](deep.md)) extends it with preflight, model routing, threat intel, and an adversarial agent.

## Pipeline

1. **Discover** — resolve `{workdir}`, `find` in-scope `.cairo` files, run deterministic preflight (skipped in `$filename ...` mode).
2. **Prepare** — Read `vector-scan.md`, build 4 bundle files (code + judging + formatting + one attack-vector partition each).
3. **Spawn** — 4 parallel vector specialists with host-aware vector model (`claude-code: sonnet`, `codex: gpt-5.4` with fallback `gpt-5.2`), each triages vectors, deep-checks survivors, applies FP gate.
4. **Report** — Merge, deduplicate by root cause, apply optional `--proven-only` severity cap for `[CODE-TRACE]`-only findings, sort by confidence, emit with scope table and disclaimer.

## Agent Configuration

| Agent | Model | Input | Role |
|-------|-------|-------|------|
| 1 | host-aware vector model | Bundle 1 (Access Control + Upgradeability) | Vector scan |
| 2 | host-aware vector model | Bundle 2 (External Calls + Reentrancy) | Vector scan |
| 3 | host-aware vector model | Bundle 3 (Math + Pricing + Economics) | Vector scan |
| 4 | host-aware vector model | Bundle 4 (Storage + Components + Trust) | Vector scan |

## Confidence Threshold

- Findings >= 75: full report with fix diff and required tests.
- If confidence is < 75: keep as low-confidence notes, no fix block.
- If `--proven-only` is set and a finding is `[CODE-TRACE]` only: cap severity to Low.
- If the FP gate fails: drop the item entirely.

---

## Turn 1 — Discover

In a single message, make parallel tool calls.

### (a) Resolve `{workdir}`

- If `CAIRO_AUDITOR_WORKDIR` is set, use it as `{workdir}`.
- Otherwise create one with `mktemp -d "${TMPDIR:-/tmp}/cairo-auditor.XXXXXX"` and `chmod 700`.
- Print `WORKDIR=<absolute-path>` in Turn 1 output and reuse that exact path as `{workdir}` for all later turns.

### (b) Enumerate in-scope files

For default and deep modes:

```bash
WORKDIR="${CAIRO_AUDITOR_WORKDIR:-$(mktemp -d "${TMPDIR:-/tmp}/cairo-auditor.XXXXXX")}"
chmod 700 "$WORKDIR"
echo "WORKDIR=$WORKDIR"
find <repo-root> \
  \( -type d \( -name test -o -name tests -o -name mock -o -name mocks -o -name example -o -name examples -o -name fixture -o -name fixtures -o -name vendor -o -name vendors -o -name preset -o -name presets \) -prune \) \
  -o \( -type f -name "*.cairo" ! -name "*_test.cairo" ! -name "*Test*.cairo" -print \) \
  | sort > "$WORKDIR/cairo-audit-files.txt"
cat "$WORKDIR/cairo-audit-files.txt"
```

For **`$filename ...`** mode, do not run `find`. Instead:

```bash
WORKDIR="${CAIRO_AUDITOR_WORKDIR:-$(mktemp -d "${TMPDIR:-/tmp}/cairo-auditor.XXXXXX")}"
chmod 700 "$WORKDIR"
echo "WORKDIR=$WORKDIR"
REPO_ROOT=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "<repo-root>")
> "$WORKDIR/cairo-audit-files.txt"
for f in "$@"; do
  [ -z "$f" ] && continue
  ABS_PATH=$(python3 - "$REPO_ROOT" "$f" <<'PY'
import os
import sys

repo_root, arg = sys.argv[1], sys.argv[2]
candidate = arg if os.path.isabs(arg) else os.path.join(repo_root, arg)
print(os.path.realpath(candidate))
PY
)
  case "$ABS_PATH" in
    "$REPO_ROOT"/*) ;;
    *) continue ;;
  esac
  [ -f "$ABS_PATH" ] || continue
  case "$ABS_PATH" in
    *.cairo) echo "$ABS_PATH" >> "$WORKDIR/cairo-audit-files.txt" ;;
  esac
done
sort -u -o "$WORKDIR/cairo-audit-files.txt" "$WORKDIR/cairo-audit-files.txt"
cat "$WORKDIR/cairo-audit-files.txt"
```

If the file list is empty, emit `CAUD-001` and stop.

### (c) Resolve skill paths

Glob for `**/references/attack-vectors/attack-vectors-1.md` and resolve:

- `{refs_root}` = two levels up from the match (`.../references`)
- `{skill_root}` = three levels up from the match (skill directory that contains `SKILL.md`, `agents/`, `references/`, `VERSION`)

### (d) Deterministic preflight

If `{skill_root}/scripts/quality/audit_local_repo.py` exists, run preflight for full-repo modes only (default/deep). In `$filename ...` mode, skip preflight so the context stays scoped to the targeted files:

```bash
python3 "{skill_root}/scripts/quality/audit_local_repo.py" --repo-root <repo-root> --scan-id preflight --output-dir "{workdir}"
```

Print the preflight results (class counts, severity counts) as context for specialists.

## Turn 2 — Prepare

In a single message, make three parallel tool calls:

### (a) Read `{skill_root}/agents/vector-scan.md`

You will paste this full text into every agent prompt.

### (b) Read `{refs_root}/report-formatting.md`

You will use this for the final report.

### (c) Build per-agent bundle files

In a **single command**, create four per-agent bundle files (`{workdir}/cairo-audit-agent-{1,2,3,4}-bundle.md`). Each bundle concatenates:

- **all** in-scope `.cairo` files (with `### path` headers and fenced code blocks),
- `{refs_root}/judging.md`,
- `{refs_root}/report-formatting.md`,
- `{refs_root}/attack-vectors/attack-vectors-N.md` (one per agent — only the attack-vectors file differs).

Print line counts per bundle. Before running this command, substitute placeholders (`{refs_root}`, `{repo-root}`, `{workdir}`) with the concrete paths resolved in Turn 1.

```bash
REFS="{refs_root}"
SRC="{repo-root}"
WORKDIR="{workdir}"
IN_SCOPE="$WORKDIR/cairo-audit-files.txt"
set -euo pipefail

build_code_block() {
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    REL=$(echo "$f" | sed "s|$SRC/||")
    echo "### $REL"
    echo '```cairo'
    cat "$f"
    echo '```'
    echo ""
  done < "$IN_SCOPE"
}

CODE=$(build_code_block)

for i in 1 2 3 4; do
  {
    echo "$CODE"
    echo "---"
    cat "$REFS/judging.md"
    echo "---"
    cat "$REFS/report-formatting.md"
    echo "---"
    cat "$REFS/attack-vectors/attack-vectors-$i.md"
  } > "$WORKDIR/cairo-audit-agent-$i-bundle.md"
  echo "Bundle $i: $(wc -l < "$WORKDIR/cairo-audit-agent-$i-bundle.md") lines"
done
```

Do NOT inline source-code files into prompts. Bundles replace raw source in prompts. Non-code context blocks (deterministic preflight summary and optional threat-intel summary) may be appended.

If any bundle ends up with zero lines, emit `CAUD-003` and rebuild before spawning.

## Turn 3 — Spawn

Use foreground Agent tool calls only (do NOT use `run_in_background`). Spawn Agents 1–4 in parallel.

For each agent, pass `model: "sonnet"` (Claude Code) or the host-resolved vector model. The prompt must contain the full text of `vector-scan.md` (read in Turn 2). After the instructions, append: `Your bundle file is {workdir}/cairo-audit-agent-N-bundle.md (XXXX lines).` (substitute the real line count). Include deterministic preflight results if available.

After spawning, persist execution evidence that will be reused in the final report:

- confirm `{workdir}/cairo-audit-files.txt` exists and count in-scope files,
- record line counts for `{workdir}/cairo-audit-agent-{1,2,3,4}-bundle.md`,
- record `Agent 5: skipped (default mode)` for the execution trace,
- record each agent's observed runtime model label to `{workdir}/cairo-audit-agent-models.txt` (use actual spawn metadata; if not exposed, use `default` or `unknown`).

Transport resilience: if a specialist stalls or returns malformed output, retry that specialist exactly once. Use a 180-second stall timeout for default-mode bundles (typically `<= 1200` lines).

## Turn 4 — Report

Merge all agent results and emit the report in canonical order:

1. Deduplicate by root cause (keep the higher-confidence version, merge broader attack path details; on confidence tie keep higher priority, then more complete path evidence).
2. Apply evidence tags per `references/judging.md` Evidence Tags section:
   - Validate every finding has `[CODE-TRACE]`; if a source agent omitted it, add `[CODE-TRACE]` during merge normalization.
   - Add `[PREFLIGHT-HIT]` if the deterministic preflight flagged the same class or entry point.
   - Add `[CROSS-AGENT]` if 2+ agents independently reported the same root cause before deduplication.
3. Findings with only `[CODE-TRACE]` (no additional tags) are valid but lower-signal; reviewers use the Evidence column in Findings Index to prioritize review order.
4. Sort findings by priority (`P0` first); within each priority tier sort by confidence (highest first).
5. Re-number findings sequentially starting at `1`.
6. Insert one **Below Confidence Threshold** separator row in the findings index immediately before the first finding with confidence < 75.
7. Print findings directly — do not re-draft or re-describe them.
8. Always include sections in this exact order: `Signal Summary`, `Scope`, `Execution Trace`, `Findings`, `Dropped Candidates`, `Findings Index`.
9. Add scope table and findings index table per `references/report-formatting.md`.
10. Add the disclaimer.

### Dropped-candidate handling

- If a candidate is discarded during FP gate or dedupe, add one row in `Dropped Candidates` with `candidate`, `class`, and `drop_reason`.
- Accepted `drop_reason` values: `false_positive`, `duplicate_root_cause`, `below_confidence_threshold`, `insufficient_evidence`.
- If none were dropped, still include the section with a single `none` row.

If `--file-output` is set, write the report to `{repo-root}/security-review-{timestamp}.md` and print the path.
