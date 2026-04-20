# Deep Workflow

Extends [default.md](default.md) with adversarial reasoning, host-capability preflight, host-aware model routing, threat-intel enrichment, and fail-closed integrity gates. Orchestrated by [SKILL.md](../SKILL.md).

This file owns deep-mode-specific logic. For the shared Turn 1–4 base orchestration (file enumeration, bundle generation, vector-spec spawn, report assembly), follow [default.md](default.md) and add the deltas described here.

## Pipeline

1. **Discover** — same as default, plus host-capability preflight (see below).
2. **Prepare** — same as default, plus resolve adversarial agent instructions.
3. **Threat Intel (optional)** — bounded `curl`-based enrichment persisted to `{workdir}/cairo-audit-threat-intel.md`. Includes `SKIPPED`/`FAILED` reason in execution trace when unavailable.
4. **Spawn** — adaptive deep fanout with host-aware model routing:
   - small scopes (largest file ≤ 1000 lines **and** all bundles ≤ 1400 lines): 4 parallel vector specialists + 1 adversarial specialist in parallel.
   - large scopes: two waves for reliability (Wave A: Agents 1–4, Wave B: Agent 5).
5. **Report** — merge all 5 agent outputs, deduplicate, apply optional `--proven-only` severity cap for `[CODE-TRACE]`-only findings, sort, emit.

## Agent Configuration

| Agent | Model | Input | Role |
|-------|-------|-------|------|
| 1–4 | host-aware (`claude-code: sonnet`, `codex: gpt-5.4`) | Bundle files (+ optional threat-intel hints) | Vector scan (same as default) |
| 5 | host-aware (`claude-code: opus`, `codex: gpt-5.4`) | Direct file reads + adversarial.md (+ optional threat-intel hints) | Free-form adversarial reasoning |

Codex fallback is `gpt-5.2` when `gpt-5.4` probe fails and `--strict-models` is not set.
`--strict-models` disables fallback and fails closed if preferred host models are unavailable.
`--proven-only` caps `[CODE-TRACE]`-only findings at Low severity for conservative release gates.

## Confidence Threshold

