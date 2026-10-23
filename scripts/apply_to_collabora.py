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



def patch_native_save_checkpoints(path: Path) -> bool:
    """Back up the *actually saved* native document after the Writer SAVE event.

    The source identity and properties format are shared with the file-browser
    pre-edit safety copies, so a single History UI can restore either version.
    Opens the temp document stream before scheduling a worker to tolerate
    Activity shutdown; never blocks the main thread for the extra backup.
    """
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_NATIVE_SAVE_CHECKPOINT'
    if marker in body:
        if body.count('captureNativeSaveCheckpoint();') != 1:
            raise PatchError('Partial native save checkpoint integration')
        return False
    save_anchor = '''            case "SAVE":
                copyTempBackToIntent();
                sendBroadcast(messageAndParam[0], messageAndParam[1]);'''
    field_anchor = '    private boolean documentLoaded = false;'
    if body.count(save_anchor) != 1 or body.count(field_anchor) != 1:
        raise PatchError('Upstream native SAVE callback or LOActivity field anchor changed')
    method = '''    // AQUAWORD_NATIVE_SAVE_CHECKPOINT:
    // Store a recoverable revision after native Writer signals SAVE.
    // The previously captured pre-edit snapshot remains untouched.
    private void captureNativeSaveCheckpoint() {
        if (!isDocEditable || mTempFile == null || !mTempFile.isFile() ||
                mTempFile.length() <= 0L)
            return;
        final android.net.Uri original = getIntent().getData();
        if (original == null)
            return;
        final String sourceIdentity = original.toString();
        // SAF document ids are not always filenames (e.g. cloud providers).
        // Prefer the provider's actual display name for the recovery list.
        String candidateName = original.getLastPathSegment() == null ?
                "Document.docx" : original.getLastPathSegment();
        // Provider metadata may require cloud IPC/network I/O. Never query
        // it on the native SAVE callback before the actual SAF writeback.
        final String fallbackName = candidateName;
        final java.io.InputStream saved;
        try {
            // Hold an FD before Activity teardown; backup work is asynchronous.
            saved = new java.io.FileInputStream(mTempFile);
        } catch (java.io.IOException failure) {
            Log.e(TAG, "Cannot open saved Writer document for recovery", failure);
            return;
        }
        new Thread(() -> {
            // Keep slow/unavailable provider queries off the SAVE callback.
            // The already-open native temp FD is owned by this worker.
            try (java.io.InputStream stream = saved) {
                // AQUAWORD_LOCAL_RECOVERY_NAME: cloud metadata IPC must never
                // delay the only post-edit recovery snapshot. The pre-edit
                // checkpoint already stored the provider's display name.
                // Look it up from private metadata before copying the bytes.
                String name = AquaWordHistory.preferredDisplayName(
                        getFilesDir(), sourceIdentity, fallbackName);
                AquaWordHistory.capture(getFilesDir(), stream, name, sourceIdentity, "saved");
            } catch (Exception failure) {
                Log.e(TAG, "AquaWord post-save recovery checkpoint failed", failure);
            }
        }, "AquaWordNativeSaveCheckpoint").start();
    }

'''
    body = body.replace(field_anchor, method + field_anchor, 1)
    body = body.replace(save_anchor, '''            case "SAVE":
                // AQUAWORD_RECOVER_FAILED_SAF_SAVE: preserve the native
                // Writer temp document BEFORE a potentially destructive
                // provider write. A failed SAF copy must not lose the
                // post-edit recovery revision.
                captureNativeSaveCheckpoint();
                if (copyTempBackToIntent()) {
                    sendBroadcast(messageAndParam[0], messageAndParam[1]);
                } else {
                    Log.e(TAG, "AquaWord SAVE not acknowledged because the original document was not written");
                }''', 1)
    return store(path, body)



