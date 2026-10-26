package org.libreoffice.androidlib;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Regression for the fsynced-data / failed-metadata-rename crash window. */
public final class AquaWordHistoryCommitTest {
    private AquaWordHistoryCommitTest() { }

    public static void main(String[] args) throws Exception {
        File root = Files.createTempDirectory("aquaword-meta-commit-").toFile();
        try {
            byte[] payload = docxFixture();
            final boolean[] rejectedMetadataRename = {false};
            boolean failedAsExpected = false;
            try {
                AquaWordHistory.capture(root, new ByteArrayInputStream(payload),
                        "metadata-failure.docx", "content://test/provider/metadata-failure",
                        "saved", (source, target) -> {
                            if (source.getName().endsWith(".meta-partial")) {
                                rejectedMetadataRename[0] = true;
                                return false;
                            }
                            return source.renameTo(target);
                        });
            } catch (IOException expected) {
                failedAsExpected = true;
            }
            check(failedAsExpected && rejectedMetadataRename[0],
                    "fixture did not reach the metadata-rename failure");
            File dir = new File(root, "aquaword-history");
            File[] snapshots = dir.listFiles((parent, name) -> name.endsWith(".snapshot"));
            check(snapshots != null && snapshots.length == 1 && snapshots[0].length() == payload.length,
                    "complete fsynced snapshot bytes were deleted after metadata failure");
            File[] partials = dir.listFiles((parent, name) ->
                    name.endsWith(".partial") || name.endsWith(".meta-partial"));
            check(partials != null && partials.length == 0,
                    "failed metadata commit left incomplete temporary files");
            List<AquaWordHistory.Snapshot> recovered = AquaWordHistory.list(root);
            check(recovered.size() == 1 && "recovered".equals(recovered.get(0).kind),
                    "history scan did not reconstruct the committed orphan metadata");
            ByteArrayOutputStream restored = new ByteArrayOutputStream();
            AquaWordHistory.restore(recovered.get(0), restored);
            check(Arrays.equals(payload, restored.toByteArray()),
                    "recovered document bytes differ from the original Arabic/English DOCX");
            System.out.println("PASS: failed metadata rename preserves and recovers fsynced DOCX bytes");
        } finally {
            deleteRecursively(root);
        }
    }

    private static byte[] docxFixture() throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write("<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>"
                    .getBytes("UTF-8"));
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            zip.write(("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>" +
                    "<w:body><w:p><w:r><w:t>Hello مرحبا</w:t></w:r></w:p></w:body></w:document>")
                    .getBytes("UTF-8"));
            zip.closeEntry();
        }
        return bytes.toByteArray();
    }

    private static void deleteRecursively(File file) {
        if (file == null) return;
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) for (File child : children) deleteRecursively(child);
        }
        file.delete();
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
