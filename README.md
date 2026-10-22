# AquaWord Android

**AquaWord** is an Android-only, offline-first document editor project for tablets and phones (Xiaomi Pad 5 first). The intended editing engine is the existing **Collabora Office / LibreOfficeKit** Android stack, not the small legacy WebView editor.

## Current status — 2026-10-22
- Real GitHub repository, kept private.
- **Not a completed Word clone**; no working APK has been produced or verified yet.
- Source overlay and a CI/build workflow are being integrated here. Do not label overlay tests as application/device tests.
- The prior AquaWord 0.2 prototype is historical reference, not the production editor.
- Windows is explicitly out of scope.

## Product requirements
- Word-for-Android-inspired tool layout (original AquaWord branding; no Microsoft graphics).
- Liquid Aurora / glass accents around an accessible, **white/neutral document page**.
- Rich offline editing; DOCX/ODT/RTF import/export; RTL Arabic mixed with English.
- Tables, images, lists, paragraph/page formatting, styles, reviewing, comments, track changes, footnotes, contents and PDF export subject to real native validation.
- Requested extras: reliable autosave and recovery, private local version history, focus mode, scientific/medical templates, PDF annotation and optional AI tools. Extras are **pending implementation**, not shipping features.
- **One user-facing delivery after internal CI and device acceptance**, not a sequence of user-requested builds.

## Engineering approach
1. Pin and fetch the Collabora Android mobile branch (upstream licensing/notices retained).
2. Apply tested AquaWord Android branding/UI overlay to the original native editor.
3. Build using GitHub Actions with SDK/NDK and validate artifacts; do not claim build success until job succeeds.
4. Integrate and verify missing product features; maintain explicit evidence-based acceptance status.
5. Release a single APK once the product meets the agreed functional gates.

## License
Integration scripts and branding are project-specific. Collabora/LibreOffice source and binaries carry their own license terms (including MPL-2.0 and other applicable notices); preserve those notices and audit redistribution before release.

## Security
Do not commit release keystores, passwords, tokens, personal documents or private data. Native builds must pin upstream refs; check downloaded sources and dependencies.
