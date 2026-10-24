#!/usr/bin/env python3
"""Generate the approved AquaWord launcher icon at each Android density.

The source is the AquaWord document-and-pen tile from the approved six-icon
brand board (with its existing wordmark preserved). No drawings are recreated.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'branding/icons'
SOURCE = ROOT / 'aquaword_launcher_source.webp'
DENSITIES = {
    'mipmap-mdpi': 48,
    'mipmap-hdpi': 72,
    'mipmap-xhdpi': 96,
    'mipmap-xxhdpi': 144,
    'mipmap-xxxhdpi': 192,
}

def make(size):
    if not SOURCE.is_file():
        raise FileNotFoundError(f'Missing approved AquaWord brand icon: {SOURCE}')
    with Image.open(SOURCE) as original:
        if original.size != (512, 512):
            raise ValueError(f'AquaWord source icon must be 512×512: {original.size}')
        return original.convert('RGBA').resize(
            (size, size), Image.Resampling.LANCZOS
        )

def generate():
    for name, size in DENSITIES.items():
        path = ROOT / name / 'aquaword_launcher.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        make(size).save(path)
        print(path)

if __name__ == '__main__':
    generate()
