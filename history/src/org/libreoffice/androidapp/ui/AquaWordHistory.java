package org.libreoffice.androidlib;

/*
 * AquaWord local pre-edit and native post-save recovery checkpoints.
 * This helper is independent of UI and works offline.
 * A saved checkpoint is created only after Writer's SAVE notification.
 * Never present this as continuous recording of every editing action.
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
        private final String sourceHash;
        public final String kind;
        private Snapshot(File file, String displayName, long createdMillis,
                         long sizeBytes, String sha256, String sourceHash, String kind) {
            this.file = file;
            this.displayName = displayName;
            this.createdMillis = createdMillis;
            this.sizeBytes = sizeBytes;
            this.sha256 = sha256;
            this.sourceHash = sourceHash;
            this.kind = kind;
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
        return capture(appFilesDir, input, name, "legacy-unspecified-source");
    }

    /** Source identity separates two distinct documents that share a file name. */
    public static synchronized Snapshot capture(File appFilesDir, InputStream input,
                                                String name, String sourceIdentity) throws IOException {
        return capture(appFilesDir, input, name, sourceIdentity, "pre-edit");
    }

    /** Saved revisions and pre-edit recovery versions use the same validated format. */
    public static synchronized Snapshot capture(File appFilesDir, InputStream input,
                                                String name, String sourceIdentity,
                                                String kind) throws IOException {
        if (!"pre-edit".equals(kind) && !"saved".equals(kind))
            throw new IOException("Unknown snapshot type");
        if (input == null) throw new IOException("No readable input stream");
        if (sourceIdentity == null || sourceIdentity.isEmpty())
            throw new IOException("Document source identity is required");
        String sourceHash = hex(digest().digest(sourceIdentity.getBytes(StandardCharsets.UTF_8)));
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
                int noProgressReads = 0;
                while ((count = input.read(buffer)) != -1) {
                    // A nonconforming cloud/provider stream can repeatedly
                    // return zero for a nonempty buffer. Never spin forever
                    // while holding the synchronized history lock.
                    if (count == 0) {
                        if (++noProgressReads >= 8)
                            throw new IOException("Document input stream made no progress");
                        continue;
                    }
                    noProgressReads = 0;
                    length += count;
                    if (length > MAX_SINGLE_BYTES)
                        throw new IOException("Document exceeds local safety-copy size limit");
                    sha.update(buffer, 0, count);
                    output.write(buffer, 0, count);
                }
                output.getFD().sync();
            }
            String newHash = hex(sha.digest());
            // An unchanged document already has a safety copy; reopening it
            // should not consume more storage. Compare with its newest entry.
            for (Snapshot previous : readAll(dir)) {
                if (!previous.displayName.equals(safeName) ||
                        !previous.sourceHash.equals(sourceHash) ||
                        !previous.kind.equals(kind))
                    continue;
                if (previous.sizeBytes == length && previous.sha256.equals(newHash)
                        && verifyBytes(previous))
                    return previous;
                break; // A changed document needs its own point-in-time copy.
            }
            Properties props = new Properties();
            props.setProperty("name", safeName);
            props.setProperty("timestamp", String.valueOf(System.currentTimeMillis()));
            props.setProperty("size", String.valueOf(length));
            props.setProperty("sha256", newHash);
            // Store only the SHA of the document URI, never the original URI.
            props.setProperty("source_sha256", sourceHash);
            props.setProperty("kind", kind);
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
            String sourceHash = props.getProperty("source_sha256",
                    hex(digest().digest("legacy-unspecified-source".getBytes(StandardCharsets.UTF_8))));
            String name = sanitizeName(props.getProperty("name"));
            String kind = props.getProperty("kind", "pre-edit");
            if (!"pre-edit".equals(kind) && !"saved".equals(kind))
                return null;
            long length = Long.parseLong(props.getProperty("size", "-1"));
            long when = Long.parseLong(props.getProperty("timestamp", "0"));
            if (hash.length() != 64 || sourceHash.length() != 64 ||
                    length != data.length() || when <= 0L)
                return null;
            return new Snapshot(data, name, when, length, hash, sourceHash, kind);
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

    /**
     * Name a native post-save checkpoint using the latest pre-edit record.
     * The pre-edit flow already resolved OpenableColumns on a background
     * thread. Writer SAVE must never wait for a cloud provider metadata query
     * before persisting the edited bytes.
     *
     * Source SHA-256 keeps identically named documents from being confused.
     * Missing/corrupt metadata is only a naming failure, not a SAVE failure.
     */
    public static synchronized String preferredDisplayName(File appFilesDir,
            String sourceIdentity, String fallbackName) {
        final String fallback = sanitizeName(fallbackName);
        if (sourceIdentity == null || sourceIdentity.isEmpty())
            return fallback;
        try {
            final String sourceHash = hex(digest().digest(
                    sourceIdentity.getBytes(StandardCharsets.UTF_8)));
            for (Snapshot entry : readAll(folder(appFilesDir))) {
                if (entry.sourceHash.equals(sourceHash) && "pre-edit".equals(entry.kind))
                    return entry.displayName;
            }
        } catch (IOException failure) {
            // A display name must never prevent an otherwise recoverable SAVE.
        }
        return fallback;
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

    /** Do not deduplicate against a corrupted on-disk safety copy. */
    private static boolean verifyBytes(Snapshot snapshot) {
        if (!snapshot.file.isFile() || snapshot.file.length() != snapshot.sizeBytes)
            return false;
        MessageDigest checksum = digest();
        try (DigestInputStream in = new DigestInputStream(
                new FileInputStream(snapshot.file), checksum)) {
            byte[] buffer = new byte[64 * 1024];
            while (in.read(buffer) != -1) { /* verify stored original */ }
            return hex(checksum.digest()).equals(snapshot.sha256);
        } catch (IOException unreadable) {
            return false;
        }
    }

    /**
     * Validate a private recovery snapshot BEFORE opening a SAF destination.
     * Opening a provider output stream in "wt"/"rwt" may truncate its existing
     * document immediately, even if restore() would later reject corrupt bytes.
     * Call this before ContentResolver.openOutputStream(), not afterwards.
     */
    public static synchronized void verifyForRestore(Snapshot snapshot) throws IOException {
        if (snapshot == null || !verifyBytes(snapshot))
            throw new IOException("Recovery snapshot missing or checksum mismatch");
    }

    /**
     * SAF read-after-write contract: verify bytes actually returned by the
     * provider match the already fsynced private recovery checkpoint.
     * This does not prove cloud sync, atomicity, or power-loss durability.
     * The caller owns/closes providerInput; do not hold the history lock
     * during slow remote provider I/O.
     */
    public static void verifyProviderWriteback(Snapshot snapshot, InputStream providerInput)
            throws IOException {
        if (snapshot == null || providerInput == null)
            throw new IOException("SAF provider readback unavailable");
        MessageDigest checksum = digest();
        byte[] buffer = new byte[64 * 1024];
        long received = 0L;
        int noProgress = 0;
        int count;
        while ((count = providerInput.read(buffer)) != -1) {
            if (count == 0) {
                if (++noProgress >= 8)
                    throw new IOException("SAF provider readback made no progress");
                continue;
            }
            noProgress = 0;
            received += count;
            if (received > snapshot.sizeBytes)
                throw new IOException("SAF provider returned extra bytes");
            checksum.update(buffer, 0, count);
        }
        if (received != snapshot.sizeBytes ||
                !hex(checksum.digest()).equals(snapshot.sha256))
            throw new IOException("SAF provider readback checksum/size mismatch");
    }

    // Keep retention/trim from deleting a snapshot midway through restore.
    public static synchronized void restore(Snapshot snapshot, OutputStream target) throws IOException {
        if (snapshot == null || target == null) throw new IOException("Missing recovery destination");
        // Re-verify at copy time, since callers outside SAF may use restore()
        // directly. Both this check and the provider preflight are intentional.
        verifyForRestore(snapshot);
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
