package org.libreoffice.androidlib;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Regressions for the fsynced-data / metadata-commit crash window. */
public final class AquaWordHistoryCommitTest {
    private AquaWordHistoryCommitTest() { }

    public static void main(String[] args) throws Exception {
        if (args.length == 2 && "--crash-after-data-commit".equals(args[0])) {
            crashAfterDataCommit(new File(args[1]));
            throw new AssertionError("crash fixture returned without halting");
        }

        File root = Files.createTempDirectory("aquaword-meta-commit-").toFile();
        try {
            testProcessDeathBetweenDataAndMetadataCommit(new File(root, "process-death"));
            testOpenedRestoreDescriptorRejectsSameSizeReplacement(new File(root, "opened-descriptor"));
            testMetadataRenameFailurePreservesBytes(new File(root, "rename-failure"));
            testRetentionPreservesLatestSnapshotPerDocument(new File(root, "retention"));
        } finally {
            deleteRecursively(root);
        }
    }

    /**
     * Kill a child JVM at the exact seam after the fsynced snapshot has been
     * renamed into place but before its metadata is renamed. The parent then
     * exercises the real history scan/recovery path against those on-disk files.
     */
    private static void testProcessDeathBetweenDataAndMetadataCommit(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create process-death fixture directory");
        String executable = System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("win")
                ? "java.exe" : "java";
        File javaExecutable = new File(new File(System.getProperty("java.home"), "bin"), executable);
        Process child = new ProcessBuilder(javaExecutable.getAbsolutePath(), "-cp",
                System.getProperty("java.class.path"), AquaWordHistoryCommitTest.class.getName(),
                "--crash-after-data-commit", root.getAbsolutePath())
                .redirectErrorStream(true).start();
        if (!child.waitFor(15, java.util.concurrent.TimeUnit.SECONDS)) {
            child.destroyForcibly();
            throw new AssertionError("metadata crash fixture child did not terminate promptly");
        }
        check(child.exitValue() == 24,
                "child did not terminate at the data-committed/metadata-not-committed boundary");

        byte[] expected = Files.readAllBytes(new File(root, "expected-docx.bin").toPath());
        File dir = new File(root, "aquaword-history");
        File[] snapshots = dir.listFiles((parent, name) -> name.endsWith(".snapshot"));
        check(snapshots != null && snapshots.length == 1 && snapshots[0].length() == expected.length,
                "process death did not leave the complete committed snapshot bytes");
        String id = snapshots[0].getName().substring(0,
                snapshots[0].getName().length() - ".snapshot".length());
        check(!new File(dir, id + ".properties").exists(),
                "fixture unexpectedly committed metadata before process death");

        List<AquaWordHistory.Snapshot> recovered = AquaWordHistory.list(root);
        check(recovered.size() == 1 && "recovered".equals(recovered.get(0).kind),
                "history scan did not reconstruct metadata after abrupt process death");
        ByteArrayOutputStream restored = new ByteArrayOutputStream();
        AquaWordHistory.restore(recovered.get(0), restored);
        check(Arrays.equals(expected, restored.toByteArray()),
                "post-crash recovered DOCX bytes differ from the fsynced payload");
        check(new File(dir, id + ".properties").isFile(),
                "recovered metadata was not durably published");
        check(!new File(dir, id + ".meta-partial").exists(),
                "metadata recovery left a stale temporary metadata file");
        System.out.println("PASS: abrupt process death between snapshot and metadata commits recovers exact DOCX bytes");
    }

    private static void crashAfterDataCommit(File root) throws Exception {
        byte[] payload = docxFixture();
        Files.write(new File(root, "expected-docx.bin").toPath(), payload);
        AquaWordHistory.capture(root, new ByteArrayInputStream(payload),
                "metadata-crash.docx", "content://test/provider/process-death",
                "saved", (source, target) -> {
                    if (source.getName().endsWith(".meta-partial")) {
                        // This is after the .snapshot rename and before metadata publication.
                        Runtime.getRuntime().halt(24);
                    }
                    return source.renameTo(target);
                });
    }

