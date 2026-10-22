#!/usr/bin/env python3
"""Prove that Android rendered an interactive UI, not only a splash screen.

uiautomator dump may return a hierarchy with one ImageView on a loading
screen. We demand multiple distinct accessible labels and interactive nodes.
This is OS-level evidence only; not a claim AquaWord's buttons work.
"""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET


def verify_ui(path: Path, min_labels: int = 4) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    nodes = root.findall(".//node")
    labels = {
        val.strip()
        for node in nodes
        for key in ("text", "content-desc")
        if (val := node.get(key, "")).strip()
    }
    interactive = [n for n in nodes if n.get("clickable") == "true" or
                   n.get("scrollable") == "true"]
    if len(labels) < min_labels or not interactive:
        raise ValueError(
            f"Unready/splash UI: labels={len(labels)} interactive={len(interactive)}")
    print(f"Rendered interactive Android UI: {len(nodes)} nodes, "
          f"{len(labels)} labeled elements, {len(interactive)} interactive nodes")
    return len(labels), len(interactive)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("xml", type=Path)
    p.add_argument("--min-labels", type=int, default=4)
    args = p.parse_args()
    verify_ui(args.xml, args.min_labels)
