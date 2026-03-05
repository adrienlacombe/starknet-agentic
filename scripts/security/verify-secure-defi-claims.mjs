#!/usr/bin/env node

import fs from "node:fs";

const REQUIRED_CLAIM_IDS = [
  "oversized_spend_denied",
  "forbidden_selector_denied",
  "revoked_or_expired_session_blocked",
  "erc8004_identity_path",
  "base_to_starknet_anchor_verified",
  "starkzap_execution_receipt",
];

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const value = argv[i + 1];
    if (!value || value.startsWith("--")) {
      args[name] = "true";
      continue;
    }
    args[name] = value;
    i += 1;
  }
  return args;
}

function loadArtifact(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const artifactPath = args.artifact;
  const requireStrict = args["require-strict"] === "true" || args["require-strict"] === true;

  if (!artifactPath) {
    console.error("Usage: node scripts/security/verify-secure-defi-claims.mjs --artifact <path> [--require-strict]");
    process.exit(2);
  }

  const artifact = loadArtifact(artifactPath);
  const claims = Array.isArray(artifact?.claims) ? artifact.claims : [];
  const byId = new Map(claims.map((claim) => [String(claim?.claimId), claim]));

  if (requireStrict && artifact?.strictSecurityProof !== true) {
    console.error("strict-proof-gate: BLOCK");
    console.error("- strictSecurityProof is not true in artifact");
    process.exit(1);
  }

  const missingClaimEntries = REQUIRED_CLAIM_IDS.filter((id) => !byId.has(id));
  if (missingClaimEntries.length > 0) {
    console.error("strict-proof-gate: BLOCK");
    for (const claimId of missingClaimEntries) {
      console.error(`- missing claim entry: ${claimId}`);
    }
    process.exit(1);
  }

  const blocking = claims.filter(
    (claim) => claim?.required === true && String(claim?.proof_status) !== "proved",
  );
  if (blocking.length > 0) {
    console.error("strict-proof-gate: BLOCK");
    for (const claim of blocking) {
      console.error(
        `- ${claim.claimId} failed (status=${claim.proof_status}, tx_hash=${claim.tx_hash ?? "null"}, evidence_path=${claim.evidence_path ?? "unknown"})`,
      );
    }
    process.exit(1);
  }

  console.log(`strict-proof-gate: PASS (${claims.length} claims validated from ${artifactPath})`);
}

main();
