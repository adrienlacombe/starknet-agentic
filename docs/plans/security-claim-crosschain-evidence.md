# Security Claim Track 3: Cross-Chain Evidence Binding

## Goal

Upgrade the demo artifact from "best effort metadata" to "required linked evidence" across Base reputation context and Starknet execution context.

## Problem

Base attestation and ERC-8004 identity/session evidence are currently optional in run output. This allows successful runs without full identity-to-execution linkage.

## Scope

1. Add strict evidence mode requiring:
   - verified Base attestation section
   - ERC-8004 identity check (`DEMO_AGENT_ID`) evidence
   - session key/account linkage evidence
2. Bind these checks in artifact validation with explicit pass/fail reasons.
3. Add tests for missing-evidence and valid-evidence strict runs.
4. Document expected env vars and sample strict evidence artifact.

## Non-Goals

1. Full CBOM/EAR implementation.
2. Mainnet indexing service changes.
3. Wallet provider migrations.

## Acceptance Criteria

1. Strict evidence run fails when attestation or identity linkage fields are missing.
2. Strict evidence run passes only when all required linkage checks are present and verified.
3. Artifact schema clearly marks mandatory vs optional fields in strict mode.
4. Docs include one reproducible command and one minimal passing env template.
