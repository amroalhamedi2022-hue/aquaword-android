package org.libreoffice.androidlib;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.OutputStream;

/**
 * Shared, platform-independent negotiation for an explicitly truncating
 * document output stream. Kept free of Android dependencies so the fallback
 * contract can be exercised on the JVM with deterministic fake providers.
 */
public final class AquaWordSafOutput {
    private AquaWordSafOutput() { }

    public interface Opener {
        OutputStream open(String mode) throws IOException;
    }

    /**
     * Try "wt" first, then "rwt" only when the provider rejects that mode or
     * returns null. Never use ambiguous "w"; propagate permission and ordinary
     * I/O failures instead of masking them as mode negotiation.
     */
    public static OutputStream openTruncating(Opener opener) throws IOException {
        if (opener == null)
            throw new IOException("Document output provider is unavailable");

        OutputStream opened;
        try {
            opened = opener.open("wt");
        } catch (FileNotFoundException | UnsupportedOperationException | IllegalArgumentException rejected) {
            opened = null;
        }

        if (opened == null)
            opened = opener.open("rwt");
        if (opened == null)
            throw new IOException("No truncating writable stream");
        return opened;
    }
}
