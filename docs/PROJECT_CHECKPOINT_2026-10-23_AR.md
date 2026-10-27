# AquaWord Android — نقطة متابعة موثقة 23 أكتوبر 2026

## قرارات ثابتة
- Android فقط، Xiaomi Pad 5 أولاً، دون تطبيق Windows.
- Collabora/LibreOffice Native Writer هو المحرك. WebView الصغير القديم ليس بديلاً.
- تنظيم قريب من Word Android مع هوية AquaWord وLiquid Aurora وصفحة تحرير واضحة.
- تطوير واختبارات داخلية عبر GitHub؛ المستخدم يستلم APK واحداً بعد قبول فعلي، وليس نسخاً تجريبية متكررة.

## المنجز على main (تحقق المصدر 23 أكتوبر)
- أحدث دمج لهذه الدفعة: `d002cb8df0eb5ed581ff8863b30b059d29b4f6b3` عبر PR #1.
- تنسيق DOCX الافتراضي؛ ربط إنشاء الملف الأصلي بمصدر `assets/aquaword/blank.docx` فارغ صالح للفتح، بدلاً من الاعتماد حصراً على `templates/untitled.docx` في المصدر المجمّع.
- أربعة قوالب تحريرية منفصلة (بحث عربي/إنجليزي، تقرير حالة، ملخصات)، واختبار أصل فارغ خامس، مع حفظ جداول واتجاه عربي في fixtures واختبارات LibreOffice Desktop.
- حراسة SAF، نسخ استرداد محلية قبل التحرير وبعد SAVE الناجح، حفظ دوري (120 ثانية)، وضع تركيز، وثوابت هوية التطبيق.
- اختبار تشغيلي يرفض المحاكي غير الداعم لـ ARM64 صراحة ويذكر ABIs المقاسة بدلاً من افتراض دعم الترجمة.

## دليل الاختبارات
- PR #1 تكامل ناجح: https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/39920807790
- اختبارات LibreOffice Desktop داخل Run لا تعني إثبات نجاح Android Native Editor.
- مصدر Collabora المثبت: `2333344185931274f9c49d6c12a408cefcef6844`، NDK `29.0.14206865`، ARM64.

## البناء الأصلي المعلّق — حالة وقت تحرير الملف
- Run #39916261052 قد وصل فعلاً إلى `Build LibreOffice native engine for Android arm64` وكان قيد التنفيذ؛ مصدره أقدم (`b0ce361`)، لذلك حتى نجاحه لا يثبت إضافات PR #1.
- Run #39918121361 كان Pending على Commit أقدم (`2883ae2`)، فلا تستخدمه دليلاً نهائياً لنسخة main الحالية.
- التشغيل الأصلي Manual، والتزاحم native محمي بـ `cancel-in-progress: false`. **لا تبدأ عدة نسخ native جديدة لنفس الإصلاح** قبل قراءة نتائج السابقة.
- سابقاً: #39699767102 فشل بسبب Python lxml بعد نجاح بناء المحرك؛ #39768833806 فشل ESLint في Collabora browser. توجد اختبارات preflight حالية لفحص هذين الشرطين، لكن يبقى إثبات تجميع APK والجهاز ضرورياً.

## بوابات إلزامية لم تنجح بعد بالدليل
1. Native Collabora + Gradle يجمع APK لهوية `com.aquaword.app`.
2. تثبيت وفتح على Android emulator فعلي يدعم ABI الحزمة، ثم جهاز Pad 5 قدر الإمكان.
3. تحرير عربي/إنجليزي داخل Writer، حفظ DOCX، إغلاق التطبيق، إعادة فتح، مقارنة محتوى وجداول وصور واتجاه فقرة.
4. اختبار إنشاء مستند فارغ من زر New Document (وليس مجرد وجود `blank.docx`).
5. اختبار الحفظ مع SAF read-only/cloud provider/failed-stream ونسخ الاسترداد عند إنهاء العملية، ووضع التركيز.
6. مراجعة Home / Insert / Layout / References / Review / View والأدوات الحقيقية، التصدير PDF والطباعة، ومعايير الأداء والأمن قبل إصدار واحد.

## طريقة المتابعة دون إعادة عمل
- افتح Actions واعتمد **آخر نتيجة مؤكدة** لا وصفاً قديماً.
- أصلح أول خطأ فعلي في Collabora configure / make / Gradle / runtime من الـlog فقط؛ لا تعيد كتابة المحرك.
- عند نجاح CI لهذا الإصدار، راجع معايير القبول في `docs/ACCEPTANCE.md`، ولا تعلن اكتمال ميزة لا يثبتها الاختبار.
- لا ترفع APK نهائياً ولا تنشر Release public قبل إثبات الاختبارات على الجهاز.

## استكمال مثبت لاحق يوم 23 أكتوبر 2026
- PR #2 دُمج إلى main: صلاحية READ-only في SAF لا تُعرض للمحرر باعتبارها WRITE. اختبارات المصدر ناجحة.
- PR #3 دُمج على Commit `4e095695545071f01a5c271aacf6f1bce659e77d`: حفظ اختيار القالب/نسخة الاسترداد عبر Activity recreation، واستخدام grant دائم قدر المستطاع، والتحقق من اكتمال محتوى القالب قبل فتحه. Fast Source وFull Integration نجحا.
- PR #5 دُمج على Commit `2658ce2aa6ff0b1c5e4d8ce1b5b6caf78d9cd51b`: الاحتفاظ بمسودة GitHub داخلية غير منشورة لـAPK اجتاز سلامة الحزمة والـSHA لكنه لم يجتز تشغيل Android. **ليس إصدارًا نهائيًا**.
- PR #4 ينظم طابور Native CI بطريقة لا تلغي build فعلي قيد التجميع، ويلغي فقط الطلبات القديمة المنتظرة ويطلب أحدث commit إذا لم يكن موجودًا. يجب دمجه بعد تحديثات الكود.
- حالة Native #39916261052 وقت توثيق النقطة: كان قيد تجميع ARM64. الأحدث لم يثبت نجاحه على محاكي/جهاز بعد.

## Native Stylelint failure (23 October 2026)
- Native Run `39916261052` completed the LibreOffice ARM64 engine but failed later at `css/notebookbar.css 1199:1`: duplicate selector `#toolbar-wrapper.hasnotebookbar`, first at line 304, during `dist/bundle.css`.
- Fix: unique selector `body #toolbar-wrapper.hasnotebookbar` in the AquaWord skin, preserving the intended styling and avoiding upstream selector duplication.
- Added pinned Stylelint `13.7.0`, with real upstream `browser/.stylelintrc.json` rules, to native preflight, fast-source tests, and integration tests *before* any long ARM64 engine compile.
- This source fix is NOT proof of a finished APK; native build and on-device opening/edit/save/reopen remain release gates.

## Active milestone M-NATIVE-01 — ARM64 compile and real Writer roundtrip (24 October 2026)

**Goal:** independently demonstrate the pinned Collabora/LibreOffice ARM64 engine builds AquaWord, then verify real DOCX open/edit/save/cold-reopen and SAF behavior. Keep this milestone active until its acceptance criteria pass; do not mark UI parity or PDF/print as completed by source-only checks.

**Acceptance:** (1) source and integration CI PASS at exact SHA; (2) a purpose-bound internal diagnostic build with native engine + Gradle + package/asset SHA256 checks and actual `lib/arm64-v8a/*.so` presence PASS; (3) compatible Android runtime installs, opens Arabic/English Writer DOCX, edits and reopens without loss, and exercises SAF failure paths; (4) Android device/emulator evidence with precise ABI and reproducible logs; (5) independent final source review before user-facing APK. Each unrun gate is NOT TESTED.

**Implementation slice:** the branch-local manual `android-native.yml` now separates diagnostic compile-only from runtime acceptance. Compile-only intentionally skips the x86_64 emulator when its ABI cannot prove ARM64, retains only an unpublished UNVERIFIED draft, and never satisfies the final approval digest gate. Native compile and real Android runtime are still NOT TESTED. `main` is unchanged. No automatic builds, no paid runners.

**Next:** validate the new workflow via source CI; inspect the pinned native toolchain for actual compiler failures; launch one justified diagnostic build only through an available authorized manual dispatch path, then repair real failures and run Android device roundtrip. A successful compile-only diagnostic is not evidence of SAF or Writer runtime.

## M-NATIVE-01 — 25 October 2026: interrupted recovery-write hygiene

- **Production:** `history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java` now reclaims incomplete `.partial` / `.meta-partial` files and metadata-only orphans older than seven days when the app-private history directory is opened. A missing/unreadable timestamp does **not** authorize deletion. Orphan `.snapshot` document bytes are deliberately preserved for manual salvage, even without metadata. This is a bounded cleanup, **not** a replacement for crash-safe Android Writer/SAF acceptance.
- **Regression:** `history/test/org/libreoffice/androidapp/ui/AquaWordHistoryTest.java` simulates process-kill leftovers and asserts cleanup of stale incomplete files, preservation of fresh in-flight data, preservation of an orphan document payload, and no loss of committed history.
- **Exact code/test SHA:** `e91244a9ae8272590914a4fbf405f09d587eca93` on draft PR #7 (`fix/saf-save-failure-recovery-20261023`); `main` untouched. **PASS — Fast Source [run 40160948352](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40160948352) and Integration [run 40160948344](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40160948344), both completed successfully on the exact code/test SHA.** JVM/desktop checks only; no native Android runtime proof.
- **Build decision:** no native APK build for this file-cleanup slice: the direct JVM integration regression can answer the cleanup question without hours of ARM64 compilation. Native Collabora compile/Gradle package and Android SAF device behavior still require a separately justified diagnostic build and remain **NOT TESTED**.
- **Milestone gates remain open:** (1) current-SHA source/integration PASS; (2) native ARM64 APK compile/package/ABI verification; (3) Android Writer Arabic/English DOCX edit-save-reopen and SAF failure/recovery; (4) device evidence on a compatible ABI and Xiaomi Pad 5 when available; (5) independent final recheck. No final APK/release claim.
- **Next:** inspect CI for this exact SHA; repair any failure. Then obtain one purpose-bound native diagnostic build via an authorized workflow dispatch path and address actual compile/runtime errors. Continue M-NATIVE-01 rather than opening another milestone. Policy 2026-10-24 allows a justified internal APK/EXE build before completion; it does not require one per code change.

## M-NATIVE-01 — 25 October 2026: retention-safe SAF writeback lease

- Production: native SAVE now holds a reference-counted AutoCloseable WritebackLease for the validated recovery checkpoint throughout provider writeback and readback. History retention skips leased snapshots, preserves the newest checkpoint, and reapplies the count/size cap after lease release. The class monitor is not held during provider I/O. This addresses possible eviction by a concurrent pre-edit capture while the SAVE worker streams to SAF.
- Regression: JVM tests cover two overlapping leases, idempotent close, 65 additional captures under retention pressure, byte preservation and post-release trimming, and rejection of a corrupt checkpoint. Overlay test checks native SAVE lease scope.
- Verification at commit creation: source CI PENDING; JVM integration PENDING; Collabora ARM64/Gradle APK NOT TESTED; Android Writer/SAF on Xiaomi Pad 5 NOT TESTED. No user-facing APK.
- Next: inspect exact-SHA CI, repair any failures, then pursue one justified manual ARM64 diagnostic build and real Android DOCX/SAF roundtrip. Keep PR #7 draft and main untouched.


## M-NATIVE-01 — 25 October 2026: nonblocking SAF recovery restore

- **Production:** `f8ee1989ef88a9e6ac9b3531e5f1e31466392017` changes `AquaWordHistory.restore()` to acquire an integrity-checked, reference-counted `WritebackLease` under the history monitor, then stream to a possibly slow SAF/cloud destination **outside** that monitor. The lease prevents retention from deleting the source until the write finishes. Destination ownership remains with the caller; no new dependency.
- **Regression:** `11f26eca87c279725e1e50bfd2fb985e46be9bd2` adds a deterministic JVM test with a blocked provider stream and a concurrent history-list operation. `ded063a8b0f1462534b22ef5fdab897ac0c941b1` updates the old source-contract assertion to require lease-based preflight rather than a globally synchronized restore. Initial Fast Source CI failed because the old assertion required `synchronized`; it was fixed, not ignored.
- **CI:** Fast Source on `ded063a8` **PASS**: https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40175969310 . Integration on the same SHA: https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40175969323 (**PENDING at checkpoint update**). Only declare JVM concurrency test PASS if Integration completes successfully.
- **NOT TESTED:** native ARM64 Collabora/Gradle APK, Writer Android runtime, actual slow/failing SAF providers, Xiaomi Pad 5, full DOCX roundtrip, PDF/print. No APK was built, no PR merged, main untouched.
- **Next:** inspect exact-SHA Integration result; fix any failing JVM regression. Continue M-NATIVE-01 with a purpose-bound native ARM64 diagnostic build when supported, then real Android SAF/DOCX testing. Do not mark this milestone complete from source CI alone.

