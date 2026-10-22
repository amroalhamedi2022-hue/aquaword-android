#!/usr/bin/env python3
"""Probe the REAL AquaWord/Collabora Android WebView with Chrome DevTools.

Use only on a debuggable APK, after the Arabic DOCX was opened through a
writable content:// grant. Launching an Android Activity is not enough:
the editor must load a Writer document and create the real document layer.
No mock responses or synthetic screenshots are accepted.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

EXPRESSION = r"""(() => {
    const map = window.app && window.app.map;
    const layer = map && map._docLayer;
    return JSON.stringify({
        path: location.pathname,
        docType: map && typeof map.getDocType === 'function' ? map.getDocType() : null,
        documentLayer: !!layer,
        documentContainer: !!document.getElementById('document-container'),
        mapCanvas: !!document.getElementById('map'),
        focusControl: !!document.getElementById('aquaword-focus-toggle'),
        renderedPageNodes: document.querySelectorAll('#document-container canvas, #document-container svg, #document-container .leaflet-tile').length
    });
})()"""

def result_from_response(response):
    if "error" in response:
        raise RuntimeError("WebView CDP call failed: " + str(response["error"]))
    value = response.get("result", {}).get("result", {}).get("value")
    if not isinstance(value, str):
        raise ValueError("No JSON result from editor JavaScript; loaded page unverified")
    return json.loads(value)


def proves_writer_ready(values):
    return (values.get("docType") == "text"
            and values.get("documentLayer") is True
            and values.get("documentContainer") is True
            and values.get("mapCanvas") is True
            and values.get("focusControl") is True)


def shell(command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


def inspect_webview(port, timeout_s):
    import websocket
    deadline = time.monotonic() + timeout_s
    attempts = []
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as response:
                pages = json.load(response)
            pages = [p for p in pages if p.get("type") == "page"
                     and p.get("webSocketDebuggerUrl")]
            for page in pages:
                ws_url = page["webSocketDebuggerUrl"]
                # WebView debugging endpoints are private loopback forwarded by ADB.
                socket = websocket.create_connection(
                    ws_url, timeout=5, suppress_origin=True)
                try:
                    socket.send(json.dumps({
                        "id": 41, "method": "Runtime.evaluate",
                        "params": {"expression": EXPRESSION, "returnByValue": True}
                    }))
                    while True:
                        payload = json.loads(socket.recv())
                        if payload.get("id") == 41:
                            result = result_from_response(payload)
                            attempts.append(result)
                            if proves_writer_ready(result):
                                return result, attempts
                            break
                finally:
                    socket.close()
        except (OSError, URLError, RuntimeError, ValueError) as exc:
            attempts.append({"diagnostic": str(exc)})
        time.sleep(3)
    raise TimeoutError("Real Collabora Writer document layer never became ready: " +
                       json.dumps(attempts[-6:], ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default="com.aquaword.app.debug")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=80)
    parser.add_argument("--port", type=int, default=9222)
    args = parser.parse_args()

    pid = shell(["adb", "shell", "pidof", args.package]).split()[0]
    endpoint = f"localabstract:webview_devtools_remote_{pid}"
    shell(["adb", "forward", f"tcp:{args.port}", endpoint])
    try:
        evidence, _ = inspect_webview(args.port, args.timeout)
    finally:
        subprocess.run(["adb", "forward", "--remove", f"tcp:{args.port}"],
                       check=False, stdout=subprocess.DEVNULL)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("PASS: real Writer WebView document layer confirmed:", evidence)


if __name__ == "__main__":
    main()
