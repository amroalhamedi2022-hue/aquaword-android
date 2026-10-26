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

## SAF provider read-only hardening (requires Android runtime acceptance)

Selected documents with only READ grants now receive native Writer EDIT intents **without invented WRITE permission**. Persisted read-only URI grants are also inspected across Activity restarts. Non-persistable URI selections are tracked only for the current Activity lifetime. Read-only provider device testing is still mandatory and a source-level PASS alone is not proof of Android runtime behavior.

## Native SAF templates / restore lifecycle hardening

The four packaged editable DOCX templates now persist grantable create-document URI permissions, reject incomplete streamed template payloads, and handle unexpected provider exceptions. The pending template and history-restore selection survive Activity recreation (orientation/process restoration where Android delivers a saved state). A recovered document opens only after the new SAF file is successfully written and closed. Source/Python checks are independent of real Android provider validation.

## Retaining expensive compiled APKs without false runtime claims

When SHA-256 checks and package/assets validation have passed but the Android emulator rejects the APK or its runtime checks fail, CI can keep that **UNVERIFIED** APK in a separate unpublished `qa-unverified-<commit>` draft Release. This avoids another hours-long engine rebuild when switching to a device-compatible test path. It is **not** a user-facing release and cannot satisfy runtime acceptance. The successful verified path still requires all Android smoke proof files, and both paths preserve draft-only visibility.


## Native diagnostic build evidence — 25 October 2026 (supersedes stale "not built" wording above)

