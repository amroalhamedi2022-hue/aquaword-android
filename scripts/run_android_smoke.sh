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
adb shell am start -W -a android.intent.action.VIEW \
  -d "file:///data/user/0/$PKG/files/aquaword-research-ar.docx" \
  -t "$MIME" \
  -n "$PKG/$EDITOR" \
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
printf '\nPASS: installed AquaWord, launched browser and editor, opened Arabic DOCX without immediate process death.\n' | tee "$ARTIFACTS/smoke-result.txt"
printf 'NOT PROVEN: text rendering, save/reopen, menus, focus mode, long-term stability or real Xiaomi Pad 5 behavior.\n' >> "$ARTIFACTS/smoke-result.txt"

# Attach first-hand ADB evidence to exactly the gates that this smoke proves.
# Do not record formatting, visual match, save/reopen or template features as PASS.
python3 - "$ARTIFACTS" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
root = Path(sys.argv[1])
evidence = []
for name in ("install.log", "installed-package.txt", "browser-screen.png",
             "browser-activity.txt", "smoke-result.txt"):
    path = root / name
    evidence.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
receipt = {
    "requirement_id": "APP-01",
    "result": "PASS",
    "tester": "GitHub Actions Android runtime harness (automated, NOT a human reviewer)",
    "device_class": "emulator",
    "device": "Android API 35 Google APIs x86_64 with arm64 translator",
    "method": "ADB install, explicit Activity start, process/foreground and screenshot verification",
    "observed": "Installed and launched an AquaWord browser and editor without immediate termination",
    "time_utc": datetime.now(timezone.utc).isoformat(),
    "evidence_files": evidence,
}
(root / "receipts.json").write_text(json.dumps([receipt], ensure_ascii=False, indent=2) + "\n")
PY
python3 quality/audit.py --evidence-dir "$ARTIFACTS" --report "$ARTIFACTS/required-vs-actual.md"