Same as default ([default.md](default.md#confidence-threshold)). The adversarial agent's findings still pass through the FP gate and confidence scoring.

---

## Turn 1 — Discover (deep delta)

Run the [default Turn 1](default.md#turn-1--discover) base steps (workdir, file enumeration, deterministic preflight). Then add the host-capability preflight below.

### Host Capability Preflight (Experimental)

The host-capability preflight is an experimental hardening path. Use it when your host exposes specialist-agent capability checks. Run a lightweight check and emit a one-line status:

- Detect host family: `codex`, `claude-code`, or `unknown`.
- Verify Agent tool availability and ability to spawn specialist agents.
- Deep mode requires 5 specialist agents total (Agents 1-4 + Agent 5 adversarial).
- Verify threat-intel fetch capability via Bash:
  - `command -v curl` must succeed, and
  - `curl -sfI --connect-timeout 5 --max-time 10 https://starknet.io` must succeed.
- For `codex` hosts, probe preferred model availability before spawn:
  - run one lightweight specialist probe using `model: gpt-5.4`,
  - persist success/failure and fallback decision.
- Persist preflight evidence to `{workdir}/cairo-audit-host-capabilities.json` when the probe is available.

If preflight fails (in hosts where preflight is enabled):

- Without `--allow-degraded`: emit `CAUD-007`, print remediation, and stop before findings.
- With `--allow-degraded`: continue in `degraded-deep` mode and keep explicit warning lines in scope and execution trace.

Remediation hints to print when preflight fails:

- `codex`: `codex features enable multi_agent`, then verify with `codex features list`, then restart the session.
- `claude-code`: run `/reload-plugins`, update the installed plugin if needed, and retry deep mode.

### Host-Aware Model Routing

Select specialist model labels from detected host before spawning:

- `claude-code`
  - `VECTOR_MODEL=sonnet` (host alias for `claude-sonnet-4-6`)
  - `ADVERSARIAL_MODEL=opus` (host alias for `claude-opus-4-6`)
- `codex`
  - `VECTOR_MODEL=gpt-5.4` (Codex-specific label; may change across host versions)
  - `ADVERSARIAL_MODEL=gpt-5.4`
  - If `gpt-5.4` probe fails and `--strict-models` is not set, fallback to `gpt-5.2` for both.
- `unknown`
  - `VECTOR_MODEL=sonnet` (host alias for `claude-sonnet-4-6`)
  - `ADVERSARIAL_MODEL=opus` (host alias for `claude-opus-4-6`)

Persist the selected plan to `{workdir}/cairo-audit-model-plan.txt` with `host`, `vector_model`, `adversarial_model`, and (when available) `gpt_5_4_probe` and `fallback_reason`. Keep model labels in the execution trace as observed runtime values (not assumptions).

Strict-model gate:

- When `--strict-models` is set, do not silently fallback.
- If preferred host mapping cannot be satisfied, emit `CAUD-009` and stop before findings unless `--allow-degraded` is explicitly present.
- If degraded execution is explicitly permitted, continue with resolved fallback labels and mark `Execution Integrity: DEGRADED`.

## Turn 2 — Prepare (deep delta)

Run [default Turn 2](default.md#turn-2--prepare) bundle generation as-is. The four vector bundles are identical to default mode; the adversarial agent reads files directly rather than via bundle.

## Turn 2.5 — Threat Intel Enrichment (Optional)

When network access is available, run a small enrichment pass and write `{workdir}/cairo-audit-threat-intel.md`:

- Read `{refs_root}/threat-intel-sources.md` first and follow its source policy.
- Use `curl` through Bash as the query mechanism for primary-source security material (official audit reports, incident postmortems, protocol docs, vendor writeups).
- Execute pre-checks before querying:
  - if `curl` is missing, mark this stage `SKIPPED: no curl`,
  - if connectivity check fails, mark this stage `SKIPPED: offline`.
- Keep it bounded: max 6 sources and max 12 extracted signals.
- Normalize each signal into: `date`, `source`, `class hint`, `one-line exploit shape`.
- Prefer Cairo/Starknet first; if sparse, include high-signal EVM analogs that map to listed vectors.
- If a fetch command fails after pre-check, mark `FAILED: curl error <code>` in execution trace and continue.
- If unavailable/offline, continue and mark this stage as `SKIPPED` in execution trace.
- Keep query commands/examples aligned with `threat-intel-sources.md`.

Threat-intel usage rules:

- Intel is a prioritization aid only.
- Never report a finding from intel alone.
- Every reported finding must still pass the local FP gate with a concrete in-scope path.

## Turn 3 — Spawn (deep delta)

Use foreground Agent tool calls only (do NOT use `run_in_background`).

Resolve host-aware model labels first:

- write `{workdir}/cairo-audit-model-plan.txt` with `host`, `vector_model`, and `adversarial_model`.
- include preflight probe fields when available: `gpt_5_4_probe` and `fallback_reason`.
- use that resolved `vector_model` for Agents 1–4 and `adversarial_model` for Agent 5.

### Adaptive fanout

- If the largest in-scope file is `<= 1000` lines and all bundles are `<= 1400` lines, spawn Agent 5 in parallel with Agents 1–4.
- Otherwise, run two waves for transport stability:
  1. **Wave A**: Agents 1–4 in parallel.
  2. **Wave B**: Agent 5 after Wave A completes.

### Agents 1–4 (vector scanning)

Spawn with `model: "{vector_model}"`. Each agent prompt must contain the full text of `vector-scan.md` (read in Turn 2). After the instructions, append: `Your bundle file is {workdir}/cairo-audit-agent-N-bundle.md (XXXX lines).` (substitute the real line count). Include deterministic preflight results if available. If `{workdir}/cairo-audit-threat-intel.md` exists and has normalized signals, append a compact "Threat Intel (hints only)" block (max 12 lines) to each prompt.

### Agent 5 (adversarial reasoning)

Spawn with `model: "{adversarial_model}"`. The prompt must instruct it to:

1. Read `{skill_root}/agents/adversarial.md` for its full instructions.
2. Read `{refs_root}/judging.md` and `{refs_root}/report-formatting.md`.
3. If present, read `{workdir}/cairo-audit-threat-intel.md` as a prioritization hint only.
4. Read `{workdir}/cairo-audit-files.txt` to obtain in-scope paths, then read only those `.cairo` files directly (not via bundle).
5. Reason freely — no attack vector reference. Look for logic errors, unsafe interactions, access control gaps, economic exploits, multi-step cross-function chains.
6. Apply FP gate to each finding immediately.
7. Format findings per `report-formatting.md`.

After spawning, persist execution evidence:

- confirm `{workdir}/cairo-audit-files.txt` exists and count in-scope files,
- record line counts for `{workdir}/cairo-audit-agent-{1,2,3,4}-bundle.md`,
- record whether Agent 5 was spawned in parallel (small scope) or as Wave B (large scope),
- record each agent's observed runtime model label to `{workdir}/cairo-audit-agent-models.txt` (use actual spawn metadata; if not exposed, use `default` or `unknown`).

### Transport resilience

- If the agent transport reports disconnect/fallback warnings or a specialist stalls with no completion, retry that specialist exactly once.
- Adaptive stall timeout by largest bundle size:
  - `<= 1200` lines: 180 seconds (parallel-spawn baseline)
  - `1201-1400` lines: 360 seconds (still parallel-spawn eligible; extra time for larger bundles)
  - `1401-1800` lines: 360 seconds (Wave B regime)
  - `> 1800` lines: 600 seconds (Wave B regime, very large bundles)
- Retry failed/stalled specialists serially (one at a time) to reduce transport saturation.
- If retry still fails, treat the specialist as unavailable and apply the integrity gate below.

### Integrity gate

For hosts where deep-mode enforcement is enabled, fail-closed semantics apply (full table is in [SKILL.md error codes](../SKILL.md#error-codes-and-recovery)):

- If any required specialist agent (1-4 or 5) cannot be spawned or returns unavailable: emit `CAUD-006`, stop before findings, print host remediation hints. `--allow-degraded` opts into degraded execution.
- If a specialist output is malformed (not `No findings.` and not valid finding blocks): rerun once. If still malformed, treat as unavailable.
- `--strict-models` failure: emit `CAUD-009`. Same `--allow-degraded` carve-out.
- Preflight failure: emit `CAUD-007`. Same `--allow-degraded` carve-out.

## Turn 4 — Report (deep delta)

Run [default Turn 4](default.md#turn-4--report) merge/dedupe/sort/emit, then add the deep-only evidence tag:

- Add `[ADVERSARIAL]` if Agent 5 discovered or confirmed the finding.

For degraded execution:

- Mark scope mode as `degraded-deep`.
- Set `Execution Integrity: DEGRADED`.
- Include an explicit warning line at top: `WARNING: degraded execution (specialist agents unavailable)`.
- Repeat a second warning immediately before `Findings Index`: `WARNING: degraded execution may omit exploitable paths`.

## When to Use Deep Mode

- Pre-deployment security review for high-value contracts.
- Contracts with complex account abstraction, session key, or multi-sig logic.
- When default mode findings suggest deeper issues worth investigating.
- Release-gate audits where thoroughness outweighs speed.
