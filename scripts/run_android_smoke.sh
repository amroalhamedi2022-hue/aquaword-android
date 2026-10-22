#!/usr/bin/env bash
# Real Android runtime smoke test. Do NOT describe as a full feature suite.
set -euo pipefail

APK="$1"
ARTIFACTS="$2"
PKG="com.aquaword.app.debug"
BROWSER="org.libreoffice.androidapp.ui.LibreOfficeUIActivity"
EDITOR="org.libreoffice.androidlib.LOActivity"
MIME="application/vnd.openxmlformats-officedocument.wordprocessingml.document"

mkdir -p "$ARTIFACTS"
adb wait-for-device
adb shell getprop ro.build.version.release | tee "$ARTIFACTS/android-version.txt"
adb shell getprop ro.product.cpu.abilist | tee "$ARTIFACTS/android-abis.txt"
adb shell getprop sys.boot_completed | tr -d '\r' | grep -qx 1 || {
  echo "Android device has not completed boot" >&2
  exit 1
}
test -s "$APK"
sha256sum "$APK" | tee "$ARTIFACTS/apk-sha256.txt"

# Do not claim a pass merely because the apk exists.
adb install -r "$APK" 2>&1 | tee "$ARTIFACTS/install.log"
adb shell pm path "$PKG" | tee "$ARTIFACTS/installed-package.txt" | grep -Fq 'package:'

adb logcat -c || true
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard || true
adb shell am force-stop "$PKG"
adb shell am start -W -n "$PKG/$BROWSER" \
  2>&1 | tee "$ARTIFACTS/browser-start.txt"
sleep 20

pid="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
if [ -z "$pid" ]; then
  echo "AquaWord process died immediately after opening document browser" >&2
  exit 1
fi
echo "$pid" > "$ARTIFACTS/browser-process.txt"

adb exec-out screencap -p > "$ARTIFACTS/browser-screen.png"
adb shell uiautomator dump /data/local/tmp/aquaword-browser.xml >/dev/null 2>&1 || true
adb pull /data/local/tmp/aquaword-browser.xml "$ARTIFACTS/browser-ui.xml" >/dev/null 2>&1 || true
adb logcat -d -v time > "$ARTIFACTS/browser-logcat.txt"
adb shell dumpsys activity activities > "$ARTIFACTS/browser-activity.txt"
grep -Fq "$BROWSER" "$ARTIFACTS/browser-activity.txt" || {
  echo "Document browser did not reach foreground Activity" >&2
  exit 1
}
if grep -E 'FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError' "$ARTIFACTS/browser-logcat.txt" | grep -Fq "$PKG"; then
  echo "Runtime/linker error while starting browser" >&2
  exit 1
fi

# Open a real, generated Arabic research DOCX; this is not a mock document.
DOCX="templates/generated/research_ar.docx"
test -s "$DOCX"
# The first runtime test should avoid special external-storage grants.
# Use run-as (only available for the debuggable CI APK) to place the DOCX
# in AquaWord's own sandbox, then launch its real document editing Activity.
adb push "$DOCX" /data/local/tmp/aquaword-research-ar.docx >/dev/null
adb shell run-as "$PKG" mkdir -p files
adb shell run-as "$PKG" cp /data/local/tmp/aquaword-research-ar.docx files/aquaword-research-ar.docx
adb shell run-as "$PKG" ls -l files/aquaword-research-ar.docx | tee "$ARTIFACTS/document-inside-app.txt"
# Launch an app-owned debug-only trampoline that creates a real writable
# content:// FileProvider URI and passes SAF grants to native LOActivity.
# The old file:// intent skipped Collabora's content-copy editor initialization.
adb shell am start -W \
  -n "$PKG/org.libreoffice.androidapp.qa.QaOpenDocumentActivity" \
  2>&1 | tee "$ARTIFACTS/editor-start.txt"
sleep 35

adb exec-out screencap -p > "$ARTIFACTS/editor-screen.png"
adb shell uiautomator dump /data/local/tmp/aquaword-editor.xml >/dev/null 2>&1 || true
adb pull /data/local/tmp/aquaword-editor.xml "$ARTIFACTS/editor-ui.xml" >/dev/null 2>&1 || true
adb logcat -d -v time > "$ARTIFACTS/editor-logcat.txt"
adb shell dumpsys activity activities > "$ARTIFACTS/editor-activity.txt"
adb shell dumpsys activity top > "$ARTIFACTS/editor-top.txt"
adb shell pidof "$PKG" > "$ARTIFACTS/editor-process.txt" || {
  echo "App process terminated during DOCX open" >&2
  exit 1
}
grep -E 'mResumedActivity|topResumedActivity' "$ARTIFACTS/editor-activity.txt" | grep -Fq "$EDITOR" || {
  echo "Editor Activity is not actually resumed after opening the DOCX" >&2
  exit 1
}
grep -Fq "$EDITOR" "$ARTIFACTS/editor-activity.txt" || {
  echo "Editor did not remain foreground Activity after DOCX open" >&2
  exit 1
}
if grep -E 'FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError' "$ARTIFACTS/editor-logcat.txt" | grep -F "$PKG"; then
  echo "AquaWord emitted a fatal Java/native load error during DOCX open" >&2
  exit 1
fi
# This queries the actual Collabora WebView through Android DevTools,
# not a mock: require Writer docType, mounted document layer, and focus button.
python3 -m pip install --quiet 'websocket-client==1.8.0'
python3 scripts/verify_editor_webview.py \
  --package "$PKG" \
  --output "$ARTIFACTS/editor-webview-state.json" \
  --timeout 80
test -s "$ARTIFACTS/editor-webview-state.json"

