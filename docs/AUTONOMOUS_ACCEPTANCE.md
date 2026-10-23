# AquaWord autonomous acceptance ledger

AUTOMATION_COMPLETE: BLOCKED

## Baseline and scope (2026-10-23)
- Repository: `amroalhamedi2022-hue/aquaword-android`; approved integration base: `main` at `837ade110843f293f21fc7807e6e32d68483c9da`.
- Development branch: `fix/saf-save-failure-recovery-20261023`.
- Android-only, ARM64 native Collabora/LibreOffice, Xiaomi Pad 5 priority; **no desktop app and no substitute WebView editor**.
- Pinned upstream: `2333344185931274f9c49d6c12a408cefcef6844`; reuse the existing native save and history infrastructure.
- No extra paid API or paid CI was used.

## This iteration — actual production fix
- **FIX PROPOSED / SOURCE TEST PASS:** Native Writer SAVE now opens and schedules a post-edit recovery snapshot *before* copying the temp document back to the Android SAF provider. Previously it only captured a saved revision after provider writeback succeeded. A provider that rejects or partially writes the stream could therefore leave the user with no post-edit recovery version. A zero-byte native temp file is not recorded as a saved revision.
- Production source: `scripts/apply_to_collabora.py`; generated target: `android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java` at the pinned upstream commit.
- Test source: `tests/test_overlay.py::AquaWordIntegrationTests::test_failed_saf_writeback_keeps_native_post_edit_recovery`. Asserts exact callback ordering, idempotent overlay, no false SAVE broadcast on provider failure, and zero-length guard. **This is a source contract, not proof of actual Android provider failure handling.**
- Latest production change commit: `935b21851f05bb57fdf558bb9f273e2c6ce1c87f`; test commit: `c7e146c37c0d37d457d7fd696a1878063eb152ce`.
- **PR #7 source CI PASS at `bb52b148409a24a634f7d415aebf7374d13ef45a`:** [Fast Source and SAF Contract run 39945100480](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39945100480), [Integration Tests run 39945100693](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39945100693). Both completed successfully on 2026-10-23. These prove overlay/contract checks, not Android-device acceptance.
- Relevant prior native CI: `39916261052` failed on duplicate Stylelint selector after ARM64 engine compilation. That source blocker was fixed on main and source/integration CI passed for `919d777ce30bdeec788687e42d2590b36e2876c0`: [fast source](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929096055), [integration](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929096270).
- Current native builds at inspection: [run 39926074349](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39926074349) in progress (older `bfac03b`), [run 39929109992](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929109992) pending (older `919d777`). **Neither tests this PR's source.** Do not start another expensive native build for this small patch.

## Acceptance matrix (evidence, not promises)
| Requirement | State | Evidence / limitation |
| --- | --- | --- |
| Native Writer source overlay and real DOCX blank asset | PASS — source contract only | Prior fast-source and integration tests on `919d777`; runtime not proven. |
| Post-edit recovery when SAF saveback fails | NOT TESTED on Android | Code and new source contract in this PR; provider failure needs an instrumented runtime test. |
| Source contract and integration tests for tested PR code SHA `bb52b148` | PASS — CI only | Both GitHub Actions runs 39945100480 and 39945100693 succeeded; Android runtime still untested. |
| Native ARM64 APK compile, package ID, launch | NOT TESTED on this SHA | Native builds for older SHAs queued/running; no current-device proof. |
| New Document UI and full Arabic/English DOCX roundtrip | NOT TESTED on Android | Requires install/open/edit/save/close/reopen and rich fixtures. |
| SAF read-only/cloud/failed-stream, restore, process death | NOT TESTED on Android | Source tests exist; no device/provider proof. |
| Home/Insert/Layout/References/Review/View, PDF export and printing | NOT TESTED end-to-end | No validated full UI workflow. |
| Visual parity Liquid Aurora, tablet landscape/phone portrait | NOT TESTED on target device | Requires actual screenshots and interactive inspection. |
| Memory/CPU, performance, security and license notices | NOT TESTED end-to-end | Requires measured Android run and release audit. |
| User-facing single final APK | BLOCKED | Must pass all required device and content roundtrip gates first. |

## Required second-pass recheck
After all gates are supported by current-SHA evidence, independently rebuild/review, run Android ARM64 editor on a compatible device, exercise positive and negative SAF flows, roundtrip Arabic/English complex DOCX, PDF/print, focus mode, history restore and process death, compare reference UI, and verify privacy/security/CPU/RAM. Do **not** change `AUTOMATION_COMPLETE` to VERIFIED until then.

## Next bounded action
The fast-source and integration contracts passed for the tested code SHA. Review any further PR CI runs after documentation-only updates. When existing native build capacity is available, validate this patch on Android with a mock SAF provider that rejects or truncates writes and ensure a post-edit recovery version remains accessible. Do not claim this test already ran.

## Native Gradle manifest-merger blocker — 2026-10-23, subsequent development round
- **CONFIRMED FAIL on older main SHA `919d777ce30bdeec788687e42d2590b36e2876c0`:** [native run 39929109992](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929109992) compiled through native Collabora but failed at `:app:processDebugMainManifest` before APK packaging. The debug QA `androidx.core.content.FileProvider` declaration collided with the pinned upstream production provider (different `android:authorities` and `android.support.FILE_PROVIDER_PATHS` values).
- **PROPOSED SOURCE FIX (this PR; NOT YET CI-VERIFIED):** give the debug-only QA provider a separate subclass `org.libreoffice.androidapp.qa.QaFixtureFileProvider`, preserving the upstream provider and its path XML. The overlay now installs the new Java source into `src/debug`; contract tests parse the manifest, verify both provider identity isolation and QA-only placement, and run the overlay twice for idempotence. Do not use `tools:replace` because overriding the production provider could break document sharing.
- AndroidX official FileProvider guidance explicitly supports extending `FileProvider` with a default constructor and declaring that class in the manifest: https://developer.android.com/reference/androidx/core/content/FileProvider . No extra dependencies, paid services, or workflow changes were introduced.
- **NOT TESTED:** manifest merger on this PR SHA, Gradle debug APK, runtime FileProvider access, editor startup, SAF failed-stream recovery, device behavior. Source CI must be checked after this commit; an older successful source run is not proof for the new patch.
- **Next:** validate fast source + integration on the updated PR; when native CI capacity is available, run exactly one native build for the approved commit and inspect `:app:processDebugMainManifest` before declaring the blocker fixed. Do not publish APK before actual Android editing/roundtrip acceptance.

### Verified source CI for manifest fix (2026-10-23)
- **PASS — source+tests commit `d0707b8a1a4c4686e57058b03bdcb05325b0c589`:** [Fast Source and SAF Contract run 39951773086](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39951773086) completed successfully.
- **PASS — same source+tests commit:** [Integration Tests run 39951773121](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39951773121) completed successfully, including the new debug QA provider contract.
- **NOT TESTED:** native Gradle manifest merger or native ARM64 APK on this source SHA. This documentation-only commit does not alter production/test source, so the above runs are the evidence for the actual code change. Native CI is manual and was deliberately not restarted here.
- **Next action:** one native Android build on the updated PR when free runner capacity permits; verify `:app:processDebugMainManifest` and `:app:assembleDebug`, then actual editor runtime and SAF roundtrip. Completion remains BLOCKED.
