#!/usr/bin/env python3
"""Real Android Writer edit -> save -> DOCX persistence verification.

STRICT QA: Runs only on a debuggable emulator APK and app-owned fixture document.
Never mutates real user files. Uses Collabora's UNO editor commands, then reads
the bytes SAVED BY ANDROID from the debug FileProvider destination.

This is a release-blocking test when included in the workflow; no silent skip.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen
from docx import Document
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quality"))
from check_rich_docx import validate_document

PKG = "com.aquaword.app.debug"
FILE = "files/aquaword-research-ar.docx"
SENTINEL = "AQUAWORD_ANDROID_SAVE_ROUNDTRIP_2026"

# Sending a UNO command is not proof that it actually changed or saved a file.
EXPRESSION = r"""(() => {
    const editor = window.app && window.app.map;
    if (!editor || editor.getDocType() !== 'text' ||
        !editor._docLayer || typeof editor.sendUnoCommand !== 'function') {
        return JSON.stringify({issued: false, reason: 'Writer edit layer unavailable'});
    }
    editor.sendUnoCommand('.uno:GoToEndOfDoc');
    editor.sendUnoCommand('.uno:InsertText', {
        Text: {type: 'string', value: 'AQUAWORD_ANDROID_SAVE_ROUNDTRIP_2026'}
    });
    editor.sendUnoCommand('.uno:Save');
    return JSON.stringify({issued: true});
})()"""


def check_document(payload: bytes) -> bool:
    """Read the produced DOCX package; don't accept a screenshot or file SHA alone."""
    doc = Document(io.BytesIO(payload))
    text = "\n".join(p.text for p in doc.paragraphs)
    if SENTINEL not in text:
        return False
    # Presence of the inserted marker is insufficient if original tables,
    # images, Arabic bidirectionality, or second-page content were lost.
    validate_document(payload, require_saved_text=SENTINEL)
    return True


def call(*args, binary=False):
    result = subprocess.check_output(
        ["adb", *args],
        stderr=None if binary else subprocess.STDOUT)
    # Binary stdout must not be polluted with warnings from adb stderr.
    # Never strip potentially valid trailing bytes from a DOCX ZIP package.
    return result if binary else result.strip()


def evaluate_on_real_editor(port: int) -> dict:
    import websocket
    with urlopen(f"http://127.0.0.1:{port}/json", timeout=5) as response:
        pages = json.load(response)
    pages = [p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")]
    if not pages:
        raise RuntimeError("Android WebView debugging exposed no Collabora editor page")
    for page in pages:
        sock = websocket.create_connection(page["webSocketDebuggerUrl"],
                                           timeout=10, suppress_origin=True)
        try:
            sock.send(json.dumps({"id": 77, "method": "Runtime.evaluate",
                    "params": {"expression": EXPRESSION, "returnByValue": True}}))
            while True:
                message = json.loads(sock.recv())
                if message.get("id") != 77:
                    continue
                if message.get("exceptionDetails"):
                    raise RuntimeError("UNO JavaScript execution failed: " + str(message))
                value = message.get("result", {}).get("result", {}).get("value")
                if isinstance(value, str):
                    obj = json.loads(value)
                    if obj.get("issued") is True:
                        return obj
                break
        finally:
            sock.close()
    raise RuntimeError("Unable to send real Writer UNO edit/save commands")


def enter_edit_mode(directory: Path) -> None:
    """Tap the real Writer Edit FAB and require an explicit edit-mode transition.

    The QA flow intentionally opens a document in Viewing mode first. Issuing
    UNO commands while read-only can look successful at the CDP layer but does
    not mutate the DOCX, so never treat the command receipt as edit acceptance.
    The viewport has already been set to the 16:10 tablet geometry by the
    parent smoke script; keep a portrait fallback for diagnostic reruns.
    """
    size_output = call("shell", "wm", "size").decode("utf-8", errors="replace")
    dimensions = re.findall(r"(\d+)x(\d+)", size_output)
    if not dimensions:
        raise RuntimeError("Cannot determine current Android viewport for Edit FAB")
    width, height = map(int, dimensions[-1])
    if width > height:
        x, y = round(width * 0.965), round(height * 0.905)
    else:
        x, y = round(width * 0.888), round(height * 0.921)

    # Keep this evidence isolated to the explicit tap; the earlier smoke
    # script already saved the pre-edit editor logcat.
    call("logcat", "-c")
    call("shell", "input", "tap", str(x), str(y))
    time.sleep(3)
    (directory / "edit-mode-screen.png").write_bytes(
        call("exec-out", "screencap", "-p", binary=True))
    logs = call("logcat", "-d", "-v", "time").decode("utf-8", errors="replace")
    (directory / "edit-mode-logcat.txt").write_text(logs, encoding="utf-8")
    # Collabora's native bridge logs both signals on the real transition.
    markers = ("postMobileMessage: EDITMODE on", "setviewreadonly value=false")
    if not any(marker in logs for marker in markers):
        raise RuntimeError(
            f"Writer did not enter edit mode after tapping ({x},{y}) on {width}x{height}; "
            "no EDITMODE on / setviewreadonly=false evidence")
    (directory / "edit-mode-confirmation.txt").write_text(
        f"PASS: edit mode confirmed by native log after tap ({x},{y}) on {width}x{height}.\n",
        encoding="utf-8")


def run(directory: Path, timeout: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    # Keep proof that the marker did NOT already exist in the original file.
    original = call("exec-out", "run-as", PKG, "cat", FILE, binary=True)
    if check_document(original):
        raise RuntimeError("Fixture already contains QA edit text; this would be a false positive")
    original_checksum = hashlib.sha256(original).hexdigest()
    (directory/"original-docx-sha256.txt").write_text(
        original_checksum + "\n", encoding="utf-8")
    pid = call("shell", "pidof", PKG).decode().split()[0]
    port=9223
    call("forward", f"tcp:{port}", f"localabstract:webview_devtools_remote_{pid}")
    enter_edit_mode(directory)
    try:
        issued = evaluate_on_real_editor(port)
    finally:
        subprocess.run(["adb", "forward", "--remove", f"tcp:{port}"],
                       stdout=subprocess.DEVNULL, check=False)
    (directory/"edit-command.json").write_text(
        json.dumps(issued, indent=2)+"\n", encoding="utf-8")

    # Force the native lifecycle onPause save as a user would by switching apps.
    # This is in addition to the regular .uno:Save command above.
    call("shell", "input", "keyevent", "KEYCODE_HOME")

    deadline=time.monotonic()+timeout
    last_error=None
    while time.monotonic()<deadline:
        try:
            payload=call("exec-out","run-as",PKG,"cat",FILE,binary=True)
            if check_document(payload):
                if hashlib.sha256(payload).hexdigest() == original_checksum:
                    raise AssertionError("DOCX saved bytes did not change")
                (directory/"roundtrip-hash.txt").write_text(
                    hashlib.sha256(payload).hexdigest()+"\n", encoding="utf-8")
                (directory/"roundtrip-result.txt").write_text(
                    "PASS: actual Android app-owned DOCX contains inserted UNO text after save.\n",
                    encoding="utf-8")
                print("PASS: real Android Writer edit/save persisted to DOCX.")
                return
            last_error="Sentinel not present in saved DOCX"
        except Exception as failure:
            last_error=f"{type(failure).__name__}: {failure}"
        time.sleep(5)
    raise RuntimeError("Android save was not verified: " + str(last_error))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence-dir",type=Path,required=True)
    parser.add_argument("--timeout",type=int,default=75)
    args=parser.parse_args()
    run(args.evidence_dir,args.timeout)
