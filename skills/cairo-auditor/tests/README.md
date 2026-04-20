# Cairo Auditor Test Suite

This directory holds deterministic fixtures and validators for the cairo-auditor skill: the preflight scanner (`scripts/quality/audit_local_repo.py`), the bundle-generation step from `workflows/default.md`, and the documented fail-closed contract for deep mode.

## Run

```bash
python3 skills/cairo-auditor/tests/validate_preflight.py
python3 skills/cairo-auditor/tests/validate_deep_smoke.py
python3 skills/cairo-auditor/tests/validate_bundle_generation.py
python3 skills/cairo-auditor/tests/validate_failclosed_contract.py
```

The check runs deterministic fixture repos:

- `insecure_upgrade_controller` (expects known upgrade-related findings)
- `secure_upgrade_controller` (expects zero findings)
- `insecure_embed_upgrade_controller` (same upgrade findings under `#[abi(embed_v0)]`)
- `insecure_per_item_upgrade_controller` (same upgrade findings under `#[abi(per_item)]`)
- `caller_read_without_auth` (ensures caller-read bookkeeping does not bypass auth checks)
- `guarded_upgrade_without_timelock` (ensures owner-guarded single-step upgrades do not trigger timelock finding)

`validate_deep_smoke.py` adds CI gating for deep-mode contract integrity by asserting:

- vulnerable fixture scan still produces at least one deterministic finding,
- report contract still exposes execution integrity + trace sections,
- canonical ordering includes `Dropped Candidates`.

`validate_bundle_generation.py` exercises the bash bundle-generation pipeline from `workflows/default.md` against the `insecure_upgrade_controller` fixture and asserts that all four per-agent bundle files exist, are non-trivially sized, and contain the expected sections (cairo source, judging rubric, report formatting, the per-agent attack-vectors partition). This catches regressions in the documented orchestration before specialist agents are spawned.

`validate_failclosed_contract.py` pins the documented fail-closed contract for deep mode without spawning real agents: SKILL.md owns the `CAUD-006`/`CAUD-007`/`CAUD-009` error codes and the `--allow-degraded` carve-out; `workflows/deep.md` owns the Integrity Gate and the explicit `WARNING: degraded execution …` lines required when degraded execution is honored; `workflows/default.md` does not duplicate that logic; `references/report-formatting.md` enumerates the `Execution Integrity: <FULL|DEGRADED|FAILED>` tri-state.
