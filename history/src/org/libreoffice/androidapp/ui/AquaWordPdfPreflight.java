package org.libreoffice.androidlib;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;

/**
 * Conservative structural preflight before truncating a SAF PDF destination.
 * Checks the final cross-reference pointer without loading the whole file.
 * This is NOT a full PDF parser, signature check, or proof of valid rendering.
 */
public final class AquaWordPdfPreflight {
    private static final int TRAILER_WINDOW_BYTES = 4096;
    private static final byte[] EOF = "%%EOF".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] STARTXREF = "startxref".getBytes(StandardCharsets.US_ASCII);

    private AquaWordPdfPreflight() { }

    private static boolean whitespace(byte b) {
        return b == 0 || b == 9 || b == 10 || b == 12 || b == 13 || b == 32;
    }

    private static boolean lineStart(byte[] bytes, int index) {
        return index == 0 || bytes[index - 1] == '\n' || bytes[index - 1] == '\r';
    }

    private static boolean matches(byte[] bytes, int start, byte[] token) {
        if (start < 0 || start + token.length > bytes.length) return false;
        for (int j = 0; j < token.length; j++)
            if (bytes[start + j] != token[j]) return false;
        return true;
    }

    private static long finalStartXref(byte[] tail, int eofIndex, long tailBase)
            throws IOException {
        // The nearest line-start "startxref" must be the one paired with
        // the final %%EOF, including in incrementally updated documents.
        for (int i = eofIndex - STARTXREF.length; i >= 0; i--) {
            if (!matches(tail, i, STARTXREF) || !lineStart(tail, i)) continue;
            int p = i + STARTXREF.length;
            while (p < eofIndex && (tail[p] == ' ' || tail[p] == '\t')) p++;
            if (p >= eofIndex || (tail[p] != '\r' && tail[p] != '\n'))
                throw new IOException("Malformed final PDF startxref line");
            while (p < eofIndex && whitespace(tail[p])) p++;
            if (p >= eofIndex || tail[p] < '0' || tail[p] > '9')
                throw new IOException("Missing PDF cross-reference offset");
            long offset = 0;
            do {
                int digit = tail[p] - '0';
                if (offset > (Long.MAX_VALUE - digit) / 10)
                    throw new IOException("PDF cross-reference offset overflow");
                offset = offset * 10 + digit;
                p++;
            } while (p < eofIndex && tail[p] >= '0' && tail[p] <= '9');
            while (p < eofIndex && whitespace(tail[p])) p++;
            if (p != eofIndex || offset < 9 || offset >= tailBase + i)
                throw new IOException("Invalid final PDF cross-reference pointer");
            return offset;
        }
        throw new IOException("Native PDF export lacks final startxref");
    }

    private static void verifyCrossReference(RandomAccessFile source, long offset)
            throws IOException {
        // Bound the probe even for very large PDFs. A plausible object header
        // alone is NOT evidence of a PDF cross-reference stream: otherwise a
        // startxref pointing at any ordinary object could pass preflight.
        source.seek(offset);
        byte[] sample = new byte[(int) Math.min(8192L, source.length() - offset)];
        source.readFully(sample);
        String start = new String(sample, StandardCharsets.US_ASCII);
        // A classic table needs a subsection and at least one real entry.
        if (start.matches("(?s)^xref\\s+[0-9]+\\s+[0-9]+\\s+" +
                "[0-9]{10}\\s+[0-9]{5}\\s+[nf]\\b.*"))
            return;
        // PDF 1.5+ cross-reference streams must be indirect objects whose
        // dictionary explicitly declares /Type /XRef before stream data.
        // This is a conservative bounded screen, NOT a complete PDF parser.
        if (!start.matches("(?s)^[0-9]+\\s+[0-9]+\\s+obj\\s*<<.*"))
            throw new IOException("PDF startxref does not reference a cross-reference structure");
        int stream = start.indexOf("stream");
        int dictionary = start.indexOf("<<");
        if (stream < 0 || dictionary < 0 || dictionary >= stream)
            throw new IOException("PDF cross-reference stream header is incomplete");
        String header = start.substring(dictionary, stream);
        if (!header.matches("(?s).*?/Type\\s*/XRef\\b.*") ||
                !header.matches("(?s).*>>\\s*"))
            throw new IOException("PDF startxref object is not a cross-reference stream");
    }

    public static void requirePlausiblePdf(File file) throws IOException {
        if (file == null || !file.isFile())
            throw new IOException("Native PDF export is missing");
        try (RandomAccessFile source = new RandomAccessFile(file, "r")) {
            long length = source.length();
            if (length < 24)
                throw new IOException("Native PDF export is too short");
            byte[] header = new byte[8];
            source.readFully(header);
            if (header[0] != '%' || header[1] != 'P' || header[2] != 'D' ||
                    header[3] != 'F' || header[4] != '-' ||
                    !((header[5] == '1' && header[6] == '.' &&
                            header[7] >= '0' && header[7] <= '7') ||
                      (header[5] == '2' && header[6] == '.' && header[7] == '0')))
                throw new IOException("Native export has no supported PDF version header");
            int window = (int) Math.min(length, TRAILER_WINDOW_BYTES);
            long base = length - window;
            byte[] tail = new byte[window];
            source.seek(base);
            source.readFully(tail);
            // The final EOF must start on a line and have only PDF whitespace
            // afterwards. Earlier EOFs are allowed for incremental updates.
            for (int i = window - EOF.length; i >= 0; i--) {
                if (!matches(tail, i, EOF) || !lineStart(tail, i) ||
                        (i == 0 && base != 0))
                    continue;
                boolean clean = true;
                for (int j = i + EOF.length; j < window; j++) {
                    if (!whitespace(tail[j])) { clean = false; break; }
                }
                if (!clean) continue;
                long offset = finalStartXref(tail, i, base);
                verifyCrossReference(source, offset);
                return;
            }
            throw new IOException("Native PDF export lacks a final EOF line");
        }
    }
}
