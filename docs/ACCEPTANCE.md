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


## Recovery history rejects in-directory symlink aliases — 2026-10-26

- **Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip remains **OPEN**.
- **Production:** `AquaWordHistory.load()` now requires canonical snapshot and metadata targets to match their exact expected child paths, not merely to reside somewhere inside the history directory. `recoverOrphanSnapshot()` applies the same check before reading bytes or synthesizing missing metadata. This prevents an in-directory symlink alias from being treated as a second recovery point or from triggering orphan metadata reconstruction.
- **Regression:** `testRecoveryRejectsInDirectorySymlinkAliases` creates a payload/metadata alias pair and a metadata-free alias to an existing snapshot; only the original snapshot may be listed, and no metadata may be created for the orphan alias. The existing external-symlink regression remains in place.
- **Code commit:** `c15f38d07ce6dc0483fa2be7d885fad438360395`. **Test commit / exact code+test head:** `44b132b9849ae51ffffef0b27a763f4c37fade76` on PR #7 branch `fix/saf-save-failure-recovery-20261023`.
- **Exact-head CI:** Fast Source [#40314108206 **PASS**](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40314108206); Integration [#40314108444 **PASS**](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40314108444). Integration ran 125 Python tests and compiled/executed `AquaWordHistoryTest`; its log explicitly reports `PASS: recovery scan rejects in-directory payload/metadata symlink aliases`.
- **Build decision:** no APK build. The JVM regression directly tests filesystem alias handling; packaging would not provide stronger evidence for this invariant.
- **NOT TESTED:** Android device storage behavior, real SAF/cloud-provider failure/readback, Android process death, native Writer Arabic/English DOCX edit-save-cold-reopen, print/PDF, and Xiaomi Pad 5 runtime.
- **Google Drive Handoff:** **FAILED / NOT AVAILABLE**. No Google Docs/Drive write connector is exposed in this runtime; the specified AquaWord — HANDOFF document (ID `1AVpneu7vimB0YjJDdUs_oHKLrGUIQW4PSg5A5cW6j4I`) was not modified. No sync success is claimed.
- **Next:** continue M-NATIVE-01 with real Android/SAF evidence; keep PR #7 Draft and do not modify `main`.


## Recovery sidecar names with an embedded `.snapshot` token — 2026-10-26

- **Finding:** deriving the metadata filename with Java `String.replace(DATA_SUFFIX, META_SUFFIX)` replaced every occurrence, not only the terminal data suffix. A valid orphan named `legacy.snapshot-copy.snapshot` therefore could not rebuild its expected `legacy.snapshot-copy.properties` sidecar, and retention could target the wrong metadata path.
- **Production fix:** `AquaWordHistory.metadataFileForSnapshot()` now strips exactly one terminal `.snapshot` suffix. Loading and both retention eviction paths share the same derivation helper. Code commit: [`a8ccaa13749756794d7ec4fd13e79590dd627cca`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/a8ccaa13749756794d7ec4fd13e79590dd627cca).
- **Regression:** `testSnapshotSuffixInsideBasename` builds a valid Arabic DOCX orphan with an embedded suffix, verifies exact-byte recovery and correct sidecar creation, then fills retention beyond 60 entries and verifies both the oldest snapshot and its matching sidecar are removed. Final code+test SHA: `8af527e334927cf73a16fe3e23d7c0c15367e9b8`.
- **CI:** Fast Source [run #40330416847 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40330416847) on the exact code+test SHA. Integration [run #40330416884](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40330416884) was still in progress at the LibreOffice DOCX roundtrip step when this checkpoint was prepared; no Integration PASS is claimed until its Java history-core test completes on a current SHA.
- **Build decision:** no APK build. The invariant is directly exercised by the JVM history test; a native package would not strengthen this filename/retention check.
- **NOT TESTED:** Android runtime/SAF providers, real process death on device, native Writer Arabic/English edit-save-reopen, PDF/print, and Xiaomi Pad 5 visual/performance acceptance.
- **Google Drive Handoff:** FAILED / NOT AVAILABLE — no Google Docs/Drive write connector is exposed in this runtime; the specified AquaWord — HANDOFF document was not modified.
- **Milestone:** M-NATIVE-01 remains OPEN. Keep PR #7 Draft and `main` unchanged; continue with current-SHA integration evidence and real Android acceptance gates.

## Cached recovery snapshot path substitution — 2026-10-26

- **Finding:** `load()` rejects path aliases during a history scan, but a caller may retain a `Snapshot` object after that scan. If the committed pathname is later replaced with a symlink to an external file containing identical bytes, the previous size/SHA-only `verifyBytes()` check could still accept it.
- **Production fix:** `isCanonicalSnapshotChild()` now checks the snapshot resolves to its exact expected child path before and after checksum verification. The verifier also checks the streamed byte count, size and modification time. `restore()` repeats the path check immediately after opening the source and before the first destination write, then checks again before flush. This narrows path-substitution races; it is **not** an OS-level no-follow open or a complete defense against an attacker able to race path changes.
- **Regression:** `testVerifyRejectsSymlinkSwapAfterListing` retains a valid `Snapshot`, replaces its path with a symlink to an external byte-identical file, and requires both preflight and restore to reject it without writing any destination bytes.
- **Production commit:** [`280e887def184e87bcadf49bbcbaf4d0036c0e9b`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/280e887def184e87bcadf49bbcbaf4d0036c0e9b). **Code+test SHA:** [`98343f343f98b9c6a675b068994f9705f8458787`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/98343f343f98b9c6a675b068994f9705f8458787).
- **CI:** Fast Source [run #40357216114 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40357216114) on the exact code+test SHA. Integration [run #40357216058 — IN PROGRESS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40357216058); at checkpoint time it remained in the real desktop LibreOffice DOCX import/re-save step, so the new JVM regression has **not yet been confirmed by Integration CI**. Earlier Integration run #40357159667 was cancelled after the branch advanced and is not evidence.
- **Build decision:** no APK build for this local history-path invariant; the focused JVM regression directly answers whether a cached snapshot is accepted after path substitution. Android Writer/SAF/device behavior is a separate acceptance gate.
- **NOT TESTED:** actual Android process death, real SAF/cloud-provider write/readback, native Writer Arabic/English DOCX edit-save-cold-reopen, PDF/print, installation/launch and Xiaomi Pad 5.
- **Google Drive Handoff:** FAILED / NOT AVAILABLE because this automation runtime exposes no Google Docs/Drive write connector. The specified `AquaWord — HANDOFF` document was not modified; no sync success is claimed.
- **Milestone:** M-NATIVE-01 remains **OPEN**; PR #7 remains Draft and `main` is unchanged.


## Opened recovery-descriptor verification — 2026-10-26

- **Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip remains **OPEN**.
- **Production:** [e507066f9c17c30e3da2887caf889dae241c97d0](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/e507066f9c17c30e3da2887caf889dae241c97d0) verifies the checksum of the exact already-open recovery FileInputStream before any destination bytes are written, then rewinds that same descriptor for restore. This catches a same-size regular-file replacement between the lease preflight and stream opening; it does not claim OS-level no-follow opening or protection against every same-UID in-place mutation race.
- **Regression:** [651f200b649f2342798af8ea6fbc0d21fd19a8c8](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/651f200b649f2342798af8ea6fbc0d21fd19a8c8) adds a deterministic same-size replacement test and asserts that no destination bytes are emitted before verification succeeds.
- **Focused JVM CI:** workflow [bc3f93cb4ac309a1c3b01c65968e2ab076fb40ee](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/bc3f93cb4ac309a1c3b01c65968e2ab076fb40ee) adds a bounded, free Ubuntu JVM-only job that runs the snapshot/history and PDF-preflight core without waiting for the desktop LibreOffice roundtrip. [Run #40377152228](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152228) **PASS**; logs include the regression result “same-size path replacement is rejected before restore writes”. Fast Source/SAF Contract [#40377152285](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152285) **PASS** on this checkpoint.
- **Full Integration:** [run #40377152231](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152231) was still in the desktop LibreOffice DOCX import/re-save step at the time of this checkpoint. **No full Integration PASS is claimed yet.**
- **Build decision:** no APK build. The question is whether the opened JVM recovery descriptor is verified before the first output write; the focused Java regression directly answers it. APK packaging would not establish real SAF-provider or device behavior.
- **NOT TESTED:** Android install/launch, real SAF read-only/failing-provider recovery, process death on Android, Arabic/English Writer cold roundtrip on device, print/PDF and Xiaomi Pad 5 UI/performance.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE** because no Google Docs/Drive write connector is exposed in this runtime. The specified Drive document was not updated; no sync success is claimed.
- **Next:** keep M-NATIVE-01 open; review completion of full Integration, then continue native Writer/SAF acceptance. PR #7 stays Draft; main unchanged.


## Recovery storage-boundary regression — 2026-10-26

- Production SHA: `a5f45dbbc90d4b97e7db897bbaf1b98b506894ea`; regression SHA: `25f976e31bfca03305b3ff969ec0a767b6c3e83f`.
- The history root now rejects a symlink/canonical-path alias before scanning or creating recovery files. JVM test verifies the outside marker remains unchanged. **CI for this exact test SHA: PENDING** until the matching run completes.
- This is a source-level storage-boundary defense, not a complete defense against every same-UID filesystem race. Android runtime and device acceptance remain NOT TESTED.
- Google Drive Handoff synchronization: FAILED / NOT AVAILABLE; no claim of a Drive write is made.

## 2026-10-26 current PR #7 verification checkpoint

- Branch/head: `fix/saf-save-failure-recovery-20261023` / `aea1a5792e90634080b85d7a1cd0a450beccb7d8`.
- Recovery-core JVM tests: **PASS**, [run #40384562650](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40384562650).
- Fast source + SAF contract: **PASS**, [run #40384562536](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40384562536).
- Full Integration: **PASS** on documentation checkpoint `28e0a4c0c3640f8dcff10f4f1ffcd31b5fe45ef1`, with production/test source unchanged at `aea1a5792e90634080b85d7a1cd0a450beccb7d8`: [run #40387367659](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40387367659). The complete LibreOffice desktop DOCX roundtrip and integration workflow finished successfully. Earlier run #40384562866 was cancelled and is superseded by this PASS.
- Android native APK/device, actual SAF provider failure/truncation, Arabic/English Writer roundtrip, PDF/print and Xiaomi Pad 5 UI remain **NOT TESTED**.
- Google Drive `AquaWord — HANDOFF` sync: **FAILED / NOT AVAILABLE** in this runtime; no Drive document write is claimed.


## 2026-10-26 — writeback-lease retention regression (M-NATIVE-01)

- Added a JVM regression proving an active `AquaWordHistory.WritebackLease` pins the exact Arabic recovery bytes while 60 distinct later checkpoints push the store over its 60-snapshot retention limit.
- The test also verifies retention returns to the 60-entry cap and that a nested restore under the active lease returns byte-identical content.
- Test commit: `d24d8e44ec71df497b8f8d8a33ed4348876607fe`.
- Recovery Core JVM-only CI [#40394504450](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394504450): **PASS**; log includes `PASS: active writeback lease pins exact recovery bytes under retention pressure`.
- Full Integration CI [#40394504512](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394504512): **IN PROGRESS** at this checkpoint; do not treat it as PASS until completed.
- Android SAF provider behavior, native APK install/launch, real Writer Arabic/English round-trip, print/PDF and Xiaomi Pad 5 remain **NOT TESTED**.


## 2026-10-27 — SAF restore staging gate (M-NATIVE-01)

- Added AquaWordHistory.restoreToDestination(snapshot, opener): a private staging copy is written, fsynced, and checked for exact size/SHA-256 and canonical parent before the destination opener is invoked. Native restore now supplies the wt/fallback rwt open as a callback, so a corrupt or changing local recovery source is rejected before the SAF destination is opened.
- Regression coverage mutates/truncates the original checkpoint during destination writes and changes it after staging but before opener invocation; the staged output must remain byte-identical and temporary files must be cleaned.
- Tested head 35d8e8009604e9ca6d979f4bff6b5803f3ebf1b3: JVM Recovery Core [#40413364675 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364675); Fast Source/SAF [#40413364669 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364669); Integration [#40413364968 PENDING at checkpoint update](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364968).
- NOT TESTED: real Android SAF provider failure/truncation, device process death, native Writer DOCX roundtrip, print/PDF, Xiaomi Pad 5 visual/performance, and device runtime. The staging design does not make a provider's mid-write failure atomic.
- No APK build: JVM/overlay tests directly answer the source-staging ordering question; no fresh native build is authorized by the consumed one-shot diagnostic route.
- Google Drive AquaWord — HANDOFF sync: FAILED / NOT AVAILABLE because this runtime exposes no Docs/Drive write connector; no Drive update is claimed. PR #7 stays Draft; main unchanged.

## 2026-10-27 — Recovery snapshot size-bound hardening

- Production: added the shared isWithinSnapshotSizeLimit(long) guard for the 512 MiB per-snapshot ceiling. Persisted metadata loading, cached snapshot verification, provider readback, opened-descriptor verification, staging, and both restore APIs now reject zero, negative, or oversized sizes before hashing or opening a destructive destination. Orphan recovery uses the same guard.
- Regression: AquaWordHistoryCommitTest.testOversizedSnapshotMetadataRejected covers zero, negative, the exact 512 MiB boundary, and cap+1. A tiny fixture with oversized metadata proves history listing rejects it before hashing and leaves the evidence files intact.
- Exact code/test/contract head: 359ff2dcb747ab46c2f7126de2e46701d3b9cf25. Production: 61ec7aa473f263760ebaacd2bcb06bb6f34b266c; JVM regression: 9aae703f43c3b2bc2c813d8e32c0d4fd97330eed; stale overlay assertion corrected in 359ff2dcb747ab46c2f7126de2e46701d3b9cf25.
- Exact-head CI: Recovery Core JVM-only #40425553795 PASS; Fast Source + SAF Contract #40425553801 PASS; Integration #40425553688 PASS. The two broader workflows each ran 125 Python tests; Integration also completed the desktop LibreOffice DOCX roundtrip and JVM recovery core. An earlier Fast Source run on intermediate SHA 9aae703 failed because the source-contract assertion still expected the previous size-check expression; the assertion was updated and the current-head run passes.
- Build decision: no APK build. This bounded Java history/storage invariant is directly exercised by JVM and source-contract tests; packaging would not prove real SAF-provider behavior.
- Still NOT TESTED: Android install/launch, real SAF provider refusal/truncation/readback, Android process death, native Writer Arabic/English edit-save-cold-reopen, print/PDF, and Xiaomi Pad 5 visual/performance acceptance.
- Status: M-NATIVE-01 remains OPEN; PR #7 remains Draft/open; main unchanged. Google Drive Handoff sync remains FAILED / NOT AVAILABLE in this runtime; no Drive write is claimed.


## 2026-10-27 — إظهار فشل تنظيف نسخة الاسترداد المؤقتة (M-NATIVE-01)

- **المشكلة:** كان حذف ملف staging بعد الاستعادة best-effort صامتًا؛ إذا رفض نظام الملفات الحذف، يمكن أن تبقى نسخة إضافية من محتوى المستند داخل مجلد التطبيق الخاص دون إشارة إلى ذلك.
- **الإنتاج:** `efd3b8d802f8c2f0501f5e9d699866ecbe92273f` يجعل فشل حذف نسخة staging يظهر كـ `IOException`. إذا فشلت الاستعادة أصلًا، يُضاف خطأ التنظيف كـ `suppressed exception` حتى لا يُخفي السبب الأساسي. يُزال تسجيل الملف من قائمة الكتابات النشطة حتى عند فشل الحذف.
- **اختبار الانحدار:** `be536961000d2ebd2ee090354ead98180539ab33` يستبدل ملف staging عمدًا بمجلد غير فارغ، ويتحقق من أن وجهة SAF لا تُفتح، وأن فشل التنظيف يُبلّغ عنه دون إخفاء خطأ الاستعادة؛ ثم ينظف fixture الاختبار.
- **الدليل على رأس الكود/الاختبار:** Recovery Core [#40437652804 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40437652804)، Fast Source + SAF Contract [#40437652701 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40437652701)، Integration [#40437652836 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40437652836). سجل Integration يؤكد نجاح اختبار التنظيف الجديد، ونجاح 125 اختبار Python ثم فحوص overlay.
- **قرار البناء:** لا APK لهذه الدفعة؛ الاختبار المركزي JVM يجيب مباشرة عن ترتيب فتح الوجهة وظهور فشل التنظيف. حزمة Android لا تثبت سلوك حذف ملفات staging على نظام الملفات، ومسار البناء التشخيصي الأصلي أحادي الاستخدام سبق استهلاكه.
- **حدود القبول:** Android install/launch، مزود SAF حقيقي يرفض أو يقتطع الكتابة، موت عملية Android، تحرير DOCX عربي/إنجليزي داخل Writer الأصلي مع cold-reopen، PDF/الطباعة، وXiaomi Pad 5 ما زالت **NOT TESTED**. التنظيف الفاشل قد يترك بيانات داخل مساحة التطبيق الخاصة؛ أصبح هذا الآن خطأً ظاهرًا بدل الصمت، لكنه لا يضمن حذفًا آمنًا عند تعطل نظام الملفات.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE**؛ لا يتوفر موصل كتابة Google Docs/Drive في بيئة هذه الجولة، لذلك لم يُعدّل المستند المحدد.
- **الاستئناف:** إبقاء `M-NATIVE-01` وPR #7 بوضع Draft/Open؛ مواصلة قبول Android/SAF الواقعي دون فتح milestone جديد أو تعديل `main`.


## 2026-10-27 — تنظيف رابط staging معلّق (M-NATIVE-01)

- **الثغرة الدقيقة:** `File.exists()` يتبع الروابط الرمزية ويُرجع `false` للرابط المعلّق؛ لذلك كان مسار التنظيف قد يتجاوز `delete()` ويترك رابط staging داخل مجلد الاسترداد.
- **الإنتاج:** [`8677130684bae1994d6e299c85987a465c39e282`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/8677130684bae1994d6e299c85987a465c39e282) يستدعي حذف المسار مباشرة حتى لو أعاد `exists()==false`، مع إبقاء الإبلاغ عن فشل الحذف وإزالة تسجيل الكتابة النشطة. كما رُتبت مسافات كتلة الاستعادة لتبقى القراءة والصيانة واضحتين.
- **اختبار الانحدار:** [`4327ed7d331cd026a0bb8d1d3efda86c6b971046`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/4327ed7d331cd026a0bb8d1d3efda86c6b971046) ينشئ رابطًا رمزيًا إلى هدف غير موجود، ويثبت أن الاستعادة ترفض فتح وجهة SAF وأن رابط staging نفسه يُحذف. إذا منع نظام الاختبار إنشاء الروابط الرمزية، يسجّل الاختبار SKIP لهذه الحالة فقط.
- **CI على رأس الكود/الاختبار:** Recovery Core [#40438130392 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40438130392)، Fast Source + SAF Contract [#40438130338 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40438130338)، Integration [#40438130406 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40438130406). سجل Integration يثبت نجاح اختبار فشل التنظيف واختبار الرابط المعلّق، ونجاح 125 اختبار Python وفحص Collabora source-layout.
- **قرار البناء:** لا APK؛ الاختبار JVM يختبر حالة رابط نظام الملفات مباشرة، والبناء لا يضيف دليلًا على مزود SAF أو الجهاز. لم يُستخدم runner أو API مدفوع.
- **حدود القبول:** Android install/launch، مزود SAF حقيقي يرفض أو يقتطع الكتابة، موت عملية Android، تحرير DOCX عربي/إنجليزي داخل Writer الأصلي مع cold-reopen، PDF/الطباعة، وقبول Xiaomi Pad 5 ما زالت **NOT TESTED**.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE**؛ لا يوجد موصل كتابة Google Docs/Drive متاح في هذه البيئة، ولم تتم مزامنة المستند المحدد.
- **الاستئناف:** الاستمرار داخل `M-NATIVE-01` وPR #7 دون فتح milestone جديد أو تعديل `main`؛ لا يُعتبر أي اختبار مصدر بديلًا عن قبول Android/SAF الفعلي.


## 2026-10-27 — Recovery metadata hash-format gate

- Added a production validation gate requiring both persisted content and source SHA-256 fields to use the canonical lowercase 64-character hexadecimal format produced by the app.
- Added JVM regression coverage for malformed content hashes and malformed source-identity hashes. The test also asserts that rejected snapshot/metadata files are preserved rather than deleted.
- Acceptance is limited to local metadata parsing/listing. Android SAF provider failures, process-death behavior on-device, native Writer DOCX round-trip, printing/PDF, and Xiaomi Pad 5 UI remain NOT TESTED.
- Milestone remains M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip (OPEN); no APK build is justified by this metadata-only safety change.


## 2026-10-27 — M-NATIVE-01 diagnostic build request (pending)

- **Purpose:** validate current-branch ARM64 native integration and APK packaging against pinned Collabora/LibreOffice, not to release the app.
- **Question:** can the current AquaWord overlay and native engine produce an integrity-checked arm64-v8a APK with the expected application identity and native ELF?
- **Why JVM/source tests are insufficient:** they do not run the NDK linker, Android resource/manifest merge, Gradle packaging or final APK inspection. The prior diagnostic APK belongs to an older source checkpoint.
- **Status:** requested; CI result and artifact are pending. This is a single diagnostic attempt using free hosted CI.
- **Not tested even if build passes:** emulator/device install and launch, Arabic/English DOCX round-trip, real SAF failure/recovery, printing/PDF and Xiaomi Pad 5 UI/performance.


## 2026-10-27 — Native diagnostic result and verifier correction

- Run 40449362565 checked out request commit 45d94cc3bda67de693beb33018ebf159c4018ff4 and used pinned Collabora source 2333344185931274f9c49d6c12a408cefcef6844. Native engine reuse, Collabora configure, Android source compile and Gradle APK generation completed far enough to produce an APK.
- **PASS within the failed verification step:** ZIP integrity and scripts/verify_native_apk.py reported arm64-v8a; the packaged native library was 198,019,656 bytes with SHA-256 ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2. APK SHA-256 printed by the verifier: 7bc4818d200c8590859300adc5635857576e752a6abba9226ef82bff20481bec. apksigner reported v2 signature verification true and printed a certificate SHA-256 digest.
- **FAIL — CI verifier false negative:** the workflow required the literal text 'Signer #1 certificate SHA-256 digest:' while the installed apksigner printed 'V2 Signer: certificate SHA-256 digest:'. The step exited before package-ID/template assertions could be confirmed. No artifact was retained; the run's artifact list is empty. The logged SHA is evidence from the runner, not a downloadable APK or release deliverable.
- Corrected the workflow to accept both supported apksigner labels and added a source-contract regression. This fix is not itself a native build retry; source CI must pass first. Any later native attempt must answer whether the corrected verification gate completes and a downloadable artifact is retained. Android install/launch and all device-level gates remain NOT TESTED.


### 2026-10-27 — Source-test contract correction

- The first Fast Source run after the verifier fix failed only because an older test still asserted the obsolete literal 'Signer #1 certificate SHA-256 digest:'. The new regression for both apksigner labels passed in that same run.
- Updated the older test to assert the new dual-format grep contract. Re-run Fast Source and Integration on the new exact commit before considering the verifier fix accepted.


## 2026-10-27 — Executable apksigner report gate

- Replaced the workflow's brittle literal grep checks with scripts/verify_apk_signature.py. The helper requires an explicit successful v2-verification line and a valid 32-byte SHA-256 certificate digest, accepting both the numbered signer and V2 Signer formats emitted by Android build-tools.
- Added executable unit cases for both formats, colon-separated digests, false v2 status, missing/malformed digest, and unknown labels. This addresses the previous false-negative where a native APK was produced but a label mismatch stopped the workflow before package/template acceptance.
- CI status at commit creation: pending; do not count this gate as accepted until Fast Source and Integration pass on the exact code SHA.
- This source-only change does not authorize another native build; the previous one-shot diagnostic attempt failed at the old verifier gate and the existing request explicitly prohibits automatic retries.
- Android install/launch, real SAF provider failure/recovery, native Writer Arabic/English edit-save-cold-reopen, print/PDF, and Xiaomi Pad 5 remain NOT TESTED.
- Google Drive AquaWord — HANDOFF sync: FAILED / NOT AVAILABLE in this runtime; no Google Docs/Drive write connector is exposed, so the specified document was not updated.


## 2026-10-27 — Executable apksigner gate: exact-head CI result

- **Code/test SHA:** 91f4ae27e2c45f1472c1e88b43a03a1533171fc9.
- **PASS — Fast Source + SAF Contract:** [run #40451699143](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451699143). All 132 Python tests passed in 5.227 s; the pinned-source and native overlay preflight completed.
- **PASS — Integration:** [run #40451699170](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451699170). All 132 Python tests passed in 4.033 s; desktop LibreOffice DOCX import/re-save, snapshot-history JVM regressions, PDF preflight tests and pinned Collabora overlay smoke passed. This remains host/desktop/JVM evidence, not Android device acceptance.
- **PASS — Recovery Core JVM-only:** [run #40451699130](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451699130).
- **Superseded failures, not counted as passes:** [Fast Source #40451553723](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451553723) exposed double-escaped parser/test newlines; [Fast Source #40451612303](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451612303) then exposed an unknown-label fixture that did not match the parser's case-sensitive detection. Both were corrected, and the exact-head runs above passed.
- The new executable report parser requires apksigner's v2 verification result to be explicitly true and a syntactically valid 32-byte SHA-256 certificate digest in a supported signer-label format. It parses the report; the preceding apksigner process and its exit status remain the actual signature-verification step.
- **Build decision:** no native rebuild in this round. The previous one-shot diagnostic failed at its old report gate, and the branch's explicit request says not to retry that diagnostic automatically. The source/test fix is now validated without consuming another multi-hour runner.
- **Still NOT TESTED:** current-source native APK download/retention, install/launch, real Android SAF provider failure/truncation and recovery, Android process death, Writer Arabic/English edit-save-cold-reopen, print/PDF runtime, and Xiaomi Pad 5 visual/performance acceptance.
- **Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip remains OPEN. PR #7 remains Draft/open; main was not changed.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE; this runtime exposes no Google Docs/Drive write connector, so the specified Drive document was not modified.


## 2026-10-27 — One-shot current-source ARM64 diagnostic queued

- **Purpose-bound build:** GitHub Actions run [#40459738117](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40459738117), source SHA `84b168b8dda1d1c6e89760631dddbb475d9ef59d`, exact one-shot commit message `AquaWordNativeDiagnosticRetryOnce`.
- **Test question:** does this exact AquaWord feature-branch source package a structurally verified `arm64-v8a` APK with the pinned Collabora/LibreOffice native ELF, expected application ID, valid signature report, matching bundled DOCX templates, SHA-256, and a downloadable short-lived Actions artifact?
- **Why source tests are insufficient:** JVM history/SAF simulations, Python overlay contracts and desktop LibreOffice DOCX round-trips do not run the Android NDK native link, Gradle manifest/resource merge, APK packaging/signature verification, or artifact retention.
- **Status at checkpoint:** native job `in_progress`; no artifact listed yet. Do not call this PASS until the run completes and the artifact is verified. This is the single newly authorized attempt; if it fails, do not automatically retry.
- **Scope limits even on build success:** no real Android install/launch, no physical-device Writer Arabic/English edit-save-cold-reopen, no actual SAF provider failure/truncation/recovery, no print/PDF runtime proof, and no Xiaomi Pad 5 visual/performance acceptance. These remain **NOT TESTED**.
- **Preflight evidence on preceding source/test SHA `48468eb1815f71bb9f462e84389fda2d1d8040be`:** Fast Source [#40451848520 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451848520), Integration [#40451848529 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451848529), Recovery Core [#40451848560 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40451848560). The native run repeats its own source preflight at the request SHA.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE in this runtime; no Google Docs/Drive write connector is exposed, so the named Drive document was not modified.


## 2026-10-27 — Current-source ARM64 diagnostic result (one-shot; compile-only)

- **PASS — Native diagnostic workflow:** [run #40459738117](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40459738117), checked-out source SHA `84b168b8dda1d1c6e89760631dddbb475d9ef59d`, pinned Collabora/LibreOffice source `2333344185931274f9c49d6c12a408cefcef6844`. Native engine, Collabora Android source integration, Gradle APK packaging, package/template/signature checks and artifact upload all succeeded.
- **APK:** `AquaWord-app-arm64-v8a-debug.apk`, 265,562,824 bytes, SHA-256 `26851485b4dc7b3b1fa840f24276ed21fe9a0a4a388fbc69199a8d7b5d97ecfc`. The package ID `com.aquaword.app.debug` passed the workflow's `aapt dump badging` gate. All five bundled DOCX templates matched the generated template files.
- **Native library:** `lib/arm64-v8a/liblo-native-code.so`, 198,019,656 bytes, SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`. Workflow validation and independent artifact inspection confirm ELF64/AArch64, shared-object type; the APK ZIP test passed.
- **Signing evidence:** Android `apksigner verify` returned v2=true. Debug certificate SHA-256 `b1de54d42a34046f9f305cae3c34b25c1aeb95c9518b51021f8c998e7dadb15b`. This is a debug-signed diagnostic build, not a production-signed release.
- **Downloadable Actions artifact:** [artifact #12715085399](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40459738117/artifacts/12715085399), 265,564,632 bytes, one-day retention. The downloaded ZIP's independently recomputed SHA-256 is `bc9943af59f61ca09f756dfdc254730359c566b66ae6f028f2b7ebcae6f1e842`; ZIP integrity passed and the embedded APK hash matches `SHA256SUMS`.
- **Purpose answered:** current-source ARM64 engine and Gradle packaging work, the corrected signature-report gate passes, and the short-lived artifact can be retained/downloaded. This closes the build/packaging question only, not the milestone.
- **NOT TESTED:** Android emulator step was intentionally skipped by the one-shot compile-only trigger. No Android install/launch, real SAF provider failure/truncation and recovery, Android process death, Arabic/English Writer edit-save-cold-reopen, print/PDF runtime, or Xiaomi Pad 5 visual/performance acceptance. Keep `M-NATIVE-01` OPEN and PR #7 Draft.
- **No retry:** this was the sole fresh diagnostic authorization; do not trigger another native build automatically.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE; this runtime has no Google Docs/Drive write connector. The specified Drive document was not modified.


## 2026-10-27 — Collision-safe local file save staging

- **Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip remains **OPEN**.
- **Production hardening:** the pinned Collabora local-file writeback overlay no longer reuses the predictable sibling path `.<destination-name>.part`. It creates a unique staging file in the destination directory with `File.createTempFile(".aquaword-", ".part", resolvedFile.getParentFile())`, writes and fsyncs the completed content, then attempts the existing rename-based replacement. Failure cleanup is null-safe and reports an unremovable staging file instead of masking the original save error.
- **Regression fixture:** now models the real pinned byte-copy loop and fsync; the overlay contract asserts unique same-directory staging and rejects the deterministic collision-prone path.
- **Source/test refs:** production overlay change [`4f24c606`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/4f24c606e5f736a683e120d8871c7b92d7bbb472), explicit newline-anchor repair [`d1f586ed`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/d1f586ed0dc58cf0b1061dc3d0edfb50a0f1bbf7), test contract [`23c9cab1`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/23c9cab13795c31e2ebf9044570c7e93ee393e5f), fixture alignment / exact tested head [`3d3a8235`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/3d3a8235a018fdfbee10228b64701dde06ac893b).
- **Exact-head CI — PASS:** [Fast Source #40463302415](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302415), 132 Python tests; [Integration #40463302399](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302399), including pinned Collabora overlay smoke, JVM recovery/PDF preflight regressions, and desktop LibreOffice DOCX round-trip; [Recovery Core #40463302400](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302400).
- **Superseded failures:** earlier Fast Source runs failed because the overlay's new anchor did not match the simplified test fixture. The overlay now uses explicit newline construction and the fixture mirrors the pinned upstream byte-count structure; all three exact-head CI jobs above pass.
- **Not device-certified:** actual local filesystem replacement on Android, SAF/cloud provider writeback, Android process death, native Writer Arabic/English edit-save-cold-reopen, PDF/print, and Xiaomi Pad 5 UI/performance remain **NOT TESTED**.
- **Build decision:** no new APK build for this source-overlay invariant. The current-source diagnostic build already answered the ARM64 packaging question; this change is directly exercised by the pinned-source overlay tests, and a rebuild would not prove actual device filesystem behavior.
- **Google Drive Handoff:** **FAILED / NOT AVAILABLE** in this runtime; no Google Docs/Drive write connector is exposed, so the specified AquaWord — HANDOFF document was not modified.


## Independent diagnostic APK artifact recheck — 2026-10-27

- Independently downloaded Actions artifact [#12715085399](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40459738117/artifacts/12715085399), created 2026-10-27 06:27:30 UTC; scheduled expiry 2026-10-28 06:27:26 UTC.
- Outer ZIP SHA-256 verified locally: `bc9943af59f61ca09f756dfdc254730359c566b66ae6f028f2b7ebcae6f1e842`, matching the GitHub artifact digest. `unzip -t` passed with no archive errors.
- Embedded APK: 265,562,824 bytes; SHA-256 `26851485b4dc7b3b1fa840f24276ed21fe9a0a4a388fbc69199a8d7b5d97ecfc`, matching the artifact's `SHA256SUMS`.
- Independent APK inspection: ZIP integrity PASS; signature report states APK Signature Scheme v2=true; debug certificate SHA-256 `b1de54d42a34046f9f305cae3c34b25c1aeb95c9518b51021f8c998e7dadb15b`; embedded `liblo-native-code.so` is ELF64 little-endian AArch64, 198,019,656 bytes, SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`. The package ID `com.aquaword.app.debug` and five DOCX template checks were recorded by the successful build workflow.
- **Provenance limitation:** this diagnostic artifact was built from source/request SHA `84b168b8dda1d1c6e89760631dddbb475d9ef59d`, pinned Collabora source `2333344185931274f9c49d6c12a408cefcef6844`. It predates the later local-save staging fix `4f24c606e5f736a683e120d8871c7b92d7bbb472` and its regression fixture. It therefore does **not** validate those later changes and is not a current-source release.
- The APK is debug-signed and compile-only. Android install/launch, real SAF provider failures/recovery, Android process death, Arabic/English Writer edit-save-cold-reopen, print/PDF, and Xiaomi Pad 5 UI/performance remain **NOT TESTED**. The artifact is temporary and must not be described as a final release.
- No rebuild was triggered: the existing checkpoint explicitly marks the diagnostic as one-shot and prohibits automatic retries. This entry is a download-and-integrity recheck, not a new CI run.
- Google Drive “AquaWord — HANDOFF” synchronization remains **FAILED / NOT AVAILABLE** because this runtime exposes no Google Docs/Drive write connector; the specified Drive document was not modified.

## Recovery capture path-collision safety — 27 October 2026

- **Milestone:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` remains **OPEN**.
- **Production finding:** capture cleanup previously called `data.delete()` when a byte-rename returned failure and metadata was absent. On a collision/failure, that path could belong to an earlier recovery point rather than this capture. The temporary `.partial` and `.meta-partial` paths were also opened with truncating `FileOutputStream` without first reserving ownership.
- **Production fix:** reject occupied final/metadata paths, reserve `.partial` and `.meta-partial` with `createNewFile()`, track which temporary paths this invocation actually created, and delete only those owned temporary paths. Final `.snapshot` files are never removed by capture cleanup; an orphan after successful data rename remains recoverable if metadata publication fails.
- **Deterministic regression:** `AquaWordHistoryCommitTest.testCaptureIdentifierCollisionsPreserveExistingFiles` exercises pre-existing `.partial`, `.snapshot`, `.properties`, and `.meta-partial` paths. All four sentinel files remain byte-identical and no extra files are left. Existing process-death, metadata-rename-failure, restore-staging, retention, and PDF-preflight tests remain in the same JVM suite.
- **Production commit:** [`e7dfd1ec`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/e7dfd1ecfd26f24b4c7e6f665db72f53bf27a9da). **Exact code/test head:** [`9bbc94d0`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/9bbc94d07a053fc2009dec4b5c0cc159cd3dc675).
- **Exact-head CI — PASS:** [Fast Source #40487900243](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40487900243) — 132 tests plus real pinned Collabora overlay/source checks; [Recovery Core #40487900239](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40487900239) — JVM crash-window/collision/restore tests and PDF preflight; [Integration #40487900234](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40487900234) — desktop LibreOffice DOCX round-trip and integration contracts.
- **Honest failure history:** earlier exact-head CI attempts failed on stale source-contract assertions after the cleanup semantics changed, including a false-positive substring check that matched `metadata.delete()`. The assertions were corrected; only the three green runs above are counted as final evidence.
- **Build decision:** no APK build. The question was whether collision paths can overwrite/delete prior recovery files; deterministic JVM tests directly exercised that invariant. Native packaging would not strengthen this source-level proof.
- **NOT TESTED:** Android device/SAF provider behavior, process death on Xiaomi Pad 5, native Writer Arabic/English edit-save-cold-reopen, printing/PDF runtime, and device visual/performance acceptance. The earlier diagnostic APK is from an older source SHA and is not proof for this fix.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE** in this automation runtime; no Google Docs/Drive write connector is exposed, so the specified Drive document was not modified. No sync success is claimed.
- **Next:** keep PR #7 Draft and `main` unchanged; continue `M-NATIVE-01` toward real Android SAF/Writer evidence. No further native build is triggered by this change.


## 2026-10-27 — Existing ARM64 APK runtime smoke (no rebuild; blocked before install)

- **Workflow:** [#40504114768](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40504114768) failed at the emulator launch step. The x86_64 Ubuntu host reported: `Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host`; ADB never obtained a booted emulator.
- **What passed:** existing artifact provenance and SHA-256 checks, ZIP integrity, and synthetic bilingual DOCX fixture generation. The APK was **not installed**, and no app/runtime evidence artifact was retained.
- **What did not run:** Android installation, app launch, native Writer, Arabic/English edit-save-cold-reopen, and simulated tablet UI checks. These remain **NOT TESTED**, not product failures.
- **Artifact provenance:** build source SHA `84b168b8dda1d1c6e89760631dddbb475d9ef59d`; APK SHA-256 `26851485b4dc7b3b1fa840f24276ed21fe9a0a4a388fbc69199a8d7b5d97ecfc`; artifact ID `12715085399`. It predates current recovery/staging fixes and is baseline-only.
- **No retry:** the runtime workflow was explicitly one-shot; no automatic retry or new native build was started. A future runtime attempt needs a proven compatible free ARM64 execution environment. The available x86_64 runner cannot boot this ARM64 AVD.
- **Evidence accuracy fix:** source audit found the smoke receipt hard-coded API 35 despite workflow configuration requesting API 30. Script commit [`5cc1c54`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/5cc1c54ed5cee7b8ea41ab45e4fe869588476d08) now records the observed SDK API and release from Android system properties; regression test commit [`16d585b`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/16d585bcc449a41c5977a22be195c6b4081e0511) prevents a return to the hard-coded value.
- **Exact code/test head CI:** Fast Source [#40506893261 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40506893261), Recovery Core [#40506893297 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40506893297), Integration [#40506893283 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40506893283). These validate source/tests at `16d585bcc449a41c5977a22be195c6b4081e0511`, not Android device acceptance.
- **Remaining NOT TESTED:** physical Xiaomi Pad 5; real SAF provider refusal/truncation and recovery; current-source native package; print/PDF; production signing and visual/performance acceptance.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE; no Google Docs/Drive write connector is exposed in this runtime, so the named document was not modified.


## 2026-10-27 — Orphan recovery metadata-staging collision guard

- **Milestone:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` remains **OPEN**.
- **Production fix:** `recoverOrphanSnapshot()` previously opened `.meta-partial` with truncating `FileOutputStream`. An occupied staging path could be overwritten and then published as committed metadata. Recovery now reserves an absent path with `createNewFile()`. If a path is already occupied, it promotes it only when the staged metadata is structurally valid and its SHA-256/size match the committed snapshot; unrelated or partial staging bytes are preserved. Cleanup is limited to a staging file this attempt created.
- **Regression:** the JVM suite creates a valid orphan DOCX snapshot plus a byte-sentinel `.meta-partial` collision, runs the real history scan, and verifies that the sentinel and original snapshot remain byte-identical and no final metadata is published.
- **CI history:** the first run (`#40511350886`) correctly exposed that crash-window recovery must preserve a valid `.meta-partial`; follow-up runs (`#40511814419`, `#40511806551`) then exposed an outdated assertion that expected a synthesized `recovered` label instead of preserving the original `saved` revision metadata. The implementation now promotes only a staged record whose SHA-256/size and metadata fields match the committed snapshot, while leaving unrelated collision bytes untouched. Exact code/test head `f7585307cd36e50e92ead4941837053bdc95d35d` passed [Recovery Core #40512128149](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40512128149), [Fast Source #40512128190](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40512128190), and [Integration #40512128093](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40512128093). Recovery logs confirm the abrupt-process-death regression passed; the occupied `.meta-partial` sentinel regression passed in the same suite.
- **Build decision:** no APK build. This is a deterministic Java filesystem contract directly tested by JVM regression; native packaging would not establish Android-provider behavior.
- **Still NOT TESTED:** real Android SAF provider collisions/failures, on-device process death, Writer Arabic/English cold-reopen, print/PDF, and Xiaomi Pad 5 visual/performance acceptance.
- **Google Drive AquaWord — HANDOFF:** sync remains **FAILED / NOT AVAILABLE** until the specified Google Docs document can actually be written; no sync success is claimed.


## 2026-10-27 — Current-source ARM64 diagnostic request (pending outcome)

- **M-NATIVE-01 remains OPEN.** One purpose-bound free ARM64 compile/package diagnostic is running at source SHA [`77f45d80e32269e1b2d3aff111ba0611f865e9b3`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/77f45d80e32269e1b2d3aff111ba0611f865e9b3): [native run #40528607353](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528607353) — **IN PROGRESS** at checkpoint time.
- Question: whether the pinned Collabora/LibreOffice ARM64 engine, AquaWord overlay and Gradle package the current source into a structurally verified ARM64 APK with valid package identity, native ELF and SHA-256. JVM/source tests cannot prove native linker/Gradle packaging, so this build has a distinct integration purpose.
- Exact trigger-SHA source checks passed: [Fast Source #40528616229](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528616229), [Recovery Core #40528615964](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528615964), [Integration #40528616032](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528616032).
- The workflow is purpose-bound and compile-only for this exact trigger; it skips emulator acceptance and must not be retried automatically if it fails. APK SHA/artifact link will be recorded only if the workflow actually produces and retains the file.
- **NOT TESTED regardless of compile result:** Android install/launch, real Writer Arabic/English round-trip, real SAF failure/recovery, print/PDF, Xiaomi Pad 5 and final release signing.
- Google Drive `AquaWord — HANDOFF`: **FAILED / NOT AVAILABLE**; no Docs/Drive write connector is exposed, so the named document was not updated.


## 2026-10-27 — ARM64 diagnostic result (compile/package only)

- Native run [#40528607353 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528607353), source SHA [`77f45d80e32269e1b2d3aff111ba0611f865e9b3`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/77f45d80e32269e1b2d3aff111ba0611f865e9b3), pinned Collabora `2333344185931274f9c49d6c12a408cefcef6844`.
- Package `com.aquaword.app.debug`, ABI `arm64-v8a`, APK 265,562,824 bytes. APK SHA-256 independently recomputed: `3c6ed4e5482416f403d97e4b732fa5423224cc4ca7869518da869a21e5751994`; ZIP integrity PASS. Native library is ELF64 AArch64 / ET_DYN, 198,019,656 bytes, SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`.
- `apksigner verify` v2=true; debug certificate SHA-256 `4a9c7a7383117331e284e86a360d96e7943521aec623dec4930562939954d4a1`. Artifact [ID 12745752188](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528607353/artifacts/12745752188), ZIP SHA-256 `495b2367ec47422dfca52fab037e25b9a9f4631aa0d82cf76669360d7d289114`, expires `2026-10-28T15:22:53Z`. This is diagnostic/debug and **not a final release**.
- Exact build-source Fast Source [#40528616229 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528616229), Recovery Core [#40528615964 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528615964), Integration [#40528616032 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40528616032). Docs-head checks on `4ff31d2`: [Fast Source #40530185405 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40530185405), [Recovery Core #40530185455 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40530185455), [Integration #40530185240 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40530185240).
- Emulator/device run was intentionally skipped. **NOT TESTED:** install/launch, Arabic/English Writer edit-save-reopen, real SAF failure/recovery, PDF/print, Xiaomi Pad 5 and production signing. M-NATIVE-01 stays OPEN; no retry or final release from this one-shot diagnostic.
- Google Drive `AquaWord — HANDOFF` sync remains FAILED / NOT AVAILABLE; no Docs/Drive write connector is exposed.


## 2026-10-27 — Reference-count active recovery staging paths

- **Milestone:** M-NATIVE-01 remains OPEN. This is a host/JVM recovery-integrity fix, not proof of Android Writer or SAF runtime acceptance.
- **Production:** `history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java` now reference-counts each active capture/restore-staging path. A second operation that collides on the same deterministic staging path can release only its own registration; it can no longer remove the first writer's protection and let stale-partial cleanup unlink bytes still being written. Restore staging uses the same balanced register/unregister helpers.
- **Regression:** `testCollisionDoesNotUnregisterActiveCapture` blocks one capture, ages its `.partial`, attempts a second capture with the same ID, runs history cleanup, and verifies the original partial and byte-exact committed recovery checkpoint survive. The test uses reflection only to reach the existing package-private deterministic-ID test seam; no production API was widened.
- **Final verification at PR head [`7cf14cc6dcf381e4bfa541414e6fdc70e3df2448`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/7cf14cc6dcf381e4bfa541414e6fdc70e3df2448):
  - Recovery Core [#40550048384 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40550048384), including Java compilation, crash-window regressions, recovery collision test, restore staging, retention and PDF preflight contracts.
  - Fast Source [#40550048356 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40550048356), including updated generated-overlay source contract.
  - Integration [#40550048403 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40550048403), including real pinned Collabora source overlay and desktop LibreOffice fixture checks; this is still not Android-device acceptance.
- **Failure history retained:** earlier CI caught a missed Set-to-Map staging call, then an accidental recursive final decrement, and then the old overlay contract still expecting Set operations. Each was corrected. The final three checks above pass; no failed attempt is represented as a pass.
- **Build decision:** no APK rebuild. The question was whether a failed colliding writer could unpin another active writer; the deterministic JVM regression directly exercises that race. Recompiling LibreOffice would not provide stronger evidence for this file-lock contract.
- **Still NOT TESTED:** real Android install/launch; Writer Arabic/English DOCX edit-save-cold-reopen; actual SAF providers that reject/truncate writes; process death on Xiaomi Pad 5; PDF/print; tablet visual/performance acceptance.
- **Google Drive `AquaWord — HANDOFF`: FAILED / NOT AVAILABLE** because no Google Docs/Drive write connector is exposed in this runtime. The named Drive document was not updated; no sync success is claimed.


## 2026-10-27 — SAF explicit-truncation fallback for provider mode rejection

- **Production overlay:** `scripts/apply_to_collabora.py`, commit [`1257ee44e21989e8c6e9e8c95939c56279dd303b`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/1257ee44e21989e8c6e9e8c95939c56279dd303b). Native DOCX writeback and PDF export now retry explicit `rwt` mode when a provider rejects `wt` with `IllegalArgumentException`, in addition to the previously handled `FileNotFoundException` / `UnsupportedOperationException`. Ambiguous `w` fallback remains prohibited.
- **Regression contract:** test update [`e2a1f5b419be4ebb9555a5d85abf7dcc4f37883b`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/e2a1f5b419be4ebb9555a5d85abf7dcc4f37883b) asserts the fallback is present in both native DOCX save and PDF export paths.
- **Exact-head CI — PASS at `e2a1f5b419be4ebb9555a5d85abf7dcc4f37883b`:** [Fast Source #40568761742](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40568761742), [Recovery Core #40568761709](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40568761709), [Integration #40568761864](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40568761864). These are source/JVM/desktop integration checks, not Android ContentProvider runtime proof.
- **Build decision:** no APK build. The test question is whether the overlay catches this specific provider-mode rejection and attempts only explicit truncation mode; exact-head source and integration tests exercise that contract. An APK build would not prove provider-specific exception behavior.
- **NOT TESTED:** real SAF providers that throw `IllegalArgumentException` for `wt` but accept `rwt`; providers that reject both modes; end-to-end Arabic/English Writer save/reopen; PDF export/print on Android; Xiaomi Pad 5 behavior.
- **Google Drive `AquaWord — HANDOFF`: FAILED / NOT AVAILABLE** because no Google Docs/Drive write connector is exposed in this automation runtime. The named Drive document was not updated.
- **Next:** continue `M-NATIVE-01`; validate on a real Android provider/device when an authorized compatible runtime is available. Do not treat source-contract PASS as device acceptance.


## 2026-10-27 — SAF fallback parity for restore and blank-document creation

- **Milestone:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` remains **OPEN**.
- **Production change:** `scripts/apply_to_collabora.py` now treats `IllegalArgumentException` from `ContentResolver.openOutputStream(uri, "wt")` as a rejected mode in both recovery restore and new-document creation, then tries explicit `rwt`. This aligns those two paths with the existing native DOCX save and PDF export fallback. No ambiguous `w` fallback was introduced.
- **Regression coverage:** `tests/test_overlay.py` asserts that both generated Java paths catch `FileNotFoundException | UnsupportedOperationException | IllegalArgumentException`, keep the explicit `rwt` fallback, and do not use plain `w`. These are overlay/source-contract tests, not proof of behavior on a real Android provider.
- **Build decision:** no APK build. The question is whether the overlay emits the complete exception/fallback contract in both code paths; the source-contract suite directly checks that. A native build would not prove real ContentProvider behavior.
- **CI on the exact code/test state:** Fast Source + SAF Contract [#40585264128 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40585264128); Recovery Core JVM-only [#40585264094 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40585264094); Integration [#40585264131 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40585264131). Production overlay commit: [`e409a04942e96181be9172683ef49b77d7fa4b91`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/e409a04942e96181be9172683ef49b77d7fa4b91); regression-test commit: [`fcf00914dc8832c0b8d4684e6d5f16df2a42e623`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/fcf00914dc8832c0b8d4684e6d5f16df2a42e623). The runs validate the overlay/source contracts, JVM recovery suite, and desktop integration path; they do not prove real Android ContentProvider behavior or device acceptance.
- **Still NOT TESTED:** an actual SAF provider throwing `IllegalArgumentException` for `wt` and accepting `rwt`; provider rejection of both modes; real recovery restore and blank-document creation; Android install/launch; native Writer Arabic/English edit-save-cold-reopen; print/PDF; Xiaomi Pad 5 visual/performance acceptance.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE**; no Google Docs/Drive write connector is exposed in this runtime, so the specified document was not updated and no sync success is claimed.
- **Resume:** continue `M-NATIVE-01`; keep PR #7 Draft/open and `main` unchanged. Require exact-head source/recovery/integration CI and then real Android provider/device evidence before closing the milestone.


## 2026-10-28 — shared SAF truncation-mode helper

- Added `history/src/org/libreoffice/androidlib/AquaWordSafOutput.java` and integrated it into native DOCX save, PDF export, recovery restore, blank-document creation, and template creation.
- The helper only tries explicit truncating modes (`wt`, then `rwt` when the first mode is rejected or null). It does not use plain `w`; `SecurityException` and ordinary I/O failures are not swallowed as mode-negotiation failures.
- The JVM regression executes the helper against fake provider behaviors for `FileNotFoundException`, `UnsupportedOperationException`, `IllegalArgumentException`, null streams, permission denial, and generic I/O failure. Overlay contracts confirm the Android-generated code delegates to the helper.
- Tested code/test state plus corrected explicit Java compile lists: [Fast Source #40601163452 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163452), [Recovery Core #40601163437 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163437), [Integration #40601163615 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163615), tested head `0160bed77339e2ef05fa4948e3adff3e1deb310f`.
- Initial recovery/integration compile attempts failed because the new helper was omitted from their explicit `javac` file lists; the workflow source lists were fixed and the final exact-head runs passed.
- **Not device-certified:** actual SAF provider behavior, Android process death, Writer Arabic/English DOCX roundtrip, print/PDF, and Xiaomi Pad 5 remain **NOT TESTED**. No APK was built because JVM tests directly answer this helper-level question.
- Google Drive `AquaWord — HANDOFF` sync: **FAILED / NOT AVAILABLE** in this runtime; no Docs/Drive write connector is exposed.
- M-NATIVE-01 remains **OPEN**; this update does not authorize PR merge, `main` changes, or a final APK handoff.


## 2026-10-28 — Current-source ARM64 diagnostic (one-shot; pending)

- Milestone `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` remains **OPEN**.
- Purpose-bound authorization commit: [`df65aa2d92881f34160eadbbfcc0a96dd5f859ab`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/df65aa2d92881f34160eadbbfcc0a96dd5f859ab). It authorizes one free native diagnostic because the shared `AquaWordSafOutput.java` helper was wired into five generated output paths after the previous native build.
- Exact question: can pinned Collabora/LibreOffice plus current AquaWord overlay pass the full native Android/NDK integration, Gradle manifest/resource processing, ARM64 APK packaging, integrity checks, and short-lived artifact upload?
- Why source tests are insufficient: the JVM helper tests and overlay contracts do not execute the full native linker/build, Gradle packaging or verify the final APK ABI/manifest.
- Run [#40613885226](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40613885226) is **IN PROGRESS** at checked-out source SHA `df65aa2d92881f34160eadbbfcc0a96dd5f859ab`; no final build result, APK SHA-256, or downloadable artifact is confirmed yet.
- Preflight source CI at code/test head `0160bed77339e2ef05fa4948e3adff3e1deb310f`: Fast Source [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163452), Recovery Core [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163437), Integration [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40601163615). The native workflow reruns its own preflight at the authorized SHA.
- This diagnostic is compile/package/artifact-integrity only. Install/launch, real SAF failure/recovery, Arabic/English Writer roundtrip, print/PDF runtime and Xiaomi Pad 5 visual/performance remain **NOT TESTED**.
- No automatic retry is authorized after this run's outcome is known. PR #7 remains Draft/open; no merge or `main` changes.
- Google Drive `AquaWord — HANDOFF` sync: **FAILED / NOT AVAILABLE** because this runtime exposes no Google Docs/Drive write connector; no sync success is claimed.


## 2026-10-28 — ARM64 native diagnostic outcome (M-NATIVE-01 remains OPEN)

- **PASS:** native Collabora/LibreOffice ARM64 engine build, Android source integration, Gradle APK packaging, package-ID check, APK ZIP integrity, and Android v2 debug-signature verification on [run #40613885226](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40613885226), source/authorization SHA `df65aa2d92881f34160eadbbfcc0a96dd5f859ab`.
- **Diagnostic artifact only:** [artifact #12785090689](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40613885226/artifacts/12785090689); APK SHA-256 `6ccbc0011c46056bf1fea1b7df8305f3da644ec780f050a6f2099b958e2a3ccc`; ARM64 native library SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`; artifact ZIP SHA-256 `1520e5bf3bffd6d0af55ddbe2ecbc9d6ca88f575af7167cd138c3051c3bd7937`. Artifact retention is short-lived (approximately until 2026-10-29 01:24 UTC).
- **NOT TESTED:** emulator installation/launch was skipped by the diagnostic workflow; no real Android device test, SAF provider failure/fallback, Arabic/English DOCX save-close-reopen, process-death recovery, print/PDF runtime, or Xiaomi Pad 5 acceptance is claimed.
- **Decision:** no automatic retry and no final-release claim. The compile/package question is answered; next useful evidence is installation and real Writer/SAF roundtrip, not another identical build.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE; no Docs/Drive write connector is exposed in this runtime, so no successful sync is claimed.


## 2026-10-28 — اختبار مباشر لعقد SAF output mode (M-NATIVE-01 ما زال مفتوحًا)

- **Commit الاختبار:** [`463c41a0c2b3653a3887d8da51f0bd2ba12a76d2`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/463c41a0c2b3653a3887d8da51f0bd2ba12a76d2).
- أضفت تغطية JVM مباشرة لـ `AquaWordSafOutput.openTruncating()` بدل الاعتماد على فحص المصدر وحده. الحالات تشمل رفض `wt` بواسطة `FileNotFoundException` و`UnsupportedOperationException` و`IllegalArgumentException`، وإرجاع `null`، وفشل `rwt`، وعدم إخفاء أخطاء I/O العادية أو `SecurityException`، ورفض المزود المفقود.
- **CI على SHA الاختبار:** Recovery Core [#40625846290 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40625846290)، Fast Source + SAF Contract [#40625846297 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40625846297)، Integration [#40625846287 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40625846287). أظهر سجل JVM `PASS: SAF output mode fallback and failure propagation`.
- تضمنت Integration تشغيل 133 اختبارًا في مجموعة overlay، وفحص توافق DOCX/PDF باستخدام **LibreOffice المكتبي** وقالبين عربي/إنجليزي، والتحقق من تطبيق التعديلات على مصدر Collabora المثبّت. هذا ليس اختبار Writer داخل Android ولا قبول جهاز فعلي.
- **قرار البناء:** لم يُنشأ APK جديد؛ السؤال كان صحة عقد التفاوض البرمجي، وقد اختبره JVM مباشرة. إعادة بناء المحرك لا تضيف دليلًا أقوى لهذا التغيير الاختباري.
- **PASS:** اختبار SAF mode negotiation على JVM، Recovery Core، Fast Source، Integration على المصدر المثبّت.
- **NOT TESTED:** مزود SAF حقيقي يرفض `wt` ويقبل `rwt`، تثبيت وتشغيل APK على Android، تحرير/حفظ/إغلاق/إعادة فتح DOCX عربي/إنجليزي داخل Writer على الجهاز، موت العملية والاستعادة على الجهاز، الطباعة/PDF من التطبيق، والقبول البصري/الأداء على Xiaomi Pad 5.
- **Handoff Drive:** مزامنة `AquaWord — HANDOFF` = **FAILED / NOT AVAILABLE**؛ لا يوجد موصل كتابة Google Docs/Drive في بيئة هذه الجولة، ولم يتم تحديث المستند المحدد. لا ندّعي نجاح المزامنة.
- `M-NATIVE-01` يبقى **OPEN**، وPR #7 يبقى Draft مفتوحًا وغير مدمج؛ لا تغيير على `main`.
