package org.libreoffice.androidapp.qa;

import androidx.core.content.FileProvider;

/**
 * Debug-only fixture provider. A distinct class name prevents Android's
 * manifest merger from combining this provider with Collabora's production
 * androidx.core.content.FileProvider (which has its own authority and paths).
 *
 * This provider is non-exported, grants only explicit URI permissions, and
 * is installed only in src/debug. It must never be packaged in release.
 */
public final class QaFixtureFileProvider extends FileProvider {
    public QaFixtureFileProvider() {
        super();
    }
}
