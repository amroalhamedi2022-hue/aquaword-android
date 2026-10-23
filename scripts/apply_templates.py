#!/usr/bin/env python3
"""Integrate generated offline AquaWord DOCX templates into native Android UI.

Run after apply_to_collabora.py --phase source and after template generation.
"""
from pathlib import Path
import argparse
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
JAVA_REL = "android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java"
ASSETS = ("research_en", "research_ar", "clinical_case", "study_notes")
PACKAGED_ASSETS = ASSETS + ("blank",)  # Internal native New Document asset


class PatchError(RuntimeError):
    pass


def require(path: Path) -> str:
    if not path.is_file():
        raise PatchError(f"Missing: {path}")
    return path.read_text(encoding="utf-8")


def replace_once(content: str, old: str, new: str, marker: str) -> str:
    if marker in content:
        return content
    if content.count(old) != 1:
        raise PatchError(f"Expected one unmodified upstream anchor: {old[:70]}")
    return content.replace(old, new, 1)


def patch_menu(path: Path) -> bool:
    content = require(path)
    marker = "AQUAWORD_TEMPLATE_MENU"
    anchor = '<item android:id="@+id/action_open_file"'
    insertion = ('<!-- AQUAWORD_TEMPLATE_MENU -->\n'
                 '    <item android:id="@+id/action_aquaword_templates"\n'
                 '        android:title="@string/aquaword_templates"\n'
                 '        app:showAsAction="never"/>\n    ' + anchor)
    patched = replace_once(content, anchor, insertion, marker)
    if patched == content:
        return False
    path.write_text(patched, encoding="utf-8")
    return True


def patch_strings(path: Path) -> bool:
    content = require(path)
    marker = '<string name="aquaword_templates">'
    addition = '''    <string name="aquaword_templates">Document templates</string>
    <string name="aquaword_template_research_en">Academic research (English)</string>
    <string name="aquaword_template_research_ar">Academic research (Arabic)</string>
    <string name="aquaword_template_clinical">Clinical case report</string>
    <string name="aquaword_template_notes">High-yield study notes</string>
    <string name="aquaword_template_save_failed">Unable to create document from template</string>
'''
    if marker in content:
        return False
    if content.count("</resources>") != 1:
        raise PatchError("Unexpected strings resources")
    path.write_text(content.replace("</resources>", addition + "</resources>"), encoding="utf-8")
    return True


