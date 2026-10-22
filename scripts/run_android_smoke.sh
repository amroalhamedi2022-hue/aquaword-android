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

adb shell screencap -p /sdcard/aquaword-home.png
adb pull /sdcard/aquaword-home.png "$ARTIFACTS/browser-screen.png" >/dev/null
adb shell uiautomator dump /sdcard/aquaword-browser.xml >/dev/null 2>&1 || true
adb pull /sdcard/aquaword-browser.xml "$ARTIFACTS/browser-ui.xml" >/dev/null 2>&1 || true
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

adb shell screencap -p /sdcard/aquaword-editor.png
adb pull /sdcard/aquaword-editor.png "$ARTIFACTS/editor-screen.png" >/dev/null
adb shell uiautomator dump /sdcard/aquaword-editor.xml >/dev/null 2>&1 || true
adb pull /sdcard/aquaword-editor.xml "$ARTIFACTS/editor-ui.xml" >/dev/null 2>&1 || true
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
printf '\nPASS: installed AquaWord, launched browser and editor, opened Arabic DOCX without immediate process death.\n' | tee "$ARTIFACTS/smoke-result.txt"
printf 'NOT PROVEN: text rendering, save/reopen, menus, focus mode, long-term stability or real Xiaomi Pad 5 behavior.\n' >> "$ARTIFACTS/smoke-result.txt"