def patch_native_saf_saveback(path: Path) -> bool:
    """Make native Android document writeback errors visible and verifiable.

    Keep Collabora's existing resolved-file path. A failed/empty stream is never
    logged as successful. The separate post-save recovery copy remains available.
    """
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_NATIVE_SAF_SAVE_BACK'
    if marker in body:
        if 'SAF writeback failed' not in body:
            raise PatchError('Partial native SAF save patch')
        return False
    start = '    private void copyTempBackToIntent() {'
    end = '    /** Copy the temp file back to the document. */'
    if body.count(start) != 1 or body.count(end) != 1:
        raise PatchError('Upstream native SAF copy method changed')
    a = body.index(start)
    b = body.index(end, a)
    original = body[a:b]
    if ('copyThread.join();' not in original or
            'contentResolver.openOutputStream(uri, "wt")' not in original):
        raise PatchError('Upstream native copy semantics changed')
    # Native SAVE has two writeback paths. Both must report success truthfully.
    file_anchor = '    private void copyTempBackToFile() {'
    file_tail = '    private void reportSaveToFileFailed() {'
    if body.count(file_anchor) != 1:
        raise PatchError('Upstream direct-file writeback method changed')
    file_start = body.index(file_anchor)
    file_end = body.find('\n    /**', file_start + len(file_anchor))
    if file_end < 0 or file_end <= file_start:
        raise PatchError('Cannot determine native direct-file writeback boundary')
    direct = body[file_start:file_end]
    if ('newContent.renameTo(resolvedFile)' not in direct or
            'reportSaveToFileFailed();' not in direct or
            'MediaScannerConnection.scanFile' not in direct):
        raise PatchError('Upstream direct-file save semantics drifted')
    direct = direct.replace('private void copyTempBackToFile()', 'private boolean copyTempBackToFile()', 1)
    direct = direct.replace('            return;', '            return false;')
    # Successful copy and rename is the only path allowed to acknowledge SAVE.
    direct = direct.replace('            MediaScannerConnection.scanFile(this, new String[]{resolvedFile.getAbsolutePath()}, null, null);',
        '            MediaScannerConnection.scanFile(this, new String[]{resolvedFile.getAbsolutePath()}, null, null);\n            return true;', 1)
    direct = direct.replace('            reportSaveToFileFailed();\n        }',
        '            reportSaveToFileFailed();\n            return false;\n        }', 1)
    if ('return true;' not in direct or direct.count('return false;') < 3):
        raise PatchError('Could not make direct-file save report its completion state')
    replacement = '''    // AQUAWORD_NATIVE_SAF_SAVE_BACK: never silently report incomplete writes.
    private boolean copyTempBackToIntent() {
        if (!isDocEditable || mTempFile == null ||
                getIntent().getData() == null ||
                !ContentResolver.SCHEME_CONTENT.equals(getIntent().getData().getScheme()))
            return false;
        if (mResolvedFile != null) {
            return copyTempBackToFile();
        }
        final Uri destination = getIntent().getData();
        try (InputStream input = new FileInputStream(mTempFile)) {
            if (mTempFile.length() <= 0L)
                throw new IOException("Refusing to replace document with empty Writer temp file");
            // Android ContentResolver.openOutputStream(uri) is equivalent to
            // mode "w", which is NOT guaranteed to truncate existing content.
            // A shorter edited DOCX could retain stale trailing ZIP bytes.
            // Never silently fall back to ambiguous "w" on an existing file.
            // Try only explicitly truncating modes, otherwise fail the SAVE
            // and leave the post-edit recovery snapshot available.
            OutputStream opened;
            try {
                opened = getContentResolver().openOutputStream(destination, "wt");
            } catch (FileNotFoundException | UnsupportedOperationException noTruncateMode) {
                Log.w(TAG, "Provider rejected wt; trying explicit rwt truncate mode", noTruncateMode);
                opened = getContentResolver().openOutputStream(destination, "rwt");
            }
            if (opened == null)
                throw new IOException("Document provider returned no writable stream");
            long bytes = 0L;
            try (OutputStream output = opened) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (count > 0) {
                        output.write(buffer, 0, count);
                        bytes += count;
                    }
                }
                output.flush();
            }
            // Stream closed successfully before any success log.
            if (bytes != mTempFile.length())
                throw new IOException("SAF copy size differs from native saved document");
            Log.i(TAG, "AquaWord safely copied " + bytes + " bytes to the document provider");
            return true;
        } catch (Exception error) {
            Log.e(TAG, "AquaWord SAF writeback failed — recovery snapshot is retained", error);
            runOnUiThread(() -> {
                if (!isFinishing() && !isDestroyed())
                    Toast.makeText(this, R.string.failed_to_save_file, Toast.LENGTH_LONG).show();
            });
            return false;
        }
    }

'''
    # Insert both patched methods in a single transaction with anchored slices.
    with_file_patch = body[:file_start] + direct + body[file_end:]
    a = with_file_patch.index(start)
    b = with_file_patch.index(end, a)
    return store(path, with_file_patch[:a] + replacement + with_file_patch[b:])


