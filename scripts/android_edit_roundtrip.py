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
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen
from docx import Document

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
    return SENTINEL in text


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


def run(directory: Path, timeout: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    pid = call("shell", "pidof", PKG).decode().split()[0]
    port=9223
    call("forward", f"tcp:{port}", f"localabstract:webview_devtools_remote_{pid}")
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
