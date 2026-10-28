package com.aquaword.saffaultprovider;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import android.util.Log;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * CI-only adversarial provider. It accepts every write byte through a pipe but
 * durably stores only the first 128 bytes. Readback waits for the writer thread
 * to finish, making the truncation deterministic rather than a timing race.
 *
 * This standalone APK is never bundled into AquaWord or any release artifact.
 */
public final class TruncatingContentProvider extends ContentProvider {
    public static final String AUTHORITY = "com.aquaword.saffaultprovider.documents";
    public static final String MIME =
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    public static final int KEEP_BYTES = 128;
    private static final String TAG = "AquaWordSafFaultQA";
    private volatile CountDownLatch writeFinished = new CountDownLatch(0);
    private volatile IOException lastWriteError;

    @Override
    public boolean onCreate() {
        return getContext() != null;
    }

    private File document() throws FileNotFoundException {
        Context context = getContext();
        if (context == null) throw new FileNotFoundException("Provider context unavailable");
        return new File(context.getFilesDir(), "qa.docx");
    }

    private static FileNotFoundException asNotFound(String message, Exception cause) {
        FileNotFoundException failure = new FileNotFoundException(message);
        failure.initCause(cause);
        return failure;
    }

    @Override
    public String getType(Uri uri) {
        return MIME;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection,
                        String[] selectionArgs, String sortOrder) {
        String[] columns = projection == null
                ? new String[] { OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE }
                : projection;
        MatrixCursor cursor = new MatrixCursor(columns, 1);
        long size = 0L;
        try {
            File file = document();
            if (file.isFile()) size = file.length();
        } catch (FileNotFoundException ignored) {
            // A missing fixture is reported as zero bytes and rejected by openFile.
        }
        Object[] row = new Object[columns.length];
        for (int i = 0; i < columns.length; i++) {
            if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) row[i] = "qa.docx";
            else if (OpenableColumns.SIZE.equals(columns[i])) row[i] = size;
            else row[i] = null;
        }
        cursor.addRow(row);
        return cursor;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"qa.docx".equals(uri.getLastPathSegment())) {
            throw new FileNotFoundException("Unknown QA document");
        }
        File target = document();
        if (mode != null && mode.indexOf('w') >= 0) {
            // Implement the truncation semantics before returning the writer FD.
            try (FileOutputStream clear = new FileOutputStream(target, false)) {
                clear.getFD().sync();
            } catch (IOException failure) {
                throw asNotFound("Unable to initialize truncation fixture", failure);
            }

            final ParcelFileDescriptor[] pipe;
            try {
                pipe = ParcelFileDescriptor.createPipe();
            } catch (IOException failure) {
                throw asNotFound("Unable to create deterministic truncation pipe", failure);
            }
            final CountDownLatch completed = new CountDownLatch(1);
            writeFinished = completed;
            lastWriteError = null;
            Thread worker = new Thread(() -> {
                try (ParcelFileDescriptor.AutoCloseInputStream input =
                             new ParcelFileDescriptor.AutoCloseInputStream(pipe[0]);
                     FileOutputStream output = new FileOutputStream(target, false)) {
                    byte[] buffer = new byte[4096];
                    int remaining = KEEP_BYTES;
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        int keep = Math.min(count, remaining);
                        if (keep > 0) {
                            output.write(buffer, 0, keep);
                            remaining -= keep;
                        }
                        // Drain every byte so the app's output stream closes normally.
                    }
                    output.flush();
                    output.getFD().sync();
                    Log.i(TAG, "QA_PROVIDER_TRUNCATED_WRITE_COMPLETE stored=" +
                            target.length() + " cap=" + KEEP_BYTES);
                } catch (IOException failure) {
                    lastWriteError = failure;
                    Log.e(TAG, "QA_PROVIDER_WRITE_FAILED", failure);
                } finally {
                    completed.countDown();
                }
            }, "AquaWordSafFaultTruncator");
            worker.setDaemon(true);
            worker.start();
            return pipe[1];
        }

        if (mode != null && mode.indexOf('r') >= 0) {
            CountDownLatch completed = writeFinished;
            try {
                if (!completed.await(15, TimeUnit.SECONDS)) {
                    throw new FileNotFoundException("Timed out waiting for QA provider write");
                }
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw asNotFound("Interrupted waiting for QA provider write", interrupted);
            }
            IOException failure = lastWriteError;
            if (failure != null) throw asNotFound("QA provider write failed", failure);
            if (!target.isFile()) throw new FileNotFoundException("QA fixture is missing");
            try {
                return ParcelFileDescriptor.open(target, ParcelFileDescriptor.MODE_READ_ONLY);
            } catch (IOException failureToOpen) {
                throw asNotFound("Unable to open QA provider readback", failureToOpen);
            }
        }
        throw new FileNotFoundException("Unsupported QA provider mode: " + mode);
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException("Read/write fixture only");
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException("Read/write fixture only");
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException("Read/write fixture only");
    }
}
