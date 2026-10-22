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


def patch_focus_bootstrap(path: Path) -> bool:
    """Install an accessible native-only focus toggle after app.map is initialized."""
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_FOCUS_BOOTSTRAP_BEGIN'
    snippet = require(ROOT/'branding/focus_mode.js').read_text(encoding='utf-8').strip()
    if marker in body:
        if snippet not in body:
            raise PatchError('Existing focus bootstrap differs from checked-in source')
        return False
    anchor = "window.addEventListener('beforeunload', function () {"
    if body.count(anchor) != 1:
        raise PatchError('Upstream main.js bootstrap anchor changed')
    block = ('/* AQUAWORD_FOCUS_BOOTSTRAP_BEGIN */\n' + snippet +
             '\n/* AQUAWORD_FOCUS_BOOTSTRAP_END */\n\n')
    return store(path, body.replace(anchor, block + anchor, 1))


def patch_focus_styles(path: Path) -> bool:
    """Hide editor chrome only while focus mode is on, never the canvas."""
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_FOCUS_CSS_BEGIN'
    snippet = require(ROOT/'branding/focus_mode.css').read_text(encoding='utf-8').strip()
    if marker in body:
        if snippet not in body:
            raise PatchError('Existing focus CSS differs from checked-in source')
        return False
    return store(path, body.rstrip() + '\n\n' + snippet + '\n')

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


def patch_history_menu(path: Path) -> bool:
    original = '<item android:id="@+id/action_open_file"'
    marker = 'AQUAWORD_HISTORY_MENU'
    content = require(path).read_text(encoding='utf-8')
    if marker in content: return False
    if content.count(original) != 1: raise PatchError('Upstream menu anchor changed')
    injected = '''<!-- AQUAWORD_HISTORY_MENU -->
    <item android:id="@+id/action_aquaword_history"
        android:title="@string/aquaword_safety_copies"
        app:showAsAction="never"/>
    '''
    return store(path, content.replace(original, injected + original))

def patch_history_strings(path: Path) -> bool:
    content = require(path).read_text(encoding='utf-8')
    if 'name="aquaword_safety_copies"' in content: return False
    if content.count('</resources>') != 1: raise PatchError('Upstream strings.xml unexpected format')
    additions = '''    <!-- AquaWord local pre-edit recovery -->
    <string name="aquaword_safety_copies">Safety copies</string>
    <string name="aquaword_creating_safety_copy">Saving a safety copy before editing…</string>
    <string name="aquaword_copy_failed">Safety copy could not be created</string>
    <string name="aquaword_copy_failed_body">The original file can still be opened, but editing without a safety copy could risk losing previous content.</string>
    <string name="aquaword_open_anyway">Open without backup</string>
    <string name="aquaword_no_copies">No safety copies yet. A copy is created before opening a document for editing.</string>
    <string name="aquaword_choose_snapshot">Choose a copy to restore as a new document</string>
    <string name="aquaword_restore_success">Safety copy restored to a new file</string>
    <string name="aquaword_restore_failure">Could not restore the selected safety copy</string>
'''
    return store(path, content.replace('</resources>', additions + '</resources>'))

