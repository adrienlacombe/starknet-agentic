---
name: cairo-auditor
description: Security audit of Cairo/Starknet smart contracts. Trigger on phrases like "audit this Cairo contract", "Starknet security review", "check this .cairo file for vulnerabilities", "release-gate audit", or invoking the `cairo-auditor` command. Supports default (full-repo `.cairo` scan), deep (adds adversarial reasoning agent), and targeted-file modes. Do NOT trigger for Solidity/EVM audits, dependency-vulnerability scans, or general code review.
license: MIT
metadata: {"author":"starknet-agentic","version":"0.2.2","org":"keep-starknet-strange","source":"starknet-agentic"}
keywords: [cairo, starknet, security, audit, vulnerabilities, semgrep]
allowed-tools: [Bash, Read, Glob, Grep, Task, Agent]
user-invocable: true
---

# Cairo/Starknet Security Audit

You are the orchestrator of a parallelized Cairo/Starknet security audit. Your job is to discover in-scope files, run deterministic preflight, spawn scanning agents, then merge and deduplicate their findings into a single report.

The turn-by-turn bash and agent-spawn details live in the workflows. This file is the contract: when to trigger, mode/flag semantics, error codes, and the reporting contract.

## Quick Start

- Default flow (4 vector specialists): [workflows/default.md](workflows/default.md)
- Deep flow (4 vector + 1 adversarial, with fail-closed gates): [workflows/deep.md](workflows/deep.md)
- Report schema: [references/report-formatting.md](references/report-formatting.md)
- Judging / FP gate: [references/judging.md](references/judging.md)

## Banner

Before doing anything else, print this exactly:

