#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${CAIRO_AUDITOR_WORKDIR:-}"
WORKDIR_EXPLICIT=0
if [[ -n "$WORKDIR" ]]; then
  WORKDIR_EXPLICIT=1
fi
REPORT_DIR="."
REPORT_PATH=""
REPORT_EXPLICIT=0

usage() {
  cat <<'EOF'
Usage: bash skills/cairo-auditor/scripts/doctor.sh [--workdir PATH] [--report-dir PATH] [--report PATH]

If --workdir is omitted and CAIRO_AUDITOR_WORKDIR is not set, the most recent
cairo-auditor.* directory under $TMPDIR (or /tmp) is auto-discovered.

Checks:
  - host-capabilities artifact exists
  - bundle artifacts 1..4 exist with non-zero lines
  - latest security-review report exists
  - report includes Execution Integrity + Execution Trace markers
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      if [[ $# -lt 2 ]]; then
        echo "--workdir requires a path" >&2
        usage
        exit 2
      fi
      WORKDIR="$2"
      WORKDIR_EXPLICIT=1
      shift 2
      ;;
    --report-dir)
      if [[ $# -lt 2 ]]; then
        echo "--report-dir requires a path" >&2
        usage
        exit 2
      fi
      REPORT_DIR="$2"
      shift 2
      ;;
    --report)
      if [[ $# -lt 2 ]]; then
        echo "--report requires a path" >&2
        usage
        exit 2
      fi
      REPORT_PATH="$2"
      REPORT_EXPLICIT=1
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

fail_count=0

say_ok() {
  echo "[OK] $1"
}

say_fail() {
  echo "[FAIL] $1"
  fail_count=$((fail_count + 1))
}

resolve_artifact_root() {
  local preferred="$1"
  local explicit="$2"
  if [[ -f "$preferred/cairo-audit-host-capabilities.json" ]]; then
    echo "$preferred"
    return
  fi
  if [[ "$explicit" -eq 1 ]]; then
    echo "$preferred"
    return
  fi

  # SKILL.md uses `mktemp -d "${TMPDIR:-/tmp}/cairo-auditor.XXXXXX"` per run.
  # When no explicit --workdir is given, discover the most-recent matching
  # directory under both $TMPDIR (if set) and /tmp.
  local candidate=""
  local newest=""
  local newest_mtime=0
  local search_root mtime
  for search_root in "${TMPDIR:-}" "/tmp"; do
    [[ -z "$search_root" ]] && continue
    [[ ! -d "$search_root" ]] && continue
    while IFS= read -r candidate; do
      [[ -z "$candidate" ]] && continue
      [[ ! -d "$candidate" ]] && continue
      mtime=$(stat -f '%m' "$candidate" 2>/dev/null || stat -c '%Y' "$candidate" 2>/dev/null || echo 0)
      if [[ "${mtime:-0}" -gt "$newest_mtime" ]]; then
        newest_mtime="$mtime"
        newest="$candidate"
      fi
    done < <(find "$search_root" -maxdepth 1 -type d -name 'cairo-auditor.*' 2>/dev/null)
  done

  if [[ -n "$newest" && -f "$newest/cairo-audit-host-capabilities.json" ]]; then
    echo "$newest"
    return
  fi
  if [[ -n "$newest" ]]; then
    # Found a workdir but no host-capabilities artifact — return it so the
    # caller can report the missing artifact rather than silently scanning /tmp.
    echo "$newest"
    return
  fi

  # Legacy fallback: artifacts may have been written directly to /tmp by an
  # older orchestration path that did not use mktemp.
  if [[ -f "/tmp/cairo-audit-host-capabilities.json" ]]; then
    echo "/tmp"
    return
  fi
  echo "$preferred"
}

ART_ROOT="$(resolve_artifact_root "$WORKDIR" "$WORKDIR_EXPLICIT")"

if [[ -z "$ART_ROOT" ]]; then
  say_fail "No cairo-auditor workdir found. Pass --workdir, set CAIRO_AUDITOR_WORKDIR, or run an audit first to create one."
else
  echo "Inspecting workdir: $ART_ROOT"
  if [[ -f "$ART_ROOT/cairo-audit-host-capabilities.json" ]]; then
    say_ok "Host capabilities file: $ART_ROOT/cairo-audit-host-capabilities.json"
  else
    say_fail "Missing host capabilities file: $ART_ROOT/cairo-audit-host-capabilities.json"
  fi

  for i in 1 2 3 4; do
    bundle="$ART_ROOT/cairo-audit-agent-$i-bundle.md"
    if [[ ! -f "$bundle" ]]; then
      say_fail "Missing bundle: $bundle"
      continue
    fi
    lines="$(wc -l < "$bundle" | tr -d ' ')"
    if [[ "${lines:-0}" -gt 0 ]]; then
      say_ok "Bundle $i lines: $lines"
    else
      say_fail "Bundle $i is empty: $bundle"
    fi
  done
fi

if [[ -z "$REPORT_PATH" ]]; then
  REPORT_PATH="$(ls -t "$REPORT_DIR"/security-review-*.md 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "$REPORT_PATH" || ! -f "$REPORT_PATH" ]]; then
  if [[ "$REPORT_EXPLICIT" -eq 1 ]]; then
    say_fail "Requested report not found: $REPORT_PATH"
  else
    say_fail "No security-review-*.md report found (report-dir: $REPORT_DIR)"
  fi
else
  say_ok "Report file: $REPORT_PATH"
  if grep -q '^`Execution Integrity: ' "$REPORT_PATH" || grep -q '^Execution Integrity: ' "$REPORT_PATH"; then
    say_ok "Execution Integrity marker present"
  else
    say_fail "Missing Execution Integrity marker in report"
  fi
  if grep -q '^## Execution Trace' "$REPORT_PATH"; then
    say_ok "Execution Trace section present"
  else
    say_fail "Missing Execution Trace section in report"
  fi
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo
  echo "Doctor status: FAILED ($fail_count issue(s))"
  exit 1
fi

echo
echo "Doctor status: PASS"
