package org.libreoffice.androidapp.ui;

import java.io.*;
import java.nio.file.*;
import java.util.*;
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
            // Different files can share both name and exact content.
            // They must remain distinct recovery histories.
            byte[] sameBytes = "another identical draft".getBytes("UTF-8");
            AquaWordHistory.Snapshot sourceA = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-a/123");
            AquaWordHistory.Snapshot sourceB = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-b/789");
            check(!sourceA.file.equals(sourceB.file), "distinct source identities were incorrectly merged");
            AquaWordHistory.Snapshot sourceAAgain = AquaWordHistory.capture(
                root, new ByteArrayInputStream(sameBytes), "duplicate-name.docx", "content://provider-a/123");
            check(sourceAAgain.file.equals(sourceA.file), "unchanged same-source duplicate not deduplicated");
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
            System.out.println("PASS: UTF-8, atomic capture, metadata, restore, corrupted data, safe names, unchanged-file deduplication, separate source histories, changed revisions, retention");
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
