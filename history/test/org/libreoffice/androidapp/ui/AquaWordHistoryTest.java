package org.libreoffice.androidapp.ui;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.libreoffice.androidlib.AquaWordHistory;
public class AquaWordHistoryTest {
    private static void check(boolean okay, String msg) {
        if (!okay) throw new AssertionError(msg);
    }
    public static void main(String[] args) throws Exception {
        File root = Files.createTempDirectory("aquaword-history-test").toFile();
        try {
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
            byte[] huge = new byte[1024];
            for (int i = 0; i < 65; i++) {
                AquaWordHistory.capture(root, new ByteArrayInputStream(huge), "sample"+i+".odt");
            }
            check(AquaWordHistory.list(root).size() <= 60, "retention count");
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
