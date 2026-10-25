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