def patch_periodic_native_autosave(path: Path) -> bool:
    """Use native save every 2 minutes while foreground editing.

    Existing upstream onPause save stays intact; lifecycle cancels callbacks.
    """
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_PERIODIC_NATIVE_AUTOSAVE'
    if marker in body:
        if 'mAquaWordSaveHandler.removeCallbacks(mAquaWordSaveTick);' not in body:
            raise PatchError('Partial periodic autosave integration')
        return False
    field_anchor = '    private boolean documentLoaded = false;'
    resume_anchor = '''    protected void onResume() {
        super.onResume();
        Log.i(TAG, "onResume..");
    }'''
    pause_anchor = '''    protected void onPause() {
        // A Save similar to an autosave'''
    destroy_anchor = '''    protected void onDestroy() {
        stopWatchingForHardwareKeyboard();'''
    for anchor in (field_anchor, resume_anchor, pause_anchor, destroy_anchor):
        if body.count(anchor) != 1:
            raise PatchError('Upstream LOActivity lifecycle changed: ' + anchor[:55])
    fields = '''    // AQUAWORD_PERIODIC_NATIVE_AUTOSAVE: save unmodified documents efficiently.
    private static final long AQUAWORD_AUTOSAVE_MS = 120_000L;
    private final Handler mAquaWordSaveHandler = new Handler(Looper.getMainLooper());
    private final Runnable mAquaWordSaveTick = new Runnable() {
        @Override
        public void run() {
            if (documentLoaded && isDocEditable && !isFinishing() && !isDestroyed()) {
                postMobileMessageNative("save dontTerminateEdit=1 dontSaveIfUnmodified=1");
            }
            if (!isFinishing() && !isDestroyed()) {
                mAquaWordSaveHandler.postDelayed(this, AQUAWORD_AUTOSAVE_MS);
            }
        }
    };
'''
    body = body.replace(field_anchor, field_anchor + '\n' + fields, 1)
    body = body.replace(resume_anchor, '''    protected void onResume() {
        super.onResume();
        mAquaWordSaveHandler.removeCallbacks(mAquaWordSaveTick);
        mAquaWordSaveHandler.postDelayed(mAquaWordSaveTick, AQUAWORD_AUTOSAVE_MS);
        Log.i(TAG, "onResume..");
    }''', 1)
    body = body.replace(pause_anchor, '''    protected void onPause() {
        mAquaWordSaveHandler.removeCallbacks(mAquaWordSaveTick);
        // A Save similar to an autosave''', 1)
    body = body.replace(destroy_anchor, '''    protected void onDestroy() {
        mAquaWordSaveHandler.removeCallbacks(mAquaWordSaveTick);
        stopWatchingForHardwareKeyboard();''', 1)
    return store(path, body)

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
                    + FileUtilities.DEFAULT_WRITER_EXTENSION,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    CREATE_DOCUMENT_REQUEST_CODE);
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
    <string name="aquaword_new_file_failed">Could not create the document. The file was not opened.</string>
    <string name="aquaword_snapshot_preedit">Before editing</string>
    <string name="aquaword_snapshot_saved">Saved revision</string>
