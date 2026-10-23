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

            ByteArrayOutputStream out = new ByteArrayOutputStream();
            AquaWordHistory.restore(s, out);
            check(Arrays.equals(unicode, out.toByteArray()), "roundtrip");
            AquaWordHistory.Snapshot safe = AquaWordHistory.capture(
                root, new ByteArrayInputStream(new byte[]{1,2,3}), "../unsafe\nfile.docx");
            check(!safe.displayName.contains("/") && !safe.displayName.contains("\n"), "name sanitization");
            try (FileOutputStream flip = new FileOutputStream(s.file)) {
                flip.write(new byte[]{9,9,9,9,9});
            }
            ByteArrayOutputStream corrupt = new ByteArrayOutputStream();
            boolean rejected = false;
            try { AquaWordHistory.restore(s, corrupt); }
            catch (IOException expected) { rejected = true; }
            check(rejected && corrupt.size() == 0, "corrupt data rejected before write");
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
