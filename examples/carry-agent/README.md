# Carry Agent Demo

Deterministic carry monitor for `starknet-agentic`.

This example fetches Extended market + funding data, applies a policy-first basis/carry decision engine, and writes a machine-readable artifact.

## What it proves

1. Production-style strategy gating (`ENTER` / `HOLD` / `EXIT` / `PAUSE`) with explicit reason codes.
2. Defensive parsing against live Extended response envelopes (`status/data`, compact funding keys).
3. Safe default behavior: monitor-only (no order execution).

## Setup

```bash
pnpm install
cp examples/carry-agent/.env.example examples/carry-agent/.env
```

Optional for user-specific fee tier:

```env
EXTENDED_API_KEY=...
```

## Run

```bash
pnpm --filter @starknet-agentic/carry-agent-demo run run
```

Output:

- structured JSON logs to stdout
- artifact JSON in `examples/carry-agent/artifacts/`

## Test

```bash
pnpm --filter @starknet-agentic/carry-agent-demo test
pnpm --filter @starknet-agentic/carry-agent-demo typecheck
```

## Safety notes

- This demo does not place orders.
- Any execution path must be added behind explicit `RUN_MODE=execute` + hard limits.
- Never commit `.env` or API keys.
