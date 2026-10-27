# AquaWord — Final-Ready gate (source-only)

Status: **BLOCKED**. Do not create an approval file or run native packaging while any acceptance requirement is incomplete.


## Diagnostic build policy — 24 October 2026

A purposeful internal build is allowed before final acceptance when source tests cannot answer a specific integration question (for example, ARM64 Collabora compile, SAF runtime persistence, or real-device PDF export). Record the question, source SHA, runner cost, outcome and NOT TESTED device gates before requesting it. Do not repeat builds without relevant changes. Diagnostic artifacts are **UNVERIFIED** and must never be presented as final releases.

**Branch-local implementation:** `android-native.yml` supports `diagnostic_build=true` with a nonblank `diagnostic_reason`; optional `diagnostic_compile_only=true` verifies ARM64 APK packaging and SHA-256 without falsely requiring an x86_64 emulator to advertise ARM64. That mode retains an **UNVERIFIED** unpublished QA draft only. Final-Ready remains mandatory for final release; `queue-current-native-once.yml` remains Final-Ready-only. This feature branch is NOT merged into main. GitHub manual dispatch may depend on the default-branch workflow registration. Ordinary pushes do not package. The only exception is the exact marker-path plus exact commit-message one-shot diagnostic on this feature branch; it is compile-only and cannot satisfy Final-Ready.

## Why this gate exists

A previous `.github/workflows/queue-current-native-once.yml` automatically dispatched an APK-building workflow after a push modifying that queue file on `main`. The development-branch version is now manual-only. `android-native.yml` also requires an explicit manual boolean `final_ready=true`. Both require `scripts/check_final_ready.sh` to pass before any build/dispatch step. **These protections do not affect `main` until reviewed and merged by an authorized maintainer; this PR must remain Draft and is not auto-merged.**

## Source acceptance before approval

Independently verify **all** requirements in `docs/ACCEPTANCE.md`, including actual native feature wiring, Arabic/English DOCX, tables, images, templates, SAF, recovery, PDF export, printing, accessibility, Liquid Aurora, security, and licensing. Run source/unit/static/integration tests and a separate independent Source Recheck. Document gaps as NOT TESTED rather than PASS.

Only after these source gates are complete may a reviewer add `docs/FINAL_READY_APPROVAL.txt` with **exactly one** each of:

```text
FINAL_READY=YES
REQUIREMENTS_COMPLETE=YES
SOURCE_RECHECK=PASS
ACCEPTANCE_REVIEW=PASS
SOURCE_DIGEST_SHA256=<64 lowercase hex digits>
```

To compute the digest from the **final tracked source tree**, after staging all reviewed changes except the approval itself, from the repository root:

```bash
git ls-files -z -- . ':(exclude)docs/FINAL_READY_APPROVAL.txt' |
  xargs -0 -r sha256sum | sha256sum | cut -d' ' -f1
```

The gate compares that digest to the approval. Any subsequent tracked file change invalidates it. The approval file is **not created during development**. This is an intentional human/independent-review authorization; passing this script does not prove Android runtime functionality or replace the post-build Android acceptance matrix.

## Final sequence

For a **diagnostic compile-only** run, first record the exact question (e.g. whether the pinned Collabora ARM64 engine and Gradle compile together); review current CI and avoid a duplicate costly run. Use manual `diagnostic_build=true`, `diagnostic_compile_only=true`, and a nonblank reason. Verify source SHA, package ID, assets, checksum, and the unpublished `qa-unverified-<sha>` draft. Android runtime remains NOT TESTED; a diagnostic build is never final approval.\n\nAfter source approval: authorize **one** final native APK build; verify package identity, signing, name and SHA-256; then test on actual compatible Android, ideally Xiaomi Pad 5, including launch, editing, save/reopen, SAF failure, PDF export, printing, negative cases and CPU/RAM. Any failed Android gate blocks delivery and requires corrective source review. Never label a source test as device-certified. No paid API, no automatic merge, and no change to other projects.
