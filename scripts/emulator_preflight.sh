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
# Verify the target tablet's 16:10 logical viewport, not just a phone viewport.
# Xiaomi Pad 5 has a 2560x1600 display. Emulator override is NOT a physical device.
adb shell wm size 2560x1600
adb shell wm density 320
adb shell cmd window set-user-rotation lock 0 || true
adb shell input keyevent KEYCODE_HOME
sleep 7
adb exec-out screencap -p > emulator-evidence/tablet-16x10.png
python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageStat
file = Path("emulator-evidence/tablet-16x10.png")
screen = Image.open(file).convert("RGB")
w, h = screen.size
print("Simulated tablet screenshot:", w, "x", h)
print("Target geometry: 2560x1600, 16:10")
if w < 1500 or h < 900 or not 1.58 < w/h < 1.62:
    raise AssertionError(f"Not a visible 16:10 tablet screen: {w}x{h}")
stats = ImageStat.Stat(screen.resize((100, 100)))
if max(stats.var) < 100 or max(stats.mean) < 10:
    raise AssertionError("Tablet screen is black or blank")
PY
printf 'PASS: Android 15 phone + tablet-size 16:10 nonblank images. Not app functional proof.\n' | tee emulator-evidence/result.txt