'''
    return store(path, content.replace('</resources>', additions + '</resources>'))

def patch_history_activity(path: Path) -> bool:
    content = require(path).read_text(encoding='utf-8')
    if 'AQUAWORD_PREEDIT_COPY' in content:
        return False
    # Shared safety history lives in :lib so both native Writer save callbacks
    # and the Android document browser use the SAME storage and metadata.
    import_anchor = 'import org.libreoffice.androidlib.LOActivity;'
    import_new = 'import org.libreoffice.androidlib.AquaWordHistory;'
    if import_new not in content:
        if import_anchor in content:
            content = content.replace(import_anchor, import_anchor + '\n' + import_new, 1)
        else:
            # Unit fixture omits the real upstream import block.
            content = import_new + '\n' + content
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
        // Provider metadata can block on cloud/network IPC: resolve it on the worker.
        final AlertDialog progress = new AlertDialog.Builder(this)
                .setTitle(R.string.aquaword_safety_copies)
                .setMessage(R.string.aquaword_creating_safety_copy)
                .setCancelable(false).create();
        progress.show();
        new Thread(() -> {
            String problem = null;
            // AQUAWORD_ASYNC_PREEDIT_METADATA: no cloud-backed query on UI.
            String name = uri.getLastPathSegment();
            if (name == null || name.trim().isEmpty())
                name = "Untitled Document";
            try {
                final String providerName = RecentFilesAdapter.getUriFilename(this, uri);
                if (providerName != null && !providerName.trim().isEmpty())
                    name = providerName;
            } catch (Exception metadataFailure) {
                Log.w(LOGTAG, "Using URI-derived name for safety copy", metadataFailure);
            }
            try (InputStream data = getContentResolver().openInputStream(uri)) {
                AquaWordHistory.capture(getFilesDir(), data, name, uri.toString());
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
        // AQUAWORD_ASYNC_HISTORY_LIST: a concurrent large snapshot capture
        // holds AquaWordHistory's lock. Never wait for it on the UI thread.
        new Thread(() -> {
            final List<AquaWordHistory.Snapshot> snapshots;
            try {
                snapshots = AquaWordHistory.list(getFilesDir());
            } catch (IOException failure) {
                Log.e(LOGTAG, "AquaWord history listing failed", failure);
                runOnUiThread(() -> {
                    if (!isFinishing() && !isDestroyed())
                        Toast.makeText(this, R.string.aquaword_restore_failure, Toast.LENGTH_LONG).show();
                });
                return;
            }
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                if (snapshots.isEmpty()) {
                    Toast.makeText(this, R.string.aquaword_no_copies, Toast.LENGTH_LONG).show();
                    return;
                }
                final String[] names = new String[snapshots.size()];
                final java.text.DateFormat timeFormat = java.text.DateFormat.getDateTimeInstance();
                for (int n = 0; n < snapshots.size(); ++n) {
                    AquaWordHistory.Snapshot snapshot = snapshots.get(n);
                    names[n] = getString("saved".equals(snapshot.kind) ?
                        R.string.aquaword_snapshot_saved : R.string.aquaword_snapshot_preedit)
                        + " · " + snapshot.displayName + " — " +
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
            });
        }, "AquaWordHistoryList").start();
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
                persistDocumentPermission(target, data);
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
                        if (!isFinishing() && !isDestroyed()) {
                            Toast.makeText(this, finished ? R.string.aquaword_restore_success :
                                R.string.aquaword_restore_failure, Toast.LENGTH_LONG).show();
                            if (finished)
                                open(target); // The recovered document is genuinely editable.
                        }
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


def patch_async_new_document_creation(path: Path) -> bool:
    """Never write SAF documents synchronously or open failed, empty templates.

    Replaces the upstream Thread.run() (which executes on the UI thread) with
    a real worker and opens the document only after a successful stream close.
    """
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_ASYNC_DOCUMENT_CREATE'
    if marker in body:
        if 'AquaWordCreateBlank' not in body or 'createNewFile(uri, extension);\n\n                open(uri);' in body:
            raise PatchError('Unexpected partial async-create patch')
        return False
    start = '    private void createNewFile(final Uri uri, final String extension) {'
    end = '    /** Context menu item handling. */'
    old_call = '                createNewFile(uri, extension);\n\n                open(uri);'
    if body.count(start) != 1 or body.count(end) < 1 or body.count(old_call) != 1:
        raise PatchError('Upstream new-document creation flow changed')
    offset = body.index(start)
    limit = body.index(end, offset)
    replacement = '''    // AQUAWORD_ASYNC_DOCUMENT_CREATE: open only when SAF write completes.
    private void createNewFile(final Uri uri, final String extension) {
        new Thread(() -> {
            boolean failed = false;
            // AQUAWORD_VERIFIED_BLANK_DOCX: guaranteed packaged OOXML for Writer.
            // Other legacy document formats retain their native upstream assets.
            try (InputStream template = getAssets().open(
                    "docx".equalsIgnoreCase(extension) ? "aquaword/blank.docx" :
                    "templates/untitled." + extension);
                 OutputStream output = getContentResolver().openOutputStream(uri, "w")) {
                if (output == null)
                    throw new IOException("No writable document URI");
                byte[] buffer = new byte[64 * 1024];
                int bytesRead;
                while ((bytesRead = template.read(buffer)) != -1) {
                    if (bytesRead > 0)
                        output.write(buffer, 0, bytesRead);
                }
                output.flush();
                // Successful close of both streams is required before opening.
            } catch (Exception error) {
                failed = true;
                Log.e(LOGTAG, "AquaWord document creation failed", error);
            }
            final boolean completed = !failed;
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed())
                    return;
                if (completed)
                    open(uri);
                else
                    Toast.makeText(this, R.string.aquaword_new_file_failed, Toast.LENGTH_LONG).show();
            });
        }, "AquaWordCreateBlank").start();
    }

