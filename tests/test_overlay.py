"""Contract tests for the pinned Collabora Android overlay (not native build tests)."""
import pathlib
import subprocess
import sys
import tempfile
import unittest
from importlib.util import spec_from_file_location, module_from_spec

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=spec_from_file_location('aquaword_overlay',ROOT/'scripts/apply_to_collabora.py')
M=module_from_spec(spec)
spec.loader.exec_module(M)

class AquaWordIntegrationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path=pathlib.Path(t.name)
        def make(path,content):
            dest=self.path/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(content,encoding='utf-8')
        make('engine/README','native')
        make('browser/css/notebookbar.css','.notebookbar {color: blue}')
        make('browser/css/mobilewizard.css','.mobile-wizard {color: blue}')
        make('browser/src/main.js', "window.addEventListener('beforeunload', function () { });")
        make('browser/css/toolbar.css', '.toolbar { display: flex; }')
        make('android/app/src/main/java/org/libreoffice/androidapp/ui/FileUtilities.java',
             'public static final String DEFAULT_WRITER_EXTENSION = ".odt";')

        make('android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java', '''
    // Real LOActivity native SAVE hook fixture.
    void handleMessage(String[] messageAndParam) {
        switch (messageAndParam[0]) {
            case "SAVE":
                copyTempBackToIntent();
                sendBroadcast(messageAndParam[0], messageAndParam[1]);
                return;
        }
    }
    private void copyTempBackToIntent() {
        if (!isDocEditable || mTempFile == null || getIntent().getData() == null || !getIntent().getData().getScheme().equals(ContentResolver.SCHEME_CONTENT))
            return;
        if (mResolvedFile != null) {
            copyTempBackToFile();
            return;
        }
        final ContentResolver contentResolver = getContentResolver();
        try {
            Thread copyThread = new Thread(new Runnable() {
                @Override
                public void run() {
                    Uri uri = getIntent().getData();
                    try {
                        OutputStream outputStream = contentResolver.openOutputStream(uri, "wt");
                    } catch (Exception e) { }
                }
            });
            copyThread.start();
            copyThread.join();
        } catch (Exception e) { }
    }

    /** Copy the temp file back to the document. */
    private void copyTempBackToFile() {
        final File resolvedFile = mResolvedFile;
        if (resolvedFile == null)
            return;
        File newContent = new File(resolvedFile.getParentFile(), "." + resolvedFile.getName() + ".part");
        try {
            try (InputStream inputStream = new FileInputStream(mTempFile)) {
                int len = inputStream.available();
                if (len <= 0)
                    return;
                try (FileOutputStream outputStream = new FileOutputStream(newContent)) {
                    byte[] buffer = new byte[1024];
                    while (inputStream.read(buffer) > 0) { }
                    outputStream.flush();
                }
            }
            if (!newContent.renameTo(resolvedFile)) {
                newContent.delete();
                reportSaveToFileFailed();
                return;
            }
            MediaScannerConnection.scanFile(this, new String[]{resolvedFile.getAbsolutePath()}, null, null);
        } catch (Exception e) {
            newContent.delete();
            reportSaveToFileFailed();
        }
    }
    /** Followup method must remain a separate anchor. */
    private boolean documentLoaded = false;
    protected void onResume() {
        super.onResume();
        Log.i(TAG, "onResume..");
    }
    protected void onPause() {
        // A Save similar to an autosave
        if (documentLoaded)
            postMobileMessageNative("save dontTerminateEdit=1 dontSaveIfUnmodified=1");
        super.onPause();
    }
    protected void onDestroy() {
        stopWatchingForHardwareKeyboard();
        super.onDestroy();
    }
    void exportResult(int requestCode, int resultCode, Intent intent) {
        switch (requestCode) {
            case REQUEST_EXPORT_FILE: {
                if (intent == null || mPendingExportSourcePath == null) {
                    mPendingExportSourcePath = null;
                    return;
                }
                File srcFile = new File(mPendingExportSourcePath);
                mPendingExportSourcePath = null;
                InputStream inputStream = null;
                OutputStream outputStream = null;
                try {
                    inputStream = new FileInputStream(srcFile);
                    try {
                        outputStream = getContentResolver().openOutputStream(intent.getData(), "wt");
                    } catch (FileNotFoundException e) {
                        Log.i(TAG, "failed with wt mode");
                        outputStream = getContentResolver().openOutputStream(intent.getData());
                    }
                    byte[] buffer = new byte[4096];
                    int len;
                    while ((len = inputStream.read(buffer)) != -1) {
                        outputStream.write(buffer, 0, len);
                    }
                    outputStream.flush();
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    try {
                        if (inputStream != null)
                            inputStream.close();
                        if (outputStream != null)
                            outputStream.close();
                    } catch (Exception e) {
                    }
                    srcFile.delete();
                }
                return;
            }
            case REQUEST_SAVEAS_PDF:
                return;
        }
    }
''')

        make('android/app/build.gradle','''android {
 defaultConfig { resValue "string", "app_name", "${coAppName}" }
 buildTypes { debug { resValue "string", "app_name", "${coAppName} Debug" } }
}''')
        make('android/app/src/main/AndroidManifest.xml','<application android:icon="${appIcon}" />')
        make('android/app/appSettings.gradle.in',"android.defaultConfig { applicationId '@APP_PACKAGE_NAME@' }")
        make('android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java', """editFAB.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                if (isFabMenuOpen)
                    collapseFabMenu();
                else
                    expandFabMenu();
            }
        });""")
        make('android/app/src/main/res/menu/view_menu.xml', '''<menu>
    <item android:id="@+id/action_open_file" android:title="Open" />
</menu>''')
        make('android/app/src/main/res/values/strings.xml', '<resources></resources>')
        # The production patch also requires activity menu, open(), and result handlers.
        activity=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        activity.write_text(activity.read_text() + """
    private static final int OPEN_FILE_REQUEST_CODE = 43;
    void open(Uri uri) {
        addDocumentToRecents(uri);

        Intent i = getIntentToEdit(uri);
        startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);
    }
    public Intent getIntentToEdit(Uri uri) {
        Intent i = new Intent(Intent.ACTION_EDIT, uri);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        return i;
    }
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == R.id.action_open_file) {
            openDocument();
            return true;
        }
    }
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putInt(FILTER_MODE_KEY, filterMode);
    }
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);
        filterMode = savedInstanceState.getInt(FILTER_MODE_KEY, FileUtilities.ALL);
    }
    /** File name extensions for which an empty document template is bundled in the assets. */
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch (requestCode) {
            case LO_ACTIVITY_REQUEST_CODE: {
            }
        }
    }
""")
        activity.write_text(activity.read_text() + """
    private void createNewFile(final Uri uri, final String extension) {
        // old UI-thread behavior:
        class CreateThread extends Thread {
            @Override public void run() {
            }
        }
        CreateThread thread = new CreateThread();
        thread.run();
        try {
            thread.join();
        } catch (Exception e) {
        }
    }

    /** Context menu item handling. */
    void doCreate() {
                createNewFile(uri, extension);

                open(uri);
    }
""")
        grant=('getContentResolver().takePersistableUriPermission(uri, ' +
               'Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);')
        activity.write_text(activity.read_text(encoding='utf-8') +
                            '\n    extension = (requestCode == CREATE_DOCUMENT_REQUEST_CODE) ? "odt" : ((requestCode == CREATE_SPREADSHEET_REQUEST_CODE) ? "ods" : "odp");\n', encoding='utf-8')
        activity.write_text(activity.read_text(encoding='utf-8') +
                            '\n' + grant + '\n' + grant + '\n', encoding='utf-8')
    def run_phase(self,phase):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/apply_to_collabora.py'),'--repo',str(self.path),'--phase',phase],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,(r.stdout,r.stderr))
    def test_saf_template_create_and_restore_survive_rotation(self):
        self.run_phase('source')
        from pathlib import Path
        subprocess.run([sys.executable, str(ROOT/'scripts/generate_templates.py')],
                       check=True, cwd=ROOT, capture_output=True, text=True)
        args = [sys.executable, str(ROOT/'scripts/apply_templates.py'),
                '--repo', str(self.path)]
        for _ in range(2):
            outcome = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(outcome.returncode, 0, (outcome.stdout, outcome.stderr))
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_PENDING_SAF_RECOVERY'), 1)
        self.assertIn('outState.putString("aquaword.pending_template"', activity)
        self.assertIn('savedInstanceState.getString("aquaword.pending_template")', activity)
        self.assertIn('outState.putString("aquaword.pending_restore"', activity)
        self.assertIn('version.file.getName().equals(previousSnapshotId)', activity)
        self.assertIn('persistDocumentPermission(destination, data);', activity)
        self.assertIn('persistDocumentPermission(target, data);', activity)
        self.assertIn('if (finished)', activity)
        self.assertIn('open(target); // The recovered document is genuinely editable.', activity)
        self.assertIn('if (written < 500L)', activity)
        self.assertIn('catch (Exception problem)', activity)

    def test_history_and_preedit_provider_metadata_never_block_ui(self):
        """UI thread must not query cloud SAF metadata or wait for a large history lock.

        Generated-source regression only; Android ANR and provider tests are
        still required before device acceptance.
        """
        self.run_phase('source')
        self.run_phase('source')  # overlay remains idempotent
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_ASYNC_HISTORY_LIST'), 1)
        self.assertEqual(activity.count('AQUAWORD_ASYNC_PREEDIT_METADATA'), 1)

        opening=activity.split('final Intent i = getIntentToEdit(uri);', 1)[1].split(
            '}, "AquaWordSafetyCopy").start();', 1)[0]
        self.assertLess(opening.index('progress.show();'),
                        opening.index('new Thread(() -> {'))
        self.assertLess(opening.index('new Thread(() -> {'),
                        opening.index('RecentFilesAdapter.getUriFilename(this, uri)'))
        self.assertIn('String name = uri.getLastPathSegment();', opening)
        self.assertIn('catch (Exception metadataFailure)', opening)
        self.assertIn('AquaWordHistory.capture(getFilesDir(), data, name, uri.toString());', opening)

        history=activity.split('private void showAquaWordHistory() {', 1)[1].split(
            '/** File name extensions for which an empty document template', 1)[0]
        self.assertLess(history.index('new Thread(() -> {'),
                        history.index('AquaWordHistory.list(getFilesDir())'))
        self.assertLess(history.index('AquaWordHistory.list(getFilesDir())'),
                        history.index('runOnUiThread(() -> {\n                if (isFinishing() || isDestroyed()) return;'))
        self.assertIn('new AlertDialog.Builder(this)', history.split(
            'if (isFinishing() || isDestroyed()) return;', 1)[1])
        self.assertIn('if (!isFinishing() && !isDestroyed())', history)
        self.assertIn('}, "AquaWordHistoryList").start();', history)

    def test_preedit_cloud_wait_can_be_cancelled_without_opening_editor(self):
        """Back must dismiss a stalled provider wait and suppress late editor launch.

        Source/overlay contract only; Android dialog and cloud provider runtime
        behavior remain NOT TESTED until final-device acceptance.
        """
        self.run_phase('source')
        self.run_phase('source')  # no duplicated listener after reapplying overlay
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        opening=activity.split('final Intent i = getIntentToEdit(uri);', 1)[1].split(
            '}, "AquaWordSafetyCopy").start();', 1)[0]
        self.assertEqual(opening.count('AQUAWORD_CANCELABLE_PREEDIT'), 1)
        self.assertIn('new java.util.concurrent.atomic.AtomicBoolean(false)', opening)
        self.assertIn('.setCancelable(true).create();', opening)
        self.assertIn('progress.setCanceledOnTouchOutside(false);', opening)
        self.assertIn('progress.setOnCancelListener(dialog -> cancelled.set(true));', opening)
        self.assertLess(opening.index('progress.setOnCancelListener('), opening.index('progress.show();'))
        self.assertIn('if (cancelled.get() || isFinishing() || isDestroyed()) return;', opening)
        self.assertLess(opening.index('if (cancelled.get() || isFinishing() || isDestroyed()) return;'),
                        opening.index('startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);'))
        self.assertIn('AquaWordHistory.capture(getFilesDir(), data, name, uri.toString());', opening)
        # Canceled/failed pre-edit attempts must not appear in Recents.
        self.assertEqual(opening.count('addDocumentToRecents(uri);'), 2)
        first_guard = 'if (cancelled.get() || isFinishing() || isDestroyed()) return;'
        self.assertNotIn('addDocumentToRecents(uri);', opening.split(first_guard, 1)[0])
        self.assertIn('AQUAWORD_RECENTS_AFTER_OPEN', opening)
        self.assertIn('startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);\n                    addDocumentToRecents(uri);', opening)
        self.assertIn('if (cancelled.get() || isFinishing() || isDestroyed()) return;\n                                startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);\n                                addDocumentToRecents(uri);', opening)

    def test_writer_creation_uses_real_docx_mime(self):
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document',activity)
        self.assertNotIn('FileUtilities.DEFAULT_WRITER_EXTENSION, "*/*"',activity)

    def test_saf_recovery_capture_rejects_nonprogressing_provider_stream(self):
        """Malformed provider reads must not spin under the history lock.

        Generated-source contract; the JVM behavior is separately exercised
        by AquaWordHistoryTest, not by an Android ContentProvider here.
        """
        self.run_phase('source')
        self.run_phase('source')  # idempotent overlay copy
        helper=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').read_text()
        capture=helper.split('public static Snapshot capture(File appFilesDir, InputStream input,\n                                                String name, String sourceIdentity,',1)[1].split(
            'private static String sanitizeName',1)[0]
        self.assertIn('int noProgressReads = 0;',capture)
        self.assertIn('if (++noProgressReads >= 8)',capture)
        self.assertIn('throw new IOException("Document input stream made no progress")',capture)
        self.assertIn('noProgressReads = 0;\n                    length += count;',capture)
        self.assertIn('finally {\n            synchronized (AquaWordHistory.class) {\n                temp.delete();',capture)
        self.assertIn('ACTIVE_CAPTURE_WRITES.add(tempKey);',capture)
        self.assertIn('ACTIVE_CAPTURE_WRITES.remove(tempKey);',capture)
        self.assertIn('ACTIVE_CAPTURE_WRITES.contains(entry.getAbsolutePath())',helper)
        self.assertIn('synchronized (AquaWordHistory.class) {',capture)
        commit_comment = capture.index('// Commit and retention are serialized')
        commit_lock = capture.index('synchronized (AquaWordHistory.class) {', commit_comment)
        self.assertLess(capture.index('output.getFD().sync();'), commit_lock)

    def test_exportfile_pdf_copy_is_async_verified_and_retains_failure_source(self):
        self.run_phase('source')
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        marker='AQUAWORD_VERIFIED_ASYNC_EXPORT'
        self.assertEqual(native.count(marker),1)
        section=native.split('case REQUEST_EXPORT_FILE: {',1)[1].split(
            'case REQUEST_SAVEAS_PDF:',1)[0]
        self.assertIn('mAquaWordSaveExecutor.execute(() ->',section)
        self.assertIn('resultCode != RESULT_OK',section)
        self.assertIn('exportSource.length() <= 0L',section)
        self.assertIn('getContentResolver().openInputStream(exportTarget)',section)
        self.assertIn('readBytes != written',section)
        self.assertIn('java.util.Arrays.equals(expected.digest(), observed.digest())',section)
        self.assertIn('if (verified && !exportSource.delete())',section)
        self.assertIn('RejectedExecutionException',section)
        self.assertNotIn('srcFile.delete();',section)
        self.assertLess(section.index('output.flush();'),
                        section.index('openInputStream(exportTarget)'))
        self.run_phase('source')
        self.assertEqual(native,(self.path/
            'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text())

    def test_pdf_export_checks_signature_before_saf_and_requires_truncate(self):
        """Source contract: reject bogus PDFs without touching destination.

        ContentResolver.openOutputStream(uri) uses ambiguous "w" mode;
        only explicit truncating modes are acceptable for PDF replacement.
        This is not an Android ContentProvider runtime test.
        """
        self.run_phase('source')
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        section=native.split('case REQUEST_EXPORT_FILE: {',1)[1].split(
            'case REQUEST_SAVEAS_PDF:',1)[0]
        self.assertEqual(section.count('AQUAWORD_PDF_SIGNATURE_AND_TRUNCATION'),1)
        self.assertIn('new java.io.DataInputStream(source).readFully(signature);',section)
        self.assertIn('source.mark(5);',section)
        self.assertIn('source.reset();',section)
        self.assertIn('Native export is not a PDF',section)
        self.assertLess(section.index('source.reset();'),
                        section.index('openOutputStream(exportTarget, "rwt")'))
        self.assertLess(section.index('Native export is not a PDF'),
                        section.index('exportTarget, "wt"'))
        self.assertIn('exportTarget, "wt"',section)
        self.assertIn('openOutputStream(exportTarget, "rwt")',section)
        self.assertNotIn('openOutputStream(exportTarget);',section)
        self.assertNotIn('openOutputStream(exportTarget, "w")',section)
        self.assertIn('Export provider returned no truncating output stream',section)
        self.run_phase('source')  # idempotent
        self.assertEqual(native,(self.path/
            'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text())

    def test_pdf_export_trailer_preflight_is_before_saf_truncation(self):
        """Source contract for preflight; JVM tests exercise the helper itself."""
        self.run_phase('source')
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        section=native.split('case REQUEST_EXPORT_FILE: {',1)[1].split(
            'case REQUEST_SAVEAS_PDF:',1)[0]
        self.assertEqual(section.count('AQUAWORD_PDF_TRAILER_PREFLIGHT'),1)
        self.assertIn('AquaWordPdfPreflight.requirePlausiblePdf(exportSource);',section)
        self.assertLess(section.index('requirePlausiblePdf(exportSource)'),
                        section.index('openOutputStream(exportTarget'))
        helper=self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordPdfPreflight.java'
        self.assertTrue(helper.is_file())
        helper_source=helper.read_text()
        self.assertIn('Native PDF export lacks a final EOF line',helper_source)
        self.assertIn('boolean clean = true;',helper_source)
        self.assertIn('finalStartXref(tail, i, base)',helper_source)
        self.assertIn('verifyCrossReference(source, offset)',helper_source)
        self.assertIn('!lineStart(tail, i)',helper_source)
        initial=helper.read_bytes()
        self.run_phase('source')
        self.assertEqual(initial,helper.read_bytes())

    def test_pdf_export_feedback_is_localized_in_native_library(self):
        """Export success is shown only after SHA readback; lib owns R.string."""
        import xml.etree.ElementTree as ET
        self.run_phase('source')
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        section=native.split('case REQUEST_EXPORT_FILE: {',1)[1].split(
            'case REQUEST_SAVEAS_PDF:',1)[0]
        keys=('aquaword_export_missing','aquaword_export_unverified',
              'aquaword_export_busy','aquaword_export_verified')
        for locale in ('values','values-ar'):
            path=self.path/'android/lib/src/main/res'/locale/'aquaword_export.xml'
            root=ET.parse(path).getroot()
            values={element.attrib['name']:element.text
                    for element in root.findall('string')}
            self.assertEqual(set(values),set(keys))
            self.assertTrue(all(values[k] and values[k].strip() for k in keys))
        for key in keys:
            self.assertIn('R.string.'+key,section)
        self.assertIn('AQUAWORD_EXPORT_VERIFIED_FEEDBACK',section)
        self.assertLess(section.index('readBytes != written'),
                        section.index('if (verified) {'))
        self.assertNotIn('"Export could not be verified. Please try again."',section)
        self.run_phase('source')  # native resources are copied idempotently

    def test_exportfile_upstream_drift_rejected(self):
        native=self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java'
        native.write_text(native.read_text().replace(
            'openOutputStream(intent.getData(), "wt")',
            'openOutputStream(intent.getData(), "w")'),encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_native_export_writeback(native)

    def test_native_saveback_reports_error_and_rejects_empty_files(self):
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        self.assertEqual(lib.count('AQUAWORD_NATIVE_SAF_SAVE_BACK'),1)
        self.assertIn('sourceFile.length() <= 0L',lib)
        self.assertIn('R.string.failed_to_save_file',lib)
        self.assertIn('output.flush();',lib)
        self.assertIn('bytes != sourceFile.length()',lib)
        self.assertNotIn('copyThread.join();',lib)
        self.assertIn('private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave)',lib)
        self.assertIn('private boolean copyTempBackToFile(java.io.File sourceFile, java.io.File resolvedFile)',lib)
        self.assertIn('return copyTempBackToFile(sourceFile, resolvedAtSave);',lib)
        self.assertIn('new FileInputStream(sourceFile)',lib)
        self.assertIn('return true;',lib)
        self.assertIn('AquaWord SAVE not acknowledged',lib)

    def test_history_restore_requires_truncating_saf_stream(self):
        """A restored DOCX must not retain a prior document's ZIP tail.

        Generated-source contract only: real providers and device runtime
        remain NOT TESTED. A null/unsupported provider must fail closed.
        """
        self.run_phase('source')
        self.run_phase('source')  # idempotent overlay
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        restore=activity.split('case AQUAWORD_RESTORE_REQUEST_CODE:',1)[1].split(
            'case LO_ACTIVITY_REQUEST_CODE:',1)[0]
        self.assertEqual(restore.count('AQUAWORD_SAFE_HISTORY_RESTORE'),1)
        self.assertEqual(restore.count('openOutputStream(target, "wt")'),1)
        self.assertEqual(restore.count('openOutputStream(target, "rwt")'),1)
        self.assertLess(restore.index('openOutputStream(target, "wt")'),
                        restore.index('openOutputStream(target, "rwt")'))
        self.assertNotIn('openOutputStream(target, "w")',restore)
        self.assertNotIn('openOutputStream(target);',restore)
        self.assertIn('catch (java.io.FileNotFoundException | UnsupportedOperationException rejected)',restore)
        self.assertIn('opened = getContentResolver().openOutputStream(target, "rwt");',restore)
        self.assertIn('throw new IOException("No truncating writable recovery destination")',restore)
        self.assertIn('AquaWordHistory.restoreToDestination(item, () -> {',restore)
        self.assertLess(restore.index('AquaWordHistory.restoreToDestination(item, () -> {'),
                        restore.index('openOutputStream(target, "wt")'))
        self.assertLess(restore.index('openOutputStream(target, "rwt")'),
                        restore.index('success = true;'))
        self.assertIn('catch (Exception failure)',restore)
        self.assertIn('success = false;',restore)
        self.assertIn('if (finished)\n                                open(target);',restore)

    def test_restore_verifies_snapshot_before_truncating_provider(self):
        """Corrupt recovery bytes must not destroy a selected SAF document.

        This checks generated Java ordering and helper presence. Actual
        ContentProvider truncation still needs Android instrumentation.
        """
        self.run_phase('source')
        self.run_phase('source')  # repeated overlay is stable
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        restore=activity.split('case AQUAWORD_RESTORE_REQUEST_CODE:',1)[1].split(
            'case LO_ACTIVITY_REQUEST_CODE:',1)[0]
        self.assertEqual(restore.count('AQUAWORD_RESTORE_PREFLIGHT'),1)
        self.assertIn('AquaWordHistory.verifyForRestore(item);',restore)
        self.assertLess(restore.index('AquaWordHistory.verifyForRestore(item);'),
                        restore.index('AquaWordHistory.restoreToDestination(item, () -> {'))
        self.assertLess(restore.index('AquaWordHistory.restoreToDestination(item, () -> {'),
                        restore.index('openOutputStream(target, "wt")'))
        self.assertLess(restore.index('AquaWordHistory.restoreToDestination(item, () -> {'),
                        restore.index('openOutputStream(target, "rwt")'))
        self.assertIn('catch (Exception failure)',restore)
        self.assertIn('success = false;',restore)
        self.assertIn('if (finished)\n                                open(target);',restore)
        helper=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').read_text()
        self.assertIn('public static synchronized void verifyForRestore(Snapshot snapshot)',helper)
        self.assertIn('snapshot == null || snapshot.sizeBytes <= 0L || !verifyBytes(snapshot)',helper)
        self.assertIn('public static void restoreToDestination(Snapshot snapshot, DestinationOpener opener)',helper)
        self.assertIn('private static File stageRestoreCopy(Snapshot snapshot)',helper)
        self.assertIn('OutputStream opened = opener.open();',helper)
        self.assertLess(helper.index('stageRestoreCopy(snapshot);'),
                        helper.index('OutputStream opened = opener.open();'))
        self.assertIn('public static void restore(Snapshot snapshot, OutputStream target)',helper)

    def test_restored_saf_docx_readback_matches_snapshot_before_open(self):
        """A successful close is insufficient: verify provider-visible bytes.

        This is an overlay/source regression contract, NOT an Android provider
        or cloud synchronization test. The JVM helper tests exercise corrupt,
        short and extra readbacks separately.
        """
        self.run_phase('source')
        self.run_phase('source')  # overlay idempotence
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        restore=activity.split('case AQUAWORD_RESTORE_REQUEST_CODE:',1)[1].split(
            'case LO_ACTIVITY_REQUEST_CODE:',1)[0]
        self.assertEqual(restore.count('AQUAWORD_RESTORE_READBACK_BARRIER'), 1)
        self.assertEqual(restore.count('openInputStream(target)'), 1)
        self.assertEqual(restore.count('AquaWordHistory.verifyProviderWriteback(item, readback);'), 1)
        self.assertLess(restore.index('AquaWordHistory.verifyForRestore(item);'),
                        restore.index('openOutputStream(target, "wt")'))
        self.assertLess(restore.index('AquaWordHistory.restoreToDestination(item, () -> {'),
                        restore.index('openInputStream(target)'))
        self.assertLess(restore.index('openInputStream(target)'),
                        restore.index('AquaWordHistory.verifyProviderWriteback(item, readback);'))
        self.assertLess(restore.index('AquaWordHistory.verifyProviderWriteback(item, readback);'),
                        restore.index('success = true;'))
        self.assertIn('catch (Exception failure)', restore)
        self.assertIn('success = false;', restore)
        self.assertIn('if (finished)\n                                open(target);', restore)
        helper=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').read_text()
        self.assertIn('public static void verifyProviderWriteback(Snapshot snapshot, InputStream providerInput)', helper)

    def test_null_native_save_stream_retries_explicit_rwt(self):
        """A null wt stream from a crashed provider must try rwt, not w."""
        self.run_phase('source')
        self.run_phase('source')
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        save=native.split('private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave) {',1)[1].split(
            '/** Copy the temp file back to the document. */',1)[0]
        self.assertEqual(save.count('openOutputStream(destination, "wt")'),1)
        self.assertEqual(save.count('openOutputStream(destination, "rwt")'),1)
        self.assertIn('if (opened == null)\n                opened = getContentResolver().openOutputStream(destination, "rwt");',save)
        self.assertIn('if (opened == null)\n                throw new IOException("Document provider returned no writable stream");',save)
        self.assertNotIn('openOutputStream(destination, "w")',save)
        self.assertLess(save.index('try (OutputStream output = opened)'),
                        save.index('return true;'))

    def test_existing_saf_docx_save_never_uses_nontruncating_w_mode(self):
        """No ambiguous w writes; source contract, NOT Android provider proof."""
        self.run_phase('source')
        self.run_phase('source')
        source=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        save=source.split('private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave) {', 1)[1].split(
            '/** Copy the temp file back to the document. */', 1)[0]
        self.assertEqual(save.count('openOutputStream(destination, "wt")'), 1)
        self.assertEqual(save.count('openOutputStream(destination, "rwt")'), 1)
        self.assertLess(save.index('openOutputStream(destination, "wt")'),
                        save.index('openOutputStream(destination, "rwt")'))
        self.assertNotIn('openOutputStream(destination);', save)
        self.assertNotIn('openOutputStream(destination, "w")', save)
        self.assertIn('catch (FileNotFoundException | UnsupportedOperationException noTruncateMode)', save)
        self.assertIn('SAF writeback failed', save)
        self.assertIn('return false;', save)
        self.assertIn('new FileInputStream(sourceFile)', save)
        self.assertNotIn('new FileInputStream(mTempFile)', save)

    def test_failed_saf_writeback_keeps_native_post_edit_recovery(self):
        """Durable snapshot MUST precede any provider truncation."""
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        callback=lib.split('case "SAVE":', 1)[1].split('return;', 1)[0]
        self.assertIn('AQUAWORD_RECOVER_FAILED_SAF_SAVE', callback)
        self.assertEqual(callback.count('captureNativeSaveCheckpoint(messageAndParam.clone());'), 1)
        self.assertNotIn('sendBroadcast(', callback)
        method=lib.split('private void captureNativeSaveCheckpoint(final String[] saveMessage)', 1)[1].split(
            'private boolean documentLoaded', 1)[0]
        self.assertIn('AQUAWORD_DURABLE_SAVE_BARRIER', method)
        self.assertLess(method.index('AquaWordHistory.capture('),
                        method.index('AquaWordHistory.holdForWriteback(checkpoint)'))
        self.assertLess(method.index('AquaWordHistory.holdForWriteback(checkpoint)'),
                        method.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'))
        self.assertLess(method.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'),
                        method.index('sendBroadcast(saveMessage[0], saveMessage[1]);'))
        self.assertIn('AquaWord SAVE not acknowledged', method)
        # Only the failed SAF writeback branch must suppress SAVE. Native
        # file:// Writer saves are already persisted and are a separate case.
        saf_failure=method.split('Log.e(TAG, "AquaWord SAVE not acknowledged', 1)[1].split(
            '} catch (Exception failure)', 1)[0]
        self.assertNotIn('sendBroadcast(', saf_failure)
        self.assertIn('writerOutput.length() <= 0L', method)

    def test_native_save_reuses_local_preedit_name_without_cloud_query(self):
        """No cloud metadata IPC; recovery and provider I/O run off callback."""
        self.run_phase('source')
        self.run_phase('source')
        source=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        checkpoint=source.split('private void captureNativeSaveCheckpoint(final String[] saveMessage) {', 1)[1].split(
            'private boolean documentLoaded', 1)[0]
        worker=checkpoint.index('mAquaWordSaveExecutor.execute(() -> {')
        self.assertLess(checkpoint.index('new java.io.FileInputStream(writerOutput)'), worker)
        self.assertIn('final String fallbackName', checkpoint[:worker])
        self.assertIn('try (java.io.InputStream stream = saved)', checkpoint[worker:])
        self.assertNotIn('getContentResolver().query(', checkpoint)
        self.assertIn('AQUAWORD_LOCAL_RECOVERY_NAME', checkpoint)
        self.assertIn('AquaWordHistory.preferredDisplayName(', checkpoint[worker:])
        self.assertLess(checkpoint.index('AquaWordHistory.preferredDisplayName('),
                        checkpoint.index('AquaWordHistory.capture('))
        self.assertIn('getFilesDir(), stream, name, sourceIdentity, "saved"', checkpoint)
        self.assertLess(checkpoint.index('AquaWordHistory.capture('),
                        checkpoint.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'))

    def test_metadata_commit_failure_preserves_recoverable_snapshot(self):
        """A failed metadata rename must not delete already-fsynced DOCX bytes."""
        self.run_phase('source')
        self.run_phase('source')  # idempotent overlay
        history=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').read_text()
        self.assertIn('interface RenameStrategy', history)
        self.assertIn('boolean dataCommitted = false;', history)
        self.assertLess(history.index('if (!renameStrategy.rename(temp, data))'),
                        history.index('dataCommitted = true;'))
        self.assertIn('if (!meta.exists() && !dataCommitted) data.delete();', history)

    def test_native_file_uri_writer_save_does_not_require_saf_copyback(self):
        """Pinned native Writer writes file:// directly; source contract only.

        With no mTempFile, SAVE must use the actual file as the snapshot
        source, never try ContentResolver, and acknowledge Writer's save even
        if best-effort history capture fails. Android runtime is NOT TESTED.
        """
        self.run_phase('source')
        self.run_phase('source')  # idempotent overlay
        native=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        method=native.split('private void captureNativeSaveCheckpoint(final String[] saveMessage) {',1)[1].split(
            'private boolean documentLoaded',1)[0]
        self.assertEqual(method.count('AQUAWORD_DIRECT_FILE_SAVE'),1)
        self.assertIn('mTempFile == null &&',method)
        self.assertIn('ContentResolver.SCHEME_FILE.equals(original.getScheme())',method)
        self.assertIn('new java.io.File(original.getPath()) : mTempFile',method)
        self.assertIn('new java.io.FileInputStream(writerOutput)',method)
        self.assertIn('boolean written = directWriterFile ||',method)
        self.assertIn('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)',method)
        self.assertLess(method.index('AquaWordHistory.holdForWriteback(checkpoint)'),
                        method.index('boolean written = directWriterFile ||'))
        self.assertIn('if (directWriterFile && writerOutput.isFile() && writerOutput.length() > 0L)',method)
        self.assertIn('Native file saved by Writer, but recovery checkpoint failed',method)
        self.assertIn('if (!writerReadbackStarted) {',method)
        self.assertIn('sendBroadcast(saveMessage[0], saveMessage[1]);\n                            return;',method)
        # The content:// branch still has the durability barrier and refuses
        # a SAVE broadcast when its explicit provider writeback fails.
        self.assertIn('AquaWord SAVE not acknowledged',method)
        self.assertIn('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)',method)

    def test_saf_writeback_readback_matches_durable_checkpoint(self):
        """Source contract: never acknowledge a silently truncated SAF SAVE."""
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        checkpoint=lib.split('private void captureNativeSaveCheckpoint(',1)[1].split(
            'private boolean documentLoaded',1)[0]
        self.assertEqual(checkpoint.count('AQUAWORD_SAF_READBACK_BARRIER'),1)
        self.assertIn('boolean written = directWriterFile ||',checkpoint)
        self.assertIn('if (written && !directWriterFile)',checkpoint)
        self.assertIn('getContentResolver().openInputStream(original)',checkpoint)
        self.assertIn('AquaWordHistory.verifyProviderWriteback(checkpoint, providerReadback);',checkpoint)
        self.assertLess(checkpoint.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'),
                        checkpoint.index('AquaWordHistory.verifyProviderWriteback(checkpoint, providerReadback);'))
        self.assertLess(checkpoint.index('AquaWordHistory.verifyProviderWriteback(checkpoint, providerReadback);'),
                        checkpoint.index('sendBroadcast(saveMessage[0], saveMessage[1]);'))
        history=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').read_text()
        verify=history.split('public static void verifyProviderWriteback(',1)[1].split(
            '// Keep retention/trim',1)[0]
        self.assertIn('received > snapshot.sizeBytes',verify)
        self.assertIn('received != snapshot.sizeBytes',verify)
        self.assertIn('hex(checksum.digest()).equals(snapshot.sha256)',verify)
        self.assertIn('noProgress >= 8',verify)
        self.assertNotIn('synchronized',verify)

    def test_resolved_local_save_uses_frozen_destination_and_readback(self):
        """Source contract only: local copies require SHA-256 readback.

        An Activity change must not redirect an already queued SAVE.
        """
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        checkpoint=lib.split('private void captureNativeSaveCheckpoint(',1)[1].split(
            'private boolean documentLoaded',1)[0]
        direct=lib.split('private boolean copyTempBackToFile(java.io.File sourceFile, java.io.File resolvedFile) {',1)[1].split(
            '\n    /**',1)[0]
        saf=lib.split('private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave) {',1)[1].split(
            '/** Copy the temp file back to the document. */',1)[0]
        self.assertEqual(checkpoint.count('AQUAWORD_RESOLVED_FILE_READBACK'),1)
        self.assertIn('final java.io.File resolvedAtSave = mResolvedFile;',checkpoint)
        self.assertIn('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)',checkpoint)
        self.assertIn('if (resolvedAtSave != null)',checkpoint)
        self.assertIn('new FileInputStream(resolvedAtSave)',checkpoint)
        self.assertIn('AquaWordHistory.verifyProviderWriteback(checkpoint, localReadback)',checkpoint)
        self.assertIn('AquaWordHistory.verifyProviderWriteback(checkpoint, providerReadback)',checkpoint)
        self.assertLess(checkpoint.index('new FileInputStream(resolvedAtSave)'),
                        checkpoint.index('sendBroadcast(saveMessage[0], saveMessage[1]);'))
        self.assertIn('return copyTempBackToFile(sourceFile, resolvedAtSave);',saf)
        self.assertNotIn('mResolvedFile',saf)
        self.assertNotIn('mResolvedFile',direct)
        self.assertIn('new FileInputStream(sourceFile)',direct)

    def test_native_save_uses_immutable_snapshot_for_both_writeback_paths(self):
        """Source contract: avoid mutable Writer temp path after async SAVE."""
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        self.assertEqual(lib.count('AQUAWORD_DURABLE_SAVE_BARRIER'),1)
        self.assertIn('new java.util.concurrent.ThreadPoolExecutor(',lib)
        self.assertIn('mAquaWordSaveExecutor.shutdown();',lib)
        self.assertIn('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)',lib)
        saf=lib.split('private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave) {',1)[1].split(
            '/** Copy the temp file back to the document. */',1)[0]
        direct=lib.split('private boolean copyTempBackToFile(java.io.File sourceFile, java.io.File resolvedFile) {',1)[1].split(
            '\n    /**',1)[0]
        self.assertIn('return copyTempBackToFile(sourceFile, resolvedAtSave);',saf)
        self.assertIn('new FileInputStream(sourceFile)',saf)
        self.assertIn('new FileInputStream(sourceFile)',direct)
        self.assertNotIn('new FileInputStream(mTempFile)',saf+direct)
        self.assertIn('catch (java.util.concurrent.RejectedExecutionException shutdown)',lib)
        self.assertIn('saved.close()',lib)

    def test_native_writer_source_stability_before_any_provider_truncation(self):
        """Source contract only: a queued FileInputStream is NOT immutable.

        A later Writer save can rewrite the same inode. Re-read the actual
        Writer file and compare SHA-256 with the durable checkpoint before
        copying to SAF or acknowledging a direct-file save. No APK is built.
        """
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        checkpoint=lib.split('private void captureNativeSaveCheckpoint(',1)[1].split(
            'private boolean documentLoaded',1)[0]
        self.assertEqual(checkpoint.count('AQUAWORD_WRITER_SOURCE_STABILITY'),1)
        self.assertIn('boolean writerReadbackStarted = false;',checkpoint)
        self.assertIn('writerReadbackStarted = true;',checkpoint)
        self.assertIn('new java.io.FileInputStream(writerOutput)',checkpoint)
        self.assertIn('AquaWordHistory.verifyProviderWriteback(checkpoint, writerReadback);',checkpoint)
        self.assertLess(checkpoint.index('AquaWordHistory.holdForWriteback(checkpoint)'),
                        checkpoint.index('writerReadbackStarted = true;'))
        self.assertLess(checkpoint.index('AquaWordHistory.verifyProviderWriteback(checkpoint, writerReadback);'),
                        checkpoint.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'))
        self.assertIn('if (!writerReadbackStarted)',checkpoint)
        self.assertLess(checkpoint.index('if (!writerReadbackStarted)'),
                        checkpoint.rindex('sendBroadcast(saveMessage[0], saveMessage[1]);'))
        self.assertIn('AquaWord post-save recovery or writeback failed',checkpoint)

    def test_stalled_saf_provider_cannot_queue_unbounded_native_saves(self):
        """Source contract only: cap queued open Writer descriptors on stalled SAF.

        This does not interrupt a provider blocked inside read/write, and
        does not establish Android runtime or memory-performance results.
        """
        self.run_phase('source')
        self.run_phase('source')  # overlay remains idempotent
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        queue=lib.split('// AQUAWORD_NATIVE_SAVE_CHECKPOINT:',1)[1].split(
            'private void captureNativeSaveCheckpoint(',1)[0]
        checkpoint=lib.split('private void captureNativeSaveCheckpoint(',1)[1].split(
            'private boolean documentLoaded',1)[0]
        self.assertEqual(queue.count('AQUAWORD_BOUNDED_SAVE_QUEUE'),1)
        self.assertIn('AQUAWORD_MAX_PENDING_SAVES = 8;',queue)
        self.assertIn('new java.util.concurrent.ThreadPoolExecutor(',queue)
        self.assertIn('new java.util.concurrent.ArrayBlockingQueue<Runnable>(',queue)
        self.assertIn('AQUAWORD_MAX_PENDING_SAVES)',queue)
        self.assertIn('new java.util.concurrent.ThreadPoolExecutor.AbortPolicy()',queue)
        self.assertNotIn('Executors.newSingleThreadExecutor(',queue)
        self.assertIn('catch (java.util.concurrent.RejectedExecutionException shutdown)',checkpoint)
        rejected=checkpoint.split(
            'catch (java.util.concurrent.RejectedExecutionException shutdown)',1)[1]
        self.assertIn('saved.close();',rejected)
        self.assertIn('queue full or Activity destroyed',rejected)
        self.assertIn('Toast.makeText(this, R.string.failed_to_save_file, Toast.LENGTH_LONG)',rejected)
        self.assertNotIn('sendBroadcast(',rejected)
        self.assertIn('mAquaWordSaveExecutor.shutdown();',lib)

    def test_save_callbacks_create_real_history_checkpoints(self):
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        browser=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        english=(self.path/'android/app/src/main/res/values/strings.xml').read_text()
        arabic=(self.path/'android/app/src/main/res/values-ar/aquaword_strings.xml').read_text()
        self.assertEqual(lib.count('AQUAWORD_NATIVE_SAVE_CHECKPOINT'),1)
        self.assertIn('captureNativeSaveCheckpoint(messageAndParam.clone());',lib)
        self.assertIn('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)',lib)
        self.assertIn('sendBroadcast(saveMessage[0], saveMessage[1])',lib)
        self.assertIn('getFilesDir(), stream, name, sourceIdentity, "saved"',lib)
        self.assertIn('AquaWordNativeSaveCheckpoint',lib)
        self.assertIn('AquaWordHistory.preferredDisplayName(',lib)
        self.assertEqual(lib.count('AQUAWORD_WRITEBACK_LEASE'),1)
        self.assertIn('AquaWordHistory.holdForWriteback(checkpoint)',lib)
        self.assertLess(lib.index('AquaWordHistory.holdForWriteback(checkpoint)'),
                        lib.index('copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)'))
        self.assertIn('} // release recovery lease after provider writeback',lib)
        self.assertNotIn('getContentResolver().query(', lib.split(
            'private void captureNativeSaveCheckpoint(',1)[1].split('private boolean documentLoaded',1)[0])
        self.assertIn('aquaword_snapshot_saved',browser)
        self.assertIn('aquaword_snapshot_preedit',browser)
        self.assertIn('"recovered".equals(snapshot.kind)',browser)
        self.assertIn('R.string.aquaword_snapshot_recovered',browser)
        self.assertIn('name="aquaword_snapshot_recovered"',english)
        self.assertIn('name="aquaword_snapshot_recovered"',arabic)
        self.assertIn('org.libreoffice.androidlib.AquaWordHistory',browser)
        self.assertTrue((self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').is_file())
        self.assertFalse((self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/AquaWordHistory.java').exists())

    def test_save_callback_drift_rejected(self):
        path=self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java'
        path.write_text('private boolean documentLoaded = false;',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_native_save_checkpoints(path)

    def test_periodic_autosave_lifecycle(self):
        self.run_phase('source')
        self.run_phase('source')
        text=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        self.assertEqual(text.count('AQUAWORD_PERIODIC_NATIVE_AUTOSAVE'),1)
        self.assertIn('AQUAWORD_AUTOSAVE_MS = 120_000L',text)
        self.assertIn('if (documentLoaded && isDocEditable',text)
        self.assertIn('dontSaveIfUnmodified=1',text)
        self.assertEqual(text.count('removeCallbacks(mAquaWordSaveTick)'),3)
        self.assertIn('postDelayed(mAquaWordSaveTick, AQUAWORD_AUTOSAVE_MS)',text)

    def test_periodic_autosave_drift_rejected(self):
        path=self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java'
        path.write_text('public class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_periodic_native_autosave(path)

    def test_docx_is_default_without_disabling_odt_open(self):
        self.run_phase('source')
        self.run_phase('source')
        base=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui'
        util=(base/'FileUtilities.java').read_text()
        activity=(base/'LibreOfficeUIActivity.java').read_text()
        self.assertIn('DEFAULT_WRITER_EXTENSION = ".docx"',util)
        self.assertIn('AQUAWORD_DEFAULT_DOCX',util)
        self.assertIn('CREATE_DOCUMENT_REQUEST_CODE) ? "docx"',activity)
        self.assertNotIn('CREATE_DOCUMENT_REQUEST_CODE) ? "odt"',activity)

    def test_docx_default_upstream_change_is_rejected(self):
        base=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui'
        (base/'FileUtilities.java').write_text('class NewFileUtilities {}')
        with self.assertRaises(M.PatchError):
            M.patch_default_docx(base/'FileUtilities.java',base/'LibreOfficeUIActivity.java')

    def test_saf_readonly_or_temporary_provider_supported(self):
        self.run_phase('source')
        self.run_phase('source')
        s=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(s.count('AQUAWORD_SAFE_SAF_PERMISSIONS'),1)
        self.assertEqual(s.count('persistDocumentPermission(uri, data);'),2)
        self.assertIn('Intent.FLAG_GRANT_READ_URI_PERMISSION',s)
        self.assertIn('SecurityException | IllegalArgumentException',s)
        self.assertIn('AQUAWORD_READONLY_DOCUMENT_GRANTS',s)
        self.assertIn('mAquaWordReadOnlyDocumentUris.add(uri.toString())',s)
        self.assertIn('permission.isReadPermission()',s)
        self.assertIn('!permission.isWritePermission()',s)
        self.assertIn('if (!readOnly)',s)
        self.assertEqual(s.count('AQUAWORD_READONLY_DOCUMENT_GRANTS'),1)

    def test_saf_upstream_drift_rejected(self):
        p=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        p.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_saf_permission_handling(p)

    def test_async_document_creation(self):
        self.run_phase('source')
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_ASYNC_DOCUMENT_CREATE'),1)
        self.assertIn('AquaWordCreateBlank', activity)
        self.assertIn('AQUAWORD_VERIFIED_BLANK_DOCX', activity)
        self.assertIn('"aquaword/blank.docx"', activity)
        self.assertIn('getContentResolver().openOutputStream(uri, "wt")', activity)
        self.assertIn('getContentResolver().openOutputStream(uri, "rwt")', activity)
        self.assertNotIn('getContentResolver().openOutputStream(uri, "w")', activity)
        self.assertNotIn('thread.run();', activity)
        self.assertNotIn('thread.join();', activity)
        self.assertIn('if (completed)\n                    open(uri);', activity)
        self.assertIn('boolean failed = false;',activity)
        self.assertIn('failed = true;',activity)
        self.assertIn('final boolean completed = !failed;',activity)
        self.assertNotIn('saved = true;',activity)
        self.assertIn('output.flush();',activity)
        self.assertLess(activity.index('output.flush();'), activity.index('final boolean completed = !failed;'))
        self.assertNotIn('createNewFile(uri, extension);\n\n                open(uri);', activity)

    def test_new_document_provider_must_truncate_and_reject_empty_template(self):
        """Source contract only: no stale ZIP tail or empty Writer launch.

        Providers may return an existing URI from ACTION_CREATE_DOCUMENT;
        Android documents that plain "w" does not guarantee truncation.
        """
        self.run_phase('source')
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        create=activity.split('private void createNewFile(final Uri uri, final String extension) {',1)[1].split(
            '/** Context menu item handling. */',1)[0]
        self.assertEqual(create.count('openOutputStream(uri, "wt")'),1)
        self.assertEqual(create.count('openOutputStream(uri, "rwt")'),1)
        self.assertLess(create.index('openOutputStream(uri, "wt")'),
                        create.index('openOutputStream(uri, "rwt")'))
        self.assertNotIn('openOutputStream(uri, "w")',create)
        self.assertNotIn('openOutputStream(uri);',create)
        self.assertIn('catch (java.io.FileNotFoundException | UnsupportedOperationException rejected)',create)
        self.assertIn('if (opened == null)',create)
        self.assertIn('throw new IOException("No truncating writable document URI")',create)
        self.assertIn('if (written <= 0L)',create)
        self.assertIn('throw new IOException("Empty document template")',create)
        self.assertLess(create.index('try (OutputStream output = opened)'),
                        create.index('final boolean completed = !failed;'))
        self.assertIn('if (completed)\n                    open(uri);',create)

    def test_new_document_provider_readback_verifies_sha_before_writer(self):
        """Source-only regression: corrupt/short/extra SAF bytes cannot launch Writer.

        This is not an Android provider or native engine runtime test.
        """
        self.run_phase('source')
        self.run_phase('source')  # patch remains idempotent
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        create=activity.split('private void createNewFile(final Uri uri, final String extension) {',1)[1].split(
            '/** Context menu item handling. */',1)[0]
        self.assertEqual(create.count('AQUAWORD_NEW_DOC_READBACK'),1)
        self.assertIn('java.security.MessageDigest.getInstance("SHA-256")',create)
        self.assertEqual(create.count('java.security.MessageDigest.getInstance("SHA-256")'),2)
        self.assertIn('expectedDigest.update(buffer, 0, bytesRead);',create)
        self.assertIn('getContentResolver().openInputStream(uri)',create)
        self.assertIn('if (readback == null)',create)
        self.assertIn('if (++noProgressReads >= 8)',create)
        self.assertIn('if (verified > written)',create)
        self.assertIn('if (verified != written ||',create)
        self.assertIn('!java.util.Arrays.equals(expectedDigest.digest(), actualDigest.digest())',create)
        self.assertIn('throw new IOException("New document failed SHA-256 readback verification")',create)
        self.assertLess(create.index('output.flush();'),create.index('readback.read(verifyBuffer)'))
        self.assertLess(create.index('readback.read(verifyBuffer)'),
                        create.index('final boolean completed = !failed;'))
        self.assertLess(create.index('if (verified != written ||'),
                        create.index('if (completed)\n                    open(uri);'))
        self.assertNotIn('getContentResolver().openOutputStream(uri, "w")',create)

    def test_async_create_rejects_changed_upstream(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('public class Changed {}', encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_async_new_document_creation(path)

    def test_focus_source_is_idempotent(self):
        self.run_phase('source')
        self.run_phase('source')
        main=(self.path/'browser/src/main.js').read_text(encoding='utf-8')
        css=(self.path/'browser/css/toolbar.css').read_text(encoding='utf-8')
        self.assertEqual(main.count('AQUAWORD_FOCUS_BOOTSTRAP_BEGIN'),1)
        self.assertEqual(css.count('AQUAWORD_FOCUS_CSS_BEGIN'),1)
        self.assertIn('ThisIsTheAndroidApp',main)
        self.assertIn('aquaword-focus-active',css)
        self.assertNotIn('body.aquaword-focus-active #map',css)
        self.assertNotIn('body.aquaword-focus-active #document-container',css)

    def test_focus_upstream_drift_is_rejected(self):
        main=self.path/'browser/src/main.js'
        main.write_text('console.log("new upstream entrypoint")',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_focus_bootstrap(main)

    def test_aurora_css_has_noncolliding_notebookbar_selector(self):
        skin=(ROOT/'branding/notebookbar.aurora.css').read_text(encoding='utf-8')
        self.assertIn('body #toolbar-wrapper.hasnotebookbar {',skin)
        self.assertNotIn('\\n#toolbar-wrapper.hasnotebookbar {',skin)
        self.run_phase('source')
        merged=(self.path/'browser/css/notebookbar.css').read_text()
        self.assertEqual(merged.count('body #toolbar-wrapper.hasnotebookbar {'),1)

    def test_idempotent_source(self):
        self.run_phase('source')
        self.run_phase('source')
        self.assertEqual((self.path/'browser/css/notebookbar.css').read_text().count('AQUAWORD_AURORA_BEGIN'),1)
        self.assertEqual((self.path/'browser/css/mobilewizard.css').read_text().count('AQUAWORD_AURORA_BEGIN'),1)
    def test_new_document_native_writer_only(self):
        self.run_phase('source')
        self.run_phase('source')
        c=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(c.count('AQUAWORD_WRITER_ONLY_NEW'),1)
        self.assertIn('CREATE_DOCUMENT_REQUEST_CODE',c)
        self.assertNotIn('expandFabMenu();',c)
    def test_reject_missing_new_document_handler(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_writer_only_home(path)
    def test_history_integration(self):
        self.run_phase('source')
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_PREEDIT_COPY'),1)
        self.assertIn('AquaWordHistory.capture(',activity)
        self.assertIn('AquaWordHistory.restoreToDestination(',activity)
        self.assertIn('R.id.action_aquaword_history',activity)
        self.assertTrue((self.path/'android/lib/src/main/java/org/libreoffice/androidlib/AquaWordHistory.java').is_file())
        menu=(self.path/'android/app/src/main/res/menu/view_menu.xml').read_text()
        self.assertEqual(menu.count('AQUAWORD_HISTORY_MENU'),1)
        ar=(self.path/'android/app/src/main/res/values-ar/aquaword_strings.xml')
        self.assertTrue(ar.is_file())
        self.assertIn('نسخ الأمان',ar.read_text(encoding='utf-8'))
        self.assertIn('wordprocessingml.document',activity)

    def test_missing_safety_copy_menu_aborts(self):
        path=self.path/'android/app/src/main/res/menu/view_menu.xml'
        path.write_text('<menu />',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_history_menu(path)

    def test_missing_activity_handler_aborts(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_history_activity(path)

    def test_gradle_labels(self):
        self.run_phase('source')
        s=(self.path/'android/app/build.gradle').read_text()
        self.assertIn('AquaWord Debug',s)
        self.assertIn('"AquaWord"',s)
    def test_template_id(self):
        self.run_phase('source')
        self.assertIn(M.APP_ID,(self.path/'android/app/appSettings.gradle.in').read_text())
    def test_manifest_icon(self):
        self.run_phase('source')
        self.assertIn('@mipmap/aquaword_launcher',(self.path/'android/app/src/main/AndroidManifest.xml').read_text())
    def test_content_uri_qa_provider_is_debug_only(self):
        self.run_phase('source')
        self.run_phase('source')
        debug=self.path/'android/app/src/debug'
        manifest=(debug/'AndroidManifest.xml').read_text(encoding='utf-8')
        paths=(debug/'res/xml/aquaword_qa_file_paths.xml').read_text(encoding='utf-8')
        # Native run 39929109992 failed because the debug manifest used the
        # exact same provider class as upstream's main FileProvider. Android
        # manifest merging matches provider declarations by android:name.
        # A distinct subclass preserves BOTH authorities and path mappings,
        # rather than tools:replace silently breaking upstream file sharing.
        import xml.etree.ElementTree as ET
        android='{http://schemas.android.com/apk/res/android}'
        provider=ET.fromstring(manifest).find('./application/provider')
        self.assertIsNotNone(provider)
        self.assertEqual(provider.get(android+'name'),
                         'org.libreoffice.androidapp.qa.QaFixtureFileProvider')
        self.assertNotEqual(provider.get(android+'name'),
                            'androidx.core.content.FileProvider')
        self.assertEqual(provider.get(android+'authorities'),
                         '${applicationId}.qa-documents')
        self.assertEqual(provider.get(android+'exported'), 'false')
        self.assertEqual(provider.get(android+'grantUriPermissions'), 'true')
        metadata=provider.find('meta-data')
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get(android+'name'),
                         'android.support.FILE_PROVIDER_PATHS')
        self.assertEqual(metadata.get(android+'resource'),
                         '@xml/aquaword_qa_file_paths')
        self.assertNotIn('tools:replace',manifest)
        self.assertIn('files-path name="fixtures"',paths)
        subclass=debug/'java/org/libreoffice/androidapp/qa/QaFixtureFileProvider.java'
        source=subclass.read_text(encoding='utf-8')
        self.assertIn('class QaFixtureFileProvider extends FileProvider',source)
        self.assertIn('public QaFixtureFileProvider()',source)
        self.assertFalse((self.path/'android/app/src/main/java/org/libreoffice/androidapp/qa/QaFixtureFileProvider.java').exists())
        launch=(debug/'java/org/libreoffice/androidapp/qa/QaOpenDocumentActivity.java').read_text(encoding='utf-8')
        self.assertIn('FileProvider.getUriForFile',launch)
        self.assertIn('FLAG_GRANT_WRITE_URI_PERMISSION',launch)
        self.assertIn('LOActivity.class',launch)
        self.assertIn('QaOpenDocumentActivity',manifest)
        self.assertFalse((self.path/'android/app/src/main/res/xml/aquaword_qa_file_paths.xml').exists())

    def test_five_icons(self):
        self.run_phase('source')
        for density in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
            self.assertTrue((self.path/f'android/app/src/main/res/mipmap-{density}/aquaword_launcher.png').is_file())
    def test_configured_id(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("android.defaultConfig { applicationId 'com.aquaword.app' }",encoding='utf-8')
        self.run_phase('postconfigure')
    def test_reject_unexpanded(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("applicationId '@APP_PACKAGE_NAME@'",encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.configured(self.path)
    def test_reject_wrong_id(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("applicationId 'org.libreoffice.androidapp'",encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.configured(self.path)
    def test_reject_gradle_change(self):
        path=self.path/'android/app/build.gradle'
        path.write_text('android {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_gradle_labels(path)
    def test_reject_manifest_change(self):
        path=self.path/'android/app/src/main/AndroidManifest.xml'
        path.write_text('<application/>',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_manifest_icon(path)
    def test_preflight_failure(self):
        (self.path/'android/app/appSettings.gradle.in').unlink()
        with self.assertRaises(M.PatchError):
            M.source(self.path)
        self.assertNotIn('AQUAWORD_AURORA_BEGIN',(self.path/'browser/css/notebookbar.css').read_text())
    def test_css_drift(self):
        self.run_phase('source')
        path=self.path/'browser/css/notebookbar.css'
        path.write_text('AQUAWORD_AURORA_BEGIN',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.append_css(path,ROOT/'branding/notebookbar.aurora.css')
    def test_requires_native_editor(self):
        (self.path/'engine').rename(self.path/'old-engine')
        with self.assertRaises(M.PatchError):
            M.validate_repo(self.path)
    def test_android_only(self):
        self.assertFalse((ROOT/'windows').exists())
    def test_document_canvas_unmodified(self):
        css=(ROOT/'branding/notebookbar.aurora.css').read_text()
        for selector in ['.leaflet-tile','.document-container','#map']:
            self.assertNotIn(selector,css)
    def test_patcher_no_shell_or_network(self):
        code=(ROOT/'scripts/apply_to_collabora.py').read_text()
        for snippet in ['subprocess.run(', 'requests.get(', 'os.system(']:
            self.assertNotIn(snippet,code)

if __name__=='__main__':
    unittest.main()
