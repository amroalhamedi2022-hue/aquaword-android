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
- Offline **pre-edit safety copies** with restore to a new file, SHA-256 validation and unchanged-file deduplication. These snapshots are separate from periodic saving and are not a full document history.
- Lifecycle-aware native save request every two minutes while an editable document is foregrounded, using upstream LibreOffice's native save command and preserving its onPause save. **CI-tested source logic only; crash-recovery and actual write completion remain unverified on device.**
- Four editable DOCX starter templates: Arabic/English research, medical case report and high-yield study notes.
- Focus Mode button in Collabora's Android document editor, with keyboard Escape and reversible tool chrome.
- Async blank-document creation: never block the UI thread while writing the template or launch an incompletely written document.
- SAF URI permission protection against non-persistable and read-only document providers.
- Original AquaWord branding overlay, Arabic recovery labels, 5 launcher icon densities and native Writer new-document flow.

## Requested extras still missing or awaiting end-to-end tests
- Reliable autosave delivery and crash recovery tested under Android process death: periodic native save commands are implemented, **but successful on-device persistence has not yet been demonstrated**.
- Full per-document history and revision controls (pre-edit safety copies do not provide this).
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
- Initial pinned LibreOffice ARM64 engine build completed successfully in GitHub Actions run #39699767102; **Collabora configure then failed** because `setup-python` selected an interpreter without apt-installed `lxml`.
- Corrected workflow now installs pinned `lxml` and `polib` into the exact Python interpreter selected by the runner, with a preflight check before the expensive native engine build.
- Superseded native runs are cancelled by the CI concurrency policy; current run status must be verified on GitHub rather than inferred from a queued job.

## Current factual state
Source overlay and integration tests, including a real Java pre-edit snapshot test and JavaScript Focus Mode test; not a finished application. Collabora source is pulled at build time. An APK cannot be described as built until the native workflow actually succeeds. Internal CI runs are allowed; the user's preference is to receive one completed build, not every intermediate artifact.
