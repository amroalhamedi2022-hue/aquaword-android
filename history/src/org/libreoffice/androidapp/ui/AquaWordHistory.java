package org.libreoffice.androidapp.ui;

/*
 * AquaWord local pre-edit safety copies.
 * This independent helper uses only java.io + java.util and works offline.
 * A capture is NOT an autosave: edits made after opening are not snapshotted
 * until another capture. Android UI must describe it accurately.
 */
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Properties;
import java.util.UUID;

public final class AquaWordHistory {
    private static final String FOLDER = "aquaword-history";
    private static final String DATA_SUFFIX = ".snapshot";
    private static final String META_SUFFIX = ".properties";
    private static final long MAX_SINGLE_BYTES = 512L * 1024L * 1024L;
    private static final long MAX_TOTAL_BYTES = 1024L * 1024L * 1024L;
    private static final int MAX_SNAPSHOTS = 60;

    private AquaWordHistory() { }

    public static final class Snapshot {
        public final File file;
        public final String displayName;
        public final long createdMillis;
        public final long sizeBytes;
        private final String sha256;
        private Snapshot(File file, String displayName, long createdMillis,
                         long sizeBytes, String sha256) {
            this.file = file;
            this.displayName = displayName;
            this.createdMillis = createdMillis;
            this.sizeBytes = sizeBytes;
            this.sha256 = sha256;
        }
    }

    private static File folder(File appFilesDir) throws IOException {
        File target = new File(appFilesDir, FOLDER);
        if (!target.isDirectory() && !target.mkdirs())
            throw new IOException("Unable to create app-private snapshot directory");
        return target;
    }

    public static synchronized Snapshot capture(File appFilesDir, InputStream input,
                                                String name) throws IOException {
        if (input == null) throw new IOException("No readable input stream");
        File dir = folder(appFilesDir);
        String safeName = sanitizeName(name);
        String id = System.currentTimeMillis() + "-" + UUID.randomUUID().toString();
        File temp = new File(dir, id + ".partial");
        File data = new File(dir, id + DATA_SUFFIX);
        File meta = new File(dir, id + META_SUFFIX);
        File pendingMeta = new File(dir, id + ".meta-partial");
        MessageDigest sha = digest();
        long length = 0L;
        try {
            try (FileOutputStream output = new FileOutputStream(temp)) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (count == 0) continue;
                    length += count;
                    if (length > MAX_SINGLE_BYTES)
                        throw new IOException("Document exceeds local safety-copy size limit");
                    sha.update(buffer, 0, count);
                    output.write(buffer, 0, count);
                }
                output.getFD().sync();
            }
            Properties props = new Properties();
            props.setProperty("name", safeName);
            props.setProperty("timestamp", String.valueOf(System.currentTimeMillis()));
            props.setProperty("size", String.valueOf(length));
            props.setProperty("sha256", hex(sha.digest()));
            try (FileOutputStream metaOut = new FileOutputStream(pendingMeta)) {
                props.store(metaOut, "AquaWord private document snapshot");
                metaOut.getFD().sync();
            }
            if (!temp.renameTo(data)) throw new IOException("Could not commit snapshot bytes");
            if (!pendingMeta.renameTo(meta)) throw new IOException("Could not commit snapshot metadata");
            Snapshot saved = load(dir, data);
            if (saved == null) throw new IOException("Snapshot validation failed");
            trim(dir);
            return saved;
        } finally {
            temp.delete();
            pendingMeta.delete();
            if (!meta.exists()) data.delete();
        }
    }

    private static String sanitizeName(String name) {
        String n = name == null ? "" : name.replaceAll("[/\\\\\\r\\n\\t\\u0000-\\u001F]", "_").trim();
        if (n.length() > 180) n = n.substring(0, 180);
        return n.isEmpty() ? "Untitled Document" : n;
    }

    private static Snapshot load(File dir, File data) {
        if (!data.getParentFile().equals(dir) || !data.getName().endsWith(DATA_SUFFIX))
            return null;
        File propsPath = new File(dir, data.getName().replace(DATA_SUFFIX, META_SUFFIX));
        if (!propsPath.isFile()) return null;
        try (FileInputStream meta = new FileInputStream(propsPath)) {
            Properties props = new Properties();
            props.load(meta);
            String hash = props.getProperty("sha256", "");
            String name = sanitizeName(props.getProperty("name"));
            long length = Long.parseLong(props.getProperty("size", "-1"));
            long when = Long.parseLong(props.getProperty("timestamp", "0"));
            if (hash.length() != 64 || length != data.length() || when <= 0L)
                return null;
            return new Snapshot(data, name, when, length, hash);
        } catch (IOException | IllegalArgumentException e) {
            return null;
        }
    }

    private static List<Snapshot> readAll(File dir) {
        File[] all = dir.listFiles((d, name) -> name.endsWith(DATA_SUFFIX));
        List<Snapshot> results = new ArrayList<>();
        if (all == null) return results;
        for (File data : all) {
            Snapshot item = load(dir, data);
            if (item != null) results.add(item);
        }
        results.sort((a, b) -> Long.compare(b.createdMillis, a.createdMillis));
        return results;
    }

    public static synchronized List<Snapshot> list(File appFilesDir) throws IOException {
        return Collections.unmodifiableList(readAll(folder(appFilesDir)));
    }

    private static void trim(File dir) {
        List<Snapshot> all = readAll(dir);
        long total = 0;
        for (Snapshot item : all) total += item.sizeBytes;
        for (int index = all.size() - 1; index >= 0; index--) {
            Snapshot entry = all.get(index);
            if (index >= MAX_SNAPSHOTS || total > MAX_TOTAL_BYTES) {
                if (entry.file.delete()) {
                    new File(dir, entry.file.getName().replace(DATA_SUFFIX, META_SUFFIX)).delete();
                    total -= entry.sizeBytes;
                }
            }
        }
    }

    public static void restore(Snapshot snapshot, OutputStream target) throws IOException {
        if (snapshot == null || target == null) throw new IOException("Missing recovery destination");
        // Verify before writing any bytes to the selected user document.
        MessageDigest checksum = digest();
        try (DigestInputStream in = new DigestInputStream(new FileInputStream(snapshot.file), checksum)) {
            byte[] buffer = new byte[64 * 1024];
            while (in.read(buffer) != -1) { /* read to verify */ }
        }
        if (!hex(checksum.digest()).equals(snapshot.sha256))
            throw new IOException("Snapshot checksum mismatch — recovery cancelled");
        try (InputStream in = new FileInputStream(snapshot.file)) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) != -1) {
                if (n > 0) target.write(buffer, 0, n);
            }
            target.flush();
        }
    }

    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException ex) { throw new IllegalStateException(ex); }
    }

    private static String hex(byte[] digest) {
        final char[] digits = "0123456789abcdef".toCharArray();
        char[] result = new char[digest.length * 2];
        for (int i = 0; i < digest.length; i++) {
            int v = digest[i] & 0xff;
            result[i * 2] = digits[v >>> 4];
            result[i * 2 + 1] = digits[v & 15];
        }
        return new String(result);
    }
}