def patch_history_activity(path: Path) -> bool:
    content = require(path).read_text(encoding='utf-8')
    if 'AQUAWORD_PREEDIT_COPY' in content:
        return False
    field = '    private static final int OPEN_FILE_REQUEST_CODE = 43;'
    if content.count(field) != 1: raise PatchError('Upstream activity field anchor changed')
    content = content.replace(field, field + '''
    // AQUAWORD_PREEDIT_COPY: recoverable pre-edit copies, not continuous autosave.
    private static final int AQUAWORD_RESTORE_REQUEST_CODE = 4477;
    private AquaWordHistory.Snapshot pendingAquaWordRestore;
''')
    original = '''        addDocumentToRecents(uri);

        Intent i = getIntentToEdit(uri);
        startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);'''
    replacement = '''        addDocumentToRecents(uri);

        final Intent i = getIntentToEdit(uri);
        final String name = RecentFilesAdapter.getUriFilename(this, uri);
        final AlertDialog progress = new AlertDialog.Builder(this)
                .setTitle(R.string.aquaword_safety_copies)
                .setMessage(R.string.aquaword_creating_safety_copy)
                .setCancelable(false).create();
        progress.show();
        new Thread(() -> {
            String problem = null;
            try (InputStream data = getContentResolver().openInputStream(uri)) {
                AquaWordHistory.capture(getFilesDir(), data, name);
            } catch (Exception failure) {
                problem = failure.getMessage() == null ? failure.getClass().getSimpleName() : failure.getMessage();
            }
            final String message = problem;
            runOnUiThread(() -> {
                progress.dismiss();
                if (isFinishing() || isDestroyed()) return;
                if (message == null) {
                    startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);
                } else {
                    new AlertDialog.Builder(this)
                        .setTitle(R.string.aquaword_copy_failed)
                        .setMessage(getString(R.string.aquaword_copy_failed_body) + "\\\\n" + message)
                        .setPositiveButton(R.string.aquaword_open_anyway,
                            (dialog, which) -> startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE))
                        .setNegativeButton(android.R.string.cancel, null)
                        .show();
                }
            });
        }, "AquaWordSafetyCopy").start();'''
    if content.count(original) != 1: raise PatchError('Upstream editor open() anchor changed')
    content = content.replace(original, replacement)
    menu = '''        if (item.getItemId() == R.id.action_open_file) {
            openDocument();
            return true;
        }'''
    if content.count(menu) != 1: raise PatchError('Upstream menu handling anchor changed')
    content = content.replace(menu, menu + '''
        if (item.getItemId() == R.id.action_aquaword_history) {
            showAquaWordHistory();
            return true;
        }''')
    before = '    /** File name extensions for which an empty document template is bundled in the assets. */'
    if content.count(before) != 1: raise PatchError('Upstream insertion anchor changed')
    methods = '''    /** Lists app-private pre-edit safety copies; restore always creates a new file. */
    private void showAquaWordHistory() {
        final List<AquaWordHistory.Snapshot> snapshots;
        try {
            snapshots = AquaWordHistory.list(getFilesDir());
        } catch (IOException failure) {
            Toast.makeText(this, R.string.aquaword_restore_failure, Toast.LENGTH_LONG).show();
            return;
        }
        if (snapshots.isEmpty()) {
            Toast.makeText(this, R.string.aquaword_no_copies, Toast.LENGTH_LONG).show();
            return;
        }
        final String[] names = new String[snapshots.size()];
        final java.text.DateFormat timeFormat = java.text.DateFormat.getDateTimeInstance();
        for (int n = 0; n < snapshots.size(); ++n) {
            AquaWordHistory.Snapshot snapshot = snapshots.get(n);
            names[n] = snapshot.displayName + " — " +
                timeFormat.format(new java.util.Date(snapshot.createdMillis));
        }
        new AlertDialog.Builder(this)
            .setTitle(R.string.aquaword_choose_snapshot)
            .setItems(names, (dialog, which) -> {
                pendingAquaWordRestore = snapshots.get(which);
                Intent destination = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                destination.addCategory(Intent.CATEGORY_OPENABLE);
                final String lowerName = pendingAquaWordRestore.displayName.toLowerCase(java.util.Locale.ROOT);
                if (lowerName.endsWith(".docx")) {
                    destination.setType("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
                } else if (lowerName.endsWith(".odt")) {
                    destination.setType("application/vnd.oasis.opendocument.text");
                } else if (lowerName.endsWith(".rtf")) {
                    destination.setType("application/rtf");
                } else if (lowerName.endsWith(".txt")) {
                    destination.setType("text/plain");
                } else {
                    destination.setType("application/octet-stream");
                }
                destination.putExtra(Intent.EXTRA_TITLE, pendingAquaWordRestore.displayName);
                startActivityForResult(destination, AQUAWORD_RESTORE_REQUEST_CODE);
            })
            .setNegativeButton(android.R.string.cancel, null)
            .show();
    }

'''
    content = content.replace(before, methods + before)
    activity_result = '''        switch (requestCode) {
            case LO_ACTIVITY_REQUEST_CODE: {'''
    restore = '''        switch (requestCode) {
            case AQUAWORD_RESTORE_REQUEST_CODE: {
                final AquaWordHistory.Snapshot item = pendingAquaWordRestore;
                pendingAquaWordRestore = null;
                if (resultCode != RESULT_OK || data == null || item == null || data.getData() == null)
                    break;
                final Uri target = data.getData();
                new Thread(() -> {
                    boolean success;
                    try (OutputStream output = getContentResolver().openOutputStream(target, "w")) {
                        AquaWordHistory.restore(item, output);
                        success = true;
                    } catch (Exception failure) {
                        Log.e(LOGTAG, "AquaWord safety copy restore failed", failure);
                        success = false;
                    }
                    final boolean finished = success;
                    runOnUiThread(() -> {
                        if (!isFinishing() && !isDestroyed())
                            Toast.makeText(this, finished ? R.string.aquaword_restore_success :
                                R.string.aquaword_restore_failure, Toast.LENGTH_LONG).show();
                    });
                }, "AquaWordRestore").start();
                break;
            }
            case LO_ACTIVITY_REQUEST_CODE: {'''
    if content.count(activity_result) != 1: raise PatchError('Upstream onActivityResult switch changed')
    content = content.replace(activity_result, restore)
    return store(path, content)

def copy_arabic_recovery_strings(repo: Path) -> bool:
    src = require(ROOT/'branding/aquaword_strings_ar.xml')
    target = repo/'android/app/src/main/res/values-ar/aquaword_strings.xml'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        if target.read_bytes() == src.read_bytes(): return False
        raise PatchError('Conflicting upstream AquaWord Arabic resources')
    shutil.copyfile(src, target)
    return True

def copy_history_source(repo: Path) -> bool:
    src = require(ROOT/'history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java')
    target = repo/'android/app/src/main/java/org/libreoffice/androidapp/ui/AquaWordHistory.java'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        if target.read_bytes() == src.read_bytes(): return False
        raise PatchError('Conflicting pre-existing AquaWordHistory.java in upstream')
    shutil.copyfile(src, target)
    return True

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
        repo/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java',
        repo/'android/app/src/main/res/menu/view_menu.xml',
        repo/'android/app/src/main/res/values/strings.xml',
        repo/'browser/src/main.js',
        repo/'browser/css/toolbar.css'
    ]
    for item in targets:
        require(item)
    print('Notebookbar style:', append_css(targets[0], ROOT/'branding/notebookbar.aurora.css'))
    print('Mobile style:', append_css(targets[1], ROOT/'branding/mobilewizard.aurora.css'))
    print('Focus bootstrap:', patch_focus_bootstrap(targets[8]))
    print('Focus styles:', patch_focus_styles(targets[9]))
    print('Android display name:', patch_gradle_labels(targets[2]))
    print('App icon:', patch_manifest_icon(targets[3]))
    print('App ID:', patch_app_settings_template(targets[4]))
    print('Writer-only new-document flow:', patch_writer_only_home(targets[5]))
    print('Safety copy menu:', patch_history_menu(targets[6]))
    print('Safety copy strings:', patch_history_strings(targets[7]))
    print('Safety copy activity:', patch_history_activity(targets[5]))
    print('History storage class:', copy_history_source(repo))
    print('Arabic recovery resources:', copy_arabic_recovery_strings(repo))
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
