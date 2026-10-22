# AquaWord Android — حالة تنفيذ موثقة (22 أكتوبر 2026)

## النطاق المعتمد
Android فقط؛ Xiaomi Pad 5 أولاً والهواتف ثانياً. واجهة قريبة في تنظيم أدواتها من Word Android، لكن بهوية AquaWord / Liquid Aurora مستقلة. **لا Windows** ولا محرر WebView مستقل.

## ما نُفّذ ككود في المستودع
- تطبيق هوية AquaWord على ملفات Collabora/LibreOffice الأصلية مع الحفاظ على ترخيص المصدر.
- حزمة CSS لشريط Notebookbar وجانبي Mobile Wizard دون تغيير مساحة الصفحة البيضاء.
- معرّف التطبيق `com.aquaword.app`، الأسماء والأيقونات بكثافات Android المختلفة.
- ربط زر الإنشاء الرئيسي بإنشاء مستند Writer من تدفق Android الأصلي مباشرة، بدل قائمة Writer/Calc/Impress.
- اختبارات Python لثبات الترقيعات، مع smoke test على ملفات الفرع الأصلي المثبت SHA: `2333344185931274f9c49d6c12a408cefcef6844`.
- GitHub Actions للدمج وبناء Native Android؛ لا يتم رفع APK إلا بعد التحقق من سلامة الملف ومعرّف الحزمة.

## أدلة CI
- نجحت اختبارات الدمج الأولى: GitHub Run #39698804701.
- كشف Build أول فشل أداة `setup-android`: Run #39699424484؛ تم تغييرها إلى SDK manager الموجود على Runner.
- كشف Build ثان فشل اسم منصة SDK `android-37`: Run #39699527680؛ عُدّل إلى `android-37.0`.
- Build رقم #39699767102 تجاوز تجهيز الأدوات واستنساخ المصدر ووصل إلى بناء محرك LibreOffice native. **حالته يُفحص من GitHub قبل أي تصريح نجاح**.
- تحديث اختبار Writer-only: Run #39699912171 (نجح وقت التحقق).

## ما ليس جاهزاً — شروط لازمة لأي تسليم نهائي
- APK ناجح وموقّع ومثبت ويعمل على جهاز Android؛ لم يؤكد بعد.
- فتح/تحرير/حفظ DOCX عربي/إنجليزي بدون تلف أو تغيير تنسيقات حرجة؛ لم يختبر بعد.
- مراجعة أدوات Word: Home / Insert / Layout / References / Review / View؛ مطلوب قياس الوظائف الأصلية على Android.
- PDF export/print وRTL، جداول، صور، هوامش، footnotes، comments، track changes؛ يتطلب اختبارات end-to-end.
- Version history المحلي، recovery القوي، وضع تركيز مخصص، قوالب علمية، PDF annotations، AI اختياري: **لم تُنفذ**.
- تجربة واجهة متكاملة على Xiaomi Pad 5 في portrait/landscape مع حفظ سلس واحترام صلاحيات Android SAF؛ لم تختبر بعد.

**مهم:** PASS في اختبار الـoverlay أو تجميع أول APK لا يكفي لإعلان أن التطبيق مكتمل، ولا ينبغي عرض ميزات غير منفذة على أنها موجودة.
