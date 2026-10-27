package org.libreoffice.androidlib;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Properties;
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
            testCaptureIdentifierCollisionsPreserveExistingFiles(new File(root, "capture-collision"));
            testOversizedSnapshotMetadataRejected(new File(root, "size-limit"));
            testMalformedChecksumMetadataRejected(new File(root, "malformed-checksum"));
            testOpenedRestoreDescriptorRejectsSameSizeReplacement(new File(root, "opened-descriptor"));
            testHistoryDirectorySymlinkRejected(new File(root, "history-symlink"));
            testMetadataRenameFailurePreservesBytes(new File(root, "rename-failure"));
            testRetentionPreservesLatestSnapshotPerDocument(new File(root, "retention"));
            testWritebackLeasePinsSnapshotDuringRetention(new File(root, "writeback-lease"));
            testRestoreStagesBeforeOpeningProvider(new File(root, "restore-staging"));
            testRestoreReportsStagingCleanupFailure(new File(root, "restore-cleanup"));
            testRestoreRemovesDanglingStagingSymlink(new File(root, "restore-dangling-link"));
        } finally {
            deleteRecursively(root);
        }
    }

    /**
     * A collision at any capture-owned path must fail closed. In particular,
     * failed staging/rename cleanup must never truncate or delete a pre-existing
     * recovery file that this capture did not create.
     */
    private static void testCaptureIdentifierCollisionsPreserveExistingFiles(File root)
            throws Exception {
        String id = "1700000000000-00000000-0000-0000-0000-000000000001";
        String[] suffixes = {".partial", ".snapshot", ".properties", ".meta-partial"};
        for (int index = 0; index < suffixes.length; index++) {
            File caseRoot = new File(root, "case-" + index);
            File dir = new File(caseRoot, "aquaword-history");
            check(dir.mkdirs() || dir.isDirectory(),
                    "could not create collision fixture directory for " + suffixes[index]);
            File existing = new File(dir, id + suffixes[index]);
            byte[] sentinel = ("pre-existing recovery bytes " + suffixes[index]).getBytes("UTF-8");
            try (FileOutputStream output = new FileOutputStream(existing)) {
                output.write(sentinel);
                output.getFD().sync();
            }

            boolean rejected = false;
            try {
                AquaWordHistory.capture(caseRoot,
                        new ByteArrayInputStream("new recovery bytes".getBytes("UTF-8")),
                        "collision.docx", "content://collision/" + index, "pre-edit",
                        (source, target) -> {
                            throw new AssertionError("rename must not run after a path collision");
                        }, id);
            } catch (IOException expected) {
                rejected = true;
            }
            check(rejected, "capture did not reject occupied " + suffixes[index] + " path");
            check(Arrays.equals(sentinel, Files.readAllBytes(existing.toPath())),
                    "capture changed pre-existing " + suffixes[index] + " bytes");
            File[] entries = dir.listFiles();
            check(entries != null && entries.length == 1 && entries[0].equals(existing),
                    "capture left or removed files after " + suffixes[index] + " collision");
            System.out.println("PASS: capture preserves pre-existing " + suffixes[index] + " collision");
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
        check(recovered.size() == 1 && "saved".equals(recovered.get(0).kind),
                "history scan did not promote the matching staged metadata after abrupt process death");
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
     * Corrupt metadata must not create a selectable recovery row. Keep the bytes
     * and sidecars intact so validation never destroys evidence during listing.
     */
    private static void testMalformedChecksumMetadataRejected(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create malformed-checksum fixture");
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(), "could not create malformed-checksum history");
        byte[] payload = docxFixture();
        String invalid = String.format(Locale.ROOT, "%064d", 0).replace('0', 'g');
        String syntacticallyValid = String.format(Locale.ROOT, "%064d", 0);
        String[] ids = {"bad-content-hash", "bad-source-hash"};
        for (String id : ids) {
            File data = new File(dir, id + ".snapshot");
            File metadata = new File(dir, id + ".properties");
            Files.write(data.toPath(), payload);
            Properties props = new Properties();
            props.setProperty("name", id + ".docx");
            props.setProperty("timestamp", String.valueOf(System.currentTimeMillis()));
            props.setProperty("size", String.valueOf(payload.length));
            props.setProperty("sha256", "bad-content-hash".equals(id) ? invalid : syntacticallyValid);
            props.setProperty("source_sha256", "bad-source-hash".equals(id) ? invalid : syntacticallyValid);
            props.setProperty("kind", "saved");
            try (FileOutputStream output = new FileOutputStream(metadata)) {
                props.store(output, "malformed checksum regression");
            }
        }
        check(AquaWordHistory.list(root).isEmpty(),
                "metadata with non-hex SHA-256 must not be shown as a recovery item");
        for (String id : ids) {
            check(new File(dir, id + ".snapshot").isFile(),
                    "rejecting malformed metadata deleted the recovery bytes");
            check(new File(dir, id + ".properties").isFile(),
                    "rejecting malformed metadata deleted its forensic sidecar");
        }
        System.out.println("PASS: malformed SHA-256 metadata is excluded without deleting recovery evidence");
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
                    byte[] buffer = new byte[8192];
                    int count;
                    while ((count = opened.read(buffer)) != -1) {
                        if (count > 0) destination.write(buffer, 0, count);
                    }
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

    /**
     * The history directory itself is part of the app-private storage boundary.
     * A directory symlink must fail closed before listing or writing outside files.
     */
    private static void testHistoryDirectorySymlinkRejected(File root) throws Exception {
        File appFiles = new File(root, "app-files");
        File outside = new File(root, "outside");
        check(appFiles.mkdirs() || appFiles.isDirectory(), "could not create app-files fixture");
        check(outside.mkdirs() || outside.isDirectory(), "could not create outside fixture");
        File marker = new File(outside, "keep.bin");
        byte[] expected = "must remain unchanged".getBytes("UTF-8");
        Files.write(marker.toPath(), expected);
        File history = new File(appFiles, "aquaword-history");
        try {
            Files.createSymbolicLink(history.toPath(), outside.toPath());
        } catch (IOException | UnsupportedOperationException | SecurityException unavailable) {
            if (Files.isSymbolicLink(history.toPath())) throw unavailable;
            System.out.println("SKIP: host does not permit history-directory symlink fixture");
            return;
        }

        boolean rejected = false;
        try {
            AquaWordHistory.list(appFiles);
        } catch (IOException expectedFailure) {
            rejected = expectedFailure.getMessage() != null &&
                    expectedFailure.getMessage().contains("app-private storage");
        }
        check(rejected, "history directory symlink was followed outside app-private storage");
        check(Arrays.equals(expected, Files.readAllBytes(marker.toPath())),
                "history scan changed data outside app-private storage");
        File[] entries = outside.listFiles();
        check(entries != null && entries.length == 1 && marker.isFile(),
                "history scan created or removed files through the directory symlink");
        System.out.println("PASS: history-directory symlink is rejected before external directory access");
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

    /**
     * A slow SAF writeback must pin its recovery bytes while later checkpoints
     * force retention above the 60-snapshot limit. Otherwise a concurrent save
     * could delete the exact file currently being restored.
     */
    private static void testWritebackLeasePinsSnapshotDuringRetention(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create writeback-lease fixture directory");
        byte[] expected = "leased recovery bytes — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot pinned = AquaWordHistory.capture(
                root, new ByteArrayInputStream(expected), "leased.docx",
                "content://test/provider/leased-document", "saved");
        AquaWordHistory.WritebackLease lease = AquaWordHistory.holdForWriteback(pinned);
        try {
            for (int i = 0; i < 60; i++) {
                AquaWordHistory.capture(root, bytes("other-revision-" + i),
                        "other-" + i + ".txt", "content://test/provider/other-" + i, "saved");
                // Keep ordering deterministic so the leased checkpoint is the oldest.
                Thread.sleep(3L);
            }
            check(pinned.file.isFile(),
                    "retention deleted a snapshot while a provider writeback lease was active");
            check(AquaWordHistory.list(root).size() == 60,
                    "retention did not enforce the snapshot count cap while preserving the lease");
            ByteArrayOutputStream restored = new ByteArrayOutputStream();
            AquaWordHistory.restore(pinned, restored);
            check(Arrays.equals(expected, restored.toByteArray()),
                    "writeback lease did not preserve exact Arabic recovery bytes under retention pressure");
            System.out.println("PASS: active writeback lease pins exact recovery bytes under retention pressure");
        } finally {
            lease.close();
        }
    }

    /**
     * Persisted metadata must not bypass the hard per-snapshot size cap.
     * Use a tiny payload with oversized metadata so the regression stays cheap
     * on both Linux and Windows and proves rejection happens before hashing.
     */
    private static void testOversizedSnapshotMetadataRejected(File root) throws Exception {
        final long limit = 512L * 1024L * 1024L;
        check(AquaWordHistory.isWithinSnapshotSizeLimit(1L),
                "positive recovery snapshot size should be allowed");
        check(AquaWordHistory.isWithinSnapshotSizeLimit(limit),
                "exact maximum recovery snapshot size should be allowed");
        check(!AquaWordHistory.isWithinSnapshotSizeLimit(0L),
                "zero-byte recovery snapshot size must be rejected");
        check(!AquaWordHistory.isWithinSnapshotSizeLimit(-1L),
                "negative recovery snapshot size must be rejected");
        check(!AquaWordHistory.isWithinSnapshotSizeLimit(limit + 1L),
                "oversized recovery snapshot size must be rejected");

        check(root.mkdirs() || root.isDirectory(), "could not create size-limit fixture");
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(), "could not create size-limit history directory");
        File data = new File(dir, "oversized.snapshot");
        File metadata = new File(dir, "oversized.properties");
        Files.write(data.toPath(), new byte[] { 0x41 });
        Properties props = new Properties();
        props.setProperty("name", "oversized.docx");
        props.setProperty("timestamp", String.valueOf(System.currentTimeMillis()));
        props.setProperty("size", String.valueOf(limit + 1L));
        props.setProperty("sha256", "0000000000000000000000000000000000000000000000000000000000000000");
        props.setProperty("source_sha256", "0000000000000000000000000000000000000000000000000000000000000000");
        props.setProperty("kind", "saved");
        try (FileOutputStream output = new FileOutputStream(metadata)) {
            props.store(output, "oversized metadata regression");
        }

        check(AquaWordHistory.list(root).isEmpty(),
                "metadata-backed snapshot above the size cap must not enter recovery history");
        check(data.isFile() && metadata.isFile(),
                "rejected oversized recovery evidence must not be deleted by listing");
        System.out.println("PASS: oversized persisted recovery metadata is rejected before hashing or restore");
    }

    /**
     * A provider may truncate as soon as openOutputStream() is called. Recovery
     * must stage and verify all bytes before invoking that destination opener.
     * Mutating the original checkpoint after staging must not change restored bytes.
     */
    private static void testRestoreStagesBeforeOpeningProvider(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create restore-staging fixture");
        byte[] expected = "verified staged recovery — مرحبا / DOCX".getBytes("UTF-8");
        AquaWordHistory.Snapshot snapshot = AquaWordHistory.capture(
                root, new ByteArrayInputStream(expected), "staged.docx",
                "content://test/provider/staged-restore", "saved");
        byte[] replacement = expected.clone();
        replacement[0] ^= 0x01;
        final boolean[] opened = {false};
        ByteArrayOutputStream destination = new ByteArrayOutputStream();

        AquaWordHistory.restoreToDestination(snapshot, () -> {
            opened[0] = true;
            return destination;
        }, staged -> {
            // This runs only after a complete staged copy has passed SHA-256.
            // Simulate another writer replacing the original checkpoint just
            // before the SAF destination would be opened.
            Files.write(snapshot.file.toPath(), replacement);
        });

        check(opened[0], "destination opener was not called after verified staging");
        check(Arrays.equals(expected, destination.toByteArray()),
                "restore used mutated original bytes instead of the verified staged copy");
        File[] leftovers = new File(root, "aquaword-history").listFiles((parent, name) ->
                name.startsWith("restore-") && name.endsWith(".partial"));
        check(leftovers != null && leftovers.length == 0,
                "restore staging file was not cleaned after successful writeback");
        System.out.println("PASS: recovery staging verifies bytes before opening destination and isolates later source replacement");
    }

    /**
     * Staging cleanup is part of the recovery safety contract. If a staged
     * private copy cannot be removed, report it without hiding the original
     * restore failure and without opening the destructive SAF destination.
     */
    private static void testRestoreReportsStagingCleanupFailure(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create restore-cleanup fixture");
        byte[] expected = "cleanup failure must be visible — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot snapshot = AquaWordHistory.capture(
                root, new ByteArrayInputStream(expected), "cleanup.docx",
                "content://test/provider/restore-cleanup", "saved");
        final boolean[] opened = {false};
        final File[] residue = {null};
        IOException restoreFailure = null;
        try {
            AquaWordHistory.restoreToDestination(snapshot, () -> {
                opened[0] = true;
                return new ByteArrayOutputStream();
            }, staged -> {
                // Deterministically model a filesystem cleanup failure by
                // replacing the staged file with a non-empty directory.
                check(staged.delete(), "could not replace staging fixture");
                check(staged.mkdir(), "could not create blocking staging directory");
                residue[0] = staged;
                Files.write(new File(staged, "blocker.bin").toPath(), new byte[] {1});
            });
        } catch (IOException expectedFailure) {
            restoreFailure = expectedFailure;
        }

        check(restoreFailure != null, "restore accepted a replaced staging file");
        check(!opened[0], "destination opener ran after staging validation failed");
        boolean cleanupReported = false;
        for (Throwable suppressed : restoreFailure.getSuppressed()) {
            if (suppressed.getMessage() != null &&
                    suppressed.getMessage().contains("Could not remove private recovery staging file")) {
                cleanupReported = true;
                break;
            }
        }
        check(cleanupReported,
                "staging cleanup failure was silently lost or masked the original restore failure");
        check(residue[0] != null && residue[0].isDirectory(),
                "fixture did not preserve the deliberate cleanup failure");
        deleteRecursively(residue[0]);
        check(!residue[0].exists(), "could not clean deterministic residue fixture");
        System.out.println("PASS: failed recovery staging cleanup is reported as suppressed without opening destination");
    }

    /**
     * File.exists() follows symlinks and returns false for a dangling link.
     * Cleanup must still unlink that path instead of silently leaving it behind.
     */
    private static void testRestoreRemovesDanglingStagingSymlink(File root) throws Exception {
        check(root.mkdirs() || root.isDirectory(), "could not create dangling-link fixture");
        byte[] expected = "dangling staging link — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot snapshot = AquaWordHistory.capture(
                root, new ByteArrayInputStream(expected), "dangling.docx",
                "content://test/provider/dangling-stage", "saved");
        final boolean[] openerCalled = {false};
        final boolean[] symlinkCreated = {false};
        final File[] stagedPath = {null};
        IOException restoreFailure = null;
        try {
            AquaWordHistory.restoreToDestination(snapshot, () -> {
                openerCalled[0] = true;
                return new ByteArrayOutputStream();
            }, staged -> {
                stagedPath[0] = staged;
                check(staged.delete(), "could not replace staging file with dangling link");
                try {
                    Files.createSymbolicLink(staged.toPath(),
                            new File(root, "target-that-does-not-exist.bin").toPath());
                    symlinkCreated[0] = true;
                } catch (IOException | UnsupportedOperationException | SecurityException unavailable) {
                    throw new IOException("SYMLINK_FIXTURE_UNAVAILABLE", unavailable);
                }
            });
        } catch (IOException expectedFailure) {
            restoreFailure = expectedFailure;
        }

        if (!symlinkCreated[0]) {
            System.out.println("SKIP: host does not permit a dangling symlink cleanup fixture");
            return;
        }
        check(restoreFailure != null, "restore accepted a dangling staging symlink");
        check(!openerCalled[0], "destination opener ran for a dangling staging symlink");
        check(stagedPath[0] != null && !Files.isSymbolicLink(stagedPath[0].toPath()),
                "dangling staging symlink was not removed during cleanup");
        System.out.println("PASS: dangling recovery staging symlink is removed even when File.exists() is false");
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
