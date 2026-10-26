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
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.List;
import java.util.Properties;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public final class AquaWordHistory {
    private static final String FOLDER = "aquaword-history";
    private static final String DATA_SUFFIX = ".snapshot";
    private static final String META_SUFFIX = ".properties";
    private static final long MAX_SINGLE_BYTES = 512L * 1024L * 1024L;
    private static final long MAX_TOTAL_BYTES = 1024L * 1024L * 1024L;
    private static final int MAX_SNAPSHOTS = 60;
    // Leave interrupted writes available for manual recovery for one week.
    private static final long INCOMPLETE_GRACE_MILLIS = 7L * 24L * 60L * 60L * 1000L;
    private static final Map<String, Integer> ACTIVE_WRITEBACKS = new HashMap<>();
    // Protect live captures from stale-partial cleanup triggered by another history scan.
    private static final Set<String> ACTIVE_CAPTURE_WRITES = new HashSet<>();

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

    /** Retain verified recovery bytes while a slow SAF provider writes them. */
    public static final class WritebackLease implements AutoCloseable {
        private final File file;
        private boolean closed;
        private WritebackLease(File file) { this.file = file; }
        @Override public void close() {
            synchronized (AquaWordHistory.class) {
                if (closed) return;
                closed = true;
                String key = file.getAbsolutePath();
                Integer active = ACTIVE_WRITEBACKS.get(key);
                if (active != null) {
                    if (active <= 1) ACTIVE_WRITEBACKS.remove(key);
                    else ACTIVE_WRITEBACKS.put(key, active - 1);
                }
                // Reapply retention once the provider no longer needs the bytes.
                trim(file.getParentFile());
            }
        }
    }

    /**
     * Pin the recovery bytes under the retention monitor, then hash them
     * OUTSIDE it. A large local checkpoint must not block unrelated history
     * operations while its SHA-256 is being verified before SAF writeback.
     * On verification failure the lease is always released.
     */
    public static WritebackLease holdForWriteback(Snapshot snapshot)
            throws IOException {
        if (snapshot == null || snapshot.sizeBytes <= 0L)
            throw new IOException("Recovery snapshot missing or checksum mismatch");
        final WritebackLease lease;
        synchronized (AquaWordHistory.class) {
            String key = snapshot.file.getAbsolutePath();
            Integer active = ACTIVE_WRITEBACKS.get(key);
            ACTIVE_WRITEBACKS.put(key, active == null ? 1 : active + 1);
            lease = new WritebackLease(snapshot.file);
        }
        boolean verified = false;
        try {
            if (!verifyBytes(snapshot))
                throw new IOException("Recovery snapshot missing or checksum mismatch");
            verified = true;
            return lease;
        } finally {
            if (!verified) lease.close();
        }
    }

    private static File folder(File appFilesDir) throws IOException {
        File target = new File(appFilesDir, FOLDER);
        if (!target.isDirectory() && !target.mkdirs() && !target.isDirectory())
            throw new IOException("Unable to create app-private snapshot directory");
        pruneStaleIncompleteFiles(target);
        return target;
    }

    /**
     * A process kill can leave large temporary data or metadata files behind.
     * Remove only week-old incomplete writes and metadata without its data.
     * Never delete an orphan .snapshot: it may be the user's only recoverable
     * document bytes even when its metadata was lost during a crash.
     * All entry points using folder() hold the class monitor in this process.
     */
    private static void pruneStaleIncompleteFiles(File dir) {
        File[] entries = dir.listFiles();
        if (entries == null) return;
        long cutoff = System.currentTimeMillis() - INCOMPLETE_GRACE_MILLIS;
        for (File entry : entries) {
            if (!entry.isFile()) continue;
            long modified = entry.lastModified();
            // An unreadable timestamp (0) is not evidence that deletion is safe.
            if (modified <= 0L || modified >= cutoff) continue;
            String name = entry.getName();
            boolean incomplete = name.endsWith(".partial") ||
                    name.endsWith(".meta-partial");
            if (!incomplete && name.endsWith(META_SUFFIX)) {
                String id = name.substring(0, name.length() - META_SUFFIX.length());
                incomplete = !new File(dir, id + DATA_SUFFIX).isFile();
            }
            if (incomplete) {
                // Capture streams can be slow (especially local SAF/cloud-backed reads).
                // Serialize the active check with registration and deletion so a live
                // .partial cannot be unlinked merely because its timestamp is old.
                synchronized (AquaWordHistory.class) {
                    if (ACTIVE_CAPTURE_WRITES.contains(entry.getAbsolutePath())) continue;
                    entry.delete(); // best effort; never block recovery
                }
            }
        }
    }

    public static Snapshot capture(File appFilesDir, InputStream input,
                                                String name) throws IOException {
        return capture(appFilesDir, input, name, "legacy-unspecified-source");
    }

    /** Source identity separates two distinct documents that share a file name. */
    public static Snapshot capture(File appFilesDir, InputStream input,
                                                String name, String sourceIdentity) throws IOException {
        return capture(appFilesDir, input, name, sourceIdentity, "pre-edit");
    }

    /** Saved revisions and pre-edit recovery versions use the same validated format. */
    public static Snapshot capture(File appFilesDir, InputStream input,
                                                String name, String sourceIdentity,
                                                String kind) throws IOException {
        return capture(appFilesDir, input, name, sourceIdentity, kind,
                (source, target) -> source.renameTo(target));
    }

    /** Package-private rename seam for deterministic crash-window regression tests. */
    interface RenameStrategy {
        boolean rename(File source, File target);
    }

    static Snapshot capture(File appFilesDir, InputStream input,
                            String name, String sourceIdentity, String kind,
                            RenameStrategy renameStrategy) throws IOException {
        if (!"pre-edit".equals(kind) && !"saved".equals(kind))
            throw new IOException("Unknown snapshot type");
        if (renameStrategy == null) throw new IOException("Snapshot rename strategy is required");
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
        final String tempKey = temp.getAbsolutePath();
        // Register before creating the file; cleanup uses the same monitor, so
        // it cannot race between file creation and active-write registration.
        synchronized (AquaWordHistory.class) {
            ACTIVE_CAPTURE_WRITES.add(tempKey);
        }
        MessageDigest sha = digest();
        long length = 0L;
        boolean dataCommitted = false;
        try {
            try (FileOutputStream output = new FileOutputStream(temp)) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                int noProgressReads = 0;
                while ((count = input.read(buffer)) != -1) {
                    // A nonconforming cloud/provider stream can repeatedly
                    // return zero for a nonempty buffer. Never spin forever
                    // while streaming a recovery copy outside the history lock.
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
            // A provider returning immediate EOF must not become a restorable
            // zero-byte revision. SAF restore can truncate its destination.
            if (length == 0L)
                throw new IOException("Refusing empty document recovery snapshot");
            String newHash = hex(sha.digest());
            // Commit and retention are serialized, but potentially slow SAF
            // input streaming above never holds the global history monitor.
            synchronized (AquaWordHistory.class) {
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
                if (!renameStrategy.rename(temp, data)) throw new IOException("Could not commit snapshot bytes");
                // The bytes are already fsynced and atomically renamed. If metadata
                // commit now fails, preserve this orphan so the next scan can recover it.
                dataCommitted = true;
                if (!renameStrategy.rename(pendingMeta, meta)) throw new IOException("Could not commit snapshot metadata");
                Snapshot saved = load(dir, data);
                if (saved == null) throw new IOException("Snapshot validation failed");
                trim(dir);
                return saved;
            }
        } finally {
            synchronized (AquaWordHistory.class) {
                temp.delete();
                pendingMeta.delete();
                // Never discard a fully committed snapshot just because its metadata
                // rename failed; readAll() can rebuild metadata from recognized bytes.
                if (!meta.exists() && !dataCommitted) data.delete();
                ACTIVE_CAPTURE_WRITES.remove(tempKey);
            }
        }
    }

    private static String sanitizeName(String name) {
        String n = name == null ? "" : name.replaceAll("[/\\\\\\r\\n\\t\\u0000-\\u001F]", "_").trim();
        if (n.length() > 180) n = n.substring(0, 180);
        return n.isEmpty() ? "Untitled Document" : n;
    }

    private static Snapshot load(File dir, File data) {
        if (!data.getParentFile().equals(dir) || !data.getName().endsWith(DATA_SUFFIX) ||
                !data.isFile())
            return null;
        File propsPath = new File(dir, data.getName().replace(DATA_SUFFIX, META_SUFFIX));
        try {
            // A recovery entry is trusted only when both payload and metadata
            // resolve inside the app-private history directory. isFile() alone
            // follows symlinks, which could otherwise expose unrelated files
            // as restore candidates after filesystem damage or tampering.
            File canonicalDir = dir.getCanonicalFile();
            File canonicalData = data.getCanonicalFile();
            File canonicalMeta = propsPath.getCanonicalFile();
            if (!canonicalDir.equals(canonicalData.getParentFile()) ||
                    !canonicalDir.equals(canonicalMeta.getParentFile()) ||
                    !propsPath.isFile())
                return null;
            try (FileInputStream meta = new FileInputStream(propsPath)) {
                Properties props = new Properties();
                props.load(meta);
                String hash = props.getProperty("sha256", "");
                String sourceHash = props.getProperty("source_sha256",
                        hex(digest().digest("legacy-unspecified-source".getBytes(StandardCharsets.UTF_8))));
                String name = sanitizeName(props.getProperty("name"));
                String kind = props.getProperty("kind", "pre-edit");
                if (!"pre-edit".equals(kind) && !"saved".equals(kind) &&
                        !"recovered".equals(kind))
                    return null;
                long length = Long.parseLong(props.getProperty("size", "-1"));
                long when = Long.parseLong(props.getProperty("timestamp", "0"));
                if (hash.length() != 64 || sourceHash.length() != 64 ||
                        length <= 0L || length != data.length() || when <= 0L)
                    return null;
                return new Snapshot(data, name, when, length, hash, sourceHash, kind);
            }
        } catch (IOException | IllegalArgumentException | SecurityException e) {
            return null;
        }
    }

    /**
     * Return a safe extension only for recognizable Writer document formats.
     * An orphaned arbitrary binary must not be mislabeled as DOCX merely because
     * its metadata vanished during a crash.
     */
    private static String guessRecoveredExtension(File data) throws IOException {
        byte[] prefix = new byte[4096];
        int length;
        try (InputStream input = new FileInputStream(data)) {
            length = input.read(prefix);
        }
        if (length <= 0) return null;
        if (length >= 4 && prefix[0] == 'P' && prefix[1] == 'K' &&
                prefix[2] == 3 && prefix[3] == 4) {
            try (ZipFile archive = new ZipFile(data)) {
                if (archive.getEntry("word/document.xml") != null &&
                        archive.getEntry("[Content_Types].xml") != null)
                    return ".docx";
                ZipEntry mimeEntry = archive.getEntry("mimetype");
                if (archive.getEntry("content.xml") != null && mimeEntry != null) {
                    try (InputStream mimeInput = archive.getInputStream(mimeEntry)) {
                        byte[] mime = new byte[128];
                        int count = mimeInput.read(mime);
                        String type = count > 0 ?
                                new String(mime, 0, count, StandardCharsets.US_ASCII) : "";
                        if (type.startsWith("application/vnd.oasis.opendocument.text"))
                            return ".odt";
                    }
                }
                return null;
            }
        }
        if (length >= 5 && prefix[0] == '{' && prefix[1] == '\\' &&
                prefix[2] == 'r' && prefix[3] == 't' && prefix[4] == 'f')
            return ".rtf";
        // Plain-text recovery is deliberately conservative: binary control
        // bytes and NULs are not exposed as editable text snapshots.
        for (int i = 0; i < length; i++) {
            int value = prefix[i] & 0xff;
            if (value == 0 || (value < 0x20 && value != 9 &&
                    value != 10 && value != 13 && value != 12))
                return null;
        }
        return ".txt";
    }

    /**
     * Recover a fully committed data file whose metadata rename was interrupted
     * by process death. capture() fsyncs the complete bytes and renames the data
     * before renaming metadata, so a metadata-free .snapshot is a recoverable
     * crash window, not an ordinary partial write. Never guess at an existing
     * but invalid metadata record; only synthesize metadata when it is absent.
     */
    private static Snapshot recoverOrphanSnapshot(File dir, File data) {
        if (!data.getParentFile().equals(dir) || !data.isFile() ||
                !data.getName().endsWith(DATA_SUFFIX))
            return null;
        final String id = data.getName().substring(
                0, data.getName().length() - DATA_SUFFIX.length());
        final File meta = new File(dir, id + META_SUFFIX);
        if (meta.exists()) return null;
        File pending = null;
        try {
            // Do not follow a symlink out of the app-private history directory.
            if (!data.getCanonicalFile().getParentFile().equals(dir.getCanonicalFile()))
                return null;
            final long size = data.length();
            if (size <= 0L || size > MAX_SINGLE_BYTES) return null;
            final String extension = guessRecoveredExtension(data);
            if (extension == null) return null;
            final long modified = data.lastModified();
            final long timestamp = modified > 0L ? modified : System.currentTimeMillis();
            final MessageDigest checksum = digest();
            long bytes = 0L;
            int noProgressReads = 0;
            try (InputStream input = new FileInputStream(data)) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (count == 0) {
                        if (++noProgressReads >= 8) return null;
                        continue;
                    }
                    noProgressReads = 0;
                    bytes += count;
                    if (bytes > size || bytes > MAX_SINGLE_BYTES) return null;
                    checksum.update(buffer, 0, count);
                }
            }
            if (bytes != size || data.length() != size ||
                    (modified > 0L && data.lastModified() != modified))
                return null;

            final String name = "Recovered document " + timestamp + extension;
            final String sourceHash = hex(digest().digest(
                    ("orphan-recovery:" + data.getName()).getBytes(StandardCharsets.UTF_8)));
            final String dataHash = hex(checksum.digest());
            Properties props = new Properties();
            props.setProperty("name", name);
            props.setProperty("timestamp", String.valueOf(timestamp));
            props.setProperty("size", String.valueOf(size));
            props.setProperty("sha256", dataHash);
            // This is a synthetic local identity, never a provider URI.
            props.setProperty("source_sha256", sourceHash);
            props.setProperty("kind", "recovered");

            pending = new File(dir, id + ".meta-partial");
            try (FileOutputStream output = new FileOutputStream(pending)) {
                props.store(output, "Recovered complete snapshot after metadata loss");
                output.getFD().sync();
            }
            if (!pending.renameTo(meta)) return null;

            Snapshot recovered = load(dir, data);
            if (recovered == null) {
                // Preserve the original bytes; let a later history scan retry.
                meta.delete();
                return null;
            }
            // Do not hash a large orphan a second time while history operations
            // are serialized. restore()/verifyForRestore() rechecks the actual
            // bytes before any destructive SAF destination is opened.
            return recovered;
        } catch (IOException | SecurityException failure) {
            return null;
        } finally {
            if (pending != null && pending.exists()) pending.delete();
        }
    }

    private static List<Snapshot> readAll(File dir) {
        File[] all = dir.listFiles((d, name) -> name.endsWith(DATA_SUFFIX));
        List<Snapshot> results = new ArrayList<>();
        if (all == null) return results;
        for (File data : all) {
            Snapshot item = load(dir, data);
            if (item == null) {
                // A missing metadata file can be the narrow crash window after
                // the durable data rename. Rebuild metadata, not document bytes.
                item = recoverOrphanSnapshot(dir, data);
            }
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
        long total = 0L;
        for (Snapshot item : all) total += item.sizeBytes;

        // Prefer retaining the newest recovery point for each source URI hash.
        // A global "newest only" rule can delete the only saved revision of
        // document A merely because document B was saved more recently.
        Set<String> newestSourceHashes = new HashSet<>();
        Set<String> protectedPaths = new HashSet<>();
        for (Snapshot entry : all) {
            if (newestSourceHashes.add(entry.sourceHash))
                protectedPaths.add(entry.file.getAbsolutePath());
        }

        int remainingCount = all.size();
        // First evict older revisions. This preserves one recent recovery point
        // per source whenever doing so is compatible with the configured caps.
        for (int index = all.size() - 1; index >= 0; index--) {
            if (remainingCount <= MAX_SNAPSHOTS && total <= MAX_TOTAL_BYTES) break;
            Snapshot entry = all.get(index);
            String path = entry.file.getAbsolutePath();
            if (ACTIVE_WRITEBACKS.containsKey(path) || protectedPaths.contains(path))
                continue;
            if (entry.file.delete()) {
                new File(dir, entry.file.getName().replace(DATA_SUFFIX, META_SUFFIX)).delete();
                total -= entry.sizeBytes;
                remainingCount--;
            }
        }

        // Hard caps still win if there are more distinct documents than the
        // retention budget can hold. In that case evict the oldest unpinned
        // source checkpoints, but never remove the global newest point or a
        // snapshot currently being streamed to a provider.
        for (int index = all.size() - 1; index >= 0; index--) {
            if (remainingCount <= MAX_SNAPSHOTS && total <= MAX_TOTAL_BYTES) break;
            Snapshot entry = all.get(index);
            String path = entry.file.getAbsolutePath();
            if (index == 0 || ACTIVE_WRITEBACKS.containsKey(path)) continue;
            if (!protectedPaths.contains(path)) continue;
            if (entry.file.delete()) {
                new File(dir, entry.file.getName().replace(DATA_SUFFIX, META_SUFFIX)).delete();
                total -= entry.sizeBytes;
                remainingCount--;
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
        if (snapshot == null || snapshot.sizeBytes <= 0L || !verifyBytes(snapshot))
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
        if (snapshot == null || snapshot.sizeBytes <= 0L || providerInput == null)
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

    /**
     * Pin the verified snapshot under the history monitor, then stream without
     * holding that monitor. A slow SAF/cloud OutputStream must not block other
     * documents' checkpoint creation, history listing, or retention. The lease
     * prevents trim() from evicting the source until the copy has finished.
     * The caller still owns and closes the destination stream.
     */
    public static void restore(Snapshot snapshot, OutputStream target) throws IOException {
        if (snapshot == null || target == null) throw new IOException("Missing recovery destination");
        // The lease re-verifies bytes before any potentially destructive SAF
        // destination write, including when restore() is called directly.
        try (WritebackLease lease = holdForWriteback(snapshot);
             InputStream in = new FileInputStream(snapshot.file)) {
            byte[] buffer = new byte[64 * 1024];
            MessageDigest streamedHash = digest();
            long streamedBytes = 0L;
            int n;
            while ((n = in.read(buffer)) != -1) {
                if (n == 0) continue;
                streamedBytes += n;
                if (streamedBytes > snapshot.sizeBytes)
                    throw new IOException("Recovery source grew during restore");
                streamedHash.update(buffer, 0, n);
                target.write(buffer, 0, n);
            }
            // A separate preflight SHA cannot freeze an inode: another Writer
            // save may rewrite it while a slow provider consumes the copy.
            // Never acknowledge success if the bytes actually streamed differ.
            if (streamedBytes != snapshot.sizeBytes ||
                    !hex(streamedHash.digest()).equals(snapshot.sha256))
                throw new IOException("Recovery source changed during restore");
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
