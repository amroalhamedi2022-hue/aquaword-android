#!/usr/bin/env bash
# Source-only Final-Ready gate. Never builds, packages, or dispatches Android.
set -euo pipefail
cd "$(dirname "$0")/.."
approval="docs/FINAL_READY_APPROVAL.txt"
if [[ ! -f "$approval" ]]; then
  echo "BLOCKED: no independent source acceptance approval ($approval)" >&2
  exit 1
fi
for requirement in "FINAL_READY=YES" "REQUIREMENTS_COMPLETE=YES" "SOURCE_RECHECK=PASS" "ACCEPTANCE_REVIEW=PASS"; do
  if ! grep -Fxq "$requirement" "$approval"; then
    echo "BLOCKED: missing $requirement" >&2
    exit 1
  fi
done
expected="$(sed -n 's/^SOURCE_DIGEST_SHA256=//p' "$approval")"
if [[ ! "$expected" =~ ^[0-9a-f]{64}$ ]]; then
  echo "BLOCKED: invalid or absent approved source digest" >&2
  exit 1
fi
# Digest includes every tracked file except the approval itself. This avoids
# the impossible self-reference of embedding a commit hash in its own commit.
# Any tracked source, test, documentation, or workflow edit invalidates approval.
actual="$(git ls-files -z -- . ':(exclude)docs/FINAL_READY_APPROVAL.txt' |
  xargs -0 -r sha256sum | sha256sum | cut -d' ' -f1)"
if [[ "$actual" != "$expected" ]]; then
  echo "BLOCKED: source changed since independent approval" >&2
  exit 1
fi
echo "PASS: independent Final-Ready markers and exact tracked-source digest match"
