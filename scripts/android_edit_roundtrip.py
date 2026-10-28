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
CLICK_EDIT_EXPRESSION = r"""(() => {
    const editor = window.app && window.app.map;
    if (!editor || editor.getDocType() !== 'text' || !editor._docLayer) {
        return JSON.stringify({target: false, issued: false, reason: 'Writer edit layer unavailable'});
    }
    // Collabora's real mobile view-mode control. Do not send UNO edits while
    // the document is still read-only: those commands can be silently ignored.
    const button = document.getElementById('mobile-edit-button');
    if (!button) {
        return JSON.stringify({target: true, issued: false,
            reason: 'Collabora mobile edit button #mobile-edit-button not found'});
    }
    const style = getComputedStyle(button);
    const visible = style.display !== 'none' && style.visibility !== 'hidden' &&
                    button.getClientRects().length > 0;
    if (!visible) {
        return JSON.stringify({target: true, issued: false,
            reason: 'Collabora mobile edit button is not visible',
            display: style.display, visibility: style.visibility,
            outerHTML: button.outerHTML.slice(0, 500)});
    }
    button.click();
    return JSON.stringify({target: true, issued: true,
        editButtonClicked: true, buttonId: button.id});
})()"""

EDIT_EXPRESSION = r"""(() => {
    const editor = window.app && window.app.map;
    if (!editor || editor.getDocType() !== 'text' ||
        !editor._docLayer || typeof editor.sendUnoCommand !== 'function') {
        return JSON.stringify({target: false, issued: false, reason: 'Writer edit layer unavailable'});
    }
    editor.sendUnoCommand('.uno:GoToEndOfDoc');
    editor.sendUnoCommand('.uno:InsertText', {
        Text: {type: 'string', value: 'AQUAWORD_ANDROID_SAVE_ROUNDTRIP_2026'}
    });
    editor.sendUnoCommand('.uno:Save');
    return JSON.stringify({target: true, issued: true, commands: ['GoToEndOfDoc', 'InsertText', 'Save']});
})()"""

# Backward-compatible name used by existing source contract tests.
EXPRESSION = EDIT_EXPRESSION


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


def evaluate_on_real_editor(port: int, expression: str) -> dict:
    """Evaluate one expression only on the live Collabora Writer document page."""
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
                    "params": {"expression": expression, "returnByValue": True}}))
            while True:
                message = json.loads(sock.recv())
                if message.get("id") != 77:
                    continue
                if message.get("exceptionDetails"):
                    raise RuntimeError("Writer JavaScript execution failed: " + str(message))
                value = message.get("result", {}).get("result", {}).get("value")
                if isinstance(value, str):
                    obj = json.loads(value)
                    if obj.get("target") is False:
                        break
                    return obj
                break
        finally:
            sock.close()
    raise RuntimeError("No live Collabora Writer document layer was found")


def native_edit_mode_confirmed(logcat: str) -> bool:
    """Return true only when native LOActivity explicitly reports edit mode."""
    states = [
        line for line in logcat.splitlines()
        if "postMobileMessage:" in line
        and ("EDITMODE" in line or "setviewreadonly" in line)
    ]
    if not states:
        return False
    latest = states[-1]
    return ("postMobileMessage: EDITMODE on" in latest
            or "setviewreadonly value=false" in latest)


def wait_for_edit_mode(timeout_s: int) -> str:
    """Wait for the native bridge confirmation after tapping the real edit button."""
    deadline = time.monotonic() + timeout_s
    last_log = ""
    while time.monotonic() < deadline:
        last_log = call("logcat", "-d", "-v", "time", "LOActivity:D", "*:S").decode(
            "utf-8", errors="replace")
        if native_edit_mode_confirmed(last_log):
            return last_log
        time.sleep(1)
    relevant = [
        line for line in last_log.splitlines()
        if "postMobileMessage:" in line
        and ("EDITMODE" in line or "setviewreadonly" in line)
    ]
    raise RuntimeError(
        "Native Writer did not confirm edit mode after tapping #mobile-edit-button; "
        "last mode messages: " + " | ".join(relevant[-8:])
    )

def enter_edit_mode(directory: Path) -> None:
    """Tap Collabora's real mobile edit button and require native confirmation."""
    display = call("shell", "wm", "size").decode("utf-8", errors="replace")
    sizes = re.findall(r"(\d+)x(\d+)", display)
    if not sizes:
        raise RuntimeError("Android runtime did not report a usable screen geometry")
    width, height = (int(value) for value in sizes[-1])
    if width < 480 or height < 640:
        raise RuntimeError(f"Android runtime viewport is too small for Writer acceptance: {width}x{height}")
    (directory/"edit-mode-screen-geometry.txt").write_text(
        f"{width}x{height}\n{display}\n", encoding="utf-8")

    # Startup emits EDITMODE off/read-only. Clear it so only the response to
    # the actual user-equivalent click can satisfy the edit-mode gate.
    call("logcat", "-c")
    clicked = evaluate_on_real_editor(9223, CLICK_EDIT_EXPRESSION)
    (directory/"edit-button-click.json").write_text(
        json.dumps(clicked, indent=2)+"\n", encoding="utf-8")
    if clicked.get("issued") is not True or clicked.get("editButtonClicked") is not True:
        raise RuntimeError("Could not activate Collabora edit mode: " +
                           json.dumps(clicked, ensure_ascii=False))
    mode_log = wait_for_edit_mode(25)
    mode_lines = [
        line for line in mode_log.splitlines()
        if "postMobileMessage:" in line
        and ("EDITMODE" in line or "setviewreadonly" in line)
    ]
    (directory/"edit-mode-confirmation.txt").write_text(
        "\n".join(mode_lines[-12:])+"\n", encoding="utf-8")


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
    try:
        enter_edit_mode(directory)
        issued = evaluate_on_real_editor(port, EDIT_EXPRESSION)
        (directory/"edit-command.json").write_text(
            json.dumps(issued, indent=2)+"\n", encoding="utf-8")
        if issued.get("issued") is not True:
            raise RuntimeError("Writer edit layer rejected UNO commands: " +
                               json.dumps(issued, ensure_ascii=False))
    finally:
        subprocess.run(["adb", "forward", "--remove", f"tcp:{port}"],
                       stdout=subprocess.DEVNULL, check=False)

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