# Second independent live runtime check: approximate Xiaomi Pad 5 landscape
# geometry using the SAME running Android app. This is a simulated viewport,
# NOT a claim to have tested a physical Pad 5.
adb shell wm size 2560x1600
adb shell wm density 320
adb shell cmd window set-user-rotation lock 0 || true
sleep 15
adb exec-out screencap -p > "$ARTIFACTS/editor-tablet-16x10.png"
if ! python3 quality/check_screen.py "$ARTIFACTS/editor-tablet-16x10.png" --aspect 1.6; then
  adb shell wm size 1600x2560
  adb shell cmd window set-user-rotation lock 1 || true
  sleep 15
  adb exec-out screencap -p > "$ARTIFACTS/editor-tablet-16x10.png"
  python3 quality/check_screen.py "$ARTIFACTS/editor-tablet-16x10.png" --aspect 1.6
fi
adb shell pidof "$PKG" >/dev/null || {
  echo "AquaWord crashed during 16:10 landscape transition" >&2
  exit 1
}
python3 scripts/verify_editor_webview.py \
  --package "$PKG" \
  --output "$ARTIFACTS/editor-tablet-webview-state.json" \
  --timeout 80
test -s "$ARTIFACTS/editor-tablet-webview-state.json"

# Perform an actual edit in the native Writer engine and require the saved
# app-owned DOCX bytes to contain it. A successful UNO command alone does NOT pass.
python3 scripts/android_edit_roundtrip.py --evidence-dir "$ARTIFACTS" --timeout 75
test -s "$ARTIFACTS/roundtrip-result.txt"

# Re-open the persisted document, proving that its actual DOCX bytes remain
# readable by the native Android document engine.
adb shell am start -W \
  -n "$PKG/org.libreoffice.androidapp.qa.QaOpenDocumentActivity" \
  2>&1 | tee "$ARTIFACTS/reopen-start.txt"
sleep 25
python3 scripts/verify_editor_webview.py \
  --package "$PKG" \
  --output "$ARTIFACTS/reopened-writer-state.json" \
  --timeout 80
test -s "$ARTIFACTS/reopened-writer-state.json"

for picture in browser-screen.png editor-screen.png; do
  test "$(stat -c %s "$ARTIFACTS/$picture")" -gt 3000 || {
    echo "Invalid screenshot evidence: $picture" >&2
    exit 1
  }
done
# Fail visibly empty or identical screenshots; this prevents a background
# Activity and non-rendering document from being counted as a full UI pass.
python3 - "$ARTIFACTS" <<'PY'
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageStat
folder = Path(sys.argv[1])
home = Image.open(folder / "browser-screen.png").convert("RGB")
editor = Image.open(folder / "editor-screen.png").convert("RGB")
if home.size != editor.size or home.width < 480 or home.height < 640:
    raise AssertionError(f"Unexpected Android screenshot geometry: {home.size}, {editor.size}")
for name, photo in (("browser", home), ("editor", editor)):
    detail = ImageStat.Stat(photo.resize((100, 100)))
    if max(detail.var) < 100.0:
        raise AssertionError(f"{name} appears to be an empty or nearly blank screen")
difference = ImageChops.difference(home, editor)
change = sum(ImageStat.Stat(difference.resize((100, 100))).mean) / 3.0
if change < 3.0:
    raise AssertionError("Browser and editor screenshots are suspiciously identical")
print(f"Visible Android UI difference: {change:.1f} average RGB units")
PY
printf '\nPASS: Real AquaWord Writer opened on phone/tablet; Focus Mode worked; UNO edit persisted to DOCX and reopened in Android.\n' | tee "$ARTIFACTS/smoke-result.txt"
printf 'NOT PROVEN: editing/save-reopen, advanced layout, tools, visual match, long-term stability or real Xiaomi Pad 5 behavior.\n' >> "$ARTIFACTS/smoke-result.txt"

# Report only the actual features exercised on Android; untested rows stay NOT_VERIFIED.
# Every receipt references checksummed files, never just a developer's assertion.
python3 - "$ARTIFACTS" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
root=Path(sys.argv[1])
now=datetime.now(timezone.utc).isoformat()

def proof(requirement, files, method, observed):
    validated=[]
    for name in files:
        path=root/name
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Missing Android runtime evidence: {name}")
        validated.append({"path":name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    return {
      "requirement_id":requirement,
      "result":"PASS",
      "tester":"GitHub Actions Android runtime harness (automated; NOT a human reviewer)",
      "device_class":"emulator",
      "device":"Android API 35 Google APIs x86_64 with ARM64 translation",
      "method":method,
      "observed":observed,
      "time_utc":now,
      "evidence_files":validated
    }

receipts=[
    proof("APP-01",
          ("install.log","installed-package.txt","browser-screen.png",
           "browser-activity.txt","editor-webview-state.json","smoke-result.txt"),
          "ADB install + Activity foreground + live WebView Writer document",
          "Installed and opened a real AquaWord Writer document on Android emulator"),
    proof("UI-03",
          ("editor-webview-state.json","editor-tablet-webview-state.json"),
          "Chrome DevTools queried live Android WebView and clicked Focus Mode twice",
          "Focus Mode entered and exited; editor page remained visible"),
    proof("FILE-03",
          ("edit-command.json","roundtrip-result.txt","roundtrip-hash.txt",
           "reopened-writer-state.json","smoke-result.txt"),
          "UNO InsertText + native Save + read actual DOCX bytes + reopen",
          "Inserted QA text survived save to app-owned DOCX and Android reopen")
]
(root/"receipts.json").write_text(
    json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 quality/audit.py --evidence-dir "$ARTIFACTS" --report "$ARTIFACTS/required-vs-actual.md"

