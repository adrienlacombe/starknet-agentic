# Threat Intel Sources (Web Enrichment)

Use these sources when deep-mode threat-intel enrichment is enabled.

## Priority Sources (Primary)

- `github.com` (official protocol repos, published audits, postmortems)
- `starknet.io` and ecosystem official docs/blogs
- `openzeppelin.com` security docs and incident writeups
- `trailofbits.com` blog/research/public audits
- `code4rena.com/reports/*` judged contest reports
- `immunefi.com` security research and common-vulnerability taxonomy

## Secondary Sources (Use With Caution)

- `sherlock.xyz/*` public reports
- `cantina.xyz/*` public reports
- `halborn.com` public research/blog
- `consensys.io` and `diligence.consensys.io` public writeups

## Normalization Contract

For each extracted signal, capture:

- `date` (ISO-like string if available),
- `source` (URL),
- `class_hint` (map to local vector/class),
- `shape` (one-line exploit pattern),
- `confidence` (`high` / `medium` / `low` for signal quality only).

## Hard Rules

- Do not treat external intel as findings.
- Do not quote low-quality social posts as primary evidence.
- Every finding must be proven in in-scope code and pass local FP gate.
