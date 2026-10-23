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
