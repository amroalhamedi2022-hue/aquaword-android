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
            Files.write(pdf.toPath(), "%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n".getBytes(StandardCharsets.US_ASCII));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);
            Files.write(pdf.toPath(), "%PDF-1.7\n1 0 obj\n<<>>\nendobj\n".getBytes(StandardCharsets.US_ASCII));
            rejects(pdf, "missing %%EOF should fail before SAF write");
            Files.write(pdf.toPath(), "NOTPDF\n%%EOF\n".getBytes(StandardCharsets.US_ASCII));
            rejects(pdf, "non-PDF header should fail");
            Files.write(pdf.toPath(), new byte[0]);
            rejects(pdf, "empty source should fail");
            Files.write(pdf.toPath(), "%PDF-1.7\n%%EOF\n".getBytes(StandardCharsets.US_ASCII));
            byte[] padded = new byte[5000];
            java.util.Arrays.fill(padded, (byte) ' ');
            try (java.io.FileOutputStream out = new java.io.FileOutputStream(pdf, true)) {
                out.write(padded);
            }
            rejects(pdf, "EOF outside bounded trailer window should fail");
            Files.write(pdf.toPath(), "%PDF-1.7\n%%EOF\n1 0 obj\n%%EOF\n".getBytes(StandardCharsets.US_ASCII));
            AquaWordPdfPreflight.requirePlausiblePdf(pdf);
            rejects(new File(temp, "missing.pdf"), "missing file should fail");
            rejects(null, "null source should fail");
            System.out.println("PASS: PDF preflight header, trailing EOF, incremental marker, invalid and missing inputs");
        } finally {
            pdf.delete();
            temp.delete();
        }
    }
}
