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

# Gate QA storage on real app execution, not build outputs or screenshots alone.
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
echo "Stored emulator-verified APK as an UNPUBLISHED QA draft: $tag"
