package org.libreoffice.androidlib;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;

/** Lightweight PDF header/trailer check before a SAF destination is truncated.
 * This is not a full PDF parser or a guarantee that every PDF object is valid.
 */
public final class AquaWordPdfPreflight {
    private static final int TRAILER_WINDOW_BYTES = 4096;

    private AquaWordPdfPreflight() { }

    public static void requirePlausiblePdf(File file) throws IOException {
        if (file == null || !file.isFile())
            throw new IOException("Native PDF export is missing");
        try (RandomAccessFile source = new RandomAccessFile(file, "r")) {
            final long length = source.length();
            if (length < 10L)
                throw new IOException("Native PDF export is too short");
            byte[] header = new byte[5];
            source.readFully(header);
            if (header[0] != '%' || header[1] != 'P' || header[2] != 'D' ||
                    header[3] != 'F' || header[4] != '-')
                throw new IOException("Native export is not a PDF");
            // PDF incremental updates may have multiple EOF markers. The last
            // one should be near the end; allow whitespace/trailing bytes.
            final int window = (int) Math.min(length, TRAILER_WINDOW_BYTES);
            byte[] tail = new byte[window];
            source.seek(length - window);
            source.readFully(tail);
            // An EOF token inside a stream or followed by non-whitespace
            // must not pass preflight. Incremental PDFs can have earlier
            // markers; only a line-start marker with a clean suffix counts.
            boolean found = false;
            for (int i = window - 5; i >= 0; i--) {
                if (tail[i] != '%' || tail[i + 1] != '%' ||
                        tail[i + 2] != 'E' || tail[i + 3] != 'O' ||
                        tail[i + 4] != 'F')
                    continue;
                if (i == 0 && length != window)
                    continue; // Cannot verify the preceding line boundary.
                if (i > 0 && tail[i - 1] != '\n' && tail[i - 1] != '\r')
                    continue;
                boolean cleanSuffix = true;
                for (int j = i + 5; j < window; j++) {
                    byte b = tail[j];
                    // PDF whitespace: NUL, TAB, LF, FF, CR, SPACE.
                    if (b != 0 && b != 9 && b != 10 &&
                            b != 12 && b != 13 && b != 32) {
                        cleanSuffix = false;
                        break;
                    }
                }
                if (cleanSuffix) {
                    found = true;
                    break;
                }
            }
            if (!found)
                throw new IOException("Native PDF export lacks a final EOF line");
        }
    }
}
