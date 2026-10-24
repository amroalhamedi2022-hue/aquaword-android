package org.libreoffice.androidapp.ui;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.libreoffice.androidlib.AquaWordPdfPreflight;

public final class AquaWordPdfPreflightTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static byte[] ascii(String s) {
        return s.getBytes(StandardCharsets.US_ASCII);
    }

    private static String classicPdf() {
        String objects = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n";
        return objects + "xref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\n" +
                "startxref\n" + objects.length() + "\n%%EOF\n";
    }

    private static String incrementalPdf() {
        String first = classicPdf();
        String secondObject = "2 0 obj\n<< /Type /Metadata >>\nendobj\n";
        int secondXref = first.length() + secondObject.length();
        return first + secondObject + "xref\n0 1\n0000000000 65535 f \n" +
                "trailer\n<< /Size 3 >>\nstartxref\n" + secondXref + "\n%%EOF\n";
    }

    private static String xrefStreamPdf() {
        String header = "%PDF-1.7\n";
        return header + "1 0 obj\n<< /Type /XRef /Size 2 /W [1 2 1] /Length 0 >>\n" +
                "stream\n\nendstream\nendobj\nstartxref\n" + header.length() + "\n%%EOF\n";
    }

    private static void rejects(File path, String description) throws Exception {
        boolean rejected = false;
        try { AquaWordPdfPreflight.requirePlausiblePdf(path); }
        catch (IOException expected) { rejected = true; }
        check(rejected, description);
    }

    public static void main(String[] args) throws Exception {
        File temp = Files.createTempDirectory("aquaword-pdf-preflight").toFile();
        File pdf = new File(temp, "export.pdf");
        try {
            Files.write(pdf.toPath(), ascii(classicPdf()));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);
            Files.write(pdf.toPath(), ascii(xrefStreamPdf()));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);
            Files.write(pdf.toPath(), ascii(incrementalPdf()));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);

            Files.write(pdf.toPath(), ascii(classicPdf().replace("%%EOF", "%EOX")));
            rejects(pdf, "missing %%EOF should fail before SAF write");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("%PDF-1.7", "NOTPDF!!")));
            rejects(pdf, "non-PDF header should fail");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("%PDF-1.7", "%PDF-9.9")));
            rejects(pdf, "invalid PDF version should fail");
            Files.write(pdf.toPath(), new byte[0]);
            rejects(pdf, "empty source should fail");

            Files.write(pdf.toPath(), ascii(classicPdf()));
            byte[] padded = new byte[5000];
            java.util.Arrays.fill(padded, (byte) ' ');
            try (java.io.FileOutputStream out = new java.io.FileOutputStream(pdf, true)) {
                out.write(padded);
            }
            rejects(pdf, "EOF outside bounded trailer window should fail");

            Files.write(pdf.toPath(), ascii(classicPdf() + "TRAILING-JUNK\n"));
            rejects(pdf, "EOF followed by junk must not pass preflight");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("%%EOF\n", "%%EOFnot-a-marker\n")));
            rejects(pdf, "embedded EOF prefix must not pass preflight");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("%%EOF\n", "stream %%EOF\n")));
            rejects(pdf, "EOF inside a data line must not pass preflight");

            Files.write(pdf.toPath(), ascii(classicPdf().replace("%%EOF\n", "%%EOF\r\n \t\f")));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);

            Files.write(pdf.toPath(), ascii(classicPdf().replace("startxref\n", "startxref\nnot-a-number\n")));
            rejects(pdf, "non-numeric startxref must be rejected");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("startxref\n", "startxref\n999999999999999999999999\n")));
            rejects(pdf, "overflowing startxref must be rejected");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("startxref\n", "startxref\n0\n")));
            rejects(pdf, "zero startxref must be rejected");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("startxref\n", "startxref\n15\n")));
            rejects(pdf, "startxref pointing inside object must be rejected");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("startxref\n", "no-pointer\n")));
            rejects(pdf, "missing startxref must be rejected");
            Files.write(pdf.toPath(), ascii(classicPdf().replace("xref\n0 1", "junk\n0 1")));
            rejects(pdf, "startxref target must contain a cross-reference structure");

            rejects(new File(temp, "missing.pdf"), "missing file should fail");
            rejects(null, "null source should fail");
            System.out.println("PASS: PDF header, classic/stream/incremental xref, EOF, offsets and negative cases");
        } finally {
            pdf.delete();
            temp.delete();
        }
    }
}
