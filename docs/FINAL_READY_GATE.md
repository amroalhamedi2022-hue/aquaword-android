# AquaWord — Final-Ready gate (source-only)

Status: **BLOCKED**. Do not create an approval file or run native packaging while any acceptance requirement is incomplete.

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

After source approval: authorize **one** final native APK build; verify package identity, signing, name and SHA-256; then test on actual compatible Android, ideally Xiaomi Pad 5, including launch, editing, save/reopen, SAF failure, PDF export, printing, negative cases and CPU/RAM. Any failed Android gate blocks delivery and requires corrective source review. Never label a source test as device-certified. No paid API, no automatic merge, and no change to other projects.
