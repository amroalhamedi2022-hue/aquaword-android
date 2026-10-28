#!/usr/bin/env python3
"""End-to-end SAF failure injection against the existing AquaWord diagnostic APK.

A separate tiny QA app accepts all bytes sent to its ContentProvider but only
persists the first 128. The test must prove that AquaWord refuses to acknowledge
SAVE and keeps the exact edited DOCX in its private recovery history.
"""
import argparse
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

from docx import Document
from PIL import Image, ImageStat
import android_edit_roundtrip as editor

PKG = "com.aquaword.app.debug"
PROVIDER_PKG = "com.aquaword.saffaultprovider"
PROVIDER_URI = "content://com.aquaword.saffaultprovider.documents/document/qa.docx"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
KEEP_BYTES = 128
SENTINEL = editor.SENTINEL


def adb(*args, binary=False):
    return editor.call(*args, binary=binary)


def configure_landscape_viewport(evidence: Path):
    """Set a tablet-like viewport without treating an unsupported rotation API as fatal.

    Android emulator images differ in whether cmd window exposes
    set-user-rotation. The command is best-effort; the rendered pixels, not the
    command's exit code, decide whether the 16:10 viewport is ready.
    """
    records = []

    def best_effort_rotation():
        try:
            adb("shell", "cmd", "window", "set-user-rotation", "lock", "1")
            records.append({"command": "set-user-rotation", "result": "accepted"})
        except Exception as failure:
            records.append({
                "command": "set-user-rotation",
                "result": "unsupported-or-failed",
                "detail": str(failure),
            })

    best_effort_rotation()
    adb("shell", "wm", "size", "2560x1600")
    adb("shell", "wm", "density", "320")
    for attempt in (1, 2):
        try:
            time.sleep(5)
            frame = adb("exec-out", "screencap", "-p", binary=True)
            frame_path = evidence / f"fault-provider-viewport-{attempt}.png"
            frame_path.write_bytes(frame)
            with Image.open(io.BytesIO(frame)) as image:
                rgb = image.convert("RGB")
                width, height = rgb.size
                statistics = ImageStat.Stat(rgb.resize((100, 100)))
                ratio = width / height if height else 0.0
                valid = (
                    width >= 480 and height >= 480
                    and abs(ratio - 1.6) <= 0.035
                    and max(statistics.var) >= 100
                    and max(statistics.mean) >= 10
                )
            records.append({
                "attempt": attempt, "width": width, "height": height,
                "aspect_ratio": ratio, "rendered_pixels_valid": valid,
            })
            if valid:
                (evidence / "fault-provider-viewport-result.json").write_text(
                    json.dumps({"result": "PASS", "attempts": records},
                               indent=2) + "\n", encoding="utf-8")
                return
        except Exception as failure:
            records.append({"attempt": attempt, "result": "capture-failed",
                            "detail": str(failure)})
        if attempt == 1:
            best_effort_rotation()
            adb("shell", "wm", "size", "2560x1600")
            adb("shell", "wm", "density", "320")
    (evidence / "fault-provider-viewport-result.json").write_text(
        json.dumps({"result": "FAIL", "attempts": records},
                   indent=2) + "\n", encoding="utf-8")
    raise RuntimeError(
        "Rendered Android viewport did not reach a nonblank 16:10 landscape frame; "
        "see fault-provider-viewport-result.json"
    )


def latest_recovery_with_sentinel(evidence: Path):
    listing = adb("shell", "run-as", PKG, "ls", "files/aquaword-history").decode(
        "utf-8", errors="replace")
    (evidence / "recovery-directory-listing.txt").write_text(listing + "\n", encoding="utf-8")
    names = [line.strip() for line in listing.splitlines() if line.strip().endswith(".snapshot")]
    candidates = []
    for name in names:
        payload = adb("exec-out", "run-as", PKG, "cat",
                      "files/aquaword-history/" + name, binary=True)
        if editor.check_document(payload):
            candidates.append((name, payload))
    if not candidates:
        raise AssertionError(
            "No valid private recovery snapshot retained the edited DOCX sentinel")
    candidates.sort(key=lambda item: item[0])
    name, payload = candidates[-1]
    (evidence / "recovered-edited-document.docx").write_bytes(payload)
    return name, payload