- Run [#40215579687](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215579687), request/source commit `7304b193355a4d0a6c45673de970c5f08e7f9890`, completed the pinned LibreOffice ARM64 engine, Collabora Android app build, Gradle debug APK packaging, package/assets/native-ELF verification and checksum steps successfully.
- Native library: ARM64 `liblo-native-code.so`, 198,019,656 bytes, SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`.
- APK: `AquaWord-app-arm64-v8a-debug.apk`, SHA-256 `956108363c9ed901cfd5c48f2d205bf200987a1c74bc4065787070fc40f7ffe4`. Package ID and five DOCX fixture payloads passed the workflow's checks.
- The job completed successfully, but its attempt to retain the compile-only APK as an unpublished draft Release received HTTP 403 (resource not accessible by integration). Therefore **the APK was built and structurally verified, but is not currently downloadable**.
- The branch now adds a one-day Actions artifact upload attempt for compile-only builds, pinned to verified MIT-licensed `actions/upload-artifact` commit `cf430e030ddbb5b0abf93d22962f4752f3646cd9`. The upload is best-effort because the repository previously reported exhausted artifact storage; the run summary must state explicitly if no artifact URL is produced.
- Android emulator/device install, real Writer document-layer rendering, Arabic/English open-edit-save-cold-reopen, SAF provider-failure recovery, print/PDF behavior and Xiaomi Pad 5 remain **NOT TESTED**. Compile-only success does not close M-NATIVE-01 or authorize a user-ready release.


## Recovery after snapshot data commit but metadata loss — 2026-10-26

- **Acceptance target:** if the process stops after the complete, fsynced `.snapshot` file is renamed but before its `.properties` metadata is committed, the next history scan reconstructs metadata and exposes the bytes as a clearly labelled `recovered` revision.
- **Safety constraints:** reconstruct metadata only when it is absent (never overwrite an existing invalid record); reject empty/oversize files and paths escaping the private history directory; hash the recovered bytes; commit generated metadata through a synced temporary file and rename; preserve the original snapshot if metadata recovery fails. Before SAF restore, the normal SHA-256 preflight must still reject missing or corrupted bytes before opening a truncating destination.
- **Regression coverage added:** JVM fixture verifies Arabic/English UTF-8 payload recovery, exact-byte restore, stable repeated listing, and that an empty orphan is preserved but not offered as a recovery item. Overlay test verifies explicit English/Arabic UI labels.
- **Current verification state:** production commits `db5cf503fdff6d45d9d32922a9680e5112efe584`, `393741ca5f00c186f602a291a1ccc510d8d9c8e4`, `e8962e5a2d3a795630569604573a2a10296b9fc7`, `00e86e4d57b09dc1d29bde6c4f2044c325bf51a0`; regression commits `04ba25dd48a09869fc0345cda087835c6c97c98b`, `34437c8f998c1a4aa25a0d442d38c56f45a65fec`, `59932b2c1e8ce218c160f642c8c383a356ab1db1`, `32af8773d2af04279380ad85153964c2be405d92`. Fast Source #194 [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40254507054), 124/124 tests; Integration #366 [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40254507061), including Java compilation/execution of the orphan-recovery fixture and PDF preflight tests. The first integration attempt exposed a missing return; the next exposed an arbitrary 3-byte orphan being misclassified as a document. Both were fixed before this passing run.
- **Not covered yet:** real Android process kill in the data/metadata rename window; Xiaomi Pad 5 Writer/SAF roundtrip; native APK install/launch; DOCX Arabic/English rich-content roundtrip; PDF/print. Bounded source recovery does not certify cloud-provider durability.

## Concurrent recovery capture and stale-file cleanup — 2026-10-26

- The history store tracks active capture temporary paths while an input stream is being copied. A concurrent history scan cannot delete an in-flight `.partial` merely because its timestamp exceeds the stale-cleanup threshold.
- A JVM regression test blocks a stream between chunks, ages the active partial, triggers cleanup, resumes the stream, and checks exact-byte restore.
- **CI status for code/test SHA `481a0f7fb9545b3f30b43b15d2e6b8bd55950052`:** Fast Source + real upstream overlay **PASS** in [run #40255989993](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255989993). Integration [run #40255990010](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255990010) was still IN PROGRESS at the desktop LibreOffice DOCX import/re-save step when recorded; the Java race test is not yet confirmed executed.
- **Runtime status:** real Android SAF/cloud-provider behavior, process death on device, native Writer round-trip, PDF/print and Xiaomi Pad 5 remain NOT TESTED.


## Recovery checkpoint metadata-commit failure — 2026-10-26

- Production now preserves an already-fsynced and renamed .snapshot if committing its metadata fails; the next history scan can recover its metadata rather than losing the document bytes in finally cleanup.
- The new deterministic JVM regression injects only the metadata-rename failure, checks temporary-file cleanup, reconstructs the recovered entry and restores byte-identical Arabic/English DOCX data.
- Exact code/test SHA b5a195f090479a0bce2d27d5521bc7b6158ec257: Fast Source [#40263124801 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40263124801); Integration [#40263124630 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40263124630). Source/JVM evidence only.
- Native Android install/launch, real SAF provider behavior, process death on device, Writer roundtrip, PDF/print and Xiaomi Pad 5 remain NOT TESTED. M-NATIVE-01 remains open.

## Recovery metadata publication — 2026-10-26

- **PASS (host/JVM):** a child JVM is terminated abruptly with exit code 24 after the complete, fsynced DOCX snapshot is renamed into place and before its metadata is published. The parent confirms that the committed bytes survive, history scanning reconstructs metadata, and restored bytes match exactly. The deterministic metadata-rename failure test remains in place.
- Test commit: `d433b9d7a6295f8b597cc53f7daff35d8420f747`. Exact-SHA Fast Source [#40273275463 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40273275463) and Integration [#40273275467 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40273275467).
- This is host-side process-death simulation only. **NOT TESTED:** Android process death, actual SAF/provider durability, Writer Arabic/English DOCX edit-save-cold-reopen, PDF/print and Xiaomi Pad 5 runtime.


## Recovery retention across multiple document sources — 2026-10-26

- **PASS (host/JVM):** retention now prefers the newest recovery checkpoint per source identity and removes older revisions of the same source before evicting another document's only/latest checkpoint. If the configured 60-snapshot / 1 GiB caps still cannot be met, the oldest unpinned source checkpoint is evicted to preserve the hard bounds; active writebacks and the global newest point remain protected.
- **Regression:** `AquaWordHistoryCommitTest.testRetentionPreservesLatestSnapshotPerDocument` creates 61 snapshots across 60 source identities and proves that the older B revision is removed while A's only checkpoint and B's newest revision restore byte-identically; final count is 60.
- **Final code+test SHA:** `5228c41a908063998ec79214c7b8625163f75ced`. Test change: `436c54a811d83dd39db8be6aff821b6a34486815`.
- **Exact-head CI:** [Fast Source #40285645818 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40285645818); [Integration #40285645716 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40285645716).
- **NOT TESTED:** real Android SAF/cloud provider failure, Android process death, native Writer DOCX edit-save-cold-reopen, PDF/print, install/launch and Xiaomi Pad 5 UI/runtime. This is host/JVM storage-retention evidence only.
- **Build decision:** no APK build; the targeted Java integration test directly answers the retention invariant and packaging would not validate provider behavior.
- **Google Drive handoff:** FAILED / NOT AVAILABLE because no Google Docs/Drive write connector is exposed in this runtime. The specified AquaWord — HANDOFF document was not updated.


## Recovery history path containment — 2026-10-26

- **Production:** `AquaWordHistory.load()` now canonicalizes the history directory, candidate `.snapshot`, and matching `.properties`; it rejects a record if either file resolves outside the app-private history directory, and treats filesystem security exceptions as an unreadable recovery entry. This closes a symlink-based path escape in recovery discovery; it is not a guarantee against privileged filesystem tampering or every concurrent path-replacement race.
- **Regression:** `testRecoveryRejectsSymlinksOutsideHistoryDirectory` prepares a checksum-valid external payload symlink and a separate external metadata symlink. The history scan must expose neither. The test reports **SKIP** only when the host cannot create symlinks (for example, restricted Windows permissions); Linux CI should exercise the actual rejection path.
- **Code + test SHA:** `986d99e02f2a743916cebfadd8de3898ffdceb7b` on PR #7 branch `fix/saf-save-failure-recovery-20261023`.
- **Final CI recheck:** Fast Source [#40299341921](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40299341921) **PASS** and Integration [#40299341903](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40299341903) **PASS** on checkpoint SHA `140505ee9cf89967d24a459c892e4d3223452199`, which includes the code/test change plus this acceptance update. The earlier Integration run [#40298998454](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40298998454) was cancelled when the branch advanced and is not counted as evidence.
- **Build decision:** no APK build for this path-validation change: the focused JVM regression directly answers whether recovery discovery accepts external symlinks. It cannot prove native Writer/SAF behavior.
- **NOT TESTED:** real Android app-private storage, native Writer recovery, SAF provider failure/readback, Arabic/English DOCX cold-reopen, print/PDF, or Xiaomi Pad 5.
- **Google Drive handoff sync:** **FAILED / NOT AVAILABLE** in this automation runtime because no Google Docs/Drive write connector is exposed; the specified AquaWord — HANDOFF document was not updated.
