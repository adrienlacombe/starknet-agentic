# Security Claim Track 2: Strict Proof Profile

## Goal

Make security claims mechanically verifiable by requiring strict probes in demo security profile runs.

## Problem

Current demo execution can be marked successful even when strict denial checks are optional in some profiles. This weakens external reproducibility of the claim set.

## Scope

1. Add a strict profile for demo runs that requires:
   - spending policy denial proof (`deniedByPolicy === true`)
   - post-revocation denial proof (`revokedSessionProbe.blocked === true`)
2. Add artifact-level validator that fails run completion when strict requirements are not satisfied.
3. Add automated tests for strict profile validation logic and failure paths.
4. Update demo docs with a strict profile command and expected outputs.

## Non-Goals

1. Replacing existing non-strict developer mode.
2. Mainnet parameter changes.
3. DFNS integration in this track.

## Acceptance Criteria

1. Strict profile run exits non-zero if denial probes are missing or false.
2. Strict profile run exits zero only when both denial conditions are proven.
3. Unit/integration tests cover both pass and fail strict-profile scenarios.
4. Documentation includes one reproducible strict-profile command and artifact examples.