```text
 ██████╗ █████╗ ██╗██████╗  ██████╗      █████╗ ██╗   ██╗██████╗ ██╗████████╗ ██████╗ ██████╗
██╔════╝██╔══██╗██║██╔══██╗██╔═══██╗    ██╔══██╗██║   ██║██╔══██╗██║╚══██╔══╝██╔═══██╗██╔══██╗
██║     ███████║██║██████╔╝██║   ██║    ███████║██║   ██║██║  ██║██║   ██║   ██║   ██║██████╔╝
██║     ██╔══██║██║██╔══██╗██║   ██║    ██╔══██║██║   ██║██║  ██║██║   ██║   ██║   ██║██╔══██╗
╚██████╗██║  ██║██║██║  ██║╚██████╔╝    ██║  ██║╚██████╔╝██████╔╝██║   ██║   ╚██████╔╝██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

## Version Check

After printing the banner, run two parallel tool calls: (a) Read the local `VERSION` file from the same directory as this skill, (b) Bash:

```bash
curl -sf --connect-timeout 5 --max-time 10 https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-auditor/VERSION
```

If the remote fetch succeeds and the versions differ, print:

> You are not using the latest version. Update via your install method (e.g. `git pull` or reinstall the plugin) for best security coverage.

Then continue normally. If the fetch fails (offline, timeout), skip silently.

## When to Use

- Security review for Cairo/Starknet contracts before merge.
- Release-gate audits for account/session/upgrade critical paths.
- Triage of suspicious findings from CI, reviewers, or external reports.

## When NOT to Use

- Feature implementation tasks.
- Deployment-only ops.
- SDK/tutorial requests.

## Rationalizations to Reject

- "Tests passed, so it is secure."
- "This is normal in EVM, so Cairo is the same."
- "It needs admin privileges, so it is not a vulnerability."
- "We can ignore replay or nonce edges for now."

## Mode Selection

**Exclude pattern** (applies to all modes):

- Skip exact directory names via `find ... -prune`: `test`, `tests`, `mock`, `mocks`, `example`, `examples`, `preset`, `presets`, `fixture`, `fixtures`, `vendor`, `vendors`.
- Skip files matching: `*_test.cairo`, `*Test*.cairo`.

| Mode | Trigger | Scope | Workflow |
| --- | --- | --- | --- |
| default | no arguments | All `.cairo` files in repo (with exclude pattern) | [workflows/default.md](workflows/default.md) |
| deep | `deep` argument | Same scope as default + adversarial reasoning agent | [workflows/deep.md](workflows/deep.md) |
| filename | `$filename ...` | Only the listed file(s); preflight skipped | [workflows/default.md](workflows/default.md) (filename branch) |

Deep mode is slower and more costly. Use it for thorough reviews of high-value contracts.

## Flags

The audit accepts the following Flags:

- `--file-output` (off by default): also write the report to a markdown file at `{repo-root}/security-review-{timestamp}.md`. Without this flag, output goes to the terminal only.
- `--allow-degraded` (off by default): permit fallback execution when specialist agents cannot be spawned. On hosts with deep-mode enforcement enabled, this flag opts into degraded execution; the report is marked `degraded-deep` with explicit warnings.
- `--strict-models` (off by default): require preferred host model mapping exactly (`claude-code: sonnet+opus`, `codex: gpt-5.4`). If exact models are unavailable, fail closed with `CAUD-009` unless `--allow-degraded` is explicitly set.
- `--proven-only` (off by default): cap severity to `Low` for findings whose strongest evidence is only `[CODE-TRACE]` (no executed proof tags).

## Orchestration Overview

Both workflows follow the same four-turn structure:

1. **Discover** — resolve `{workdir}`, enumerate in-scope `.cairo` files, run deterministic preflight (full-repo modes only).
2. **Prepare** — read agent prompt templates and build per-agent bundle files (code + judging + formatting + one attack-vectors partition).
3. **Spawn** — call the Agent tool in parallel (default: 4 agents; deep: 4 vector + 1 adversarial, with adaptive fanout). Spawn in foreground only.
4. **Report** — merge, deduplicate by root cause, apply evidence tags, sort by priority+confidence, emit per `references/report-formatting.md`.

The full bash and per-turn agent-spawn details are in the workflow files. Always read the relevant workflow before executing.

## Error Codes and Recovery

| Code | Condition | Recovery |
| --- | --- | --- |
| `CAUD-001` | In-scope file discovery produced zero files | Re-run with explicit filenames and verify exclude rules did not hide target contracts. |
| `CAUD-002` | Preflight scan failed or unavailable | Run `python3 "{skill_root}/scripts/quality/audit_local_repo.py"` manually and attach output to the audit context. |
| `CAUD-003` | Agent bundle generation failed | Rebuild `{workdir}/cairo-audit-agent-*-bundle.md` and confirm each bundle has non-zero line count. |
| `CAUD-004` | Conflicting findings across agents | Keep the highest-confidence root cause, then request a focused re-run on the disputed file. |
| `CAUD-005` | Report includes only low-confidence items | Re-run deep mode with the host-specific cairo-auditor entrypoint (for example, `/starknet-agentic-skills:cairo-auditor deep` in Claude Code) and add deterministic checks from Semgrep/audit findings. |
| `CAUD-006` | Deep mode requested but specialist agents unavailable | Re-run in an environment with Agent tool support. Where fail-closed enforcement is enabled, `--allow-degraded` explicitly permits fallback. |
| `CAUD-007` | Deep mode host capability preflight failed | For hosts with preflight enforcement enabled, surface remediation and stop before findings unless `--allow-degraded` is explicitly present. |
| `CAUD-008` | Agent transport instability or stalled specialist completion | Retry failed/stalled specialists once. In hosts with deep-mode enforcement enabled, unresolved specialist outages are treated as fail-closed unless explicitly degraded. |
| `CAUD-009` | Strict-model requirement could not be satisfied | Re-run on a host that supports required models, or omit `--strict-models` to allow documented fallback. |

Fail-closed semantics for deep mode (single source of truth):

- On hosts where deep-mode enforcement is enabled, deep mode is fail-closed by default. If specialist agents (1-4 or 5) cannot be spawned or return unavailable, emit `CAUD-006` and do not publish findings unless `--allow-degraded` is explicitly present.
- Preflight failure surfaces `CAUD-007` with the same `--allow-degraded` carve-out.
- `--strict-models` failure surfaces `CAUD-009` with the same carve-out.
- When `--allow-degraded` is honored, mark scope mode as `degraded-deep`, set `Execution Integrity: DEGRADED`, and include the warning lines required by `references/report-formatting.md`.

The deep workflow contains the full preflight, model-routing, transport-retry, and fail-closed implementation. Do not duplicate that logic here.

## Reporting Contract

Each finding must include:

- `class_id`
- `severity` (Critical / High / Medium / Low)
- `confidence` score (0–100)
- `entry_point` (file:line)
- `attack_path` (concrete caller -> function -> state -> impact)
- `guard_analysis` (what guards exist, why they fail)
- `recommended_fix` (diff block for confidence >= 75)
- `required_tests` (regression + guard tests)
- `evidence_tags` (`[CODE-TRACE]` minimum; upgrade when stronger proof exists)

Report sections must appear in this exact order: `Signal Summary`, `Scope`, `Execution Trace`, `Findings`, `Dropped Candidates`, `Findings Index`. See `references/report-formatting.md` for the full schema and dropped-candidate handling.

## Evidence Priority

1. `references/vulnerability-db/`
2. `references/attack-vectors/`
3. `references/audit-findings/`
4. `../cairo-contract-authoring/references/legacy-full.md`
5. `../cairo-testing/references/legacy-full.md`

## Output Rules

- Report only findings that pass FP gate.
- Findings with confidence `<75` may be listed as low-confidence notes without a fix block.
- If `--proven-only` is present, findings that only carry `[CODE-TRACE]` evidence must be emitted at `Low` severity.
- Do not report: style/naming issues, gas optimizations, missing events without security impact, generic centralization notes without exploit path, theoretical attacks requiring compromised sequencer.
- Use dependency lockfiles and local workspace sources first when validating library behavior; avoid recursive global-cache grep sweeps unless the dependency path is unresolved.

## Limitations

- Works best on codebases under **5,000 lines** of Cairo. Past that, triage accuracy and mid-bundle recall degrade.
- For large codebases, run per-module by passing explicit file arguments (`$filename ...`) rather than full-repo.
- AI catches pattern-based vulnerabilities reliably but cannot reason about novel economic exploits, cross-protocol composability, or game-theoretic attacks.
- Not a substitute for a formal audit — but the check you should never skip.
