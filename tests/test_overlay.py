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
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == R.id.action_open_file) {
            openDocument();
            return true;
        }
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
    def test_writer_creation_uses_real_docx_mime(self):
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document',activity)
        self.assertNotIn('FileUtilities.DEFAULT_WRITER_EXTENSION, "*/*"',activity)

    def test_native_saveback_reports_error_and_rejects_empty_files(self):
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        self.assertEqual(lib.count('AQUAWORD_NATIVE_SAF_SAVE_BACK'),1)
        self.assertIn('mTempFile.length() <= 0L',lib)
        self.assertIn('R.string.failed_to_save_file',lib)
        self.assertIn('output.flush();',lib)
        self.assertIn('bytes != mTempFile.length()',lib)
        self.assertNotIn('copyThread.join();',lib)

    def test_save_callbacks_create_real_history_checkpoints(self):
        self.run_phase('source')
        self.run_phase('source')
        lib=(self.path/'android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java').read_text()
        browser=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(lib.count('AQUAWORD_NATIVE_SAVE_CHECKPOINT'),1)
        self.assertIn('captureNativeSaveCheckpoint();',lib)
        self.assertIn('AquaWordHistory.capture(getFilesDir(), stream, name, sourceIdentity, "saved")',lib)
        self.assertIn('AquaWordNativeSaveCheckpoint',lib)
        self.assertIn('android.provider.OpenableColumns.DISPLAY_NAME',lib)
        self.assertIn('try (android.database.Cursor cursor',lib)
        self.assertIn('candidateName = cursor.getString(column)',lib)
        self.assertIn('aquaword_snapshot_saved',browser)
        self.assertIn('aquaword_snapshot_preedit',browser)
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
        self.assertIn('OutputStream output = getContentResolver().openOutputStream(uri, "w")', activity)
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
        self.assertIn('AquaWordHistory.restore(',activity)
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
        self.assertIn('androidx.core.content.FileProvider',manifest)
        self.assertIn('qa-documents',manifest)
        self.assertIn('android:exported="false"',manifest)
        self.assertIn('files-path name="fixtures"',paths)
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