'''
    body = body[:offset] + replacement + body[limit:]
    body = body.replace(old_call, '                createNewFile(uri, extension);', 1)
    return store(path, body)


def patch_saf_permission_handling(path: Path) -> bool:
    """Allow read-only and non-persistable Android document providers safely."""
    body = require(path).read_text(encoding='utf-8')
    marker = 'AQUAWORD_SAFE_SAF_PERMISSIONS'
    if marker in body:
        if 'persistDocumentPermission(uri, data);' not in body:
            raise PatchError('Partial SAF permission patch detected')
        return False
    original = ('getContentResolver().takePersistableUriPermission(uri, '
                'Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);')
    if body.count(original) != 2:
        raise PatchError('Expected two native file-picker URI permission calls')
    anchor = '    /** File name extensions for which an empty document template is bundled in the assets. */'
    if body.count(anchor) != 1:
        raise PatchError('Expected unique SAF helper insertion point')
    # Collabora originally adds WRITE even when Android grants READ only.
    edit_anchor = '''    public Intent getIntentToEdit(Uri uri) {
        Intent i = new Intent(Intent.ACTION_EDIT, uri);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);'''
    if body.count(edit_anchor) != 1:
        raise PatchError('Upstream editable Intent grant handler changed')
    edit_replacement = '''    public Intent getIntentToEdit(Uri uri) {
        Intent i = new Intent(Intent.ACTION_EDIT, uri);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        boolean readOnly = mAquaWordReadOnlyDocumentUris.contains(uri.toString());
        // Android persisted document permissions survive Activity restarts.
        for (android.content.UriPermission permission : getContentResolver().getPersistedUriPermissions()) {
            if (uri.equals(permission.getUri()) && permission.isReadPermission() &&
                    !permission.isWritePermission()) {
                readOnly = true;
                break;
            }
        }
        if (!readOnly)
            i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);'''
    body = body.replace(edit_anchor, edit_replacement, 1)
    helper = '''    // AQUAWORD_SAFE_SAF_PERMISSIONS: do not crash on read-only or GET_CONTENT providers.
    // AQUAWORD_READONLY_DOCUMENT_GRANTS: never invent WRITE permission.
    private final java.util.Set<String> mAquaWordReadOnlyDocumentUris =
            new java.util.HashSet<String>();
    private void persistDocumentPermission(final Uri uri, final Intent returnedIntent) {
        if (uri == null || returnedIntent == null)
            return;
        final int supported = Intent.FLAG_GRANT_READ_URI_PERMISSION |
                              Intent.FLAG_GRANT_WRITE_URI_PERMISSION;
        final int granted = returnedIntent.getFlags() & supported;
        // Providers may grant READ alone (including temporary grants).
        if ((granted & Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0 &&
                (granted & Intent.FLAG_GRANT_WRITE_URI_PERMISSION) == 0)
            mAquaWordReadOnlyDocumentUris.add(uri.toString());
        else if ((granted & Intent.FLAG_GRANT_WRITE_URI_PERMISSION) != 0)
            mAquaWordReadOnlyDocumentUris.remove(uri.toString());
        if (granted == 0) {
            Log.w(LOGTAG, "Provider did not grant persistable document access");
            return;
        }
        try {
            getContentResolver().takePersistableUriPermission(uri, granted);
        } catch (SecurityException | IllegalArgumentException denied) {
            Log.w(LOGTAG, "Document grant cannot be persisted; continuing with temporary access", denied);
        }
    }

'''
    body = body.replace(original, 'persistDocumentPermission(uri, data);')
    return store(path, body.replace(anchor, helper + anchor, 1))


def patch_default_docx(file_utilities: Path, activity: Path) -> bool:
    """New AquaWord documents use Microsoft's interoperable DOCX container by default.

    All existing ODT documents remain supported by the native Collabora engine.
    """
    utilities = require(file_utilities).read_text(encoding='utf-8')
    original = 'public static final String DEFAULT_WRITER_EXTENSION = ".odt";'
    branded = 'public static final String DEFAULT_WRITER_EXTENSION = ".docx"; // AQUAWORD_DEFAULT_DOCX'
    if utilities.count(original) == 1:
        changed_util = utilities.replace(original, branded, 1)
    elif utilities.count(branded) == 1:
        changed_util = utilities
    else:
        raise PatchError('Default Writer extension anchor changed')
    body = require(activity).read_text(encoding='utf-8')
    original_fallback = '(requestCode == CREATE_DOCUMENT_REQUEST_CODE) ? "odt" :'
    branded_fallback = '(requestCode == CREATE_DOCUMENT_REQUEST_CODE) ? "docx" :'
    if body.count(original_fallback) == 1:
        changed_body = body.replace(original_fallback, branded_fallback, 1)
    elif body.count(branded_fallback) == 1:
        changed_body = body
    else:
        raise PatchError('Default document extension fallback anchor changed')
    change1 = store(file_utilities, changed_util)
    change2 = store(activity, changed_body)
    return change1 or change2


def copy_debug_qa_file_provider(repo: Path) -> int:
    """Add Android FileProvider fixture ONLY to debug variant (never release).

    The runtime harness must open a real content:// Uri, the same code path
    used by Android's Storage Access Framework and other document providers.
    """
    source_dir = ROOT / 'quality/debug_android'
    pairs = [
        (source_dir / 'AndroidManifest.xml',
         repo / 'android/app/src/debug/AndroidManifest.xml'),
        (source_dir / 'aquaword_qa_file_paths.xml',
         repo / 'android/app/src/debug/res/xml/aquaword_qa_file_paths.xml'),
        (source_dir / 'QaOpenDocumentActivity.java',
         repo / 'android/app/src/debug/java/org/libreoffice/androidapp/qa/QaOpenDocumentActivity.java'),
        (source_dir / 'QaFixtureFileProvider.java',
         repo / 'android/app/src/debug/java/org/libreoffice/androidapp/qa/QaFixtureFileProvider.java')
    ]
    for src, dst in pairs:
        require(src)
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            raise PatchError(f'Conflicting upstream debug-provider file: {dst}')
    changed = 0
    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file():
            shutil.copyfile(src, dst)
            changed += 1
    return changed

def copy_history_source(repo: Path) -> bool:
    src = require(ROOT/'history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java')
    target = repo/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java'
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
        repo/'browser/css/toolbar.css',
        repo/'android/app/src/main/java/org/libreoffice/androidapp/ui/FileUtilities.java',
        repo/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java'
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
    print('Async safe new-file creation:', patch_async_new_document_creation(targets[5]))
    print('SAF document permission handling:', patch_saf_permission_handling(targets[5]))
    print('DOCX default document format:', patch_default_docx(targets[10], targets[5]))
    print('Lifecycle-aware native autosave:', patch_periodic_native_autosave(targets[11]))
    print('Native post-save recovery checkpoints:', patch_native_save_checkpoints(targets[11]))
    print('SAF native saveback error detection:', patch_native_saf_saveback(targets[11]))
    print('History storage class:', copy_history_source(repo))
    print('Arabic recovery resources:', copy_arabic_recovery_strings(repo))
    print('Debug-only real ContentProvider test route:', copy_debug_qa_file_provider(repo))
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
