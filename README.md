# AquaWord Android

**AquaWord** is an Android-only, offline-first document editor project for tablets and phones (Xiaomi Pad 5 first). The intended editing engine is the existing **Collabora Office / LibreOfficeKit** Android stack, not the small legacy WebView editor.

## Current status — 2026-10-22
- Real **public** GitHub repository. Public Linux runners restored free CI execution; all dependencies must retain required licenses and notices.
- **Not a completed Word clone**; no working APK has been produced or verified yet.
- The source overlay and integration CI are checked in. A previous **LibreOffice ARM64 engine build succeeded**, while the subsequent Collabora app configure failed on an unavailable Python module; the workflow preflight now tests its Python dependencies. An AquaWord APK is **not** verified.
- App-private **pre-edit safety copies plus post-save recovery checkpoints**, SHA-256 verification, deduplication of unchanged files, and restore-as-new-document are implemented and JVM/source-tested. The history is bounded (60 copies / 1 GiB) and needs Android validation.
- **Periodic native save requests every 120 seconds**, shared save checkpoints, DOCX MIME-aware creation, and explicit SAF writeback error warnings have been integrated. These require device validation and do not guarantee crash recovery.
- The prior AquaWord 0.2 prototype is historical reference, not the production editor.
- Windows is explicitly out of scope.

## Product requirements
- Word-for-Android-inspired tool layout (original AquaWord branding; no Microsoft graphics).
- Liquid Aurora / glass accents around an accessible, **white/neutral document page**.
- Rich offline editing; DOCX/ODT/RTF import/export; RTL Arabic mixed with English.
- Tables, images, lists, paragraph/page formatting, styles, reviewing, comments, track changes, footnotes, contents and PDF export subject to real native validation.
- CI-tested additions include Focus Mode, four editable DOCX templates, DOCX-first creation, safer Storage Access Framework handling, asynchronous document creation, and real LibreOffice Desktop DOCX round-trip tests.
- Android emulator acceptance harness now checks actual Writer document layer, reversible Focus Mode, bilingual table/image-rich DOCX edit/save/reopen, and phone/tablet 16:10 viewport. This test requires a native APK before it can produce a PASS.
- Requested extras still pending: device-proven crash recovery, unrestricted history, advanced PDF annotation, bibliography/reference automation, optional AI tools, and complete functional/visual parity with Microsoft Word. A source change or a green unit test does not imply these exist.
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
