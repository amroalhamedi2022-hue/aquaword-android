package org.libreoffice.androidapp.ui;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import org.libreoffice.androidlib.AquaWordHistory;
public class AquaWordHistoryTest {
    private static void crashDuringCapture(File root) throws Exception {
        // First commit a complete recovery point, then kill the child during a second capture.
        AquaWordHistory.capture(root, new ByteArrayInputStream(
                "durable checkpoint — مرحبا".getBytes("UTF-8")), "durable.docx",
                "content://durable/provider");
        InputStream interrupted = new InputStream() {
            private boolean wroteChunk;
            @Override public int read() {
                Runtime.getRuntime().halt(23);
                return -1;
            }
            @Override public int read(byte[] buffer, int offset, int length) {
                if (!wroteChunk) {
                    wroteChunk = true;
                    int count = Math.min(length, 4096);
                    Arrays.fill(buffer, offset, offset + count, (byte) 'C');
                    return count;
                }
                // Terminate the child JVM after bytes have reached the .partial file,
                // bypassing capture()'s finally block and normal stream close.
                Runtime.getRuntime().halt(23);
                return -1;
            }
        };
        AquaWordHistory.capture(root, interrupted, "process-killed.docx",
                "content://crash/provider");
        throw new AssertionError("crash fixture unexpectedly completed");
    }

    private static void testProcessDeathRecovery(File root) throws Exception {
        String executable = System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("win")
                ? "java.exe" : "java";
        File javaExecutable = new File(new File(System.getProperty("java.home"), "bin"), executable);
        Process child = new ProcessBuilder(javaExecutable.getAbsolutePath(), "-cp",
                System.getProperty("java.class.path"), AquaWordHistoryTest.class.getName(),
                "--crash-during-capture", root.getAbsolutePath())
                .redirectErrorStream(true).start();
        if (!child.waitFor(15, java.util.concurrent.TimeUnit.SECONDS)) {
            child.destroyForcibly();
            throw new AssertionError("crash fixture child did not terminate promptly");
        }
        check(child.exitValue() == 23, "child did not exit at the deliberate process-death point");
        File dir = new File(root, "aquaword-history");
        File[] partials = dir.listFiles((parent, name) -> name.endsWith(".partial"));
        check(partials != null && partials.length == 1 && partials[0].length() > 0,
                "process death did not leave a non-empty partial recovery write");
        List<AquaWordHistory.Snapshot> afterDeath = AquaWordHistory.list(root);
        check(afterDeath.size() == 1 && "durable.docx".equals(afterDeath.get(0).displayName),
                "completed checkpoint did not survive abrupt process death");
        ByteArrayOutputStream durableBytes = new ByteArrayOutputStream();
        AquaWordHistory.restore(afterDeath.get(0), durableBytes);
        check(Arrays.equals("durable checkpoint — مرحبا".getBytes("UTF-8"),
                durableBytes.toByteArray()), "persisted checkpoint bytes changed after process death");
        check(partials[0].isFile(), "recent incomplete write was deleted before grace period");
        long stale = System.currentTimeMillis() - 15L * 24L * 60L * 60L * 1000L;
        check(partials[0].setLastModified(stale), "could not age process-death fixture");
        List<AquaWordHistory.Snapshot> afterCleanup = AquaWordHistory.list(root);
        check(afterCleanup.size() == 1, "stale partial changed the committed recovery history");
        check(!partials[0].exists(), "stale process-death partial was not reclaimed");
    }

