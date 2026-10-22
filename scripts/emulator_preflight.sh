#!/usr/bin/env bash
# One-time proof Android CI actually boots; not AquaWord app functional testing.
set -euo pipefail
mkdir -p emulator-evidence
adb wait-for-device
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = "1"
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = "35"
adb shell getprop ro.product.cpu.abilist | tee emulator-evidence/abis.txt
adb shell getprop ro.dalvik.vm.isa.arm64 | tee emulator-evidence/arm64-translator.txt
adb shell getprop ro.build.version.release | tee emulator-evidence/android-version.txt
# A boot-completed VM may have a black/off screen. Explicitly wake and show HOME.
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard || true
adb shell input keyevent KEYCODE_HOME
adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME || true
sleep 7
adb exec-out screencap -p > emulator-evidence/screen.png
test -s emulator-evidence/screen.png
python3 - <<'PY'
from PIL import Image, ImageStat
image = Image.open('emulator-evidence/screen.png').convert('RGB')
stat = ImageStat.Stat(image.resize((100, 100)))
print('Screen:', image.size, 'mean RGB:', stat.mean, 'variance:', stat.var)
if max(stat.var) < 100 or max(stat.mean) < 10:
    raise AssertionError('Android emulator framebuffer is black/blank; no visual proof')
PY
echo 'PASS: Android 15 emulator booted and rendered a NON-BLANK home screenshot. App APK has NOT yet been tested.' | tee emulator-evidence/result.txt