def patch_activity(path: Path) -> bool:
    content = require(path)
    if "// AQUAWORD_TEMPLATES_V1" in content:
        return False
    field = "    private static final int AQUAWORD_RESTORE_REQUEST_CODE = 4477;"
    if content.count(field) != 1:
        raise PatchError("Missing AquaWord history integration anchor")
    content = content.replace(field, field + '''
    // AQUAWORD_TEMPLATES_V1: offline editable DOCX templates, saved through SAF.
    private static final int AQUAWORD_TEMPLATE_REQUEST_CODE = 4488;
    private String pendingAquaWordTemplate;
''')
    menu = '''        if (item.getItemId() == R.id.action_open_file) {
            openDocument();
            return true;
        }'''
    if content.count(menu) != 1:
        raise PatchError("Missing native open-menu anchor")
    content = content.replace(menu, '''        if (item.getItemId() == R.id.action_aquaword_templates) {
            showAquaWordTemplates();
            return true;
        }
''' + menu)
    before = "    /** File name extensions for which an empty document template is bundled in the assets. */"
    if content.count(before) != 1:
        raise PatchError("Missing template methods insertion anchor")
    methods = '''    /** Creates a genuine editable DOCX file from packaged AquaWord templates. */
    private void showAquaWordTemplates() {
        final String[] templateIds = { "research_en", "research_ar", "clinical_case", "study_notes" };
        final String[] choices = {
            getString(R.string.aquaword_template_research_en),
            getString(R.string.aquaword_template_research_ar),
            getString(R.string.aquaword_template_clinical),
            getString(R.string.aquaword_template_notes)
        };
        new AlertDialog.Builder(this)
            .setTitle(R.string.aquaword_templates)
            .setItems(choices, (dialog, which) -> {
                if (which < 0 || which >= templateIds.length) return;
                pendingAquaWordTemplate = templateIds[which];
                Intent output = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                output.addCategory(Intent.CATEGORY_OPENABLE);
                output.setType("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
                output.putExtra(Intent.EXTRA_TITLE, "AquaWord_" + pendingAquaWordTemplate + ".docx");
                startActivityForResult(output, AQUAWORD_TEMPLATE_REQUEST_CODE);
            })
            .setNegativeButton(android.R.string.cancel, null)
            .show();
    }

'''
    content = content.replace(before, methods + before)
    marker = '''        switch (requestCode) {
            case AQUAWORD_RESTORE_REQUEST_CODE: {'''
    template_case = '''        switch (requestCode) {
            case AQUAWORD_TEMPLATE_REQUEST_CODE: {
                final String template = pendingAquaWordTemplate;
                pendingAquaWordTemplate = null;
                if (resultCode != RESULT_OK || data == null || data.getData() == null || template == null)
                    break;
                if (!Arrays.asList("research_en", "research_ar", "clinical_case", "study_notes").contains(template))
                    break;
                final Uri destination = data.getData();
                // ACTION_CREATE_DOCUMENT may grant persistable access. Retain it
                // so a template document remains available after restarting.
                persistDocumentPermission(destination, data);
                new Thread(() -> {
                    boolean saved = false;
                    try (InputStream source = getAssets().open("aquaword/" + template + ".docx");
                         OutputStream output = getContentResolver().openOutputStream(destination, "w")) {
                        if (output == null) throw new IOException("No writable document destination");
                        byte[] buffer = new byte[64 * 1024];
                        int count;
                        long written = 0L;
                        while ((count = source.read(buffer)) != -1) {
                            if (count > 0) {
                                output.write(buffer, 0, count);
                                written += count;
                            }
                        }
                        if (written < 500L)
                            throw new IOException("Packaged DOCX template is incomplete");
                        output.flush();
                        saved = true;
                    } catch (Exception problem) {
                        Log.e(LOGTAG, "AquaWord template creation failed", problem);
                    }
                    final boolean ready = saved;
                    runOnUiThread(() -> {
                        if (isFinishing() || isDestroyed()) return;
                        if (ready) open(destination);
                        else Toast.makeText(this, R.string.aquaword_template_save_failed, Toast.LENGTH_LONG).show();
                    });
                }, "AquaWordCreateTemplate").start();
                break;
            }
            case AQUAWORD_RESTORE_REQUEST_CODE: {'''
    if content.count(marker) != 1:
        raise PatchError("Missing AquaWord history result handler anchor")
    content = content.replace(marker, template_case)
    # SAF document pickers may rotate or recreate the Activity before
    # returning. Preserve both template and restore intents across recreation.
    save_anchor = '        outState.putInt(FILTER_MODE_KEY, filterMode);'
    restore_anchor = '        filterMode = savedInstanceState.getInt(FILTER_MODE_KEY, FileUtilities.ALL);'
    if content.count(save_anchor) != 1 or content.count(restore_anchor) != 1:
        raise PatchError("Upstream Activity saved-state hooks changed")
    content = content.replace(save_anchor, '''        // AQUAWORD_PENDING_SAF_RECOVERY
        outState.putString("aquaword.pending_template", pendingAquaWordTemplate);
        outState.putString("aquaword.pending_restore",
            pendingAquaWordRestore == null ? null : pendingAquaWordRestore.file.getName());
''' + save_anchor, 1)
    content = content.replace(restore_anchor, '''        pendingAquaWordTemplate = savedInstanceState.getString("aquaword.pending_template");
        final String previousSnapshotId = savedInstanceState.getString("aquaword.pending_restore");
        if (previousSnapshotId != null) {
            try {
                for (AquaWordHistory.Snapshot version : AquaWordHistory.list(getFilesDir())) {
                    if (version.file.getName().equals(previousSnapshotId)) {
                        pendingAquaWordRestore = version;
                        break;
                    }
                }
            } catch (IOException restoreFailure) {
                Log.w(LOGTAG, "Unable to reload pending snapshot after rotation", restoreFailure);
            }
        }
''' + restore_anchor, 1)
    path.write_text(content, encoding="utf-8")
    return True


def copy_template_files(repo: Path) -> int:
    dest = repo / "android/app/src/main/assets/aquaword"
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in PACKAGED_ASSETS:
        src = ROOT / "templates/generated" / (name + ".docx")
        if not src.is_file() or src.stat().st_size < 500:
            raise PatchError(f"Generate template first: {src}")
        out = dest / src.name
        if not out.is_file() or out.read_bytes() != src.read_bytes():
            shutil.copyfile(src, out)
            count += 1
    return count


def patch_arabic(path: Path) -> bool:
    content = require(path)
    marker = '<string name="aquaword_templates">'
    if marker in content:
        return False
    ar = '''    <string name="aquaword_templates">قوالب المستندات</string>
    <string name="aquaword_template_research_en">بحث أكاديمي (إنجليزي)</string>
    <string name="aquaword_template_research_ar">بحث أكاديمي (عربي)</string>
    <string name="aquaword_template_clinical">تقرير حالة سريرية</string>
    <string name="aquaword_template_notes">ملخصات دراسية مركزة</string>
    <string name="aquaword_template_save_failed">تعذّر إنشاء مستند من القالب</string>
'''
    if content.count("</resources>") != 1:
        raise PatchError("Invalid Arabic strings XML")
    path.write_text(content.replace("</resources>", ar + "</resources>"), encoding="utf-8")
    return True


def integrate(repo: Path) -> None:
    paths = (
        repo / JAVA_REL,
        repo / "android/app/src/main/res/menu/view_menu.xml",
        repo / "android/app/src/main/res/values/strings.xml",
        repo / "android/app/src/main/res/values-ar/aquaword_strings.xml",
    )
    for path in paths:
        require(path)
    for name in PACKAGED_ASSETS:
        doc = ROOT / "templates/generated" / (name + ".docx")
        if not doc.exists():
            raise PatchError(f"Missing generated document {doc}")
    print("Template menu:", patch_menu(paths[1]))
    print("Template resources:", patch_strings(paths[2]))
    print("Arabic template resources:", patch_arabic(paths[3]))
    print("Native new-template dialog:", patch_activity(paths[0]))
    print("Templates copied:", copy_template_files(repo))


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--repo", required=True, type=Path)
    path = args.parse_args().repo.resolve()
    try:
        integrate(path)
    except PatchError as error:
        sys.exit("Template integration aborted: " + str(error))
