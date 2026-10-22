package org.libreoffice.androidapp.qa;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;

import androidx.core.content.FileProvider;

import org.libreoffice.androidlib.LOActivity;

import java.io.File;

/**
 * DEBUG BUILD ONLY.
 * Launches the same real content:// document path used by Android SAF,
 * including both read + write grants. Never ship in release builds.
 *
 * The emulator harness first places the fixture in this app's private files.
 * This small trampoline is not a replacement editor or a mock renderer.
 */
public final class QaOpenDocumentActivity extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        final File docx = new File(getFilesDir(), "aquaword-research-ar.docx");
        if (!docx.isFile() || !docx.canRead()) {
            throw new IllegalStateException("Missing real Arabic DOCX fixture in app-private files");
        }
        final Uri uri = FileProvider.getUriForFile(
            this, getPackageName() + ".qa-documents", docx);
        final Intent intent = new Intent(this, LOActivity.class);
        intent.setAction(Intent.ACTION_EDIT);
        intent.setDataAndType(uri,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION |
            Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        startActivity(intent);
        finish();
    }
}
