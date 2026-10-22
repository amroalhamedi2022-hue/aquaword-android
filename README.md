# AquaWord Android

**AquaWord** is an Android-only, offline-first document editor project for tablets and phones (Xiaomi Pad 5 first). The intended editing engine is the existing **Collabora Office / LibreOfficeKit** Android stack, not the small legacy WebView editor.

## Current status — 2026-10-22
- Real GitHub repository, kept private.
- **Not a completed Word clone**; no working APK has been produced or verified yet.
- The source overlay and integration CI are checked in. A previous **LibreOffice ARM64 engine build succeeded**, while the subsequent Collabora app configure failed on an unavailable Python module; the workflow preflight now tests its Python dependencies. An AquaWord APK is **not** verified.
- App-private **pre-edit safety copies**, SHA-256 verification, deduplication of unchanged files, and restore-as-new-document are JVM/source-tested.
- **Periodic native save commands every 120 seconds** while editing have been integrated using LibreOffice's existing save mechanism. These require real-device validation and are not a guarantee of crash recovery or full version history.
- The prior AquaWord 0.2 prototype is historical reference, not the production editor.
- Windows is explicitly out of scope.

## Product requirements
- Word-for-Android-inspired tool layout (original AquaWord branding; no Microsoft graphics).
- Liquid Aurora / glass accents around an accessible, **white/neutral document page**.
- Rich offline editing; DOCX/ODT/RTF import/export; RTL Arabic mixed with English.
- Tables, images, lists, paragraph/page formatting, styles, reviewing, comments, track changes, footnotes, contents and PDF export subject to real native validation.
- CI-tested additions include Focus Mode, four offline editable DOCX templates, DOCX-first creation, safe Storage Access Framework handling and asynchronous document creation. Actual device testing is still mandatory.
- Requested extras still pending: verified crash recovery, complete version history, advanced PDF annotation, bibliography/reference automation and optional AI tools.
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

## Verified CI checkpoints
- [First real LibreOffice native build](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39699767102): ARM64 engine compiled successfully; Collabora configure **failed** on missing `lxml` in the selected Python environment.
- [CI integration tests](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39738414456): source patching, Java syntax/core, DOCX template, focus interaction, SAF and autosave guards passed.
- [Latest native build workflow](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/workflows/android-native.yml): consult actual run status; do **not** treat queue/start as APK success.
- No finished AquaWord APK should be advertised or released until native build and on-device quality gates pass.
