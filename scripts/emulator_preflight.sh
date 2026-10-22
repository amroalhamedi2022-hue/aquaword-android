#!/usr/bin/env bash
# Actual Android 15 graphical preflight. Not a test of AquaWord itself.
set -euo pipefail
mkdir -p emulator-evidence
adb wait-for-device
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = "1"
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = "35"
adb shell getprop ro.product.cpu.abilist | tee emulator-evidence/abis.txt
adb shell getprop ro.dalvik.vm.isa.arm64 | tee emulator-evidence/arm64-translator.txt
adb shell getprop ro.build.version.release | tee emulator-evidence/android-version.txt
adb shell settings put system screen_off_timeout 600000 || true

capture() {
  local filename="$1"
  local aspect="$2"
  local attempt
  for attempt in 1 2 3 4 5 6; do
    echo "Capture $filename attempt $attempt"
    adb shell input keyevent KEYCODE_WAKEUP || true
    adb shell wm dismiss-keyguard || true
    # Android home can be black if software GPU composition is not ready.
    # Launch a real Settings Activity to request a visible surface.
    adb shell am start -a android.settings.SETTINGS >/dev/null 2>&1 || true
    sleep 5
    adb exec-out screencap -p > "$filename"
    if [ -n "$aspect" ]; then
      if python3 quality/check_screen.py "$filename" --aspect "$aspect"; then return 0; fi
    else
      if python3 quality/check_screen.py "$filename"; then return 0; fi
    fi
  done
  echo "Android has no verifiable framebuffer after six attempts" >&2
  return 1
}

capture emulator-evidence/screen.png ""

# A 16:10 logical tablet display, matching Xiaomi Pad 5 resolution.
adb shell wm size 2560x1600
adb shell wm density 320
adb shell cmd window set-user-rotation lock 0 || true
if ! capture emulator-evidence/tablet-16x10.png 1.6; then
  # Some images transpose a display override when portrait is locked.
  adb shell wm size 1600x2560
  adb shell cmd window set-user-rotation lock 1 || true
  capture emulator-evidence/tablet-16x10.png 1.6
fi
printf 'PASS: Android 15 phone and tablet-size 16:10 UI; AquaWord APK NOT tested.\n' | tee emulator-evidence/result.txt
