# AquaWord autonomous acceptance ledger

AUTOMATION_COMPLETE: BLOCKED

## Baseline and scope (2026-10-23)
- Repository: `amroalhamedi2022-hue/aquaword-android`; approved integration base: `main` at `837ade110843f293f21fc7807e6e32d68483c9da`.
- Development branch: `fix/saf-save-failure-recovery-20261023`.
- Android-only, ARM64 native Collabora/LibreOffice, Xiaomi Pad 5 priority; **no desktop app and no substitute WebView editor**.
- Pinned upstream: `2333344185931274f9c49d6c12a408cefcef6844`; reuse the existing native save and history infrastructure.
- No extra paid API or paid CI was used.

## This iteration — actual production fix
- **FIX PROPOSED / TEST PENDING:** Native Writer SAVE now opens and schedules a post-edit recovery snapshot *before* copying the temp document back to the Android SAF provider. Previously it only captured a saved revision after provider writeback succeeded. A provider that rejects or partially writes the stream could therefore leave the user with no post-edit recovery version. A zero-byte native temp file is not recorded as a saved revision.
- Production source: `scripts/apply_to_collabora.py`; generated target: `android/lib/src/main/java/org/libreoffice/androidlib/LOActivity.java` at the pinned upstream commit.
- Test source: `tests/test_overlay.py::AquaWordIntegrationTests::test_failed_saf_writeback_keeps_native_post_edit_recovery`. Asserts exact callback ordering, idempotent overlay, no false SAVE broadcast on provider failure, and zero-length guard. **This is a source contract, not proof of actual Android provider failure handling.**
- Latest production change commit: `935b21851f05bb57fdf558bb9f273e2c6ce1c87f`; test commit: `c7e146c37c0d37d457d7fd696a1878063eb152ce`.
- Relevant prior native CI: `39916261052` failed on duplicate Stylelint selector after ARM64 engine compilation. That source blocker was fixed on main and source/integration CI passed for `919d777ce30bdeec788687e42d2590b36e2876c0`: [fast source](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929096055), [integration](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929096270).
- Current native builds at inspection: [run 39926074349](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39926074349) in progress (older `bfac03b`), [run 39929109992](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39929109992) pending (older `919d777`). **Neither tests this PR's source.** Do not start another expensive native build for this small patch.

## Acceptance matrix (evidence, not promises)
| Requirement | State | Evidence / limitation |
| --- | --- | --- |
| Native Writer source overlay and real DOCX blank asset | PASS — source contract only | Prior fast-source and integration tests on `919d777`; runtime not proven. |
| Post-edit recovery when SAF saveback fails | NOT TESTED on Android | Code and new source contract in this PR; provider failure needs an instrumented runtime test. |
| Source contract and integration tests for this exact PR SHA | NOT TESTED | Await PR CI; check exact SHA and logs before changing this row. |
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
Review PR fast-source/integration results and fix any regression. When existing native build capacity is available, validate this patch on Android with a mock SAF provider that rejects or truncates writes and ensure a post-edit recovery version remains accessible. Do not claim this test already ran.
