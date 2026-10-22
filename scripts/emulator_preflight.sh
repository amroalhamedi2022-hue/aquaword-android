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
adb exec-out screencap -p > emulator-evidence/screen.png
test -s emulator-evidence/screen.png
echo 'PASS: Android 15 emulator booted and rendered a real screenshot. App APK has NOT yet been tested.' | tee emulator-evidence/result.txt
