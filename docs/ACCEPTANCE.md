# AquaWord Android — acceptance gates

**Scope**: Android only (Xiaomi Pad 5 priority). Windows is expressly excluded.

## Product direction
1. Native Collabora / LibreOffice-based editing. No substitute HTML/WebView word-processing engine.
2. Document toolbar organized in familiar Word Android groupings: Home, Insert, Layout, Review, View; original AquaWord colors, icons and naming.
3. Responsive landscape tablet/portrait phone. High-contrast readable document page; Liquid Aurora limited primarily to surrounding UI. Respect dark mode and reduced motion.
4. Offline local documents; preserve originals and enforce Android SAF permissions correctly.
5. Import/export compatible DOCX, ODT, RTF, TXT; PDF export and print.
6. Arabic RTL mixed with English, Unicode, tables, images, styles, headers, sections, footnotes, page breaks, comments and tracked edits, if actually supported by the mobile engine.

## Independently implemented and CI-tested (not yet device-certified)
- Offline **pre-edit safety copies and post-save recovery checkpoints**, shared in the native library, with restore-to-new-file, SHA-256 validation, corruption-aware deduplication and labeled revision type. Retention remains capped at 60 copies / 1 GiB; not a full unlimited history.
- Lifecycle-aware save request every two minutes for an editable foreground document, native SAVE checkpoint capture and a stricter SAF copy-back path that refuses empty data and reports provider write failures. **Source/JVM-tested, not yet Android-device-certified.**
- Four editable DOCX starter templates: Arabic/English research, medical case report and high-yield study notes. Additionally, a complex QA fixture covers mixed RTL/English, tables, embedded image and multiple pages; desktop LibreOffice compatibility is an independent test.
- Focus Mode button in Collabora's Android document editor, with keyboard Escape and reversible tool chrome.
- Async blank-document creation: never block the UI thread while writing the template or launch an incompletely written document.
- SAF URI permission protection against non-persistable and read-only document providers.
- Original AquaWord branding overlay, Arabic recovery labels, 5 launcher icon densities and native Writer new-document flow.

## Requested extras still missing or awaiting end-to-end tests
- Reliable autosave delivery and crash recovery tested under Android process death: periodic native save commands are implemented, **but successful on-device persistence has not yet been demonstrated**.
- Unlimited full document history with advanced revision comparisons (bounded pre-edit and native post-save checkpoints are a partial implementation).
- AI proofreading, rewriting, summarization and translation (optional, with explicit opt-in).
- PDF annotations and conversions beyond any native Collabora capabilities, citations/bibliography automation and advanced reference styling.
- Repeated Android UI/device verification of focus mode, SAF persistence, document round-trips, printing and compatibility.
- Full feature parity with desktop Microsoft Word is not established and may not be achievable on Android.

## Verification before a SINGLE user-facing APK handoff
- Native APK assembles, installs, launches and stays running on real Android.
- Open/save round-trip without losing content or formatting on a fixture corpus.
- Cross-check round-trip with MS Word / LibreOffice for Arabic+English, styles, tables, images and footnotes.
- Test SAF read-only/open-as-copy and kill/relaunch scenarios.
- Confirm all exposed buttons work (no fake options).
- Verify APK applicationId, minSdk, SHA256 and signing; keep signing keys OUTSIDE git.
- Check notices/licenses and security status.

## Build diagnostics (22 October 2026)
- A prior pinned LibreOffice ARM64 engine build succeeded in GitHub Actions run #39699767102; **Collabora configure then failed** because `setup-python` selected an interpreter missing `lxml`.
- Corrected workflow now installs pinned `lxml` and `polib` into the exact Python interpreter selected by the runner, with a preflight check before the expensive native engine build.
- Repository is now PUBLIC; standard GitHub runners run successfully again. Native CI concurrency now preserves ongoing builds, and full test evidence is written to job summaries while Actions artifact storage is exhausted.

## Current factual state
Source overlay and integration tests, including Java version-recovery checks, rich DOCX compatibility and JavaScript Focus Mode tests; **not a finished application**. A previously started native build uses an older source SHA, so its result cannot verify newer features. Collabora source is pulled at build time. An APK cannot be described as built until the native workflow actually succeeds. Internal CI runs are allowed; the user's preference is to receive one completed build, not every intermediate artifact.