## M-NATIVE-01 — 25 October 2026: nonblocking SAF input capture (verified source/JVM)

- **Production:** `f4fcd1643f1060ea10258795ec010efc6c8d287d` moves slow pre-edit / post-save input streaming out of the global `AquaWordHistory` monitor; metadata publication, deduplication, and retention trimming remain serialized. A concurrent first-open directory creation race is handled by rechecking the directory after `mkdirs()`. No new dependencies or third-party code.
- **Regression:** deterministic Java test blocks a simulated cloud InputStream while another thread calls `list()`; verifies unrelated history remains responsive and that the delayed copy commits intact. Python overlay contract now verifies the streaming/commit lock boundary instead of assuming a synchronized capture method.
- **Initial FAIL and repair:** source and integration runs `40184067185` / `40184067166` failed because `tests/test_overlay.py` still searched for the removed `synchronized Snapshot capture` declaration. Updated the contract to test the new correct behavior, not to skip the assertion.
- **PASS on exact code/test SHA `f4fcd1643f1060ea10258795ec010efc6c8d287d`:** Fast Source https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40184159141 ; Integration https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40184159103 . JVM test is simulated-provider concurrency only; desktop LibreOffice checks are not Android Writer proof.
- **NOT TESTED:** pinned Collabora ARM64/Gradle APK at this SHA; installation/runtime on compatible Android or Xiaomi Pad 5; native Writer DOCX Arabic/English edit-save-cold-reopen; real SAF cloud/read-only/failure recovery; print/PDF and full toolbar.
- **Build decision:** no APK build for this lock-contention change because Java concurrency and source integration tests directly answer the regression question. A separate native ARM64 diagnostic build is still justified for the *different* open question of actual Collabora compilation and Android runtime; current connector lacks a manual workflow-dispatch action, so do not claim it was started.
- **Milestone:** M-NATIVE-01 remains OPEN. Next: purpose-bound native ARM64 compile/package/ABI verification, then real Writer/SAF roundtrip and device evidence, independent recheck, and only then final user-facing APK. Keep PR #7 draft and `main` unchanged. PDF Studio is separate and untouched in this slice.


## M-NATIVE-01 — 25 October 2026: checksum preflight without global history contention

- **Acceptance slice:** During native SAF save, acquiring a verified recovery `WritebackLease` must not block history listing/capture for the duration of a potentially large SHA-256 disk read. The recovery artifact must remain pinned against retention while hashing; failed verification must release the lease.
- **Production:** `history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java` now registers the lease under the class monitor, then runs `verifyBytes` outside it, releasing on any failed verification. Existing pre-truncation `verifyForRestore` contract is unchanged. No third-party code or dependencies.
- **Regression:** `AquaWordHistoryTest.java` creates a deterministic delayed filesystem `File.isFile()` checksum fixture and verifies concurrent history listing completes before hashing resumes, the lease remains valid, and both threads finish without error. Existing saved/restore/retention/SAF simulated tests remain.
- **Code/test SHA:** `04ac86e2d86f3e786d219b44edef7805dad9f55b` (production `18668c4a733795da11db8cc147d40183bb768a42`). PR #7 draft, `main` untouched. Fast Source CI [#40188311087](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40188311087) **PASS**. Integration CI [#40188311114](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40188311114) **PASS (completed/success)** on the exact code/test SHA; JVM snapshot-core, desktop DOCX, integration and real pinned Collabora source-layout checks all completed successfully. This is source/JVM evidence, not native APK/runtime evidence.
- **Milestone remains OPEN:** Collabora ARM64 diagnostic APK compile/package, Android Writer Arabic/English edit/save/cold-reopen, real SAF cloud/provider failure paths, Xiaomi Pad 5 device tests, PDF/print and final recheck **NOT TESTED**. No APK build triggered: this exact lock-contention behavior is directly testable on JVM; a separately justified native ARM64 build remains needed for native runtime acceptance. Continue M-NATIVE-01; no merge/release.

## M-NATIVE-01 — 2026-10-25: validate bytes *during* recovery restore

