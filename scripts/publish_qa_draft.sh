#!/usr/bin/env bash
# Keep verified AquaWord APK on GitHub without consuming Actions Artifacts quota.
# Draft releases are maintainers-only; NEVER auto-publish an unfinished app.
set -euo pipefail

: "$GITHUB_REPOSITORY"
: "$GITHUB_SHA"
: "$GH_TOKEN"
test "$GITHUB_REPOSITORY" = "amroalhamedi2022-hue/aquaword-android" || {
  echo "Refusing to push an AquaWord build into a different repository" >&2
  exit 1
}
command -v gh >/dev/null
count="$(find output -maxdepth 1 -type f -name 'AquaWord-*.apk' | wc -l)"
test "$count" -eq 1 || {
  echo "Exactly one validated debug APK is required; found $count" >&2
  exit 1
}
APK="$(find output -maxdepth 1 -type f -name 'AquaWord-*.apk' -print -quit)"
test -s "$APK"
test -s output/SHA256SUMS
(cd output && sha256sum -c SHA256SUMS)

# Verified and unverified builds are separate, both ALWAYS unpublished.
# An emulator architecture failure must not throw away hours of compiled APK.
MODE="${1:---verified}"
case "$MODE" in
  --verified|--unverified) ;;
  *) echo "Use --verified or --unverified" >&2; exit 2 ;;
esac

if [ "$MODE" = "--verified" ]; then
# Gate verified QA status on actual runtime evidence, never mere APK existence.
for proof in smoke-evidence/smoke-result.txt \
             smoke-evidence/editor-webview-state.json \
             smoke-evidence/editor-tablet-webview-state.json \
             smoke-evidence/roundtrip-result.txt \
             smoke-evidence/reopened-writer-state.json \
             smoke-evidence/required-vs-actual.md; do
  test -s "$proof" || {
    echo "No QA draft without Android proof: $proof" >&2
    exit 1
  }
done
grep -Fq 'PASS: Real AquaWord Writer' smoke-evidence/smoke-result.txt
grep -Fq 'PASS: actual Android app-owned DOCX' smoke-evidence/roundtrip-result.txt
python3 - <<'PY'
import json
from pathlib import Path
for name in (
    'smoke-evidence/editor-webview-state.json',
    'smoke-evidence/editor-tablet-webview-state.json',
    'smoke-evidence/reopened-writer-state.json'):
    state=json.loads(Path(name).read_text(encoding='utf-8'))
    assert state['docType']=='text' and state['documentLayer'] is True,name
    assert state['focusModeFunctional'] is True,name
PY
fi

shortsha="$(printf '%s' "$GITHUB_SHA" | cut -c1-12)"
tag="qa-$shortsha"
notes="$(cat <<EOF
**UNPUBLISHED INTERNAL QA DRAFT — NOT A FINAL APP RELEASE.**

AquaWord Android APK built from source commit $GITHUB_SHA.
Android emulator: actual Writer opened, Arabic DOCX loaded, focus toggle
worked, and test-document UNO edit/save/readback/reopen passed.
No physical Xiaomi Pad 5 acceptance, full feature parity, or final release
approval has occurred. Keep this GitHub release in DRAFT state.

See original CI run logs for detailed evidence and SHA-256 checksums.
EOF
)"
if [ "$MODE" = "--unverified" ]; then
  tag="qa-unverified-$shortsha"
  notes="$(cat <<EOF
**UNPUBLISHED INTERNAL BUILD ARTIFACT — ANDROID RUNTIME NOT VERIFIED.**

APK compiled and checksum-validated from source commit $GITHUB_SHA.
It is retained solely to avoid rebuilding the expensive Collabora ARM64 engine.
Android installation, real document loading, writing, crash recovery and
tablet correctness are NOT established. A failed/unsupported emulator run
MUST NOT be counted as acceptance. Do not publish this draft or distribute
it as a completed AquaWord APK.

See native CI run logs, failure summary and SHA-256 verification output.
EOF
)"
fi

if gh release view "$tag" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  echo "An internal QA draft already exists; refusing overwrite: $tag" >&2
  exit 1
fi
gh release create "$tag" \
  "$APK" output/SHA256SUMS \
  --repo "$GITHUB_REPOSITORY" \
  --target "$GITHUB_SHA" \
  --title "AquaWord internal QA $tag (NOT FINAL)" \
  --notes "$notes" \
  --draft \
  --latest=false
if [ "$MODE" = "--verified" ]; then
  echo "Stored emulator-verified APK as an UNPUBLISHED QA draft: $tag"
else
  echo "Stored checksummed build-only APK in UNPUBLISHED UNVERIFIED draft: $tag"
fi