    private static void testOrphanSnapshotRecovery(File root) throws Exception {
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(), "could not create orphan recovery fixture");
        ByteArrayOutputStream packageBytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(packageBytes)) {
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write("<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>".getBytes("UTF-8"));
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            zip.write("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>مرحبا</w:t></w:r></w:p></w:body></w:document>".getBytes("UTF-8"));
            zip.closeEntry();
        }
        byte[] payload = packageBytes.toByteArray();
        File orphan = new File(dir, "crash-window.snapshot");
        try (FileOutputStream output = new FileOutputStream(orphan)) {
            output.write(payload);
            output.getFD().sync();
        }
        check(orphan.setLastModified(System.currentTimeMillis() - 2000L),
                "could not set orphan fixture timestamp");
        File empty = new File(dir, "empty.snapshot");
        try (FileOutputStream ignored = new FileOutputStream(empty)) { }

        List<AquaWordHistory.Snapshot> first = AquaWordHistory.list(root);
        check(first.size() == 1, "only a complete metadata-free snapshot should be recovered");
        AquaWordHistory.Snapshot recovered = first.get(0);
        check("recovered".equals(recovered.kind), "orphan recovery kind not recorded");
        check(recovered.file.equals(orphan), "recovery must retain the original committed bytes");
        check(recovered.displayName.startsWith("Recovered document ") &&
                        recovered.displayName.endsWith(".docx"),
                "missing source metadata must use a safe DOCX recovery label");
        check(new File(dir, "crash-window.properties").isFile(),
                "recovery metadata was not committed atomically");

        ByteArrayOutputStream restored = new ByteArrayOutputStream();
        AquaWordHistory.restore(recovered, restored);
        check(Arrays.equals(payload, restored.toByteArray()),
                "orphan recovery changed the committed document bytes");
        List<AquaWordHistory.Snapshot> second = AquaWordHistory.list(root);
        check(second.size() == 1 && second.get(0).file.equals(orphan),
                "repeated history scans must not duplicate recovered metadata");
        check(empty.isFile() && !new File(dir, "empty.properties").exists(),
                "empty orphan must be preserved but never offered as a restorable document");
    }


    /**
     * Orphan recovery must not truncate an existing metadata staging file.
     */
    private static void testOrphanRecoveryPreservesOccupiedMetadataStaging(File root)
            throws Exception {
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(),
                "could not create orphan metadata-staging fixture directory");
        ByteArrayOutputStream packageBytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(packageBytes)) {
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write("<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>".getBytes("UTF-8"));
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            zip.write("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>مرحبا</w:t></w:r></w:p></w:body></w:document>".getBytes("UTF-8"));
            zip.closeEntry();
        }
        byte[] payload = packageBytes.toByteArray();
        File orphan = new File(dir, "staging-collision.snapshot");
        try (FileOutputStream output = new FileOutputStream(orphan)) {
            output.write(payload);
            output.getFD().sync();
        }
        byte[] sentinel = "another interrupted metadata write — preserve me".getBytes("UTF-8");
        File occupied = new File(dir, "staging-collision.meta-partial");
        try (FileOutputStream output = new FileOutputStream(occupied)) {
            output.write(sentinel);
            output.getFD().sync();
        }

        List<AquaWordHistory.Snapshot> recovered = AquaWordHistory.list(root);
        check(recovered.isEmpty(),
                "orphan recovery should defer while its metadata staging path is occupied");
        check(Arrays.equals(sentinel, Files.readAllBytes(occupied.toPath())),
                "orphan recovery truncated or replaced a pre-existing metadata staging file");
        check(Arrays.equals(payload, Files.readAllBytes(orphan.toPath())),
                "orphan recovery changed the original committed snapshot bytes");
        check(!new File(dir, "staging-collision.properties").exists(),
                "orphan recovery published metadata after a staging collision");
    }

    /**
     * A valid snapshot basename may contain the data suffix before its final
     * extension. Recovery and retention must strip only the terminal suffix.
     */
    private static void testSnapshotSuffixInsideBasename(File root) throws Exception {
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(), "could not create suffix fixture directory");
        ByteArrayOutputStream packageBytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(packageBytes)) {
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write("<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>".getBytes("UTF-8"));
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            byte[] xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>مرحبا</w:t></w:r></w:p></w:body></w:document>".getBytes("UTF-8");
            zip.write(xml);
            zip.closeEntry();
        }
        byte[] payload = packageBytes.toByteArray();
        File orphan = new File(dir, "legacy.snapshot-copy.snapshot");
        try (FileOutputStream output = new FileOutputStream(orphan)) {
            output.write(payload);
            output.getFD().sync();
        }
        long old = System.currentTimeMillis() - 2L * 24L * 60L * 60L * 1000L;
        check(orphan.setLastModified(old), "could not age suffix fixture");

        List<AquaWordHistory.Snapshot> recovered = AquaWordHistory.list(root);
        check(recovered.size() == 1 && recovered.get(0).file.equals(orphan),
                "snapshot basename containing an embedded suffix was not recovered");
        File sidecar = new File(dir, "legacy.snapshot-copy.properties");
        check(sidecar.isFile(), "recovery created the wrong metadata sidecar path");
        ByteArrayOutputStream restored = new ByteArrayOutputStream();
        AquaWordHistory.restore(recovered.get(0), restored);
        check(Arrays.equals(payload, restored.toByteArray()),
                "embedded-suffix orphan recovery changed DOCX bytes");

        for (int i = 0; i < 60; i++) {
            byte[] bytes = ("retention-" + i).getBytes("UTF-8");
            AquaWordHistory.capture(root, new ByteArrayInputStream(bytes),
                    "retention-" + i + ".txt", "content://retention/" + i, "saved");
        }
        check(!orphan.exists(), "retention did not evict the oldest embedded-suffix snapshot");
        check(!sidecar.exists(), "retention deleted the snapshot but left its metadata sidecar");
        check(AquaWordHistory.list(root).size() <= 60,
                "retention exceeded the snapshot count after suffix-sidecar eviction");
        System.out.println("PASS: embedded .snapshot basename recovers and retention removes its exact sidecar");
    }

    private static String sha256Hex(byte[] bytes) throws Exception {
        byte[] digest = java.security.MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder result = new StringBuilder(digest.length * 2);
        for (byte value : digest) result.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return result.toString();
    }

    private static void writeSnapshotMetadata(File path, byte[] payload, String name)
            throws Exception {
        Properties metadata = new Properties();
        metadata.setProperty("name", name);
        metadata.setProperty("timestamp", String.valueOf(System.currentTimeMillis()));
        metadata.setProperty("size", String.valueOf(payload.length));
        metadata.setProperty("sha256", sha256Hex(payload));
        metadata.setProperty("source_sha256", String.join("", Collections.nCopies(64, "0")));
        metadata.setProperty("kind", "saved");
        try (FileOutputStream output = new FileOutputStream(path)) {
            metadata.store(output, "AquaWord symlink regression fixture");
        }
    }

    /**
     * A recovery scan must not follow a snapshot or metadata symlink outside
     * the app-private history directory, even if the target and checksum
     * metadata otherwise look like a valid saved revision.
     */
    private static void testRecoveryRejectsSymlinksOutsideHistoryDirectory(File root)
            throws Exception {
        File dir = new File(root, "aquaword-history");
        check(dir.mkdirs() || dir.isDirectory(), "could not create symlink fixture directory");
        byte[] payload = "private recovery fixture — لا تعرض ملفًا خارجيًا".getBytes("UTF-8");
        File outsideData = new File(root, "outside-payload.bin");
        File outsideMetadata = new File(root, "outside-metadata.properties");
        Files.write(outsideData.toPath(), payload);
        writeSnapshotMetadata(outsideMetadata, payload, "outside.docx");

        Path dataLink = new File(dir, "external-data.snapshot").toPath();
        Path metadataLink = new File(dir, "external-metadata.properties").toPath();
        try {
            Files.createSymbolicLink(dataLink, outsideData.toPath());
            File localPayload = new File(dir, "external-metadata.snapshot");
            Files.write(localPayload.toPath(), payload);
            Files.createSymbolicLink(metadataLink, outsideMetadata.toPath());
            writeSnapshotMetadata(new File(dir, "external-data.properties"),
                    payload, "external-data.docx");
        } catch (IOException | UnsupportedOperationException | SecurityException unsupported) {
            System.out.println("SKIP: symlink escape fixture unavailable on this host: " +
                    unsupported.getClass().getSimpleName());
            return;
        }

        List<AquaWordHistory.Snapshot> snapshots = AquaWordHistory.list(root);
        check(snapshots.isEmpty(),
                "recovery scan followed a symlink outside the private history directory");
        System.out.println("PASS: recovery scan rejects external payload and metadata symlinks");
    }

    /**
     * Recovery records must not accept symlink aliases even when their targets
     * stay inside the private directory. A metadata-free alias must not trigger
     * orphan reconstruction for bytes owned by another snapshot.
     */
    private static void testRecoveryRejectsInDirectorySymlinkAliases(File root) throws Exception {
        byte[] payload = "private recovery fixture — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot original = AquaWordHistory.capture(
                root, new ByteArrayInputStream(payload), "internal.docx",
                "content://test/provider/internal", "saved");
        File dir = new File(root, "aquaword-history");
        File originalMeta = new File(dir,
                original.file.getName().replace(".snapshot", ".properties"));
        Path dataAlias = new File(dir, "alias.snapshot").toPath();
        Path metadataAlias = new File(dir, "alias.properties").toPath();
        Path orphanAlias = new File(dir, "orphan-alias.snapshot").toPath();
        try {
            Files.createSymbolicLink(dataAlias, original.file.toPath());
            Files.createSymbolicLink(metadataAlias, originalMeta.toPath());
            List<AquaWordHistory.Snapshot> withPair = AquaWordHistory.list(root);
            check(withPair.size() == 1 && withPair.get(0).file.equals(original.file),
                    "in-directory payload/metadata symlink alias became a recovery entry");

            Files.createSymbolicLink(orphanAlias, original.file.toPath());
            List<AquaWordHistory.Snapshot> withOrphan = AquaWordHistory.list(root);
            check(withOrphan.size() == 1 && withOrphan.get(0).file.equals(original.file),
                    "metadata-free in-directory symlink alias became a recovered document");
            check(!new File(dir, "orphan-alias.properties").exists(),
                    "orphan recovery published metadata for a symlink alias");
            System.out.println("PASS: recovery scan rejects in-directory payload/metadata symlink aliases");
        } catch (IOException | UnsupportedOperationException | SecurityException unsupported) {
            System.out.println("SKIP: in-directory symlink alias fixture unavailable on this host: " +
                    unsupported.getClass().getSimpleName());
        }
    }

    /**
     * A Snapshot may outlive the history scan that produced it. Replacing its
     * committed path with a symlink afterwards must not pass checksum preflight,
     * even when the external target contains byte-identical data.
     */
    private static void testVerifyRejectsSymlinkSwapAfterListing(File root) throws Exception {
        byte[] payload = "cached recovery — مرحبا".getBytes("UTF-8");
        AquaWordHistory.Snapshot cached = AquaWordHistory.capture(
                root, new ByteArrayInputStream(payload), "cached.docx",
                "content://test/provider/cached", "saved");
        File external = new File(root, "external-identical-target.bin");
        Files.write(external.toPath(), payload);
        Files.delete(cached.file.toPath());
        try {
            Files.createSymbolicLink(cached.file.toPath(), external.toPath());
        } catch (IOException | UnsupportedOperationException | SecurityException unsupported) {
            System.out.println("SKIP: cached-snapshot symlink swap unavailable on this host: " +
                    unsupported.getClass().getSimpleName());
            return;
        }

        boolean preflightRejected = false;
        try {
            AquaWordHistory.verifyForRestore(cached);
        } catch (IOException expected) {
            preflightRejected = true;
        }
        check(preflightRejected,
                "cached Snapshot accepted a symlink replacement with identical external bytes");

        ByteArrayOutputStream destination = new ByteArrayOutputStream();
        boolean restoreRejected = false;
        try {
            AquaWordHistory.restore(cached, destination);
        } catch (IOException expected) {
            restoreRejected = true;
        }
        check(restoreRejected && destination.size() == 0,
                "restore wrote bytes from a path-substituted recovery snapshot");
        System.out.println("PASS: cached recovery snapshot rejects post-list symlink substitution");
    }

    private static void testActiveCaptureSurvivesStaleCleanup(File root) throws Exception {
        final byte[] first = "capture-start — مرحبا".getBytes("UTF-8");
        final byte[] second = " — capture-finished".getBytes("UTF-8");
        final java.util.concurrent.CountDownLatch firstChunkRead =
                new java.util.concurrent.CountDownLatch(1);
        final java.util.concurrent.CountDownLatch allowFinish =
                new java.util.concurrent.CountDownLatch(1);
        final java.util.concurrent.atomic.AtomicReference<AquaWordHistory.Snapshot> result =
                new java.util.concurrent.atomic.AtomicReference<>();
        final java.util.concurrent.atomic.AtomicReference<Throwable> failure =
                new java.util.concurrent.atomic.AtomicReference<>();
        InputStream slowProvider = new InputStream() {
            private int phase;
            private int offset;
            @Override public int read() throws IOException {
                byte[] one = new byte[1];
                int count = read(one, 0, 1);
                return count < 0 ? -1 : one[0] & 0xff;
            }
            @Override public int read(byte[] buffer, int start, int length) throws IOException {
                if (length == 0) return 0;
                if (phase == 0) {
                    int count = Math.min(length, first.length - offset);
                    System.arraycopy(first, offset, buffer, start, count);
                    offset += count;
                    if (offset == first.length) {
                        phase = 1;
                        offset = 0;
                        firstChunkRead.countDown();
                    }
                    return count;
                }
                if (phase == 1) {
                    try {
                        if (!allowFinish.await(5, java.util.concurrent.TimeUnit.SECONDS))
                            throw new IOException("timed out waiting to finish slow provider fixture");
                    } catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new IOException("slow provider fixture interrupted", interrupted);
                    }
                    phase = 2;
                }
                if (phase == 2) {
                    int count = Math.min(length, second.length - offset);
                    System.arraycopy(second, offset, buffer, start, count);
                    offset += count;
                    if (offset == second.length) phase = 3;
                    return count;
                }
                return -1;
            }
        };
        Thread worker = new Thread(() -> {
            try {
                result.set(AquaWordHistory.capture(root, slowProvider, "slow-capture.docx",
                        "content://slow-capture/provider"));
            } catch (Throwable error) {
                failure.set(error);
            }
        }, "slow-history-capture");
        worker.start();
        try {
            check(firstChunkRead.await(3, java.util.concurrent.TimeUnit.SECONDS),
                    "slow capture never began streaming");
            File dir = new File(root, "aquaword-history");
            File[] partials = dir.listFiles((parent, name) -> name.endsWith(".partial"));
            check(partials != null && partials.length == 1,
                    "slow capture did not expose its active partial file");
            long deadline = System.currentTimeMillis() + 3000L;
            while (partials[0].length() < first.length && System.currentTimeMillis() < deadline)
                Thread.sleep(10L);
            check(partials[0].length() >= first.length,
                    "first capture chunk was not flushed to the partial file");
            long stale = System.currentTimeMillis() - 15L * 24L * 60L * 60L * 1000L;
            check(partials[0].setLastModified(stale),
                    "could not age the active capture fixture");
            AquaWordHistory.list(root); // invokes stale-incomplete cleanup
            check(partials[0].isFile(),
                    "stale cleanup unlinked a capture that was still actively streaming");
            check(partials[0].lastModified() <= stale,
                    "blocked active capture timestamp changed before the stream resumed");
        } finally {
            allowFinish.countDown();
            worker.join(6000L);
            if (worker.isAlive()) {
                worker.interrupt();
                worker.join(1000L);
            }
        }
        check(!worker.isAlive(), "slow capture worker did not terminate");
        check(failure.get() == null, "active capture failed during concurrent cleanup: " + failure.get());
        AquaWordHistory.Snapshot captured = result.get();
        check(captured != null && captured.file.isFile(),
                "active capture did not commit after stale cleanup ran");
        byte[] expected = new byte[first.length + second.length];
        System.arraycopy(first, 0, expected, 0, first.length);
        System.arraycopy(second, 0, expected, first.length, second.length);
        ByteArrayOutputStream restored = new ByteArrayOutputStream();
        AquaWordHistory.restore(captured, restored);
        check(Arrays.equals(expected, restored.toByteArray()),
                "active capture bytes changed while stale cleanup ran");
    }

    private static void check(boolean okay, String msg) {
        if (!okay) throw new AssertionError(msg);
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2 && "--crash-during-capture".equals(args[0])) {
            crashDuringCapture(new File(args[1]));
            throw new AssertionError("crash fixture returned without halting");
        }
        File root = Files.createTempDirectory("aquaword-history-test").toFile();
        try {
            testProcessDeathRecovery(new File(root, "process-death-fixture"));
            testOrphanSnapshotRecovery(new File(root, "orphan-recovery-fixture"));
            testOrphanRecoveryPreservesOccupiedMetadataStaging(new File(root, "orphan-staging-collision-fixture"));
            testSnapshotSuffixInsideBasename(new File(root, "embedded-suffix-fixture"));
            testRecoveryRejectsSymlinksOutsideHistoryDirectory(new File(root, "symlink-escape-fixture"));
            testRecoveryRejectsInDirectorySymlinkAliases(new File(root, "symlink-alias-fixture"));
            testVerifyRejectsSymlinkSwapAfterListing(new File(root, "symlink-swap-fixture"));
            testActiveCaptureSurvivesStaleCleanup(new File(root, "active-capture-cleanup-fixture"));
            byte[] unicode = "Hello—مرحبا بالعالم\n📕 PDF & DOCX".getBytes("UTF-8");
            AquaWordHistory.Snapshot s = AquaWordHistory.capture(
                root, new ByteArrayInputStream(unicode), "قصتي.docx");
            check(s.file.isFile(), "archive missing");
            check(s.displayName.equals("قصتي.docx"), "Unicode metadata");
            check(s.sizeBytes == unicode.length, "size mismatched");
            check(AquaWordHistory.list(root).size() == 1, "list missing");
            AquaWordHistory.Snapshot same = AquaWordHistory.capture(
                root, new ByteArrayInputStream(unicode), "قصتي.docx");
            check(same.file.equals(s.file), "unchanged document should reuse snapshot");
            check(AquaWordHistory.list(root).size() == 1, "duplicate copy incorrectly created");
            AquaWordHistory.Snapshot changed = AquaWordHistory.capture(
                root, new ByteArrayInputStream("تغيير جديد".getBytes("UTF-8")), "قصتي.docx");
            check(!changed.file.equals(s.file), "edited document must receive new snapshot");
            check(AquaWordHistory.list(root).size() == 2, "new revision not captured");
            check("pre-edit".equals(s.kind), "original must be labeled before editing");
            AquaWordHistory.Snapshot savedVersion = AquaWordHistory.capture(
                root, new ByteArrayInputStream("saved writer revision".getBytes("UTF-8")),
                "قصتي.docx", "content://new/document", "saved");
            check("saved".equals(savedVersion.kind), "saved checkpoint metadata lost");
            // A provider may accept every output.write yet silently return
            // stale, truncated, appended or corrupted bytes on readback.
            byte[] expectedWriteback = "saved writer revision".getBytes("UTF-8");
            AquaWordHistory.verifyProviderWriteback(savedVersion,
                    new ByteArrayInputStream(expectedWriteback));
            boolean shortReadbackRejected = false;
            try { AquaWordHistory.verifyProviderWriteback(savedVersion,
                    new ByteArrayInputStream("saved writer".getBytes("UTF-8"))); }
            catch (IOException expected) { shortReadbackRejected = true; }
            check(shortReadbackRejected, "truncated SAF readback accepted");
            byte[] wrongWriteback = Arrays.copyOf(expectedWriteback, expectedWriteback.length);
            wrongWriteback[0] ^= 1;
            boolean corruptedReadbackRejected = false;
            try { AquaWordHistory.verifyProviderWriteback(savedVersion,
                    new ByteArrayInputStream(wrongWriteback)); }
            catch (IOException expected) { corruptedReadbackRejected = true; }
            check(corruptedReadbackRejected, "same-size corrupted SAF readback accepted");
            boolean appendedReadbackRejected = false;
            try { AquaWordHistory.verifyProviderWriteback(savedVersion,
                    new ByteArrayInputStream((new String(expectedWriteback, "UTF-8") + "x").getBytes("UTF-8"))); }
            catch (IOException expected) { appendedReadbackRejected = true; }
            check(appendedReadbackRejected, "appended SAF readback accepted");
            boolean missingReadbackRejected = false;
            try { AquaWordHistory.verifyProviderWriteback(savedVersion, null); }
            catch (IOException expected) { missingReadbackRejected = true; }
            check(missingReadbackRejected, "null SAF readback accepted");
            InputStream zeroReadback = new InputStream() {
                @Override public int read() { return 0; }
                @Override public int read(byte[] b, int off, int len) { return 0; }
            };
            boolean stalledReadbackRejected = false;
            try { AquaWordHistory.verifyProviderWriteback(savedVersion, zeroReadback); }
            catch (IOException expected) { stalledReadbackRejected = true; }
            check(stalledReadbackRejected, "non-progressing SAF readback accepted");
            AquaWordHistory.Snapshot matchingPreEdit = AquaWordHistory.capture(
                root, new ByteArrayInputStream("saved writer revision".getBytes("UTF-8")),
                "قصتي.docx", "content://new/document", "pre-edit");
            check(!matchingPreEdit.file.equals(savedVersion.file),
                    "saved and pre-edit versions must remain separately labeled");
            AquaWordHistory.Snapshot matchingSavedAgain = AquaWordHistory.capture(
                root, new ByteArrayInputStream("saved writer revision".getBytes("UTF-8")),
                "قصتي.docx", "content://new/document", "saved");
            check(matchingSavedAgain.file.equals(savedVersion.file),
                    "matching saved revision should safely deduplicate");

            check("saved".equals(AquaWordHistory.list(root).stream()
                    .filter(x -> x.file.equals(savedVersion.file)).findFirst().get().kind),
                    "saved checkpoint not reloaded");

            // Different files can share both name and exact content.
            // They must remain distinct recovery histories.
            byte[] sameBytes = "another identical draft".getBytes("UTF-8");
            AquaWordHistory.Snapshot sourceA = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-a/123");
            AquaWordHistory.Snapshot sourceB = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-b/789");
            check(!sourceA.file.equals(sourceB.file), "distinct source identities were incorrectly merged");
            // Native SAVE obtains its display name locally from the pre-edit
            // snapshot, never from a possibly hung cloud ContentResolver.
            check("duplicate-name.docx".equals(AquaWordHistory.preferredDisplayName(
                    root, "content://provider-a/123", "opaque-a")),
                    "same-source pre-edit name not recovered");
            check("duplicate-name.docx".equals(AquaWordHistory.preferredDisplayName(
                    root, "content://provider-b/789", "opaque-b")),
                    "second provider source not resolved independently");
            check("opaque_unknown".equals(AquaWordHistory.preferredDisplayName(
                    root, "content://missing/0", "opaque/unknown")),
                    "unknown source must use sanitized fallback");
            check("Untitled Document".equals(AquaWordHistory.preferredDisplayName(
                    root, null, null)), "missing source must have safe fallback");
            AquaWordHistory.capture(root,
                    new ByteArrayInputStream("later Writer revision".getBytes("UTF-8")),
                    "wrong-saved-name.docx", "content://provider-a/123", "saved");
            check("duplicate-name.docx".equals(AquaWordHistory.preferredDisplayName(
                    root, "content://provider-a/123", "opaque-a")),
                    "saved checkpoint must not override original pre-edit name");
            AquaWordHistory.Snapshot sourceAAgain = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-a/123");
            check(sourceAAgain.file.equals(sourceA.file), "unchanged same-source duplicate not deduplicated");
            // A matching metadata SHA does not prove existing bytes are healthy.
            // If a previously saved file suffered bit rot, recapture from the
            // still-readable input instead of reusing the corrupted backup.
            try (RandomAccessFile flip = new RandomAccessFile(sourceA.file, "rw")) {
                flip.seek(0);
                flip.write(0x7e);
            }
            AquaWordHistory.Snapshot repaired = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx",
                "content://provider-a/123");
            check(!repaired.file.equals(sourceA.file), "bit-rot backup was incorrectly reused");
            ByteArrayOutputStream repairedData = new ByteArrayOutputStream();
            AquaWordHistory.restore(repaired, repairedData);
            check(Arrays.equals(sameBytes, repairedData.toByteArray()), "fresh copy must be readable");

            // Preflight must succeed while the private recovery bytes are
            // intact, before a SAF provider is opened in truncating mode.
            AquaWordHistory.verifyForRestore(s);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            AquaWordHistory.restore(s, out);
            check(Arrays.equals(unicode, out.toByteArray()), "roundtrip");
            AquaWordHistory.Snapshot safe = AquaWordHistory.capture(
                root, new ByteArrayInputStream(new byte[]{1,2,3}), "../unsafe\nfile.docx");
            check(!safe.displayName.contains("/") && !safe.displayName.contains("\n"), "name sanitization");
            try (FileOutputStream flip = new FileOutputStream(s.file)) {
                flip.write(new byte[]{9,9,9,9,9});
            }
            // Simulate a previously captured snapshot being corrupted.
            // In Android the preflight runs before ContentResolver opens
            // a potentially destructive "wt"/"rwt" output stream.
            boolean preflightRejected = false;
            try { AquaWordHistory.verifyForRestore(s); }
            catch (IOException expected) { preflightRejected = true; }
            check(preflightRejected, "corrupt snapshot was accepted for provider write");
            ByteArrayOutputStream corrupt = new ByteArrayOutputStream();
            boolean rejected = false;
            try { AquaWordHistory.restore(s, corrupt); }
            catch (IOException expected) { rejected = true; }
            check(rejected && corrupt.size() == 0, "corrupt data rejected before write");
            AquaWordHistory.Snapshot missing = AquaWordHistory.capture(
                root, new ByteArrayInputStream("missing-file-test".getBytes("UTF-8")),
                "missing-file.docx", "content://missing/provider");
            check(missing.file.delete(), "could not simulate lost recovery snapshot");
            boolean missingRejected = false;
            try { AquaWordHistory.verifyForRestore(missing); }
            catch (IOException expected) { missingRejected = true; }
            check(missingRejected, "missing snapshot was accepted for provider write");
            // A provider can return immediate EOF without an I/O error. Never
            // publish an empty revision: restoring it could truncate the
            // user's destination while pretending to recover their document.
            int beforeEmpty = AquaWordHistory.list(root).size();
            for (String kind : new String[]{"pre-edit", "saved"}) {
                boolean emptyRejected = false;
                try {
                    AquaWordHistory.capture(root, new ByteArrayInputStream(new byte[0]),
                            "empty-provider.docx", "content://empty/provider", kind);
                } catch (IOException expected) {
                    emptyRejected = expected.getMessage().contains("empty document");
                }
                check(emptyRejected, "immediate-EOF " + kind + " snapshot accepted");
            }
            check(AquaWordHistory.list(root).size() == beforeEmpty,
                    "empty provider created a restorable recovery entry");
            File emptyHistoryDir = new File(root, "aquaword-history");
            File[] emptyPartials = emptyHistoryDir.listFiles((dir, filename) ->
                    filename.endsWith(".partial") || filename.endsWith(".meta-partial"));
            check(emptyPartials != null && emptyPartials.length == 0,
                    "empty provider left incomplete recovery files");

            // A broken SAF provider may violate InputStream's progress
            // contract. Capture must fail promptly and clean partial files,
            // rather than hold the synchronized history lock indefinitely.
            int beforeStall = AquaWordHistory.list(root).size();
            InputStream stalledProvider = new InputStream() {
                @Override public int read() { return 0; }
                @Override public int read(byte[] buffer, int off, int len) { return 0; }
            };
            boolean stallRejected = false;
            try {
                AquaWordHistory.capture(root, stalledProvider, "stalled.docx",
                        "content://stalled/provider");
            } catch (IOException expected) {
                stallRejected = expected.getMessage().contains("no progress");
            }
            check(stallRejected, "zero-progress provider must fail without hanging");
            check(AquaWordHistory.list(root).size() == beforeStall,
                    "failed provider must not create a committed recovery snapshot");
            File historyDir = new File(root, "aquaword-history");
            File[] partials = historyDir.listFiles((dir, filename) ->
                    filename.endsWith(".partial") || filename.endsWith(".meta-partial"));
            check(partials != null && partials.length == 0,
                    "failed provider left a temporary snapshot behind");

            // Simulate an app process killed midway through a capture. A
            // subsequent list/open should reclaim old incomplete writes, but
            // never delete orphan document bytes or a recent in-flight write.
            int intactBeforeCleanup = AquaWordHistory.list(root).size();
            long oldTimestamp = System.currentTimeMillis() - 15L * 24L * 60L * 60L * 1000L;
            File oldDataPartial = new File(historyDir, "killed.partial");
            File oldMetaPartial = new File(historyDir, "killed.meta-partial");
            File orphanMetadata = new File(historyDir, "metadata-only.properties");
            File orphanDocument = new File(historyDir, "only-document.snapshot");
            File recentPartial = new File(historyDir, "still-active.partial");
            for (File fixture : new File[]{oldDataPartial, oldMetaPartial,
                    orphanMetadata, orphanDocument, recentPartial}) {
                try (FileOutputStream stream = new FileOutputStream(fixture)) {
                    stream.write(new byte[]{1, 2, 3});
                }
            }
            for (File stale : new File[]{oldDataPartial, oldMetaPartial,
                    orphanMetadata, orphanDocument})
                check(stale.setLastModified(oldTimestamp), "could not age crash fixture");
            AquaWordHistory.list(root); // opening history triggers crash cleanup
            check(!oldDataPartial.exists() && !oldMetaPartial.exists() &&
                    !orphanMetadata.exists(), "week-old incomplete files not reclaimed");
            check(orphanDocument.isFile(), "orphan recovery document bytes were destroyed");
            check(recentPartial.isFile(), "recent in-flight snapshot was deleted");
            check(savedVersion.file.isFile(), "valid recovery checkpoint was deleted");
            check(AquaWordHistory.list(root).size() == intactBeforeCleanup,
                    "cleanup changed the committed history");
            check(recentPartial.delete(), "could not clean recent test fixture");

            // A brief intermittent zero read is recoverable; a successful
            // subsequent read must reset the consecutive-stall counter.
            InputStream intermittentProvider = new InputStream() {
                private int phase = 0;
                @Override public int read() { return phase++ < 3 ? 0 : -1; }
                @Override public int read(byte[] buffer, int off, int len) {
                    if (phase++ < 3) return 0;
                    if (phase == 4) { buffer[off] = 65; return 1; }
                    return -1;
                }
            };
            AquaWordHistory.Snapshot recoveredAfterPause = AquaWordHistory.capture(
                    root, intermittentProvider, "intermittent.docx",
                    "content://intermittent/provider");
            ByteArrayOutputStream afterPause = new ByteArrayOutputStream();
            AquaWordHistory.restore(recoveredAfterPause, afterPause);
            check(Arrays.equals(new byte[]{65}, afterPause.toByteArray()),
                    "intermittent provider lost valid document bytes");
            // Concurrent SAF writeback leases must survive retention pressure.
            AquaWordHistory.Snapshot pinned = AquaWordHistory.capture(
                root, new ByteArrayInputStream("in-flight SAF save".getBytes("UTF-8")),
                "pinned.docx", "content://slow-provider/active", "saved");
            AquaWordHistory.WritebackLease firstLease =
                    AquaWordHistory.holdForWriteback(pinned);
            AquaWordHistory.WritebackLease secondLease =
                    AquaWordHistory.holdForWriteback(pinned);
            firstLease.close();
            firstLease.close(); // idempotent, must not release second lease
            byte[] huge = new byte[1024];
            for (int i = 0; i < 65; i++) {
                AquaWordHistory.capture(root, new ByteArrayInputStream(huge), "sample"+i+".odt");
            }
            check(pinned.file.isFile(), "active SAF source deleted during retention");
            ByteArrayOutputStream pinnedCopy = new ByteArrayOutputStream();
            AquaWordHistory.restore(pinned, pinnedCopy);
            check("in-flight SAF save".equals(pinnedCopy.toString("UTF-8")),
                    "pinned recovery bytes changed");
            secondLease.close();
            secondLease.close();
            check(AquaWordHistory.list(root).size() <= 60,
                    "retention not restored after releasing the lease");
            boolean invalidLeaseRejected = false;
            try (AquaWordHistory.WritebackLease ignored =
                         AquaWordHistory.holdForWriteback(s)) {
                // Earlier test intentionally corrupted s.
            } catch (IOException expected) { invalidLeaseRejected = true; }
            check(invalidLeaseRejected, "corrupt recovery source was pinned");
            // A slow SAF/cloud *input* must not block unrelated history
            // operations while a pre-edit safety copy is being streamed.
            java.util.concurrent.CountDownLatch captureEntered =
                    new java.util.concurrent.CountDownLatch(1);
            java.util.concurrent.CountDownLatch allowCapture =
                    new java.util.concurrent.CountDownLatch(1);
            java.util.concurrent.atomic.AtomicReference<Throwable> captureFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            java.util.concurrent.atomic.AtomicReference<Throwable> concurrentCaptureListFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            byte[] cloudBytes = "blocked cloud safety copy".getBytes("UTF-8");
            InputStream blockedCloudInput = new InputStream() {
                private int offset;
                private boolean firstRead = true;
                @Override public int read() throws IOException {
                    byte[] one = new byte[1];
                    int count = read(one, 0, 1);
                    return count == -1 ? -1 : one[0] & 0xff;
                }
                @Override public int read(byte[] buffer, int off, int len) throws IOException {
                    if (firstRead) {
                        firstRead = false;
                        captureEntered.countDown();
                        try {
                            if (!allowCapture.await(5, java.util.concurrent.TimeUnit.SECONDS))
                                throw new IOException("Timed out waiting for cloud input");
                        } catch (InterruptedException interrupted) {
                            Thread.currentThread().interrupt();
                            throw new IOException(interrupted);
                        }
                    }
                    if (offset == cloudBytes.length) return -1;
                    int count = Math.min(len, cloudBytes.length - offset);
                    System.arraycopy(cloudBytes, offset, buffer, off, count);
                    offset += count;
                    return count;
                }
            };
            Thread captureWorker = new Thread(() -> {
                try {
                    AquaWordHistory.capture(root, blockedCloudInput,
                            "cloud-input.docx", "content://slow/cloud-input");
                } catch (Throwable failure) { captureFailure.set(failure); }
            }, "blocked-cloud-capture");
            captureWorker.start();
            Thread listDuringCapture = null;
            boolean listFinishedWhileInputBlocked = false;
            try {
                check(captureEntered.await(3, java.util.concurrent.TimeUnit.SECONDS),
                        "capture never reached simulated cloud input");
                listDuringCapture = new Thread(() -> {
                    try { AquaWordHistory.list(root); }
                    catch (Throwable failure) { concurrentCaptureListFailure.set(failure); }
                }, "list-during-cloud-capture");
                listDuringCapture.start();
                listDuringCapture.join(1500);
                listFinishedWhileInputBlocked = !listDuringCapture.isAlive();
            } finally {
                allowCapture.countDown();
                captureWorker.join(6000);
                if (listDuringCapture != null) listDuringCapture.join(6000);
            }
            check(listFinishedWhileInputBlocked,
                    "slow SAF input blocked unrelated history operations");
            check(!captureWorker.isAlive() &&
                    (listDuringCapture == null || !listDuringCapture.isAlive()),
                    "capture/list worker did not terminate");
            check(captureFailure.get() == null,
                    "cloud capture failed: " + captureFailure.get());
            check(concurrentCaptureListFailure.get() == null,
                    "history list during capture failed: " + concurrentCaptureListFailure.get());
            check(AquaWordHistory.list(root).stream().anyMatch(x ->
                    x.displayName.equals("cloud-input.docx") && x.sizeBytes == cloudBytes.length),
                    "blocked cloud capture was not committed");
            // A slow SAF/cloud destination must not monopolize the history
            // monitor. Another document must remain listable while restore()
            // is waiting for provider output. Retention must still pin bytes.
            AquaWordHistory.Snapshot slowRestore = AquaWordHistory.capture(
                    root, new ByteArrayInputStream("slow provider restore".getBytes("UTF-8")),
                    "slow-restore.docx", "content://slow/restore", "saved");
            java.util.concurrent.CountDownLatch restoreEntered =
                    new java.util.concurrent.CountDownLatch(1);
            java.util.concurrent.CountDownLatch allowRestore =
                    new java.util.concurrent.CountDownLatch(1);
            java.util.concurrent.atomic.AtomicReference<Throwable> restoreFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            java.util.concurrent.atomic.AtomicReference<Throwable> concurrentFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            OutputStream blockedProvider = new OutputStream() {
                private boolean firstWrite = true;
                @Override public void write(int b) throws IOException {
                    if (firstWrite) {
                        firstWrite = false;
                        restoreEntered.countDown();
                        try {
                            if (!allowRestore.await(5, java.util.concurrent.TimeUnit.SECONDS))
                                throw new IOException("Timed out waiting for simulated SAF provider");
                        } catch (InterruptedException interrupted) {
                            Thread.currentThread().interrupt();
                            throw new IOException(interrupted);
                        }
                    }
                }
            };
            Thread restoreWorker = new Thread(() -> {
                try { AquaWordHistory.restore(slowRestore, blockedProvider); }
                catch (Throwable failure) { restoreFailure.set(failure); }
            }, "blocked-saf-restore");
            restoreWorker.start();
            Thread otherDocument = null;
            boolean listFinishedWhileProviderBlocked = false;
            try {
                check(restoreEntered.await(3, java.util.concurrent.TimeUnit.SECONDS),
                        "SAF restore never reached simulated slow provider");
                otherDocument = new Thread(() -> {
                    try { AquaWordHistory.list(root); }
                    catch (Throwable failure) { concurrentFailure.set(failure); }
                }, "concurrent-history-list");
                otherDocument.start();
                otherDocument.join(1500);
                listFinishedWhileProviderBlocked = !otherDocument.isAlive();
                check(slowRestore.file.isFile(),
                        "active restore snapshot disappeared during provider write");
            } finally {
                allowRestore.countDown();
                restoreWorker.join(6000);
                if (otherDocument != null) otherDocument.join(6000);
            }
            check(listFinishedWhileProviderBlocked,
                    "slow SAF restore blocked unrelated history operations");
            check(!restoreWorker.isAlive() && (otherDocument == null || !otherDocument.isAlive()),
                    "restore/list worker did not terminate");
            check(restoreFailure.get() == null, "restore failed: " + restoreFailure.get());
            check(concurrentFailure.get() == null,
                    "concurrent history list failed: " + concurrentFailure.get());
            check(slowRestore.file.isFile(), "restore source lost after successful copy");

            // Deterministically block the checksum preflight itself, not
            // provider I/O. A lease must be registered under the monitor
            // before hashing, but the SHA-256 read must not hold that monitor.
            java.util.concurrent.CountDownLatch hashEntered =
                    new java.util.concurrent.CountDownLatch(1);
            java.util.concurrent.CountDownLatch allowHash =
                    new java.util.concurrent.CountDownLatch(1);
            File slowHashFile = new File(slowRestore.file.getAbsolutePath()) {
                @Override public boolean isFile() {
                    hashEntered.countDown();
                    try {
                        if (!allowHash.await(5, java.util.concurrent.TimeUnit.SECONDS))
                            throw new IllegalStateException("Timed out waiting for checksum test");
                    } catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new IllegalStateException(interrupted);
                    }
                    return super.isFile();
                }
            };
            java.lang.reflect.Field hashField =
                    AquaWordHistory.Snapshot.class.getDeclaredField("sha256");
            java.lang.reflect.Field sourceField =
                    AquaWordHistory.Snapshot.class.getDeclaredField("sourceHash");
            java.lang.reflect.Field parentPathField =
                    AquaWordHistory.Snapshot.class.getDeclaredField("canonicalParentPath");
            hashField.setAccessible(true);
            sourceField.setAccessible(true);
            parentPathField.setAccessible(true);
            java.lang.reflect.Constructor<AquaWordHistory.Snapshot> constructor =
                    AquaWordHistory.Snapshot.class.getDeclaredConstructor(
                            File.class, String.class, long.class, long.class,
                            String.class, String.class, String.class, String.class);
            constructor.setAccessible(true);
            AquaWordHistory.Snapshot slowHashSnapshot = constructor.newInstance(
                    slowHashFile, slowRestore.displayName, slowRestore.createdMillis,
                    slowRestore.sizeBytes, (String) hashField.get(slowRestore),
                    (String) sourceField.get(slowRestore), slowRestore.kind,
                    (String) parentPathField.get(slowRestore));
            java.util.concurrent.atomic.AtomicReference<Throwable> hashFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            java.util.concurrent.atomic.AtomicReference<Throwable> listFailure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            Thread checksumWorker = new Thread(() -> {
                try (AquaWordHistory.WritebackLease lease =
                             AquaWordHistory.holdForWriteback(slowHashSnapshot)) {
                    check(slowRestore.file.isFile(), "leased source disappeared");
                } catch (Throwable failure) { hashFailure.set(failure); }
            }, "slow-recovery-checksum");
            checksumWorker.start();
            Thread listDuringHash = null;
            boolean listedWhileHashBlocked = false;
            try {
                check(hashEntered.await(3, java.util.concurrent.TimeUnit.SECONDS),
                        "recovery checksum never reached synthetic slow filesystem");
                listDuringHash = new Thread(() -> {
                    try { AquaWordHistory.list(root); }
                    catch (Throwable failure) { listFailure.set(failure); }
                }, "list-during-recovery-checksum");
                listDuringHash.start();
                listDuringHash.join(1500);
                listedWhileHashBlocked = !listDuringHash.isAlive();
            } finally {
                allowHash.countDown();
                checksumWorker.join(6000);
                if (listDuringHash != null) listDuringHash.join(6000);
            }
            check(listedWhileHashBlocked,
                    "large recovery checksum blocked unrelated history operations");
            check(!checksumWorker.isAlive() &&
                    (listDuringHash == null || !listDuringHash.isAlive()),
                    "recovery checksum/list worker did not terminate");
            check(hashFailure.get() == null,
                    "leased checksum verification failed: " + hashFailure.get());
            check(listFailure.get() == null,
                    "history list during checksum failed: " + listFailure.get());

            // Restore now copies and verifies a private staging file before
            // destination writeback. A concurrent Writer mutation of the
            // original checkpoint must not alter the bytes being restored.
            byte[] multiBlock = new byte[128 * 1024];
            Arrays.fill(multiBlock, (byte) 0x41);
            AquaWordHistory.Snapshot changingDuringRestore = AquaWordHistory.capture(
                    root, new ByteArrayInputStream(multiBlock), "mutating.docx",
                    "content://mutation/restore", "saved");
            ByteArrayOutputStream mutatedDestination = new ByteArrayOutputStream();
            OutputStream mutateOnFirstWrite = new OutputStream() {
                private boolean modified;
                @Override public void write(int b) { mutatedDestination.write(b); }
                @Override public void write(byte[] b, int off, int len) throws IOException {
                    mutatedDestination.write(b, off, len);
                    if (!modified) {
                        modified = true;
                        try (RandomAccessFile file = new RandomAccessFile(
                                changingDuringRestore.file, "rw")) {
                            file.seek(64L * 1024L + 13L);
                            file.write(0x7f);
                        }
                    }
                }
            };
            AquaWordHistory.restore(changingDuringRestore, mutateOnFirstWrite);
            check(Arrays.equals(multiBlock, mutatedDestination.toByteArray()),
                    "restore did not isolate output from a concurrent mutation of the original checkpoint");

            AquaWordHistory.Snapshot truncatedDuringRestore = AquaWordHistory.capture(
                    root, new ByteArrayInputStream(multiBlock), "truncating.docx",
                    "content://truncation/restore", "saved");
            ByteArrayOutputStream truncatedDestination = new ByteArrayOutputStream();
            OutputStream truncateOnFirstWrite = new OutputStream() {
                private boolean truncated;
                @Override public void write(int b) { truncatedDestination.write(b); }
                @Override public void write(byte[] b, int off, int len) throws IOException {
                    truncatedDestination.write(b, off, len);
                    if (!truncated) {
                        truncated = true;
                        try (RandomAccessFile file = new RandomAccessFile(
                                truncatedDuringRestore.file, "rw")) {
                            file.setLength(64L * 1024L);
                        }
                    }
                }
            };
            AquaWordHistory.restore(truncatedDuringRestore, truncateOnFirstWrite);
            check(Arrays.equals(multiBlock, truncatedDestination.toByteArray()),
                    "restore output was truncated by a concurrent change to the original checkpoint");

            AquaWordHistory.Snapshot stableDuringRestore = AquaWordHistory.capture(
                    root, new ByteArrayInputStream(multiBlock), "stable.docx",
                    "content://stable/restore", "saved");
            ByteArrayOutputStream stableDestination = new ByteArrayOutputStream();
            AquaWordHistory.restore(stableDuringRestore, stableDestination);
            check(Arrays.equals(multiBlock, stableDestination.toByteArray()),
                    "stable multiblock restore did not preserve exact bytes");

            System.out.println("PASS: UTF-8, atomic capture, metadata, restore, corrupted data, safe names, saved revision labels, verified deduplication, bit-rot recovery, separate source histories, changed revisions, retention");
        } finally {
            delete(root);
        }
    }
    private static void delete(File path) {
        File[] child = path.listFiles();
        if (child != null) for (File f : child) delete(f);
        path.delete();
    }
}