def run(evidence: Path, timeout: int):
    evidence.mkdir(parents=True, exist_ok=True)
    original = adb("exec-out", "run-as", PROVIDER_PKG, "cat", "files/qa.docx", binary=True)
    if not zipfile.is_zipfile(io.BytesIO(original)):
        raise AssertionError("Provider's initial fixture is not a valid DOCX ZIP")
    original_text = "\n".join(p.text for p in Document(io.BytesIO(original)).paragraphs)
    if SENTINEL in original_text:
        raise AssertionError("Provider fixture already contains the QA sentinel")
    original_sha = hashlib.sha256(original).hexdigest()
    (evidence / "provider-original-sha256.txt").write_text(original_sha + "\n", encoding="utf-8")
    (evidence / "provider-original.docx").write_bytes(original)

    # Approximate tablet landscape. Unsupported rotation APIs are best-effort;
    # accept the viewport only after checking the actual rendered screenshot.
    configure_landscape_viewport(evidence)

    launch = adb("shell", "am", "start", "-W",
                 "-n", f"{PKG}/org.libreoffice.androidlib.LOActivity",
                 "-a", "android.intent.action.VIEW",
                 "-d", PROVIDER_URI, "-t", MIME, "-f", "0x43").decode(
                     "utf-8", errors="replace")
    (evidence / "fault-provider-editor-start.txt").write_text(launch, encoding="utf-8")
    if "Status: ok" not in launch:
        raise RuntimeError("Android did not start native Writer for the fault-provider URI: " + launch)

    time.sleep(35)
    deadline = time.monotonic() + 100
    pid = ""
    activities = ""
    while time.monotonic() < deadline:
        try:
            pid = adb("shell", "pidof", PKG).decode().strip().split()[0]
            activities = adb("shell", "dumpsys", "activity", "activities").decode(
                "utf-8", errors="replace")
            if "org.libreoffice.androidlib.LOActivity" in activities:
                break
        except Exception:
            pass
        time.sleep(2)
    if not pid or "org.libreoffice.androidlib.LOActivity" not in activities:
        raise RuntimeError("Native LOActivity did not remain foreground for the SAF fault fixture")
    (evidence / "fault-provider-editor-activity.txt").write_text(activities, encoding="utf-8")
    (evidence / "fault-provider-editor-screen.png").write_bytes(
        adb("exec-out", "screencap", "-p", binary=True))

    port = 9223
    adb("forward", f"tcp:{port}", f"localabstract:webview_devtools_remote_{pid}")
    try:
        editor.enter_edit_mode(evidence)
        canvas = editor.tap_document_canvas(evidence)
        cursor = editor.evaluate_on_real_editor(port, editor.GO_TO_END_EXPRESSION)
        if cursor.get("issued") is not True:
            raise RuntimeError("Writer could not place the cursor: " + json.dumps(cursor))
        time.sleep(0.5)
        inserted = editor.evaluate_on_real_editor(port, editor.EDIT_EXPRESSION)
        if inserted.get("issued") is not True:
            raise RuntimeError("Writer rejected QA sentinel insertion: " + json.dumps(inserted))
        time.sleep(1)
        save = editor.evaluate_on_real_editor(port, editor.SAVE_EXPRESSION)
        if save.get("issued") is not True:
            raise RuntimeError("Native Writer save request was not accepted: " + json.dumps(save))
        (evidence / "fault-provider-edit-receipt.json").write_text(
            json.dumps({"canvas": canvas, "cursor": cursor, "insert": inserted, "save": save},
                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        adb("forward", "--remove", f"tcp:{port}")

    # Wait for the actual native callback to reject the provider's truncated readback.
    deadline = time.monotonic() + timeout
    latest_log = ""
    while time.monotonic() < deadline:
        latest_log = adb("logcat", "-d", "-v", "time").decode("utf-8", errors="replace")
        if "QA_PROVIDER_TRUNCATED_WRITE_COMPLETE" in latest_log and \
                "AquaWord SAVE not acknowledged" in latest_log:
            break
        time.sleep(2)
    (evidence / "saf-fault-logcat.txt").write_text(latest_log, encoding="utf-8")
    if "QA_PROVIDER_TRUNCATED_WRITE_COMPLETE" not in latest_log:
        raise AssertionError("Fault provider did not complete its deliberate truncated write")
    # The native callback logs the failed readback path (not the
    # separate "not written" branch) because the provider accepted the pipe
    # but persisted a truncated document. Both markers must be present.
    failure_markers = (
        "AquaWord post-save recovery or writeback failed",
        "SAF provider readback checksum/size mismatch",
    )
    missing_markers = [marker for marker in failure_markers if marker not in latest_log]
    if missing_markers:
        raise AssertionError(
            "AquaWord did not reject the truncated provider readback; missing log evidence: "
            + repr(missing_markers)
        )

    adb("shell", "am", "force-stop", PKG)
    time.sleep(2)
    truncated = adb("exec-out", "run-as", PROVIDER_PKG, "cat", "files/qa.docx", binary=True)
    (evidence / "provider-truncated.docx").write_bytes(truncated)
    (evidence / "provider-truncated-sha256.txt").write_text(
        hashlib.sha256(truncated).hexdigest() + "\n", encoding="utf-8")
    if len(truncated) != KEEP_BYTES or zipfile.is_zipfile(io.BytesIO(truncated)):
        raise AssertionError(
            f"Fault injection did not leave the expected invalid {KEEP_BYTES}-byte DOCX prefix; "
            f"got {len(truncated)} bytes")

    recovery_name, recovered = latest_recovery_with_sentinel(evidence)
    recovery_sha = hashlib.sha256(recovered).hexdigest()
    (evidence / "saf-fault-result.json").write_text(json.dumps({
        "result": "PASS",
        "runtime": "Android 15 API 35 x86_64 with translated ARM64 native engine",
        "provider": PROVIDER_URI,
        "original_docx_sha256": original_sha,
        "provider_truncated_bytes": len(truncated),
        "provider_truncated_sha256": hashlib.sha256(truncated).hexdigest(),
        "recovery_snapshot": recovery_name,
        "recovery_docx_sha256": recovery_sha,
        "recovery_contains_sentinel": True,
        "save_acknowledged": False,
        "meaning": "Provider silently persisted only 128 bytes; AquaWord rejected the readback and retained the edited recovery DOCX."
    }, indent=2) + "\n", encoding="utf-8")
    print("PASS: silent SAF truncation was rejected; edited DOCX recovery bytes survived.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    run(args.evidence_dir, args.timeout)
