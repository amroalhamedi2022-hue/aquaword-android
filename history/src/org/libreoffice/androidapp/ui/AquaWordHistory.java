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

    /** Shared guard for persisted, cached, staged, and provider-bound snapshots. */
    static boolean isWithinSnapshotSizeLimit(long size) {
        return size > 0L && size <= MAX_SINGLE_BYTES;
    }
    // Leave interrupted writes available for manual recovery for one week.
    private static final long INCOMPLETE_GRACE_MILLIS = 7L * 24L * 60L * 60L * 1000L;
    private static final Map<String, Integer> ACTIVE_WRITEBACKS = new HashMap<>();
    // Protect live captures from stale-partial cleanup triggered by another history scan.
    private static final Set<String> ACTIVE_CAPTURE_WRITES = new HashSet<>();

    private AquaWordHistory() { }

    public interface DestinationOpener {
        /** Open the selected destination only after the recovery bytes are staged and verified. */
        OutputStream open() throws IOException;
    }

    /** Package-private deterministic seam for recovery race regression tests. */
    interface RestoreStageHook {
        void afterVerifiedStage(File staged) throws IOException;
    }

    public static final class Snapshot {
        public final File file;
        public final String displayName;
        public final long createdMillis;
        public final long sizeBytes;
        private final String sha256;
        private final String sourceHash;
        private final String canonicalParentPath;
        public final String kind;
        private Snapshot(File file, String displayName, long createdMillis,
                         long sizeBytes, String sha256, String sourceHash, String kind,
                         String canonicalParentPath) {
            this.file = file;
            this.displayName = displayName;
            this.createdMillis = createdMillis;
            this.sizeBytes = sizeBytes;
            this.sha256 = sha256;
            this.sourceHash = sourceHash;
            this.kind = kind;
            this.canonicalParentPath = canonicalParentPath;
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
        if (appFilesDir == null)
            throw new IOException("App-private snapshot root is unavailable");
        // Resolve the app-private root first, then require the history directory
        // to remain the exact expected child. File.isDirectory() follows symlinks,
        // so it cannot by itself establish this storage boundary.
        File base = appFilesDir.getCanonicalFile();
        // Preserve the helper's existing contract: callers/tests may supply a
        // not-yet-created files root, which can safely be created before the
        // history child is validated.
        if (!base.isDirectory() && !base.mkdirs() && !base.isDirectory())
            throw new IOException("Unable to create app-private snapshot root");
        File target = new File(base, FOLDER);
        if (!target.exists() && !target.mkdirs() && !target.isDirectory())
            throw new IOException("Unable to create app-private snapshot directory");
        if (!target.isDirectory())
            throw new IOException("App-private snapshot path is not a directory");

        File canonicalTarget = target.getCanonicalFile();
        File expectedTarget = new File(base, FOLDER).getAbsoluteFile();
        if (!base.equals(canonicalTarget.getParentFile()) ||
                !expectedTarget.equals(canonicalTarget))
            throw new IOException("History directory must remain inside app-private storage");

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
        return capture(appFilesDir, input, name, sourceIdentity, kind, renameStrategy,
                System.currentTimeMillis() + "-" + UUID.randomUUID().toString());
    }

    /** Deterministic identifier seam for collision-safety regression tests. */
    static Snapshot capture(File appFilesDir, InputStream input,
                            String name, String sourceIdentity, String kind,
                            RenameStrategy renameStrategy, String id) throws IOException {
        if (id == null || !id.matches("[A-Za-z0-9-]{1,80}"))
            throw new IOException("Invalid snapshot identifier");
        if (!"pre-edit".equals(kind) && !"saved".equals(kind))
            throw new IOException("Unknown snapshot type");
        if (renameStrategy == null) throw new IOException("Snapshot rename strategy is required");
        if (input == null) throw new IOException("No readable input stream");
        if (sourceIdentity == null || sourceIdentity.isEmpty())
            throw new IOException("Document source identity is required");
        String sourceHash = hex(digest().digest(sourceIdentity.getBytes(StandardCharsets.UTF_8)));
        File dir = folder(appFilesDir);
        String safeName = sanitizeName(name);
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
        boolean tempCreated = false;
        boolean pendingMetaCreated = false;
        try {
            // A prior crash or path collision must never cause FileOutputStream
            // to truncate another recovery entry. Refuse occupied committed
            // and metadata paths, then reserve the staging path exclusively.
            if (data.exists() || meta.exists() || pendingMeta.exists())
                throw new IOException("Snapshot identifier collision");
            if (!temp.createNewFile())
                throw new IOException("Could not reserve unique snapshot staging path");
            tempCreated = true;
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
                if (!pendingMeta.createNewFile())
                    throw new IOException("Could not reserve unique snapshot metadata path");
                pendingMetaCreated = true;
                try (FileOutputStream metaOut = new FileOutputStream(pendingMeta)) {
                    props.store(metaOut, "AquaWord private document snapshot");
                    metaOut.getFD().sync();
                }
                if (!renameStrategy.rename(temp, data)) throw new IOException("Could not commit snapshot bytes");
                // The bytes are already fsynced and atomically renamed. If metadata
                // commit now fails, preserve this orphan so the next scan can recover it.
                if (!renameStrategy.rename(pendingMeta, meta)) throw new IOException("Could not commit snapshot metadata");
                Snapshot saved = load(dir, data);
                if (saved == null) throw new IOException("Snapshot validation failed");
                trim(dir);
                return saved;
            }
        } finally {
            synchronized (AquaWordHistory.class) {
                // Delete only temporary paths this capture successfully reserved.
                // Never delete the final .snapshot here: a failed rename may mean
                // that path belongs to an older recovery point, while a successful
                // rename followed by metadata failure must preserve the orphan bytes.
                if (tempCreated) temp.delete();
                if (pendingMetaCreated) pendingMeta.delete();
                ACTIVE_CAPTURE_WRITES.remove(tempKey);
            }
        }
    }

    private static String sanitizeName(String name) {
        String n = name == null ? "" : name.replaceAll("[/\\\\\\r\\n\\t\\u0000-\\u001F]", "_").trim();
        if (n.length() > 180) n = n.substring(0, 180);
        return n.isEmpty() ? "Untitled Document" : n;
    }

    /**
     * Derive the sidecar name by removing only the terminal data suffix.
     * String.replace() is unsafe because a valid basename may itself contain
     * the text ".snapshot".
     */
    private static File metadataFileForSnapshot(File dir, File data) {
        if (dir == null || data == null) return null;
        String name = data.getName();
        if (!name.endsWith(DATA_SUFFIX)) return null;
        String id = name.substring(0, name.length() - DATA_SUFFIX.length());
        return new File(dir, id + META_SUFFIX);
    }

    /** Metadata hashes are generated as canonical lowercase SHA-256 hex. */
    private static boolean isSha256Hex(String value) {
        if (value == null || value.length() != 64) return false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
        }
        return true;
    }

    private static Snapshot load(File dir, File data) {
        if (!data.getParentFile().equals(dir) || !data.getName().endsWith(DATA_SUFFIX) ||
                !data.isFile())
            return null;
        File propsPath = metadataFileForSnapshot(dir, data);
        if (propsPath == null) return null;
        try {
            // A recovery entry is trusted only when both payload and metadata
            // resolve inside the app-private history directory. isFile() alone
            // follows symlinks, which could otherwise expose unrelated files
            // as restore candidates after filesystem damage or tampering.
            File canonicalDir = dir.getCanonicalFile();
            File canonicalData = data.getCanonicalFile();
            File canonicalMeta = propsPath.getCanonicalFile();
            // Require the canonical target to be the exact expected child path,
            // not merely another file inside this directory. Otherwise an
            // in-directory symlink could alias a valid snapshot/sidecar, creating
            // duplicate or misleading recovery entries and confusing retention.
            File expectedData = new File(canonicalDir, data.getName()).getAbsoluteFile();
            File expectedMeta = new File(canonicalDir, propsPath.getName()).getAbsoluteFile();
            if (!canonicalDir.equals(canonicalData.getParentFile()) ||
                    !canonicalDir.equals(canonicalMeta.getParentFile()) ||
                    !canonicalData.equals(expectedData) ||
                    !canonicalMeta.equals(expectedMeta) ||
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
                // Do not expose malformed metadata as a selectable recovery item.
                // Keep its files untouched for forensic/manual recovery, but require
                // the exact lowercase format produced by hex() before listing it.
                if (!isSha256Hex(hash) || !isSha256Hex(sourceHash) ||
                        !isWithinSnapshotSizeLimit(length) || length != data.length() || when <= 0L)
                    return null;
                return new Snapshot(data, name, when, length, hash, sourceHash, kind,
                        canonicalDir.getPath());
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
            // Orphan recovery must reject symlink aliases too, including links
            // whose targets remain inside the private directory. Otherwise a
            // metadata-free alias can synthesize a second recovery record.
            File canonicalDir = dir.getCanonicalFile();
            File canonicalData = data.getCanonicalFile();
            File expectedData = new File(canonicalDir, data.getName()).getAbsoluteFile();
            if (!canonicalDir.equals(canonicalData.getParentFile()) ||
                    !canonicalData.equals(expectedData))
                return null;
            final long size = data.length();
            if (!isWithinSnapshotSizeLimit(size)) return null;
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
                File metadata = metadataFileForSnapshot(dir, entry.file);
                if (metadata != null) metadata.delete();
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
                File metadata = metadataFileForSnapshot(dir, entry.file);
                if (metadata != null) metadata.delete();
                total -= entry.sizeBytes;
                remainingCount--;
            }
        }
    }

    /**
     * Reject a cached recovery entry if its pathname now resolves through a
     * symlink or alias. load() checks this when listing history, but callers may
     * hold a Snapshot while the filesystem changes; revalidate at use time too.
     * This narrows path-replacement races but is not an OS-level no-follow open.
     */
    private static boolean isCanonicalSnapshotChild(File file) {
        if (file == null || !file.getName().endsWith(DATA_SUFFIX)) return false;
        File parent = file.getParentFile();
        if (parent == null) return false;
        try {
            File canonicalDir = parent.getCanonicalFile();
            File canonicalFile = file.getCanonicalFile();
            File expectedFile = new File(canonicalDir, file.getName()).getAbsoluteFile();
            return canonicalDir.equals(canonicalFile.getParentFile()) &&
                    expectedFile.equals(canonicalFile);
        } catch (IOException | SecurityException unreadable) {
            return false;
        }
    }

    /** Bind a cached snapshot to the exact canonical history directory it came from. */
    private static boolean isCanonicalSnapshotChild(Snapshot snapshot) {
        return snapshot != null && snapshot.file != null &&
                snapshot.canonicalParentPath != null &&
                snapshot.file.getName().endsWith(DATA_SUFFIX) &&
                isCanonicalChildAtParent(snapshot.file, snapshot.canonicalParentPath);
    }

    private static boolean isCanonicalChildAtParent(File file, String expectedParentPath) {
        if (file == null || file.getParentFile() == null || expectedParentPath == null)
            return false;
        try {
            File expectedParent = new File(expectedParentPath).getCanonicalFile();
            File actualParent = file.getParentFile().getCanonicalFile();
            File canonicalFile = file.getCanonicalFile();
            File expectedFile = new File(expectedParent, file.getName()).getAbsoluteFile();
            return expectedParent.getPath().equals(expectedParentPath) &&
                    expectedParent.equals(actualParent) &&
                    expectedParent.equals(canonicalFile.getParentFile()) &&
                    expectedFile.equals(canonicalFile);
        } catch (IOException | SecurityException unreadable) {
            return false;
        }
    }

    /** Do not deduplicate against a corrupted or path-aliased safety copy. */
    private static boolean verifyBytes(Snapshot snapshot) {
        if (snapshot == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes) ||
                !isCanonicalSnapshotChild(snapshot.file) || !snapshot.file.isFile())
            return false;
        long initialModified = snapshot.file.lastModified();
        if (snapshot.file.length() != snapshot.sizeBytes) return false;
        MessageDigest checksum = digest();
        long received = 0L;
        try (DigestInputStream in = new DigestInputStream(
                new FileInputStream(snapshot.file), checksum)) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = in.read(buffer)) != -1) {
                if (count == 0) continue;
                received += count;
                if (received > snapshot.sizeBytes) return false;
            }
            // Check both the bytes read and the path/metadata after hashing.
            // A cached Snapshot must not bless a later symlink substitution,
            // even when the external target happens to contain identical bytes.
            return received == snapshot.sizeBytes &&
                    snapshot.file.isFile() &&
                    snapshot.file.length() == snapshot.sizeBytes &&
                    snapshot.file.lastModified() == initialModified &&
                    isCanonicalSnapshotChild(snapshot.file) &&
                    hex(checksum.digest()).equals(snapshot.sha256);
        } catch (IOException | SecurityException unreadable) {
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
        if (snapshot == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes) || !verifyBytes(snapshot))
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
        if (snapshot == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes) || providerInput == null)
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
    /**
     * Verify the exact already-open file descriptor before the caller writes
     * any bytes to a potentially destructive SAF destination. Path/hash
     * preflight alone cannot bind a later FileInputStream to the same bytes.
     *
     * Package-private so the same-package commit regression can deterministically
     * exercise replacement between lease verification and stream opening.
     */
    static void verifyOpenedRestoreSource(Snapshot snapshot, FileInputStream input)
            throws IOException {
        if (snapshot == null || input == null || snapshot.sizeBytes <= 0L)
            throw new IOException("Missing recovery source");
        verifyOpenedFile(snapshot.file, snapshot.canonicalParentPath,
                snapshot.sizeBytes, snapshot.sha256, input,
                "Recovery source changed before restore");
    }

    private static void verifyOpenedFile(File file, String parentPath, long expectedSize,
                                         String expectedHash, FileInputStream input,
                                         String failureMessage) throws IOException {
        if (file == null || input == null || !isWithinSnapshotSizeLimit(expectedSize) ||
                !isCanonicalChildAtParent(file, parentPath) || !file.isFile() ||
                file.length() != expectedSize)
            throw new IOException(failureMessage);
        long initialModified = file.lastModified();
        MessageDigest checksum = digest();
        byte[] buffer = new byte[64 * 1024];
        long received = 0L;
        int noProgress = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (count == 0) {
                if (++noProgress >= 8) throw new IOException(failureMessage);
                continue;
            }
            noProgress = 0;
            received += count;
            if (received > expectedSize) throw new IOException(failureMessage);
            checksum.update(buffer, 0, count);
        }
        if (received != expectedSize ||
                !hex(checksum.digest()).equals(expectedHash) ||
                !isCanonicalChildAtParent(file, parentPath) || !file.isFile() ||
                file.length() != expectedSize || file.lastModified() != initialModified)
            throw new IOException(failureMessage);
        input.getChannel().position(0L);
    }

    /**
     * Stage and verify recovery bytes before opening a potentially truncating
     * SAF destination. Use this overload for Android document providers.
     */
    public static void restoreToDestination(Snapshot snapshot, DestinationOpener opener)
            throws IOException {
        restoreToDestination(snapshot, opener, null);
    }

    static void restoreToDestination(Snapshot snapshot, DestinationOpener opener,
                                     RestoreStageHook hook) throws IOException {
        if (snapshot == null || opener == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes))
            throw new IOException("Missing or oversized recovery destination");
        try (WritebackLease lease = holdForWriteback(snapshot)) {
            File staged = stageRestoreCopy(snapshot);
            Throwable primaryFailure = null;
            try {
                if (hook != null) hook.afterVerifiedStage(staged);
                try (FileInputStream input = new FileInputStream(staged)) {
                    verifyOpenedFile(staged, snapshot.canonicalParentPath,
                            snapshot.sizeBytes, snapshot.sha256, input,
                            "Recovery staging file changed before restore");
                    // Critical ordering: the provider is not opened until the
                    // complete local staging copy has passed SHA-256 verification.
                    OutputStream opened = opener.open();
                    if (opened == null)
                        throw new IOException("No truncating writable recovery destination");
                    try (OutputStream target = opened) {
                        streamVerifiedBytes(snapshot, input, target);
                    }
                }
            } catch (IOException | RuntimeException | Error failure) {
                primaryFailure = failure;
                throw failure;
            } finally {
                try {
                    deleteStagedRestoreCopy(staged);
                } catch (IOException cleanupFailure) {
                    if (primaryFailure != null) primaryFailure.addSuppressed(cleanupFailure);
                    else throw cleanupFailure;
                }
            }
        }
    }

    /**
     * Legacy stream API. It verifies a private staging copy before writing,
     * but callers must use restoreToDestination() when opening the stream itself
     * can truncate an existing provider document.
     */
    public static void restore(Snapshot snapshot, OutputStream target) throws IOException {
        if (snapshot == null || target == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes))
            throw new IOException("Missing or oversized recovery destination");
        try (WritebackLease lease = holdForWriteback(snapshot)) {
            File staged = stageRestoreCopy(snapshot);
            Throwable primaryFailure = null;
            try {
                try (FileInputStream input = new FileInputStream(staged)) {
                    verifyOpenedFile(staged, snapshot.canonicalParentPath,
                            snapshot.sizeBytes, snapshot.sha256, input,
                            "Recovery staging file changed before restore");
                    streamVerifiedBytes(snapshot, input, target);
                }
            } catch (IOException | RuntimeException | Error failure) {
                primaryFailure = failure;
                throw failure;
            } finally {
                try {
                    deleteStagedRestoreCopy(staged);
                } catch (IOException cleanupFailure) {
                    if (primaryFailure != null) primaryFailure.addSuppressed(cleanupFailure);
                    else throw cleanupFailure;
                }
            }
        }
    }

    private static File stageRestoreCopy(Snapshot snapshot) throws IOException {
        if (snapshot == null || !isWithinSnapshotSizeLimit(snapshot.sizeBytes) ||
                !isCanonicalSnapshotChild(snapshot) || !snapshot.file.isFile() ||
                snapshot.file.length() != snapshot.sizeBytes)
            throw new IOException("Recovery snapshot changed before staging");
        File dir = snapshot.file.getParentFile();
        File staged = new File(dir, "restore-" + UUID.randomUUID().toString() + ".partial");
        String key = staged.getAbsolutePath();
        synchronized (AquaWordHistory.class) {
            ACTIVE_CAPTURE_WRITES.add(key);
        }
        boolean created = false;
        boolean ready = false;
        try {
            if (!staged.createNewFile())
                throw new IOException("Could not create private recovery staging file");
            created = true;
            MessageDigest stagedHash = digest();
            long stagedBytes = 0L;
            int noProgress = 0;
            try (FileInputStream input = new FileInputStream(snapshot.file)) {
                verifyOpenedRestoreSource(snapshot, input);
                try (FileOutputStream output = new FileOutputStream(staged)) {
                    byte[] buffer = new byte[64 * 1024];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (count == 0) {
                            if (++noProgress >= 8)
                                throw new IOException("Recovery source made no progress while staging");
                            continue;
                        }
                        noProgress = 0;
                        stagedBytes += count;
                        if (stagedBytes > snapshot.sizeBytes)
                            throw new IOException("Recovery source grew while staging");
                        stagedHash.update(buffer, 0, count);
                        output.write(buffer, 0, count);
                    }
                    output.getFD().sync();
                }
            }
            if (stagedBytes != snapshot.sizeBytes ||
                    !hex(stagedHash.digest()).equals(snapshot.sha256) ||
                    !isCanonicalSnapshotChild(snapshot) ||
                    !isCanonicalChildAtParent(staged, snapshot.canonicalParentPath) ||
                    !staged.isFile() || staged.length() != snapshot.sizeBytes ||
                    !verifyStagedBytes(staged, snapshot.canonicalParentPath,
                            snapshot.sizeBytes, snapshot.sha256))
                throw new IOException("Recovery source changed while staging");
            ready = true;
            return staged;
        } finally {
            if (!ready) {
                synchronized (AquaWordHistory.class) {
                    if (created) staged.delete();
                    ACTIVE_CAPTURE_WRITES.remove(key);
                }
            }
        }
    }

    private static boolean verifyStagedBytes(File file, String parentPath,
                                             long expectedSize, String expectedHash) {
        if (!isWithinSnapshotSizeLimit(expectedSize) ||
                !isCanonicalChildAtParent(file, parentPath) || !file.isFile() ||
                file.length() != expectedSize) return false;
        long modified = file.lastModified();
        MessageDigest checksum = digest();
        long received = 0L;
        try (DigestInputStream input = new DigestInputStream(
                new FileInputStream(file), checksum)) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) {
                if (count == 0) continue;
                received += count;
                if (received > expectedSize) return false;
            }
            return received == expectedSize && file.isFile() &&
                    file.length() == expectedSize && file.lastModified() == modified &&
                    isCanonicalChildAtParent(file, parentPath) &&
                    hex(checksum.digest()).equals(expectedHash);
        } catch (IOException | SecurityException failure) {
            return false;
        }
    }

    private static void deleteStagedRestoreCopy(File staged) throws IOException {
        if (staged == null) return;
        IOException cleanupFailure = null;
        synchronized (AquaWordHistory.class) {
            try {
                // Call delete even when exists() is false: a dangling symlink
                // reports exists()==false but still occupies the staging path.
                boolean deleted = staged.delete();
                if (!deleted && staged.exists()) {
                    cleanupFailure = new IOException(
                            "Could not remove private recovery staging file; recovery bytes may remain in app-private storage");
                }
            } catch (SecurityException denied) {
                cleanupFailure = new IOException(
                        "Could not remove private recovery staging file; recovery bytes may remain in app-private storage",
                        denied);
            } finally {
                // Never leave a failed cleanup marked as an active writer forever.
                ACTIVE_CAPTURE_WRITES.remove(staged.getAbsolutePath());
            }
        }
        if (cleanupFailure != null) throw cleanupFailure;
    }

    private static void streamVerifiedBytes(Snapshot snapshot, FileInputStream input,
                                            OutputStream target) throws IOException {
        byte[] buffer = new byte[64 * 1024];
        MessageDigest streamedHash = digest();
        long streamedBytes = 0L;
        int noProgress = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (count == 0) {
                if (++noProgress >= 8)
                    throw new IOException("Recovery staging stream made no progress");
                continue;
            }
            noProgress = 0;
            streamedBytes += count;
            if (streamedBytes > snapshot.sizeBytes)
                throw new IOException("Recovery staging file grew during restore");
            streamedHash.update(buffer, 0, count);
            target.write(buffer, 0, count);
        }
        if (streamedBytes != snapshot.sizeBytes ||
                !hex(streamedHash.digest()).equals(snapshot.sha256))
            throw new IOException("Recovery staging file changed during restore");
        target.flush();
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