    /**
     * A same-size regular file can replace a cached path after lease preflight.
     * Restore must hash the exact opened descriptor and reject it before the
     * first destination byte, rather than discovering corruption after SAF writes.
     */
    private static void testOpenedRestoreDescriptorRejectsSameSizeReplacement(File root)
            throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create opened-descriptor fixture directory");
        byte[] payload = "saved recovery bytes — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot snapshot = AquaWordHistory.capture(
                root, new ByteArrayInputStream(payload), "replace.docx",
                "content://test/provider/opened-descriptor", "saved");
        byte[] replacement = payload.clone();
        replacement[0] ^= 0x01;
        ByteArrayOutputStream destination = new ByteArrayOutputStream();

        try (AquaWordHistory.WritebackLease lease = AquaWordHistory.holdForWriteback(snapshot)) {
            // Model replacement after the lease's successful SHA check but
            // before restore opens the path. Length and canonical path still match.
            Files.delete(snapshot.file.toPath());
            Files.write(snapshot.file.toPath(), replacement);
            try (FileInputStream opened = new FileInputStream(snapshot.file)) {
                boolean rejected = false;
                try {
                    AquaWordHistory.verifyOpenedRestoreSource(snapshot, opened);
                    destination.write(opened.read(new byte[0]));
                } catch (IOException expected) {
                    rejected = expected.getMessage().contains("changed before restore");
                }
                check(rejected, "same-size replacement passed opened-descriptor verification");
            }
        }
        check(destination.size() == 0,
                "restore emitted bytes before verifying the opened recovery descriptor");
        System.out.println("PASS: same-size path replacement is rejected before restore writes");
    }

    private static void testMetadataRenameFailurePreservesBytes(File root) throws Exception {
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
    }


    /**
     * Retention must remove an older revision of a busy document before it
     * removes another document's only recovery point. This matters when a
     * newer save on one URI follows a failed SAF writeback on another URI.
     */
    private static void testRetentionPreservesLatestSnapshotPerDocument(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create retention fixture directory");
        try {
            AquaWordHistory.capture(root, bytes("A-recoverable"), "A.docx",
                    "content://test/provider/document-A", "saved");
            Thread.sleep(3L);
            AquaWordHistory.capture(root, bytes("B-old"), "B.docx",
                    "content://test/provider/document-B", "saved");
            Thread.sleep(3L);
            AquaWordHistory.capture(root, bytes("B-new"), "B.docx",
                    "content://test/provider/document-B", "saved");
            for (int i = 0; i < 58; i++) {
                AquaWordHistory.capture(root, bytes("other-" + i), "other-" + i + ".txt",
                        "content://test/provider/other-" + i, "saved");
            }

            List<AquaWordHistory.Snapshot> snapshots = AquaWordHistory.list(root);
            check(snapshots.size() == 60,
                    "retention should remove one older duplicate revision to stay within the count cap");
            AquaWordHistory.Snapshot a = null;
            AquaWordHistory.Snapshot b = null;
            int bRevisions = 0;
            for (AquaWordHistory.Snapshot snapshot : snapshots) {
                if ("A.docx".equals(snapshot.displayName)) a = snapshot;
                if ("B.docx".equals(snapshot.displayName)) {
                    b = snapshot;
                    bRevisions++;
                }
            }
            check(a != null,
                    "retention deleted document A's only/latest recovery point when another URI was newer");
            check(b != null && bRevisions == 1,
                    "retention did not discard the older B revision first");
            ByteArrayOutputStream restoredA = new ByteArrayOutputStream();
            AquaWordHistory.restore(a, restoredA);
            check(Arrays.equals("A-recoverable".getBytes("UTF-8"), restoredA.toByteArray()),
                    "document A recovery bytes changed after retention");
            ByteArrayOutputStream restoredB = new ByteArrayOutputStream();
            AquaWordHistory.restore(b, restoredB);
            check(Arrays.equals("B-new".getBytes("UTF-8"), restoredB.toByteArray()),
                    "retention did not preserve B's newest saved revision");
            System.out.println("PASS: retention preserves each document's latest recovery point and evicts older revisions first");
        } finally {
            deleteRecursively(root);
        }
    }

    private static ByteArrayInputStream bytes(String value) throws IOException {
        return new ByteArrayInputStream(value.getBytes("UTF-8"));
    }

    private static byte[] docxFixture() throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
            ZipEntry types = new ZipEntry("[Content_Types].xml");
            types.setTime(0L);
            zip.putNextEntry(types);
            zip.write("<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>"
                    .getBytes("UTF-8"));
            zip.closeEntry();
            ZipEntry document = new ZipEntry("word/document.xml");
            document.setTime(0L);
            zip.putNextEntry(document);
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
