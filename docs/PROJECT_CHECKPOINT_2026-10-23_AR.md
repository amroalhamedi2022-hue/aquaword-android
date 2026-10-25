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
