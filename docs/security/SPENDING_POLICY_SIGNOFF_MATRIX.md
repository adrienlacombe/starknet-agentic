# Spending Policy Launch Sign-Off Matrix

This matrix operationalizes remaining launch-gate tasks from
`docs/security/SPENDING_POLICY_AUDIT.md` for issue `#335`.

Status values:

- `open`
- `in-progress`
- `done`
- `waived` (requires residual-risk note)

## Owners

- `contracts-owner`: contract behavior and invariants
- `runtime-owner`: runtime flows and operational checks
- `qa-owner`: test execution and evidence packaging
- `security-owner`: security review, threat modeling, vuln triage, and sign-off

## E2E / Load / Sign-Off Matrix

| ID | Task | Owner | Evidence Link | Status | Notes |
|---|---|---|---|---|---|
| SP-01 | Deploy SessionAccount with spending policy on Sepolia | contracts-owner |  | open | |
| SP-02 | Deploy mock ERC-20 tokens and fund test account | contracts-owner |  | open | |
| SP-03 | Generate session key pair and bind policy | runtime-owner |  | open | |
| SP-04 | Happy-path transfer sequence + counter verification | qa-owner |  | open | |
| SP-05 | Window reset test (devnet time-advance + Sepolia timestamp-delta confirmation) | qa-owner |  | open | |
| SP-06 | Failure-path tests (per-call/window/blocklist) | qa-owner |  | open | |
| SP-07 | Edge cases (boundary, multicall, non-spending selectors) | qa-owner |  | open | |
| SP-08 | Sustained load test (100+ tx/hour) | qa-owner |  | open | |
| SP-09 | Threat model publication link | security-owner |  | open | |
| SP-10 | User guide/examples publication link | runtime-owner |  | open | |
| SP-11 | Known limitations section verified and up to date | security-owner |  | open | |
| SP-12 | Final sign-off (Lead Developer) | contracts-owner |  | open | |
| SP-13 | Final sign-off (Security Reviewer) | security-owner |  | open | |
| SP-14 | Final sign-off (QA Engineer) | qa-owner |  | open | |

## Required Evidence Format

For each row marked `done`, include:

- workflow/run link or tx hash
- exact command(s) used
- pass/fail output summary
- residual risk (if any)

SP-05 evidence requirements:

- Fast path: devnet/Katana time-advance invocation evidence plus pass output.
- Launch path: Sepolia confirmation with tx timestamp delta covering the full
  policy window (or explicit waiver with owner + due date).

## Suggested Command Evidence Snippets

```bash
# SP-06: policy-denied transfer (exceeds per-call limit)
starkli invoke "$ERC20_TOKEN_ADDR" transfer "$RECIPIENT_ADDR" u256:99999999999 \
  --rpc "$SEPOLIA_RPC_URL" \
  --account "$SESSION_ACCOUNT_ADDR" \
  --keystore "$SESSION_KEY_KEYSTORE_PATH"
# expected: revert / denied status due to spending policy
```

```bash
# SP-08: sustained-load sample (attach full script + output artifact)
start_time=$(date +%s)
success=0
failed=0
for i in $(seq 1 100); do
  starkli invoke "$ERC20_TOKEN_ADDR" transfer "$RECIPIENT_ADDR" u256:1 \
    --rpc "$SEPOLIA_RPC_URL" \
    --account "$SESSION_ACCOUNT_ADDR" \
    --keystore "$SESSION_KEY_KEYSTORE_PATH" \
    && success=$((success + 1)) || failed=$((failed + 1))
done
end_time=$(date +%s)
elapsed=$((end_time - start_time))
[ "$elapsed" -le 0 ] && elapsed=1
total=$((success + failed))
tx_count_per_hour=$((total * 3600 / elapsed))
if [ "$total" -gt 0 ]; then
  success_rate=$((success * 100 / total))
  failure_rate=$((failed * 100 / total))
else
  success_rate=0
  failure_rate=0
fi
echo "success=$success failed=$failed total=$total elapsed_seconds=$elapsed tx_count_per_hour=$tx_count_per_hour success_rate_pct=$success_rate failure_rate_pct=$failure_rate"
# include tx_count_per_hour, success_rate_pct, failure_rate_pct, and elapsed_seconds in evidence bundle
```

## Tracking

This document is evidence for:

- `#335` spending-policy E2E/load/sign-off closure
- `#273` launch gate
