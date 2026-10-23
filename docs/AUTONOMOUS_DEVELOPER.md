# Autonomous Developer Contract — AquaWord Android
Project repo: amroalhamedi2022-hue/aquaword-android
Authoritative working base: `main`

## Approved outcome
Continue native Android ARM64 Collabora/LibreOffice Writer, not a WebView substitute. Read docs/PROJECT_CHECKPOINT_2026-10-23_AR.md, docs/ACCEPTANCE.md and CI evidence. Avoid duplicate costly native build queues. Required: real blank DOCX, Arabic/English editing, formatting, save/reopen/export, SAF and recovery, authentic Word-Android-style controls and Liquid Aurora. Test real native APK and Android editor before final acceptance; Xiaomi Pad 5 first. Android only, no Windows desktop.

## Mandatory development loop
1. On each authorized run, inspect actual files, authoritative handoff, current branch, last PR and CI results. Never restart the project or invent progress. Do not treat READMEs as more recent than verified commits.
2. Identify the highest-priority **unmet requirement** from established user instructions and the repository's own plan. First inspect reputable maintained open-source solutions and their compatibility, license, security and actual implementation rather than rewrite blindly.
3. Make a bounded, useful production-code + test change in **this repository only**. Avoid cosmetic-only revisions, fake implementations and meaningless tests. Do not edit GitHub Actions or credentials/autonomous runner permissions, do not publish releases or change repo visibility.
4. Execute available relevant unit/integration/static/compile tests within this runner. If platform SDK/Windows/real-device verification is impossible, record it explicitly as NOT TESTED. Never describe old CI results as testing the current SHA.
5. Maintain `docs/AUTONOMOUS_ACCEPTANCE.md` recording each user's requirement as PASS / FAIL / NOT TESTED / BLOCKED with exact test command, SHA, CI URL where available, remaining tasks, and the next bounded development action. Preserve prior historical evidence. Always record whether this run actually changed production source.
6. Once you suspect ALL requirements are met, change `AUTOMATION_COMPLETE: CANDIDATE` in that status file. Do **not** write VERIFIED yourself. A separate second-pass agent invocation will recheck from scratch.
7. Never certify finished if target-device/app startup, real UI, user workflow, reliability, data safety, relevant security and resource acceptance have not been actually demonstrated. Do not make up missing test results.
8. Do not modify another project's repo, auto-merge, force-push, make public releases, send private assets to public repos, or ask the user to perform routine coding. In real approval/security/access/device blockers, document the exact minimum required action.

## Double-check gate
For CANDIDATE, independent recheck must separately inspect: exact user requirements vs actual code/tests, real build output, test log links, negative/error handling, end-to-end functional workflows, visual parity when reference available, credentials/privacy, regressions, and the actual platform/device. Only if every mandatory requirement has direct proof may a second pass write `AUTOMATION_COMPLETE: VERIFIED`; otherwise it must write `AUTOMATION_COMPLETE: BLOCKED` and specific failures. When VERIFIED, refrain from further feature changes and report the evidence; final public releases require user approval.

## Cost and action boundaries
This workflow is opt-in using GitHub repository variable `AUTONOMOUS_DEV_ENABLED=true` and an OpenAI API `OPENAI_API_KEY` GitHub Actions secret. Without both it is disabled. Each run may incur separate API/GitHub Actions charges. Observe rate/spend caps and keep PRs reviewable.
