#!/usr/bin/env python3
"""Apply AquaWord visual and package overlay to pinned native Collabora Android source.

Two phases: 'source' before upstream configure and 'postconfigure' after.
Does not build the engine or implement unsupported Word features.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
BEGIN = 'AQUAWORD_AURORA_BEGIN'
APP_ID = 'com.aquaword.app'
PINNED_SHA = '2333344185931274f9c49d6c12a408cefcef6844'

class PatchError(RuntimeError):
    pass

def require(path: Path) -> Path:
    if not path.is_file():
        raise PatchError(f'Missing expected upstream path: {path}')
    return path

def store(path: Path, content: str) -> bool:
    current = require(path).read_text(encoding='utf-8')
    if current == content:
        return False
    path.write_text(content, encoding='utf-8')
    return True

def append_css(target: Path, skin: Path) -> bool:
    original = require(target).read_text(encoding='utf-8')
    block = require(skin).read_text(encoding='utf-8').strip()
    if original.count(BEGIN) > 1:
        raise PatchError(f'Duplicate AquaWord CSS marker: {target}')
    if BEGIN in original:
        if block not in original:
            raise PatchError(f'AquaWord CSS mismatch: {target}')
        return False
    return store(target, original.rstrip() + '\n\n' + block + '\n')

def patch_app_settings_template(path: Path) -> bool:
    original = "applicationId '@APP_PACKAGE_NAME@'"
    branded = "applicationId '" + APP_ID + "'"
    content = require(path).read_text(encoding='utf-8')
    if content.count(original) == 1:
        content = content.replace(original, branded)
    elif content.count(branded) != 1:
        raise PatchError(f'Unexpected appSettings template: {path}')
    return store(path, content)

def patch_gradle_labels(path: Path) -> bool:
    content = require(path).read_text(encoding='utf-8')
    variable = '$' + '{coAppName}'
    for original, branded in [
        ('resValue "string", "app_name", "' + variable + '"',
         'resValue "string", "app_name", "AquaWord"'),
        ('resValue "string", "app_name", "' + variable + ' Debug"',
         'resValue "string", "app_name", "AquaWord Debug"'),
    ]:
        if content.count(original) == 1:
            content = content.replace(original, branded)
        elif content.count(branded) != 1:
            raise PatchError(f'Unexpected Gradle label format: {path}')
    return store(path, content)

def patch_manifest_icon(path: Path) -> bool:
    original = 'android:icon="' + '$' + '{appIcon}"'
    branded = 'android:icon="@mipmap/aquaword_launcher"'
    content = require(path).read_text(encoding='utf-8')
    if content.count(original) == 1:
        content = content.replace(original, branded)
    elif content.count(branded) != 1:
        raise PatchError(f'Unexpected manifest icon format: {path}')
    return store(path, content)


def patch_writer_only_home(path: Path) -> bool:
    """AquaWord's New document FAB opens the native Writer flow directly.

    Avoids advertising Calc/Impress creation in a Word-specific editor.
    """
    original = """editFAB.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                if (isFabMenuOpen)
                    collapseFabMenu();
                else
                    expandFabMenu();
            }
        });"""
    branded = """// AQUAWORD_WRITER_ONLY_NEW
        editFAB.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                createNewFileInputDialog(getString(R.string.new_textdocument)
                    + FileUtilities.DEFAULT_WRITER_EXTENSION, "*/*", CREATE_DOCUMENT_REQUEST_CODE);
            }
        });"""
    content = require(path).read_text(encoding='utf-8')
    if content.count(original) == 1:
        content = content.replace(original, branded)
    elif content.count(branded) != 1:
        raise PatchError(f'Unexpected Android New-document handler: {path}')
    return store(path, content)

def copy_icons(repo: Path) -> int:
    icons = list(sorted((ROOT / 'branding/icons').rglob('aquaword_launcher.png')))
    if len(icons) != 5:
        raise PatchError('Run python3 scripts/make_icons.py first; expected 5 PNG icon sizes')
    count = 0
    for icon in icons:
        destination = repo / 'android/app/src/main/res' / icon.parent.name / icon.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.read_bytes() != icon.read_bytes():
            shutil.copyfile(icon, destination)
            count += 1
    return count

def validate_repo(repo: Path) -> None:
    if not repo.is_dir() or not (repo/'engine').is_dir() or not (repo/'browser').is_dir():
        raise PatchError('Expected native Collabora monorepo, including engine/ and browser/')

def source(repo: Path) -> None:
    targets = [
        repo/'browser/css/notebookbar.css',
        repo/'browser/css/mobilewizard.css',
        repo/'android/app/build.gradle',
        repo/'android/app/src/main/AndroidManifest.xml',
        repo/'android/app/appSettings.gradle.in',
        repo/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
    ]
    for item in targets:
        require(item)
    print('Notebookbar style:', append_css(targets[0], ROOT/'branding/notebookbar.aurora.css'))
    print('Mobile style:', append_css(targets[1], ROOT/'branding/mobilewizard.aurora.css'))
    print('Android display name:', patch_gradle_labels(targets[2]))
    print('App icon:', patch_manifest_icon(targets[3]))
    print('App ID:', patch_app_settings_template(targets[4]))
    print('Writer-only new-document flow:', patch_writer_only_home(targets[5]))
    print('Icons copied:', copy_icons(repo))

def configured(repo: Path) -> None:
    file = require(repo/'android/app/appSettings.gradle')
    text = file.read_text(encoding='utf-8')
    if text.count("applicationId '" + APP_ID + "'") != 1:
        raise PatchError('Configured appSettings.gradle is not using AquaWord application ID')
    if '@APP_' in text or '@ANDROID_' in text:
        raise PatchError('Unexpanded autotools tokens remain after configure')
    gradle = require(repo/'android/app/build.gradle').read_text(encoding='utf-8')
    if 'resValue "string", "app_name", "AquaWord"' not in gradle:
        raise PatchError('Missing AquaWord Gradle display name')
    print('Configured Android app ID verified:', APP_ID)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path)
    p.add_argument('--phase', required=True, choices=('source','postconfigure'))
    args = p.parse_args()
    repo = args.repo.resolve()
    validate_repo(repo)
    if args.phase == 'source':
        source(repo)
    else:
        configured(repo)
    print('Overlay checks passed. Actual native build and device validation remain separate.')

if __name__ == '__main__':
    try:
        main()
    except PatchError as exc:
        sys.exit('AquaWord overlay aborted: ' + str(exc))