- **Problem:** SHA-256 preflight in `holdForWriteback` validates the snapshot before opening a SAF destination, but a concurrent Writer/file rewrite can mutate the same inode *after* preflight and during a slow multi-block restore. A successful `target.flush()` previously gave the caller no indication that copied bytes differed from the checkpoint.
- **Production:** `AquaWordHistory.restore()` now hashes and counts the bytes actually streamed to the destination; it rejects a size or digest mismatch **before** the final flush. This avoids falsely acknowledging a corrupted restore. It does **not** roll back an already-truncated SAF destination, prevent concurrent writes, or guarantee provider durability; retain original/recovery bytes and verify provider readback at the caller.
- **Regression:** JVM test deterministically mutates a 128 KiB source in the second block during the first output write, separately truncates the source during streaming, and confirms a stable two-block restore is byte-identical. Code commit `0f3cae8ce699b31f691b4cd752a5bc283bd44327`; test commit `9c658406ee3e9a40e4cb5bb20ed3ba0723c53467`. Draft [PR #7](https://github.com/amroalhamedi2022-hue/aquaword-android/pull/7).
- **CI (at checkpoint update):** [Fast Source #40196877226](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40196877226) IN PROGRESS; [Integration #40196877180](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40196877180) PENDING. Neither is PASS until independently verified on the exact SHA. JVM/local source checks NOT TESTED outside CI.
- **M-NATIVE-01 acceptance remains OPEN:** exact-SHA source/integration CI PASS; one purpose-bound native ARM64/Gradle diagnostic compile/package and verified ABI; Android Writer Arabic/English DOCX edit-save-cold-reopen; SAF read-only/cloud/failure and restore with device evidence; print/PDF, tablet UI and independent release recheck. **Native APK and Xiaomi Pad 5 runtime NOT TESTED**. No native build this slice: JVM/CI can answer the streamed-hash regression, whereas real ARM64 build is needed separately to prove native compile/runtime. Policy since 2026-10-24 allows a justified diagnostic build; it does not require or prohibit builds categorically.
- **Next:** check and fix both CI runs; prioritize an authorized native ARM64 diagnostic compile/package and real Android Writer/SAF roundtrip instead of another source-only recovery microfix. Keep PR #7 draft and `main` unchanged.

## M-NATIVE-01 — 2026-10-25: purpose-bound ARM64 diagnostic build actually queued

- **Milestone and acceptance:** M-NATIVE-01 stays OPEN until (a) real pinned Collabora/LibreOffice ARM64 configure/compile, Gradle APK packaging, native .so, classes.dex, applicationId, embedded DOCX templates and SHA-256 are verified; (b) Android Writer Arabic/English DOCX edit/save/cold-reopen, SAF read-only/cloud/failure recovery and PDF/print are tested on a compatible Android device including Xiaomi Pad 5 where possible; (c) independent recheck. This run targets **(a) only**, not a user-facing release.
- **Why a build now:** Source/JVM and desktop LibreOffice tests cannot detect native C++/NDK/Gradle linking and APK ABI/manifest errors. The build is one diagnostic on free ubuntu-24.04 GitHub-hosted runners, not an automatic build every round. No paid service, private documents or secrets.
- **CI orchestration:** Feature-branch `.github/workflows/android-native.yml` now permits a narrowly gated push to `.github/native-diagnostic-once.request` with exact commit message `AquaWordNativeDiagnosticRetryOnce`, in addition to existing manually authorized `workflow_dispatch`. The one-shot path is compile/package/ABI-only; emulator verification is skipped, and any APK is marked **UNVERIFIED** in an unpublished QA draft, not released. Subsequent ordinary pushes cannot meet the exact message+path gate. `main` untouched, PR #7 still draft.
- **Failed attempt and repair:** First request SHA `b09ea0321d37bd3dc59532a339a8e38cdee45325` produced [native run 40206331263](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206331263) **SKIPPED** because the event's added-path job gate was false; **no native compilation was verified**. Initial source CI exposed outdated manual-only test assertions; they were updated to assert a narrowly gated diagnostic path. A later workflow edit with a colon-containing commit-message expression produced invalid YAML workflow runs; replaced it with YAML-safe token. These FAIL/SKIPPED results must not be represented as PASS.
- **Source check:** SHA `b00e869eadc1d69d5f0a49f25f14f7b84c1c11ef`: [Fast Source CI 40206578609](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206578609) **PASS**, including current workflow-gate tests and real pinned Collabora source overlay; [Integration CI 40206578603](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206578603) **IN PROGRESS** at checkpoint time. Do not infer integration PASS.
- **Native diagnostic:** exact source SHA `a14389c890ea6cbf12c406ef19edccb4e070bbbe`, [GitHub Actions native run 40206631720](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206631720) **IN PROGRESS** at checkpoint time. An actual runner job was observed; APK existence, ABI, SHA-256 and success remain **NOT TESTED** until logs and packaging evidence finish. A new checkpoint commit changes documentation only; it does not change the native source SHA under test.
- **Next:** inspect native run steps and logs; if native compile/configure fails, fix the actual root cause before any justified retry. Do not run another native build merely to obtain a fresh SHA. When/if compile passes, verify output manifest/ABI/SHA-256 and obtain real Android device DOCX/SAF evidence. Do not merge or publish a final APK prematurely.


## M-NATIVE-01 — 2026-10-25: diagnostic native build failure confirmed

- **Verified result:** [native CI #40206631720](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206631720) completed **FAIL** in the `Build AquaWord APK with Gradle` step. Ninja reports missing `collabora/engine/android/jniLibs/arm64-v8a/liblo-native-code.so`, required by the Android CMake target. No verified APK or SHA-256 was produced. This supersedes the earlier IN PROGRESS checkpoint.
- **Other verification:** [Integration #40206665191](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206665191) completed PASS for overlay contracts; it does not prove native packaging.
- **Root-cause status:** the missing shared library is confirmed; why the preceding LO/Collabora build steps did not generate/copy it into the expected path remains **NOT TESTED**. Do not claim a compiler fix from log inspection alone.
- **Next ordered gates:** (1) inspect `collabora/engine/android/jniLibs` production/copy targets and Collabora Android make rules at pinned upstream SHA; (2) add fail-fast validation immediately after Collabora native build, with actionable diagnostics listing expected .so paths and architecture; (3) repair native build generation/copy wiring based on source evidence; (4) only then run one purpose-bound free ARM64 retry; (5) verify APK native libs, manifest, SHA-256, then device Writer/SAF roundtrip. No new APK build, main change or merge in this status-check round.

## M-NATIVE-01 — 2026-10-25: repair incomplete engine cache / verify real ARM64 ELF

- **Confirmed cause from native run [40206631720](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40206631720):** cache restoration reported "Reusing compiled LO ARM64 engine", but Gradle/Ninja failed because `engine/android/jniLibs/arm64-v8a/liblo-native-code.so` did not exist. The v1 cache persisted `engine/workdir` and `engine/instdir` but omitted `engine/android/jniLibs`. At pinned upstream `2333344185931274f9c49d6c12a408cefcef6844`, `engine/android/CustomTarget_lo_android.mk` generates the missing library through `android/source/Makefile` / `Bootstrap/Makefile.shared`; the cached gbuild target `workdir/CustomTarget/android/loandroid3.done` can incorrectly indicate completion without the omitted binary. This is a cache completeness issue, not evidence that Gradle itself compiled a bad binary.
- **Production CI repair:** `scripts/native_engine_artifact.py` checks real ELF magic, AArch64 machine 183, 64-bit little-endian ET_DYN, minimum size and SHA-256; rejects symlinks, wrong architecture and placeholders. Its prepare mode removes only the generated library and the two exact stale gbuild stamps when invalid/missing, preserving cached LO static archives. `.github/workflows/android-native.yml` now runs prepare before `make`, verifies the ELF before Gradle, and uses a v2 cache including `engine/android/jniLibs` while allowing a one-time restore from v1. It does not manufacture any .so or weaken ABI checks.
- **Regression:** `tests/test_native_engine_artifact.py` exercises valid/wrong-ABI/wrong-type/tiny ELF, stale-stamp invalidation, valid-cache preservation, symlink rejection, missing-library CLI failure and workflow ordering. Upstream implementation reviewed from the pinned MPL-2.0 Collabora monorepo; no external code copied.
- **Source evidence:** feature branch code+tests `35c49242c5f22af506487040fba9e663f157ce10`; [Fast Source #40215454654](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215454654) **PASS**, [Integration #40215454659](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215454659) **PASS**. The exact marker/request SHA `7304b193355a4d0a6c45673de970c5f08e7f9890` also has [Fast Source #40215584103](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215584103) **PASS** and [Integration #40215584375](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215584375) **PASS**.
- **Purpose-bound native retry:** the exact-message marker push `7304b193355a4d0a6c45673de970c5f08e7f9890` requests one compile-only diagnostic to answer whether repairing the missing native shared object unblocks NDK/Gradle packaging. JVM/source tests cannot answer that question. **Native retry run ID/outcome NOT YET VERIFIED** through the available PR-only workflow query; do not claim the job started or an APK exists until an actual native workflow run and logs are observed.
- **Milestone acceptance remains OPEN:** Native ARM64 .so and APK verification **NOT TESTED on the retry**, Android Writer Arabic/English DOCX edit/save/cold-reopen, real SAF providers, PDF/print, Xiaomi Pad 5 and independent final recheck **NOT TESTED**. Next: retrieve native retry run and logs; if it fails, fix the next real root cause; if it succeeds, validate APK SHA-256/ABI and test on Android. No main change, merge or public release.

## M-NATIVE-01 — 2026-10-25: verify *packaged* native ELF, not merely an APK containing any .so

- **Milestone acceptance slice:** a diagnostic APK is structurally acceptable only if it contains exactly one nonempty `classes.dex`, exactly one `lib/arm64-v8a/liblo-native-code.so`, and the actual packaged ELF is proven to originate from the pinned, ABI-verified native engine. Existing aapt application ID, template byte-identity, ZIP integrity and APK SHA-256 gates remain mandatory. This does not certify Android runtime behavior.
- **Production:** `scripts/verify_native_apk.py` streams the APK's native ZIP member with bounded RAM; compares exact SHA-256 with the engine when possible; when Android Gradle strips non-loadable debug sections, compares each ELF PT_LOAD segment's virtual address, flags, file/memory size and SHA-256. Rejects altered executable bytes, missing/wrong-ABI libraries, duplicates, absent/empty DEX, truncated ZIP, malformed program headers and oversized extracted native members. The workflow now calls this verifier before recording a successful package. No third-party code copied or new dependency.
- **Regression:** `tests/test_verify_native_apk.py` covers exact identity, stripped-debug acceptance, altered loadable bytes, truncated load segment, wrong ABI, missing/empty DEX, duplicate ZIP members and invalid APK. `tests/test_native_preflight_contract.py` now verifies the stronger production gate rather than an obsolete literal grep. Local synthetic ZIP/ELF tests: **8/8 PASS** in a Python test harness; this is not real APK evidence.
- **Changes:** code/test/workflow through `26a584e5aaa7006695fd86a6da29dfa812b0fc70` on draft [PR #7](https://github.com/amroalhamedi2022-hue/aquaword-android/pull/7). Source CI [Fast #40225182457](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40225182457) **IN PROGRESS** and [Integration #40225182479](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40225182479) **IN PROGRESS** when recorded. Earlier SHA `263fefde` CI FAIL because an obsolete source contract expected the removed generic .so grep; test repaired, not skipped. Do not mark exact-SHA CI PASS before verification.
- **Separate native retry:** [native run #40215579687](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215579687), exact source SHA `7304b193355a4d0a6c45673de970c5f08e7f9890`, is **IN PROGRESS** at LibreOffice ARM64 engine make. The new APK verifier is on a *later* SHA and is **not** part of that already-running native job. No additional native build was triggered in this slice.
- **NOT TESTED:** verified native APK/ABI/package SHA on a real build; Writer Android DOCX Arabic/English edit/save/reopen; real SAF cloud/provider failures; Xiaomi Pad 5; PDF/print. M-NATIVE-01 remains **OPEN**. Next: resolve exact-SHA source CI; inspect native retry completion/logs and repair any actual linker/Gradle failure. When native build produces a real APK, run the stronger packaging verifier on a separately justified build or artifact before acceptance. No main edits, merges or releases.

### Exact-source verification closure (2026-10-25)
- Checkpoint source SHA `567f55096630d48d039810dae8997ad270c49c1e`: [Fast Source #40225236221](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40225236221) **PASS (completed/success)**; [Integration #40225236243](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40225236243) **PASS (completed/success)**. This verifies source/JVM/integration checks on the stronger APK verifier; native APK packaging and Android runtime remain **NOT TESTED**.
- Independently launched native retry [#40215579687](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215579687) remained **IN PROGRESS** at engine make when checked. It runs earlier SHA `7304b193`, not the current verifier. No duplicate native build requested.


## M-NATIVE-01 — 2026-10-25: native APK compiled; retention path repair in progress

- **Verified native build:** GitHub Actions run [#40215579687](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215579687) checked out request commit `7304b193355a4d0a6c45673de970c5f08e7f9890` and completed LibreOffice ARM64 native compilation, Collabora Android app compilation, Gradle APK packaging, APK package/assets verification, and SHA-256 checks. Job conclusion: **SUCCESS**.
- **Native library evidence:** `liblo-native-code.so`, ABI `arm64-v8a`, 198,019,656 bytes, SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`.
- **APK evidence:** `AquaWord-app-arm64-v8a-debug.apk`, SHA-256 `956108363c9ed901cfd5c48f2d205bf200987a1c74bc4065787070fc40f7ffe4`; expected debug application ID and five packaged DOCX fixtures passed. This is a compile-only diagnostic APK, **not** a user-ready build.
- **Retention failure:** Android emulator smoke was intentionally skipped. The attempt to keep the APK as an unpublished draft Release failed with HTTP 403 “Resource not accessible by integration”; no downloadable artifact exists for this run. This was a *retention permission failure*, not a compiler/Gradle failure.
- **Workflow fix in progress:** compile-only diagnostics now attempt a pinned, MIT-licensed `actions/upload-artifact` action for a one-day artifact and explicitly report upload success/failure. The known permission-sensitive draft-Release fallback is skipped for compile-only runs. Upload is best-effort because the repository previously reported exhausted Actions artifact quota.
- **New workflow/test commits:** `a2f48549532312d75d1563effc8df6d0074708dd` (workflow), `0f7617ab0f560aaa55cdc1d72e172da36cea57f4` (contract tests), `1475b65e1077e54b31667badc92aa76711b6a68c` (test assertion correction), `fc376cf6d84acef0d7ee953871418edee133d7ec` (follow-up assertion fix). The first CI run failed on the new test's selector logic; it is corrected. Current CI for the latest SHA must pass before authorizing another native run.
- **Acceptance status:** native compile/package at the diagnostic SHA **PASS**; downloadable artifact **NOT RETAINED**; Android emulator/device install and real Writer open/edit/save/cold-reopen, SAF failure recovery, print/PDF, and Xiaomi Pad 5 **NOT TESTED**.
- **Next ordered steps:** (1) require Fast Source + Integration PASS at the exact latest SHA; (2) only then authorize one purpose-bound retry to test the new one-day artifact route (the LibreOffice build cache was saved by the successful run); (3) confirm the actual artifact URL and SHA-256 if upload succeeds; (4) separately schedule device/runtime acceptance. Do not claim a delivered APK unless a real downloadable artifact is confirmed.


## M-NATIVE-01 — 2026-10-25: one authorized artifact-retention retry requested

- **Question:** does the updated, SHA-pinned one-day Actions artifact route retain the already-proven ARM64 compile as a downloadable artifact? This is not a redundant compile request: prior successful native run [#40215579687](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40215579687) has an empty artifact list and its source SHA predates the current upload-artifact step.
- **Request commit:** `86682a5e02ae70905a4fa64e330be35b0f7056fe` (`AquaWordNativeDiagnosticRetryOnce`), on PR #7. It changes only the one-shot marker; native workflow is guarded by both that marker path and the exact commit message. No additional retry is authorized after this result.
- **Current exact-SHA source/integration checks:** [Fast Source #40236633056](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236633056) and [Integration #40236633038](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236633038) were IN PROGRESS when checked. Native push-run ID and its artifact result are not yet independently retrievable through the available run-list connector; therefore do not claim the retry is running, passed, or produced an artifact until a run URL/artifact listing confirms it.
- **Existing compile evidence remains valid only for SHA `7304b193355a4d0a6c45673de970c5f08e7f9890`:** APK SHA-256 `956108363c9ed901cfd5c48f2d205bf200987a1c74bc4065787070fc40f7ffe4`; native library SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`. No downloadable artifact was retained from that run. Do not present it as a current downloadable APK.
- **Acceptance:** source-only and integration checks must pass on exact current SHA; downloadable artifact and its SHA must be confirmed if the authorized retry runs; Writer Android Arabic/English round-trip, real SAF failure recovery, print/PDF and Xiaomi Pad 5 remain **NOT TESTED**. M-NATIVE-01 remains OPEN.
- **Next step:** retrieve the exact native run status/logs/artifacts and stop after this one retention attempt. No main changes, merge, or release.


## M-NATIVE-01 — 2026-10-26: downloadable diagnostic APK independently verified

- The authorized diagnostic build [run #40236629771](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236629771) completed **PASS** and retained artifact [aquaword-native-diagnostic-86682a5e02ae70905a4fa64e330be35b0f7056fe, artifact ID 12615547822](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236629771/artifacts/12615547822), uploaded 2026-10-25; expiry shown by GitHub: 2026-10-26T21:54:50Z. Artifact ZIP digest: `d00f2c42b57baf20246de4d5a0b945402bba6c325df397ba80e5541bbfabb4ba`.
- Downloaded and inspected the exact ZIP. APK SHA-256 from embedded `SHA256SUMS`, independently recomputed: `c10e0cfa4e6d0802f369f79c8410dd8849c54b028c6d3fa8b0d555f5b353d014`. ZIP integrity check and file extraction succeeded. `lib/arm64-v8a/liblo-native-code.so` is ELF64 AArch64 / Android shared object; SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`. Upstream Collabora source pin: `2333344185931274f9c49d6c12a408cefcef6844`; NDK `29.0.14206865`.
- **Scope/limits:** this is a compile-only diagnostic/debug APK built at commit `86682a5e02ae70905a4fa64e330be35b0f7056fe`, not the final deliverable. Artifact availability is time-limited. APK structure and ABI were verified offline, but APK signature verification with Android SDK tools, installation, app launch, real Writer document open/edit/save/reopen, Arabic/English DOCX, SAF, print/PDF, and Xiaomi Pad 5 runtime remain **NOT TESTED**. M-NATIVE-01 remains OPEN.
- **Next:** preserve this APK as diagnostic evidence, verify the latest Fast Source/Integration checks, then plan device/runtime acceptance; do not repeat the same build without a relevant source change.
- **Google Drive Handoff sync:** unavailable in this automation runtime (no Google Drive/Docs write connector is exposed). The requested AquaWord Handoff document was **not updated**; sync status is **FAILED / NOT AVAILABLE**, not claimed successful.


## M-NATIVE-01 — 2026-10-26: process-death recovery regression test added

- **Milestone remains OPEN:** compile/retain a verified ARM64 diagnostic APK, then prove real Writer DOCX open/edit/save/reopen and SAF failure recovery on compatible Android (Xiaomi Pad 5 priority). Acceptance gates remain: package/signature verification, device launch, Arabic/English DOCX with tables/images, SAF read-only/write-failure/process-death paths, PDF/print, and recorded evidence. Do not mark the milestone complete from host-side tests alone.
- **Existing diagnostic APK remains verified for structure/ABI only:** run [#40236629771](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236629771), artifact [12615547822](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236629771/artifacts/12615547822), source SHA `86682a5e02ae70905a4fa64e330be35b0f7056fe`, APK SHA-256 `c10e0cfa4e6d0802f369f79c8410dd8849c54b028c6d3fa8b0d555f5b353d014`, native library SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2`. It is diagnostic/debug, not final-ready; install, launch, runtime and device behavior remain **NOT TESTED**. No repeated native build requested because no native production source changed.
- **New host-side crash test:** `history/test/org/libreoffice/androidapp/ui/AquaWordHistoryTest.java` launches a child JVM, commits one durable recovery snapshot, then calls `Runtime.halt(23)` during a second capture after partial bytes are written. Parent JVM checks that the committed snapshot and exact Unicode bytes survive process exit, the incomplete write is never published, a recent partial is retained during the grace period, and a stale partial is reclaimed. This is a host/JVM process-death simulation, **not** Android process-death/device proof.
- Test commits: `427946ee70e3c3b651b2ed85e328ef9f147f2203` (crash fixture), `d0d63a485d9f1673fda4b0acf54af1dd104b8501` (test cleanup), `9298af65b69a2a1bc36beb326d37284c277e960e` (verify committed snapshot survives the crash). Earlier Fast Source run [#40244371262](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244371262) **PASS** but did not compile/run the Java history test; integration run [#40244371260](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244371260) was **CANCELLED**. Follow-up exact-code PR checks then completed successfully: [Fast Source #40244539113](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244539113) **PASS** and [Integration #40244539226](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244539226) **PASS**. Integration job checked out merge commit `4799410` merging exact test commit `9298af65b69a2a1bc36beb326d37284c277e960e`; logs confirm compilation and execution of both `AquaWordHistoryTest` and `AquaWordPdfPreflightTest`, including the child-JVM abrupt-termination fixture. This is host/JVM evidence only, not Android process-death proof.
- **Build decision:** no new APK build in this round. The added change is a host-side recovery test and cannot be answered by another expensive Collabora build; existing artifact is sufficient for package/ABI inspection. No device attached to this runtime and no compatible ARM64 Android emulator evidence available.
- **Google Drive sync:** **FAILED / NOT AVAILABLE** in this runtime because no Google Drive/Docs write connector is exposed. The requested AquaWord Handoff document was not modified; no sync success is claimed. ChatGPT Library and all other Handoffs remain untouched.
- **Next ordered action:** first obtain an exact-current-commit integration result that compiles and runs `AquaWordHistoryTest`; fix any platform-specific failure. Then perform independent static/package recheck and pursue real-device Writer/SAF/PDF/print acceptance when a compatible device test path exists. No main edits, PR merge, release, or paid resource.


## M-NATIVE-01 — 2026-10-26: APK signing gate added; source CI PASS

- Native workflow now runs the Android SDK `apksigner verify --verbose --print-certs` against each packaged APK, requires v2 verification and a signer certificate SHA-256, and includes the signature report in the short-retention diagnostic artifact and Actions summary. This closes a pipeline acceptance gap; it does **not** retroactively verify the already-built diagnostic APK's signature.
- Workflow commit: `71e33b79f444cc6a112f054029131c94ec6a9dc2`; contract test commit: `47b880353a65c8c62049e0b03d4946f09ffab03a`.
- Exact-code PR checks: [Fast Source #40244942655](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244942655) **PASS**; [Integration #40244942656](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40244942656) **PASS**. Integration logs confirm compilation/execution of `AquaWordHistoryTest` (including abrupt child-JVM termination with durable-checkpoint verification), `AquaWordPdfPreflightTest`, and the PDF preflight against desktop LibreOffice-generated Arabic and English PDFs. These are host-side tests, not Android runtime acceptance.
- **Build decision:** no new APK build in this round. Source change adds a future package-signature gate; no need to repeat the hours-long native engine build before device/runtime acceptance is available. The current APK's signature remains **NOT TESTED with apksigner**; its archive/ABI/SHA remain verified as recorded above.
- **Google Drive Handoff:** still **FAILED / NOT AVAILABLE** because no Google Docs write connector is exposed in this runtime. No successful sync is claimed. ChatGPT Library and other Handoffs remain untouched.
- **Next:** use a compatible Android device to install and run the existing diagnostic APK; in the next purposeful native package run, capture the new `apksigner` certificate/scheme report. Keep M-NATIVE-01 OPEN until real Writer Arabic/English DOCX edit-save-reopen, SAF failure recovery, PDF/print and Xiaomi Pad 5 checks have evidence.


## M-NATIVE-01 — 2026-10-26: استعادة Snapshot مكتمل فقد ملف Metadata أثناء انهيار العملية

- **العثور على فجوة استرداد حقيقية:** تُزامن `capture()` بيانات المستند وتعيد تسمية ملف `.snapshot` قبل إعادة تسمية ملف `.properties`. إذا توقفت العملية في هذه النافذة، كانت البايتات الكاملة تبقى على القرص، لكن `readAll()/load()` يتجاهلانها؛ أي إن البيانات محفوظة ماديًا لكنها غير ظاهرة للمستخدم وغير قابلة للاستعادة من قائمة السجل.
- **تغيير الإنتاج:** `history/src/org/libreoffice/androidapp/ui/AquaWordHistory.java` يعيد بناء Metadata فقط عند غياب ملفها تمامًا، مع التحقق من أن الملف محلي داخل مجلد السجل، وحجم موجب ضمن حد 512 MiB، وSHA-256، ثم كتابة Metadata إلى `.meta-partial` مع `fsync` وإعادة تسميتها. لا تُستبدل Metadata موجودة لكنها تالفة، ولا تُحذف بايتات المستند عند فشل الاسترداد. أضيف نوع `recovered`، وتُعاد مراجعة البايتات قبل أي استعادة إلى SAF.
- **واجهة المستخدم:** أُضيفت تسمية مستقلة للنسخة التي استُعيدت بعد انقطاع الحفظ، بالإنجليزية والعربية، بدل عرضها خطأً كنسخة «قبل التحرير».
- **اختبارات أضيفت:** `AquaWordHistoryTest.testOrphanSnapshotRecovery` يختبر Snapshot عربيًا مكتملًا بلا Metadata، وإعادة بناء Metadata، واستعادة البايتات، وعدم تكرار السجل عند الفحص المتكرر. كما يتحقق من عدم عرض Snapshot فارغ للاستعادة مع إبقاء ملفه الأصلي دون حذف. اختبار Overlay يتحقق من التسمية في الموردين الإنجليزي والعربي.
- **Commits:** الإنتاج `db5cf503fdff6d45d9d32922a9680e5112efe584`؛ اختبار JVM `04ba25dd48a09869fc0345cda087835c6c97c98b`؛ تحديث Overlay/الترجمة `100ccb60067c6b8c2cad5ab032ba0649e9c6b8e4`, `1db7919a67b781b0f53dae3ac90433522cece013`, `34437c8f998c1a4aa25a0d442d38c56f45a65fec`؛ تقليل إعادة قراءة الملفات الكبيرة `393741ca5f00c186f602a291a1ccc510d8d9c8e4`.
- **التحقق النهائي للكود/الاختبارات على SHA `32af8773d2af04279380ad85153964c2be405d92`: PASS.** Fast Source #194 [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40254507054) — 124/124 اختبارًا، بما فيها عقد الـOverlay والتسميات العربية/الإنجليزية. Integration #366 [PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40254507061)؛ سجل التشغيل يثبت تجميع `AquaWordHistory.java` و`AquaWordHistoryTest.java` وتشغيل اختبار الاسترداد و`AquaWordPdfPreflightTest` بنجاح، مع roundtrip PDF مكتبي عربي/إنجليزي وفحوص Overlay. كان هناك فشل وسيط بسبب `return` مفقودة ثم لأن fixture عشوائيًا من 3 بايتات عومل كوثيقة؛ أُصلحا بإرجاع Snapshot المستعاد والتعرف المحافظ على DOCX/ODT/RTF/النص قبل إعادة بناء Metadata.
- **قرار البناء:** لم يُنشأ APK جديد؛ التغيير محصور في سجل الاسترداد واختبارات JVM وOverlay، ولا يحتاج إلى إعادة بناء محرك LibreOffice المكلف للإجابة عن سؤال الاختبار. تشغيل Android/SAF الحقيقي ما زال NOT TESTED.
- **Google Drive Handoff:** FAILED / NOT AVAILABLE؛ لا يتوفر موصل Google Docs للكتابة في بيئة التشغيل. لم يتم تعديل مستند AquaWord — HANDOFF ولم يُدّعَ نجاح المزامنة.
- **المتبقي:** الحصول على Fast Source + Integration على SHA الحالي وإصلاح أي فشل؛ ثم اختبار قتل عملية Android الفعلية، وSAF read-only/provider failure، وDOCX عربي/إنجليزي مع الجداول والصور، والحفظ وإعادة الفتح وPDF/الطباعة على جهاز ARM64 متوافق. **M-NATIVE-01 يبقى OPEN**؛ لا دمج ولا تعديل `main`.

## M-NATIVE-01 — 2026-10-26: protect live recovery captures from stale cleanup

- **Production issue:** history scans prune week-old `.partial` files. A slow SAF/cloud-backed input stream can still be writing a capture when another history/list operation runs; if its partial timestamp is stale, cleanup could unlink the active file and make the capture fail at the final rename.
- **Production fix:** register each active capture path under the history monitor before creating the temporary file. Stale cleanup checks the same registry while holding that monitor before deleting an incomplete file. The registry is released in the capture `finally` block after temporary-file cleanup. Recovery data and metadata commit ordering are unchanged.
- **Regression test added:** a blocked input stream writes a first chunk, the test ages its active partial by 15 days, triggers history cleanup concurrently, then resumes the stream and verifies that capture commits and restores the exact Arabic/English UTF-8 bytes.
- **Verification:** implementation and regression test are committed together. Exact-SHA Fast Source + Integration results must be inspected before marking source verification PASS. This is a host/JVM concurrency test, not a real Android SAF/cloud-provider or Xiaomi Pad 5 test.
- **Acceptance limits:** native APK install/launch, Writer DOCX Arabic/English roundtrip, Android process death, SAF provider failure, print/PDF and target-device UI remain NOT TESTED. M-NATIVE-01 stays OPEN.

### Automation handoff status — 2026-10-26
- Google Drive document **AquaWord — HANDOFF** sync: **FAILED / NOT AVAILABLE**. This runtime exposes no Google Docs/Drive write connector, so the requested document ID `1AVpneu7vimB0YjJDdUs_oHKLrGUIQW4PSg5A5cW6j4I` was not modified. No sync success is claimed.
- Current connector evidence does not expose the workflow/check-run list for the new commits (commit workflow query returned no PR-triggered runs and combined legacy statuses were empty). Therefore the new slow-capture regression remains **CI PENDING / NOT VERIFIED HERE** until Fast Source and Integration are confirmed on the exact current PR head. This is not a claim that GitHub Actions itself failed.

### Follow-up regression verification — 2026-10-26
- **Initial CI failure diagnosed:** Fast Source run [#40255852904](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255852904) failed because `tests/test_overlay.py` asserted the old exact `finally { temp.delete(); }` formatting. The production behavior was not the failing assertion; the source contract was stale after the active-capture guard was added. Integration run [#40255853052](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255853052) was cancelled after that test failure.
- **Test repair:** contract assertions now require active-path registration, removal, and cleanup protection, and compare fsync ordering against the commit-lock section rather than the earlier registration lock. Commits: `6cca4e350218911ca79098f77a333f3c3fea9f83` and `481a0f7fb9545b3f30b43b15d2e6b8bd55950052`.
- **Fast Source + real upstream overlay: PASS** on code/test commit `481a0f7fb9545b3f30b43b15d2e6b8bd55950052`: [run #40255989993](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255989993). The generated-source contract and application of the overlay to the pinned Collabora source completed successfully.
- **Integration:** [run #40255990010](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40255990010) was still IN PROGRESS at the last check, at the desktop LibreOffice DOCX import/re-save step. The JVM active-capture race test has not yet been confirmed executed; do not mark Integration PASS until the job completes.
- **No Android build was requested:** this is a Java history concurrency fix; the existing native diagnostic APK is unchanged and does not answer the new race test. Android SAF/device behavior remains NOT TESTED.


## M-NATIVE-01 — 2026-10-26: preserve committed recovery bytes when metadata rename fails

- **Production fix:** AquaWordHistory.capture() now tracks whether the fsynced .snapshot data rename succeeded. If the subsequent .meta-partial → .properties rename fails, final cleanup removes temporary files but preserves the complete data file. The next history scan can rebuild metadata for a recognized DOCX/ODT/RTF/TXT orphan. If the data rename itself fails, the uncommitted target is still cleaned up.
- **Regression test:** history/test/org/libreoffice/androidlib/AquaWordHistoryCommitTest.java injects a deterministic metadata-rename failure, checks that the full Arabic/English DOCX bytes survive, verifies no temporary files remain, then calls list() and restore() and compares exact bytes.
- **Code/test SHA:** b5a195f090479a0bce2d27d5521bc7b6158ec257 on draft PR #7; no third-party dependency. Fast Source + SAF contract PASS: [run #40263124801](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40263124801). Integration PASS: [run #40263124630](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40263124630), including Java compilation/execution of the new failure-injection test and pinned Collabora source-layout checks.
- **Build decision:** no new APK for this Java history transaction fix; the JVM regression directly answers the failure question. Existing diagnostic artifact [run #40236629771](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40236629771) belongs to older source SHA 86682a5e02ae70905a4fa64e330be35b0f7056fe, so it does not contain this fix and is not a final delivery.
- **NOT TESTED:** real Android process death exactly during metadata commit; actual SAF/cloud provider failures; native Writer Arabic/English edit-save-cold-reopen; PDF/print; Xiaomi Pad 5 UI/runtime. M-NATIVE-01 remains OPEN.
- **Google Drive Handoff sync:** FAILED / NOT AVAILABLE in this runtime; no Google Docs/Drive write connector is exposed, so the specified AquaWord Handoff document was not modified. No sync success is claimed.

## M-NATIVE-01 — 2026-10-26: اختبار انهيار فعلي بين اعتماد Snapshot وMetadata

- **الفجوة التي اختُبرت:** لم يكن اختبار رفض إعادة تسمية Metadata وحده يحاكي موت العملية بعد اعتماد ملف `.snapshot` الكامل وقبل نشر `.properties`. أُضيف child-JVM test يوقف العملية بـ `Runtime.halt(24)` عند هذا الحد بالضبط، بعد كتابة البيانات و`fsync` واعتماد اسم Snapshot.
- **التحقق بعد الانهيار:** العملية الأم تتحقق من وجود بايتات DOCX كاملة مع غياب Metadata المنشورة، ثم تستدعي مسار فحص السجل الحقيقي، وتتحقق من إعادة بناء Metadata، وعدم بقاء ملف Metadata المؤقت، واستعادة البايتات نفسها دون تغيير. بقي اختبار فشل rename الاعتيادي أيضًا.
- **Commit الاختبار:** `d433b9d7a6295f8b597cc53f7daff35d8420f747`.
- **CI على SHA نفسه:** Fast Source [#40273275463 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40273275463)؛ Integration [#40273275467 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40273275467). سجل Integration يؤكد تنفيذ اختبار الانهيار الجديد واختبار فشل Metadata ونجاحهما.
- **قرار البناء:** لم يُنشأ APK؛ هذا تغيير اختبار JVM، والاختبار المباشر يجيب عن سؤال نافذة الانهيار دون إعادة تجميع محرك LibreOffice. بناء APK لن يثبت سلوك SAF أو الجهاز.
- **NOT TESTED:** موت عملية Android الحقيقية، SAF/cloud provider الفعلي، تثبيت وتشغيل Writer، تعديل DOCX عربي/إنجليزي وإعادة فتحه، PDF/الطباعة، وXiaomi Pad 5. يبقى M-NATIVE-01 مفتوحًا.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE؛ لا توجد أداة كتابة Google Docs/Drive في بيئة التشغيل، لذا لم يُعدّل المستند المحدد. لا يُدّعى نجاح المزامنة.


## M-NATIVE-01 — 2026-10-26: حماية أحدث نقطة استرداد لكل مستند تحت ضغط الاحتفاظ

- **المشكلة:** خوارزمية الاحتفاظ القديمة كانت تحذف أقدم Snapshot عالميًا عند تجاوز حد 60، حتى لو كانت هذه النسخة أحدث/وحيدة نسخة استرداد لمستند A، بينما المستند B يملك عدة نسخ أقدم وأحدث. قد يحدث ذلك بعد فشل SAF لمستند A ثم حفظ مستندات أخرى.
- **التغيير الإنتاجي:** `AquaWordHistory.trim()` تعمل الآن على مرحلتين: تحذف النسخ القديمة المكررة للمصدر نفسه أولًا، ثم لا تحذف أحدث Snapshot لكل مصدر إلا إذا بقي حد 60 Snapshot أو 1 GiB متجاوزًا بسبب كثرة المصادر المختلفة/حجمها. يبقى Snapshot الجاري بثّه إلى SAF محميًا، ولا تُحذف أحدث نقطة عالمية. الحدود القصوى تظل نافذة عند تعذر تحقيقها بإزالة النسخ القديمة وحدها.
- **اختبار الانحدار:** `AquaWordHistoryCommitTest.testRetentionPreservesLatestSnapshotPerDocument` ينشئ 61 سجلًا: نقطة وحيدة للمستند A، ونسختين للمستند B، و58 مستندًا إضافيًا. يتحقق أن الاحتفاظ يحذف B-old بدل نقطة A الوحيدة، ويحتفظ بـB-new، ويستعيد بايتات A وB-new مطابقة، ويعود العدد إلى 60.
- **Commits:** اختبار الانحدار `436c54a811d83dd39db8be6aff821b6a34486815`؛ نقطة الكود والاختبار النهائية `5228c41a908063998ec79214c7b8625163f75ced`.
- **CI على SHA النهائي نفسه:** Fast Source [#40285645818 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40285645818)؛ Integration [#40285645716 PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40285645716). نجح فحص المصدر والتكامل على Windows/Linux workflow matrix؛ اختبار Java ينفّذ من مسار التكامل.
- **قرار البناء:** لم يُنشأ APK. هذا تعديل Java/ملفات محلية في طبقة سجل الاسترداد؛ اختبار JVM الفعلي يغطي ترتيب الإخلاء والاستعادة مباشرة، بينما APK لا يثبت سلوك مزوّد SAF الحقيقي.
- **NOT TESTED:** مزوّد SAF حقيقي/سحابي، موت عملية Android، تثبيت وتشغيل Collabora Writer، تحرير DOCX عربي/إنجليزي ثم حفظه وإعادة فتحه، PDF/الطباعة، واختبار Xiaomi Pad 5.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE؛ لا توجد أداة كتابة Google Docs/Drive في بيئة التشغيل، لذا لم يُعدّل المستند المحدد. لا يُدّعى نجاح المزامنة.
- **نقطة الاستئناف:** الاستمرار داخل M-NATIVE-01. بعد هذا الإصلاح، ركّز على اختبار تكامل واقعي لخطأ SAF/القراءة الراجعة واستعادة أحدث DOCX، ثم بوابات تشغيل Android/الجهاز؛ لا تعتبر المشروع مكتملًا اعتمادًا على اختبارات JVM وحدها.


## M-NATIVE-01 — 2026-10-26: recovery path containment

- **Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip remains OPEN. This slice hardens recovery discovery; it does not satisfy the native build or device roundtrip gates.
- **Production/test:** `AquaWordHistory.load()` now checks canonical containment for both snapshot payload and sidecar metadata. A symlink whose target escapes the app-private history folder is not surfaced as a recovery candidate. Added `testRecoveryRejectsSymlinksOutsideHistoryDirectory` for both external payload and metadata links.
- **Code/test SHA:** `986d99e02f2a743916cebfadd8de3898ffdceb7b` on draft PR #7. `main` remains unchanged.
- **Final exact-checkpoint evidence:** Fast Source [#40299341921](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40299341921) **PASS** and Integration [#40299341903](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40299341903) **PASS** on checkpoint SHA `140505ee9cf89967d24a459c892e4d3223452199`. Integration logs explicitly report `PASS: recovery scan rejects external payload and metadata symlinks`. The earlier run #40298998454 was cancelled after the branch advanced; it is not counted. Windows may report a clearly labeled symlink-test SKIP if runner permissions prohibit link creation.
- **Build decision:** no APK build. JVM path-containment testing is the direct test for this change; packaging would not establish the symlink invariant.
- **Remaining acceptance gates:** native ARM64 Collabora/Gradle package and ABI verification; install/launch; native Writer Arabic/English DOCX edit-save-cold-reopen; real SAF read-only/failure/truncation and recovery; print/PDF; Xiaomi Pad 5 UI/runtime; independent final recheck.
- **Google Drive sync:** **FAILED / NOT AVAILABLE** — no Docs/Drive write connector is available in this runtime. The specified AquaWord — HANDOFF file was not modified. This failure does not block development.
- **Next:** verify exact-SHA Integration completion, then continue M-NATIVE-01 toward native/runtime evidence; keep PR #7 Draft and do not modify `main`.


## M-NATIVE-01 — 2026-10-26: رفض روابط الاسترداد الرمزية داخل المجلد

- **الميلستون:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` ما زال **OPEN**؛ هذه دفعة تقوية لمسار الاسترداد ولا تغلق بوابات التشغيل الأصلية.
- **التغيير الإنتاجي:** أصبح `AquaWordHistory.load()` يشترط أن يكون المسار canonical لكل من `.snapshot` و`.properties` هو المسار المباشر المتوقع بالاسم نفسه، وليس مجرد مسار داخل مجلد الاسترداد. وطُبق الشرط نفسه قبل قراءة Snapshot يتيمة أو إنشاء Metadata لها. يمنع ذلك قبول symlink داخلي كأنه نسخة استرداد ثانية، أو إنشاء Metadata لاسم مستعار لملف قائم.
- **اختبار الانحدار:** أضيف `testRecoveryRejectsInDirectorySymlinkAliases`: ينشئ رابطًا رمزيًا لبيانات Snapshot ورابطًا لملف Metadata داخل المجلد، ثم رابطًا يتيمًا بلا Metadata إلى Snapshot موجود. يجب أن تظهر النسخة الأصلية فقط، وألا تُنشأ Metadata للرابط اليتيم. اختبار الروابط الخارجية السابق باقٍ أيضًا.
- **مراجع Git:** Commit الكود `c15f38d07ce6dc0483fa2be7d885fad438360395`؛ Commit الاختبار ونقطة الكود+الاختبار النهائية `44b132b9849ae51ffffef0b27a763f4c37fade76` على فرع PR #7 `fix/saf-save-failure-recovery-20261023`.
- **CI على نقطة الكود والاختبار:** Fast Source [#40314108206 **PASS**](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40314108206)؛ Integration [#40314108444 **PASS**](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40314108444). شغّل التكامل 125 اختبار Python، ثم كمبايل وتشغيل `AquaWordHistoryTest`؛ ويؤكد السجل `PASS: recovery scan rejects in-directory payload/metadata symlink aliases`.
- **قرار البناء:** لم يُنشأ APK؛ اختبار JVM يختبر هوية المسارات والروابط مباشرة، وإعادة بناء المحرك لا تضيف دليلًا لهذه الحالة.
- **PASS:** فحص المصدر والتكامل على Commit الاختبار؛ رفض alias للبيانات والـMetadata، ورفض إعادة بناء Metadata لرابط يتيم.
- **NOT TESTED:** تشغيل Android، SAF/cloud provider الحقيقي، موت عملية Android، فتح/تحرير/حفظ/إعادة فتح DOCX عربي وإنجليزي داخل Writer، الطباعة/PDF، واختبار Xiaomi Pad 5.
- **مزامنة Google Drive:** **FAILED / NOT AVAILABLE**؛ لا توجد أداة كتابة Google Docs/Drive في بيئة التشغيل، لذلك لم يُعدّل مستند AquaWord — HANDOFF ذي المعرّف `1AVpneu7vimB0YjJDdUs_oHKLrGUIQW4PSg5A5cW6j4I`. لا يُدّعى نجاح المزامنة.
- **المتبقي ومعايير القبول:** بناء ARM64 والتحقق من ABI؛ تثبيت وتشغيل فعلي؛ DOCX عربي/إنجليزي مع الجداول والصور والحفظ وإعادة الفتح؛ اختبار SAF read-only/failure/truncation والاسترداد بعد موت العملية؛ PDF/الطباعة؛ UI على Pad 5؛ ثم recheck مستقل. لا انتقال إلى milestone جديد.
- **نقطة الاستئناف:** متابعة `M-NATIVE-01` على فرع PR #7، مع إبقاء PR Draft وعدم تعديل `main`.


## M-NATIVE-01 — 2026-10-26: إصلاح اشتقاق Metadata عند وجود `.snapshot` داخل اسم الملف

- **الميلستون:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` ما زال **OPEN**.
- **المشكلة:** استخدام `String.replace(DATA_SUFFIX, META_SUFFIX)` كان يستبدل كل ظهور لـ`.snapshot` في الاسم، لا اللاحقة النهائية فقط. قد يفشل بذلك استرداد Snapshot يتيمة اسمها `legacy.snapshot-copy.snapshot`، وقد تُحذف Metadata غير المطابقة أثناء retention.
- **إصلاح الإنتاج:** أضيف `AquaWordHistory.metadataFileForSnapshot()` لإزالة اللاحقة النهائية فقط؛ يستخدمها `load()` ومسارا حذف Metadata داخل `trim()`.
- **اختبار الانحدار:** `testSnapshotSuffixInsideBasename` ينشئ DOCX عربيًا صالحًا بلا Metadata بهذا الاسم، ويتحقق من إعادة بناء `legacy.snapshot-copy.properties` ومن تطابق البايتات بعد الاسترداد، ثم يضغط سجل التاريخ إلى أكثر من 60 نقطة ويتحقق من حذف Snapshot الأقدم وملف Metadata المطابق معًا.
- **مراجع Git:** كود الإنتاج `a8ccaa13749756794d7ec4fd13e79590dd627cca`؛ الكود والاختبار `8af527e334927cf73a16fe3e23d7c0c15367e9b8`؛ تحديث القبول `bba7d1a9225c1b7f7d4adf40980250f42b0ffedb`.
- **CI:** Fast Source [#40330416847 **PASS**](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40330416847) على SHA الكود والاختبار. Integration [#40330416884](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40330416884) لم يصل بعد إلى خطوة اختبار Java الأساسية؛ كان في خطوة LibreOffice DOCX roundtrip. تحديث الوثائق غيّر رأس PR، لذلك لا تُنسب نتيجة التكامل السابقة إلى الرأس الجديد، ولا يُدّعى PASS قبل ظهور نتيجة التشغيل الأحدث.
- **قرار البناء:** لم يُنشأ APK؛ اختبار JVM هو الدليل المباشر المناسب لهذا العيب، والبناء لا يضيف إثباتًا لقاعدة اشتقاق المسار.
- **PASS:** فحص Fast Source على SHA الكود والاختبار؛ تم توثيق المشكلة والإصلاح والاختبار.
- **NOT TESTED:** تكامل Java على أحدث رأس بعد توثيق الدفعة؛ تشغيل Android وSAF الحقيقي؛ موت العملية على الجهاز؛ DOCX عربي/إنجليزي داخل Writer؛ PDF والطباعة؛ Xiaomi Pad 5.
- **مزامنة Google Drive:** **FAILED / NOT AVAILABLE**؛ لا توجد أداة كتابة Google Docs/Drive في هذه البيئة، لذلك لم يُعدّل مستند `AquaWord — HANDOFF` المحدد. لا يُدّعى نجاح المزامنة.
- **المتبقي ومعايير القبول:** انتظار Integration على أحدث رأس؛ بناء ARM64 والتحقق من ABI عند توافر مسار البناء؛ تثبيت/تشغيل؛ DOCX round-trip عربي/إنجليزي بالجداول والصور؛ SAF read-only/failure/truncation والاسترداد بعد موت العملية؛ PDF/الطباعة؛ واجهة Pad 5؛ ثم recheck مستقل.
- **نقطة الاستئناف:** متابعة نفس `M-NATIVE-01` في PR #7 على `fix/saf-save-failure-recovery-20261023`. أبقِ PR Draft، ولا تعدّل `main` أو تفتح milestone جديدًا.

## M-NATIVE-01 — 26 أكتوبر 2026: رفض استبدال مسار نسخة الاسترداد بعد عرض السجل

- **المشكلة:** قد يحتفظ المستدعي بكائن `Snapshot` بعد فحص السجل. إذا استُبدل مساره لاحقًا برابط رمزي إلى ملف خارجي مطابق بايتًا ببايت، فإن فحص الحجم وSHA-256 وحدهما لا يثبتان أن المسار ما زال يشير إلى نسخة الاسترداد الخاصة بالتطبيق.
- **إصلاح الإنتاج:** أضيفت `isCanonicalSnapshotChild()` للتحقق من أن النسخة تحل إلى مسارها المتوقع داخل مجلد السجل قبل التحقق من البايتات وبعده. أصبح التحقق يعدّ البايتات ويعيد فحص الحجم ووقت التعديل والمسار. وتعيد `restore()` التحقق بعد فتح المصدر وقبل أول كتابة للوجهة، ثم قبل `flush()`. هذا يقلل سباقات استبدال المسار، لكنه **ليس فتحًا نظاميًا مضمونًا بخيار no-follow ولا دفاعًا كاملًا ضد سباقات مهاجم محلي**.
- **اختبار الانحدار:** `testVerifyRejectsSymlinkSwapAfterListing` يحتفظ بنسخة معتمدة، ثم يستبدل مسارها برابط رمزي إلى ملف خارجي مطابق، ويتوقع رفض التحقق والاستعادة دون كتابة أي بايت إلى الوجهة.
- **Commit الإنتاج:** [`280e887def184e87bcadf49bbcbaf4d0036c0e9b`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/280e887def184e87bcadf49bbcbaf4d0036c0e9b). **SHA الكود والاختبار:** [`98343f343f98b9c6a675b068994f9705f8458787`](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/98343f343f98b9c6a675b068994f9705f8458787).
- **CI:** Fast Source [#40357216114 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40357216114) على SHA الكود والاختبار. Integration [#40357216058 — IN PROGRESS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40357216058) بقي عند خطوة LibreOffice المكتبية لاستيراد DOCX وإعادة حفظه؛ لذلك لم يُؤكّد تشغيل اختبار Java الجديد حتى الآن. التشغيل السابق #40357159667 أُلغي عند تقدم الفرع ولا يُحتسب دليلًا.
- **قرار البناء:** لم يُبنَ APK؛ اختبار JVM المركز يجيب مباشرة عن قبول المسار بعد الاستبدال، بينما بناء الحزمة لا يثبت سلوك SAF الحقيقي. اختبار Android الأصلي والجهاز يبقى بوابة منفصلة.
- **الحالة:** Android/SAF الفعلي، موت العملية على الجهاز، تحرير DOCX عربي/إنجليزي وإعادة فتحه، PDF/الطباعة، التثبيت والتشغيل وXiaomi Pad 5 = **NOT TESTED**.
- **Google Drive Handoff:** **FAILED / NOT AVAILABLE**؛ لا توجد أداة كتابة Google Docs/Drive في بيئة هذه الجولة. لم يُعدّل مستند `AquaWord — HANDOFF` المحدد، ولا ندّعي نجاح المزامنة.
- **الاستئناف:** أبقِ M-NATIVE-01 مفتوحًا وPR #7 بوضع Draft؛ تحقّق من Integration على أحدث SHA ثم تابع قبول Writer/SAF على Android. `main` لم يتغير.



## 2026-10-26 — تصحيح حالة Integration CI

- SHA الحالي وقت الفحص: `13158c93fb1be65eeaf6154e98f278252826b62e`.
- Fast Source and SAF Contract [#40358863204](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40358863204): **PASS**.
- Integration [#40358863389](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40358863389): **CANCELLED** وليس PASS. أُلغيت خطوة استيراد DOCX وإعادة حفظه عبر LibreOffice المكتبي؛ لذا تم تجاوز اختبارات Java اللاحقة ولم يُثبت هذا التشغيل نجاح اختبار استبدال مسار الاسترداد برابط رمزي.
- لا بناء APK لهذا التغيير التوثيقي؛ يلزم دليل تكامل محدود زمنيًا، ثم اختبار Android/SAF فعلي. تثبيت/تشغيل Android، تحرير DOCX عربي/إنجليزي وإعادة فتحه، الحفظ لدى مزود فاشل، PDF/الطباعة وXiaomi Pad 5 = **NOT TESTED**.
- مزامنة Google Drive `AquaWord — HANDOFF`: **FAILED / NOT AVAILABLE** لغياب موصل كتابة Google Docs/Drive؛ لم تتم المزامنة.
- الاستئناف: أبقِ `M-NATIVE-01` وPR #7 مفتوحين بوضع Draft، واعزل اختبار Java history-core في مسار تكامل محدود إذا تعذر إكمال مرحلة LibreOffice الحالية. لم يتغير `main`.


## 2026-10-26 — تأكيد نجاح أحدث CI على نقطة المتابعة الحالية

- نقطة الوثائق السابقة: `80538e02883169d84865b3c78bf5df81e76813a8`؛ SHA الكود والاختبارات ما زال `13158c93fb1be65eeaf6154e98f278252826b62e`.
- Fast Source/SAF Contract [#40368384781](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40368384781): **PASS**.
- Integration [#40368384806](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40368384806): **PASS**. اكتملت مرحلة LibreOffice المكتبي لاستيراد DOCX وإعادة حفظه، واختبارات التكامل، وتجميع/اختبار Java لمكوّن استرداد المستندات، والتحقق من سكربتات المحاكي، وفحص بنية مصدر Collabora المثبت. هذا دليل مصدر وتكامل مكتبي، وليس قبولًا على جهاز Android.
- تشغيل Integration الأقدم [#40358863389](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40358863389) يظل **CANCELLED**؛ التشغيل الأحدث أعلاه هو دليل الحالة الحالية ولا يغيّر الحالة التاريخية للتشغيل السابق.
- **NOT TESTED:** تثبيت وتشغيل APK على جهاز، تحرير DOCX عربي/إنجليزي وحفظه وإعادة فتحه، SAF read-only/فشل المزود والتعافي الحقيقي، موت العملية على Android، PDF/الطباعة، وواجهة/أداء Xiaomi Pad 5.
- لا بناء لهذه المراجعة التوثيقية. مزامنة Google Drive `AquaWord — HANDOFF` ما زالت **FAILED / NOT AVAILABLE** لغياب موصل كتابة Docs/Drive. يبقى M-NATIVE-01 مفتوحًا وPR #7 بوضع Draft؛ لم يتغير `main`.


## 2026-10-26 — التحقق من واصف ملف الاسترداد المفتوح

- **الميلستون:** M-NATIVE-01 — بناء ARM64 الأصلي ودورة تحرير Writer وإعادة الفتح ما زال **OPEN**.
- **الإصلاح الإنتاجي:** [e507066f9c17c30e3da2887caf889dae241c97d0](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/e507066f9c17c30e3da2887caf889dae241c97d0) يتحقق من SHA-256 للـ FileInputStream المفتوح نفسه قبل كتابة أي بايت إلى وجهة الاستعادة، ثم يعيد موضع الواصف نفسه إلى البداية. هذا يرفض استبدال المسار بملف عادي مختلف وبالحجم نفسه بين فحص الـ lease وفتح الملف. لا يدّعي منعًا نظاميًا كاملًا للروابط الرمزية أو حماية من كل تعديل متزامن داخل العملية نفسها.
- **اختبار الانحدار:** [651f200b649f2342798af8ea6fbc0d21fd19a8c8](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/651f200b649f2342798af8ea6fbc0d21fd19a8c8) يستبدل ملف الاسترداد بملف مختلف بالحجم نفسه بعد نجاح فحص الـ lease، ويتأكد أن التحقق من الواصف المفتوح يرفضه قبل إرسال أي بايت إلى الوجهة.
- **اختبار JVM مستقل ومحدود:** أُضيف workflow مجاني لاختبارات Java الأساسية في [bc3f93cb4ac309a1c3b01c65968e2ab076fb40ee](https://github.com/amroalhamedi2022-hue/aquaword-android/commit/bc3f93cb4ac309a1c3b01c65968e2ab076fb40ee)، كي لا يعتمد إثبات استرداد المستندات على انتظار مرحلة LibreOffice المكتبية الطويلة. تشغيل [#40377152228](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152228): **PASS**، وتظهر سجلاته نجاح اختبار رفض استبدال الملف قبل كتابة الاستعادة. فحص Fast Source/SAF [#40377152285](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152285): **PASS**.
- **التكامل الكامل:** التشغيل [#40377152231](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40377152231) كان لا يزال عند خطوة استيراد DOCX وإعادة حفظه عبر LibreOffice المكتبي وقت تحديث هذه النقطة؛ لذلك **لا أحتسب Integration PASS** حتى الآن.
- **قرار البناء:** لم يُبنَ APK؛ سؤال الاختبار هنا يتعلق بواصف Java المفتوح قبل أول كتابة، والاختبار المركز يجيب عنه مباشرة. بناء APK لا يثبت سلوك مزود SAF الحقيقي أو الجهاز.
- **NOT TESTED:** تثبيت وتشغيل Android، فشل مزود SAF الحقيقي والتعافي، موت العملية على الجهاز، تحرير DOCX عربي/إنجليزي وإعادة فتحه على Writer الأصلي، PDF/الطباعة وواجهة وأداء Xiaomi Pad 5.
- **مزامنة Google Drive:** **FAILED / NOT AVAILABLE** لعدم توفر موصل كتابة Google Docs/Drive؛ لم يُعدّل مستند AquaWord — HANDOFF المحدد، ولا ندّعي نجاح المزامنة.
- **الاستئناف:** إبقاء M-NATIVE-01 مفتوحًا وPR #7 بوضع Draft؛ مراجعة نتيجة Integration الحالية ثم متابعة اختبارات Writer/SAF الأصلية. لم يتغير main.


## تحديث 26 أكتوبر 2026 — حدّ مجلد الاسترداد الخاص (M-NATIVE-01)

- **إنتاج:** `a5f45dbbc90d4b97e7db897bbaf1b98b506894ea`؛ أصبحت دالة مجلد التاريخ تتحقق من أن `aquaword-history` هو المجلد الفرعي المتوقع تحت جذر ملفات التطبيق، وترفض المسار الرمزي أو أي مسار canonical خارج هذا الحد قبل الفهرسة أو الكتابة.
- **اختبار JVM:** `25f976e31bfca03305b3ff969ec0a767b6c3e83f`؛ يربط `aquaword-history` بمجلد خارجي ويحاول تعداد التاريخ، ويتطلب رفض العملية وبقاء ملف خارجي كما هو. إذا لم تسمح بيئة Windows بإنشاء الروابط الرمزية، يُسجّل الاختبار SKIP لهذه الحالة فقط.
- **CI على SHA الاختبار:** PENDING حتى ظهور تشغيل مكتمل مرتبط بالتغييرات أعلاه؛ لا تُستخدم نتائج CI أقدم كدليل لهذا الإصلاح.
- **الحدود:** فحص canonical يرفض رابط المجلد المعروف، لكنه ليس فتحًا ذريًا no-follow ولا يزيل كل سباقات تعديل المسار من عملية أخرى تحت UID نفسه.
- **NOT TESTED:** Android SAF حقيقي، موت العملية على جهاز، round-trip تحرير DOCX عربي/إنجليزي على Xiaomi Pad 5، الطباعة/PDF والقبول البصري.
- **Google Drive Handoff:** FAILED / NOT AVAILABLE في بيئة التشغيل؛ لم تتم كتابة مستند Drive المحدد. تم توثيق التعذر هنا بدل الادعاء بالمزامنة.
- **الاستئناف:** افحص JVM-only/History CI على SHA الاختبار، أصلح أي فشل قبل متابعة قبول المحرر الأصلي؛ أبقِ M-NATIVE-01 مفتوحًا.

## إعادة تحقق حالة CI — 26 أكتوبر 2026

- رأس PR #7 الحالي: `aea1a5792e90634080b85d7a1cd0a450beccb7d8`.
- **PASS:** اختبار الاسترداد JVM-only رقم [40384562650](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40384562650).
- **PASS:** فحص المصدر وعقد SAF رقم [40384562536](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40384562536).
- **PASS:** اكتمل تكامل LibreOffice المكتبي/DOCX في التشغيل [40387367659](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40387367659) على نقطة التوثيق `28e0a4c0c3640f8dcff10f4f1ffcd31b5fe45ef1`، مع بقاء مصدر/اختبارات التطبيق على SHA `aea1a5792e90634080b85d7a1cd0a450beccb7d8`. التشغيل الملغى الأقدم 40384562866 تجاوزه هذا النجاح. هذا لا يثبت قبول Android أو SAF الحقيقي.
- **NOT TESTED:** تثبيت وتشغيل APK على Android، فشل/اقتطاع SAF الحقيقي والتعافي، دورة تحرير DOCX عربي/إنجليزي وإعادة فتحه في Writer الأصلي، PDF والطباعة، وقبول Xiaomi Pad 5.
- مزامنة Google Drive لمستند AquaWord — HANDOFF: **FAILED / NOT AVAILABLE**؛ لم تتم كتابة المستند من هذه البيئة.
- نقطة الاستئناف: أبقِ M-NATIVE-01 مفتوحًا، أكمل تكامل LibreOffice على SHA الحالي، ثم نفّذ اختبار Android/SAF حقيقيًا. لا تُعلن الاكتمال اعتمادًا على JVM أو فحص المصدر وحدهما.


## 2026-10-26 — M-NATIVE-01 recovery retention sub-gate

**Milestone:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip (still OPEN).

- Added regression `testWritebackLeasePinsSnapshotDuringRetention` to prove a checkpoint currently being streamed to SAF cannot be evicted by retention when 60 newer distinct-document checkpoints arrive. It verifies the exact Arabic payload can still be restored and the retention cap remains 60.
- Code/test SHA: `d24d8e44ec71df497b8f8d8a33ed4348876607fe`.
- Recovery Core JVM-only CI [#40394504450](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394504450): **PASS** (compile, history/crash-window regressions, PDF preflight; new lease test explicitly passed).
- Full Integration CI [#40394504512](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394504512): **IN PROGRESS** when recorded.
- **Still NOT TESTED:** native ARM64 build at current head; APK install/launch; Android SAF provider refusal/truncation and recovery; native Writer DOCX Arabic/English edit-save-cold-reopen; print/PDF; Xiaomi Pad 5 visual/performance.
- **Next:** finish the current full Integration run, then continue toward a purpose-bound native build only if the current source has a concrete compile/package question and a permitted one-shot route. Do not bypass the existing one-shot native diagnostic guard.
- Google Drive AquaWord — HANDOFF sync: **FAILED / NOT AVAILABLE** in this runtime; no Docs/Drive write connector is exposed, so the specified Drive document was not modified.


### 2026-10-26 — current checkpoint CI closed

- Current code/test commit: `d24d8e44ec71df497b8f8d8a33ed4348876607fe`; current documentation checkpoint: `24c2cb509019e22dbcf95f50f0bce7b698d5d49b`.
- Fast Source + SAF Contract [#40394729968](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394729968): **PASS** on the current documentation SHA.
- Recovery Core JVM-only [#40394729849](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394729849): **PASS**; active writeback-lease retention regression passed.
- Full Integration [#40394729928](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394729928): **PASS** on the current documentation SHA. LibreOffice desktop DOCX roundtrip, source/integration tests, recovery core, and pinned Collabora layout smoke completed. This is still not Android device acceptance.
- Superseded Integration run [#40394504512](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40394504512) ended **CANCELLED** when the follow-up documentation checkpoint triggered a newer run; it is not counted as a pass.
- M-NATIVE-01 remains **OPEN**. Native build for the current source, Android install/launch, actual SAF provider-failure recovery, native Writer Arabic/English edit-save-cold-reopen, PDF/print and Xiaomi Pad 5 acceptance remain **NOT TESTED**.


## 2026-10-27 — M-NATIVE-01: تجهيز الاسترداد والتحقق منه قبل فتح وجهة SAF

- **الميلستون:** M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip؛ ما زال **OPEN**.
- **المشكلة المعالجة:** فتح مزود SAF بوضع wt أو rwt قد يقتطع الملف فورًا. فحص SHA-256 للنسخة ثم فتح الوجهة ثم نسخ المصدر مباشرة يترك فجوة إذا تغيّرت نسخة الاسترداد أثناء النسخ؛ وقد تكون الوجهة قد اقتُطعت قبل اكتشاف اختلاف البايتات.
- **إنتاج:** أُضيفت AquaWordHistory.restoreToDestination(snapshot, opener)؛ تنسخ النسخة إلى ملف staging خاص داخل مجلد التاريخ، وتعمل fsync، وتتحقق من الحجم وSHA-256 والمسار الأب canonical قبل استدعاء opener. واجهة Writer أصبحت تمرر فتح مزود SAF كـcallback، لذلك لا يُفتح openOutputStream(wt/rwt) قبل نجاح staging والتحقق. كما رُبط كل Snapshot بمسار مجلد التاريخ canonical الذي حُمّل منه.
- **اختبار انحدار:** testRestoreStagesBeforeOpeningProvider يغيّر ملف المصدر بعد اكتمال staging وقبل فتح الوجهة، ثم يثبت أن بايتات الاستعادة المرسلة تظل مطابقة للنسخة الموثقة وأن ملف staging يُنظّف. عُدّلت اختبارات الانحدار السابقة لتثبت عزل الاستعادة عن تغيير/اقتطاع المصدر الأصلي أثناء كتابة الوجهة.
- **المراجع:** تنفيذ API والـoverlay والاختبارات الأولية 091fee88160582cfd6c60a4dc154618cc2d6bce7؛ تحديث fixture الانعكاسي fd9609e4862f9204da232386881abf2d0fad3f66؛ تحديث اختبار التغيير المتزامن d5b7e53f331c41a10c78f412e575c874f66d5480؛ تصحيح نطاق اختبار overlay 35d8e8009604e9ca6d979f4bff6b5803f3ebf1b3.
- **CI على رأس 35d8e80:** Recovery Core JVM-only [#40413364675 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364675)؛ Fast Source/SAF Contract [#40413364669 — PASS](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364669). Integration [#40413364968 — PENDING](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413364968) عند كتابة هذا السجل؛ لا يُحتسب PASS. التشغيل الأقدم [#40413304913](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40413304913) كان في LibreOffice desktop DOCX roundtrip على SHA أقدم، وليس دليلًا على رأس PR الحالي.
- **حدود الضمان:** staging يمنع تغيير المصدر الأصلي من تبديل بايتات الملف المحلي الذي يُنسخ إلى الوجهة بعد اكتمال staging. لا يضمن ذرّية مزود SAF إذا فشل المزود نفسه في منتصف الكتابة، ولا يثبت cloud sync أو قبول Android.
- **NOT TESTED:** Android SAF provider فعلي يقتطع/يرفض الكتابة؛ تثبيت وتشغيل APK على جهاز؛ موت عملية Android؛ DOCX عربي/إنجليزي كامل داخل Writer الأصلي؛ الطباعة/PDF والقبول البصري/الأداء على Xiaomi Pad 5.
- **البناء:** لا APK في هذه الدفعة؛ سؤال الاختبار هو ترتيب فتح وجهة SAF وسلامة بايتات الاسترداد، وقد أجابت عنه اختبارات JVM وoverlay مباشرة. لا يُعاد تشغيل البناء الأصلي التشخيصي ذي التفويض أحادي الاستخدام.
- **Google Drive AquaWord — HANDOFF:** FAILED / NOT AVAILABLE؛ موصل كتابة Google Docs/Drive غير متاح في هذه البيئة، لذلك لم تتم مزامنة المستند المحدد.
- **نقطة الاستئناف:** أبقِ PR #7 Draft وM-NATIVE-01 مفتوحين. انتظر Integration على الرأس الحالي؛ ثم تابع قبول Android/SAF الواقعي دون فتح milestone جديد أو تعديل main.

## 2026-10-27 — حدّ حجم موحّد لنسخ الاسترداد

- الإنتاج: إضافة الدالة المشتركة isWithinSnapshotSizeLimit(long) لفرض حد 512 MiB لكل نسخة. أصبح تحميل metadata المحفوظة، والتحقق من النسخة المخزنة مؤقتًا، وقراءة ما بعد الكتابة من المزود، والتحقق من واصف الملف المفتوح، وملف staging، وواجهتا الاستعادة، ترفض الحجم الصفري أو السالب أو الذي يتجاوز الحد قبل hashing أو فتح وجهة قد تُقتطع. استرداد النسخ اليتيمة يستخدم الحارس نفسه.
- اختبار الانحدار: AquaWordHistoryCommitTest.testOversizedSnapshotMetadataRejected يغطي الحدود السالبة والصفرية، وحد 512 MiB نفسه، وحالة الحد + 1. يستخدم الاختبار ملفًا صغيرًا وmetadata بحجم مبالغ فيه لإثبات رفض السجل قبل hashing مع إبقاء ملفات الدليل دون حذف.
- رأس الكود والاختبارات والعقد: 359ff2dcb747ab46c2f7126de2e46701d3b9cf25. Commit الإنتاج 61ec7aa473f263760ebaacd2bcb06bb6f34b266c، واختبار JVM 9aae703f43c3b2bc2c813d8e32c0d4fd97330eed، وتصحيح عقد المصدر 359ff2dcb747ab46c2f7126de2e46701d3b9cf25.
- CI على الرأس الحالي — PASS: Recovery Core JVM-only #40425553795، وFast Source + SAF Contract #40425553801، وIntegration #40425553688. اجتاز التشغيلان الأوسع 125 اختبار Python لكل منهما، وأكمل Integration دورة DOCX المكتبية عبر LibreOffice واختبارات نواة الاسترداد. فشل Fast Source على SHA وسيط 9aae703 بسبب assertion قديم يتوقع تعبير الحجم السابق؛ صُحح الاختبار وأصبح التشغيل على الرأس الحالي PASS.
- قرار البناء: لم يُبنَ APK؛ invariant التخزين محدد واختبارات JVM/المصدر تتحقق منه مباشرة، والبناء لا يثبت سلوك مزود SAF الحقيقي.
- NOT TESTED: تثبيت وتشغيل Android، رفض/اقتطاع/قراءة SAF الفعلية، موت العملية على Android، دورة Writer عربية/إنجليزية مع الحفظ وإعادة الفتح، الطباعة/PDF، والقبول البصري/الأداء على Xiaomi Pad 5.
- الحالة: يبقى M-NATIVE-01 مفتوحًا وPR #7 بوضع Draft، ولم يتغير main. مزامنة Google Drive Handoff متعذرة في هذه البيئة؛ لا ندّعي كتابة المستند الخارجي.


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


## تحديث 27 أكتوبر 2026 — بوابة صيغة SHA-256 للنسخ الاحتياطية

- أضيف فحص إنتاجي لصيغة حقلي SHA-256 في بيانات الاسترداد: 64 محرفًا سداسيًا عشريًا صغيرًا، بما يطابق الصيغة التي ينشئها التطبيق.
- أضيف اختبار JVM لبيانات checksum تالفة ولـ source hash تالف؛ ويتحقق الاختبار من عدم عرضها كنسخ قابلة للاستعادة ومن بقاء ملفات البيانات والبيانات الوصفية دون حذف.
- هذا قبول محلي لقراءة البيانات الوصفية فقط، ولا يثبت تشغيل Android أو SAF الحقيقي أو موت العملية أو دورة DOCX عربي/إنجليزي أو PDF والطباعة على Xiaomi Pad 5.
- الميلستون النشط: M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip، والحالة OPEN. لم يُنشأ APK لأن التغيير لا يتطلب إثباتًا على مستوى الحزمة.


## تحديث 27 أكتوبر 2026 — طلب فحص Native تكاملي للميلستون M-NATIVE-01

- **الغرض:** فحص تكامل المصدر الحالي مع Collabora/LibreOffice ARM64 وتجميع APK وفحص سلامة الحزمة، وليس إصدارًا نهائيًا.
- **سؤال الاختبار:** هل ينتج الفرع الحالي APK بمعمارية arm64-v8a وهوية التطبيق المتوقعة ومكتبة ELF AArch64 سليمة بعد ربط Android/Gradle؟
- **لماذا لا تكفي اختبارات المصدر:** اختبارات JVM وعقود المصدر لا تشغّل NDK linker ولا دمج manifest/resources ولا Gradle packaging ولا فحص الحزمة النهائية. الحزمة التشخيصية السابقة مبنية من نقطة مصدر أقدم.
- **الحالة:** طلب تشغيل تشخيصي واحد على runner مجاني؛ النتيجة والـartifact قيد الانتظار.
- **حتى لو نجح البناء تبقى NOT TESTED:** تثبيت/تشغيل Android، تحرير DOCX عربي/إنجليزي وإعادة فتحه، فشل SAF والتعافي، الطباعة/PDF، والواجهة والأداء على Xiaomi Pad 5.


## تحديث 27 أكتوبر 2026 — نتيجة Native diagnostic وإصلاح فحص التوقيع

- التشغيل 40449362565 بنقطة الطلب 45d94cc3bda67de693beb33018ebf159c4018ff4 استخدم Collabora المثبت على 2333344185931274f9c49d6c12a408cefcef6844. نجح فحص المحرك وتهيئة Collabora وتجميع المصادر حتى إنتاج APK داخل runner.
- **PASS جزئي:** سلامة ZIP وفحص scripts/verify_native_apk.py أكدا arm64-v8a. مكتبة المحرك المضمنة 198,019,656 بايت، SHA-256 = ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2. SHA-256 للـAPK كما ظهر في السجل: 7bc4818d200c8590859300adc5635857576e752a6abba9226ef82bff20481bec. apksigner أكد توقيع v2 وطبع بصمة شهادة SHA-256.
- **FAIL — خطأ في بوابة CI وليس خطأ تجميع مثبتًا:** كان workflow يبحث حرفيًا عن 'Signer #1 certificate SHA-256 digest:' بينما أداة apksigner الفعلية طبعت 'V2 Signer: certificate SHA-256 digest:'. انتهت الخطوة قبل تأكيد package ID وتطابق القوالب. لم يُحتفظ بأي artifact، وقائمة artifacts للتشغيل فارغة؛ لذلك لا توجد APK قابلة للتسليم رغم وجود SHA في السجل.
- صُحّح الفحص لقبول صيغتي apksigner وأضيف اختبار عقد مصدر. هذا الإصلاح لا يشغّل Native build تلقائيًا؛ يجب نجاح source CI أولًا، وأي محاولة لاحقة يجب أن تختبر اكتمال بوابة التحقق والاحتفاظ بملف قابل للتنزيل. تثبيت وتشغيل Android واختبارات الجهاز ما زالت NOT TESTED.


## تحديث 27 أكتوبر 2026 — تصحيح اختبار عقد التوقيع

- فشل أول تشغيل Fast Source بعد إصلاح verifier بسبب اختبار قديم ما زال يطلب النص الحرفي القديم 'Signer #1 certificate SHA-256 digest:'. الاختبار الجديد الذي يغطي صيغتي apksigner اجتاز التشغيل نفسه.
- حُدّث الاختبار القديم ليتحقق من عقد grep الجديد بصيغتيه. يجب إعادة فحص Fast Source وIntegration على commit الجديد قبل قبول الإصلاح.


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


## 2026-10-27 — منع تصادم ملف staging في الحفظ المحلي

- **الميلستون:** `M-NATIVE-01 — ARM64 Native Build & Writer Roundtrip` ما زال **OPEN**.
- **التغيير الإنتاجي:** كان مسار الحفظ المحلي في overlay يستخدم اسمًا ثابتًا `.<اسم-الوجهة>.part`؛ قد يتعارض مع ملف موجود مسبقًا ويُفرّغ ثم يُحذف إذا فشل الحفظ. أصبح ينشئ ملف staging فريدًا في مجلد الوجهة عبر `File.createTempFile(".aquaword-", ".part", resolvedFile.getParentFile())`، ويحتفظ بكتابة المحتوى ثم `flush + fsync` قبل محاولة الاستبدال بالـrename. التنظيف أصبح null-safe ويُسجل تعذّر إزالة ملف staging بدل إخفاء الخطأ الأصلي.
- **اختبار الانحدار:** عُدّل fixture ليطابق حلقة النسخ الفعلية من Collabora ويكتب كل chunk فعلًا ثم ينفّذ fsync. أضيفت تأكيدات تمنع رجوع المسار الثابت وتتحقق من الملف الفريد والنسخ المتين.
- **المراجع:** كود overlay `4f24c606e5f736a683e120d8871c7b92d7bbb472`؛ إصلاح anchor `d1f586ed0dc58cf0b1061dc3d0edfb50a0f1bbf7`؛ اختبار العقد `23c9cab13795c31e2ebf9044570c7e93ee393e5f`؛ رأس الاختبار النهائي `3d3a8235a018fdfbee10228b64701dde06ac893b`.
- **CI على الرأس النهائي — PASS:** [Fast Source #40463302415](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302415) — 132 اختبار Python؛ [Integration #40463302399](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302399) — فحص overlay على مصدر Collabora المثبّت واختبارات JVM/PDF وDOCX round-trip عبر LibreOffice المكتبي؛ [Recovery Core #40463302400](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40463302400).
- **المحاولات الفاشلة التي تم تجاوزها:** فشل تشغيلان وسيطان لأن anchor الجديد لم يطابق fixture الاختبار المبسّط. عولج بناء anchor باستخدام `chr(10)`، ثم جرى جعل fixture يطابق بنية upstream؛ التشغيلات الثلاثة النهائية أعلاه ناجحة.
- **حدود القبول:** لم يُختبر هذا السلوك على نظام ملفات Android الحقيقي أو مزود SAF/cloud. كذلك ما زالت دورة Writer عربية/إنجليزية مع cold-reopen، موت عملية Android، الطباعة/PDF، وواجهة وأداء Xiaomi Pad 5 **NOT TESTED**.
- **قرار البناء:** لم يُنشأ APK جديد؛ اختبار overlay يجيب مباشرة عن invariant المصدر. بناء جديد لن يثبت سلوك نظام الملفات على الجهاز. بناء ARM64 التشخيصي الحالي موثق أعلاه وهو دليل packaging فقط، وليس قبولًا نهائيًا.
- **مزامنة Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE**؛ لا يوجد موصل كتابة Google Docs/Drive في هذه البيئة، ولم يُعدّل المستند المحدد.
- **نقطة الاستئناف:** متابعة `M-NATIVE-01` وPR #7 بوضع Draft/Open، مع إعطاء الأولوية لاختبار SAF/Writer على Android فعلي؛ لا تعديل لـ`main` ولا دمج.


## إعادة تحقق مستقلة من APK التشخيصي — 27 أكتوبر 2026

- **Artifact:** [AquaWord native diagnostic artifact #12715085399](https://github.com/amroalhamedi2022-hue/aquaword-android/actions/runs/40459738117/artifacts/12715085399)، أُنشئ 2026-10-27 06:27:30 UTC وتنتهي صلاحيته المجدولة 2026-10-28 06:27:26 UTC.
- **التحقق المستقل:** نُزّل ZIP وفُحص محليًا؛ SHA-256 للأرشيف `bc9943af59f61ca09f756dfdc254730359c566b66ae6f028f2b7ebcae6f1e842) يطابق digest المسجل في GitHub، و`unzip -t` نجح بلا أخطاء.
- **APK:** الحجم 265,562,824 بايت؛ SHA-256 `26851485b4dc7b3b1fa840f24276ed21fe9a0a4a388fbc69199a8d7b5d97ecfc)، مطابق لـ`SHA256SUMS` داخل الأرشيف. تقرير التوقيع يثبت APK Signature Scheme v2=true؛ الشهادة Debug وبصمتها SHA-256 `b1de54d42a34046f9f305cae3c34b25c1aeb95c9518b51021f8c998e7dadb15b`.
- **المحرك:** `liblo-native-code.so` بحجم 198,019,656 بايت، ELF64 little-endian/AArch64؛ SHA-256 `ba55c821ea3c199758da0d819109ded923deebc68c3e69669a401d68f4124fa2). workflow سجّل نجاح تحقق package ID `com.aquaword.app.debug) وفحص القوالب الخمسة.
- **قيد المصدر:** بُني هذا الـAPK من SHA `84b168b8dda1d1c6e89760631dddbb475d9ef59d) وعلى Collabora pin `2333344185931274f9c49d6c12a408cefcef6844). وهو أقدم من إصلاح staging المحلي `4f24c606e5f736a683e120d8871c7b92d7bbb472) واختبار الانحدار اللاحق؛ لذلك لا يثبت تلك التعديلات ولا يُعد إصدارًا من رأس الفرع الحالي.
- **قرار البناء:** لم يُعاد البناء؛ checkpoint يحدد المحاولة التشخيصية بأنها one-shot ويحظر إعادة المحاولة التلقائية. هذا تحقق تنزيل/سلامة مستقل وليس تشغيل CI جديدًا.
- **PASS:** artifact موجود وقابل للتنزيل وقت الفحص؛ سلامة ZIP وSHA-256 للـAPK؛ تقرير توقيع v2؛ معمارية مكتبة AArch64.
- **NOT TESTED:** تثبيت وتشغيل Android، SAF حقيقي وفشل/اقتطاع الكتابة والتعافي، موت العملية، Writer عربي/إنجليزي مع حفظ وإعادة فتح بارد، الطباعة/PDF، وواجهة/أداء Xiaomi Pad 5. الـAPK debug-signed وتشخيصي ومؤقت.
- **Google Drive AquaWord — HANDOFF:** **FAILED / NOT AVAILABLE**؛ لا يوجد موصل كتابة Google Docs/Drive متاح في بيئة التشغيل، ولم يُعدّل المستند المحدد.
- **نقطة الاستئناف:** إبقاء `M-NATIVE-01` مفتوحًا؛ لا تستخدم هذا الـAPK كدليل لقبول رأس المصدر الحالي، ولا تبدأ بناءً تشخيصيًا آخر تلقائيًا. يلزم مسار اختبار Android صالح ومصرّح به قبل إغلاق بوابات الجهاز.
