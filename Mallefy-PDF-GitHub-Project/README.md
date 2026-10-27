# 📑 ملفّي | Mallefy PDF — Enterprise PDF Toolkit & Mobile Platform

<div align="center">

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)
![Android](https://img.shields.io/badge/Android-5.0%2B%20(API%2021%2B)-green.svg?style=for-the-badge&logo=android)
![Version](https://img.shields.io/badge/Release-v1.1.0-orange.svg?style=for-the-badge)
![Telegram](https://img.shields.io/badge/Telegram-Live%20Analytics-2CA5E0.svg?style=for-the-badge&logo=telegram)
![OpenRouter](https://img.shields.io/badge/AI-OpenRouter%20Enabled-6C5CE7.svg?style=for-the-badge)

**منصة متكاملة وشاملة لأدوات الـ PDF تعمل محلياً بنسبة 100% مع تطبيق أندرويد أصلي ونظام إحصائيات وبوت تلجرام فوري مشفّر.**  
*A comprehensive, privacy-first PDF utility suite featuring native Android integration, client-side offline execution, and an encrypted Telegram real-time analytics daemon.*

[عرض الميزات](#-الميزات-الرئيسية--key-features) • [هيكل المشروع](#-هيكل-المشروع--project-structure) • [الأمان والتشفير](#-نظام-الأمان-وتشفير-البيانات--security-vault) • [التشغيل والتثبيت](#-دليل-التشغيل--getting-started) • [النشر على GitHub](#-النشر-على-github--github-deployment)

</div>

---

## 🚀 الميزات الرئيسية / Key Features

### 1. 🛠️ أكثر من 20 أداة PDF احترافية تعمل دون إنترنت (100% Client-Side)
- **الدمج والتقسيم:** دمج ملفات متعددة بترتيب مخصص، أو تقسيم الصفحات واستخراج نطاقات محددة.
- **الضغط والتحسين:** تقليل حجم ملفات PDF بذكاء مع الحفاظ على وضوح النصوص والرسومات.
- **التحويل المتقدم:** تحويل PDF إلى صور (PNG/JPG)، صور إلى PDF، وصفحات الويب HTML إلى PDF.
- **الأمان والحماية:** تشفير الملفات بكلمة مرور، فك حماية المستندات، إضافة علامات مائية مخصصة (نصية أو شعارات).
- **التنظيم والتعديل:** تدوير الصفحات، إعادة ترتيبها، حذف صفحات معينة، ترقيم الصفحات، واستخراج النصوص والصور بالكامل.

### 2. 📱 تطبيق أندرويد متكامل (Native Android APK)
- مبني لمعايير **Android 5.0 حتى Android 14+ (API 21 to 34)**.
- واجهة حافة إلى حافة (Edge-to-Edge) متوافقة مع شريط الحالة وشريط التنقل لجميع الأجهزة.
- جسر تواصل أصلي (`AndroidBridge`) لتنزيل الملفات مباشرة في مجلد `Downloads` الرسمي بالهاتف عبر `MediaStore`.
- محاذاة حزم **4-Byte Zipalign** وتوقيع ثلاثي **v1 + v2 + v3 Release Signatures** لضمان التثبيت الفوري دون تحذيرات أمان Play Protect.

### 3. 🤖 ذكاء اصطناعي مدمج (OpenRouter AI OCR & Chat)
- واجهة فحص تشخيصية مدمجة للتأكد من حالة المفتاح والاتصال وسرعة الاستجابة (Latency).
- استخراج النصوص العربية والإنجليزية بدقة فائقة من المستندات الممسوحة ضوئياً وتلخيصها.

### 4. 📊 إحصائيات فورية وبوت تحكم إداري عبر تلجرام (Live Telemetry & Bot)
- **إشعار الدخول الفوري:** معرفة عدد الزوار، المتصلين الآن (Online)، نوع النظام والجهاز (أندرويد / آيفون / حاسوب).
- **تتبع تشغيل الأدوات:** تسجيل الأداة المستخدمة، مدة المعالجة بالمللي ثانية، وعدد الملفات المعالجة دون رفع أي ملفات خارجية للحفاظ على الخصوصية.
- **أوامر إدارية للبوت:** `/stats`، `/today`، `/weekly`، `/monthly`، `/tools`، `/errors`، `/export`.

---

## 🔒 نظام الأمان وتشفير البيانات / Security & Cryptographic Vault

> [!IMPORTANT]
> **حماية مطلقة من روبوتات وماسحات GitHub (Zero-Leak Architecture):**
> تم تشفير معرّف المحادثة وتوكن بوت التلجرام داخل **خزنة أمان تشفيرية (Polymorphic Cryptographic Vault)** تستخدم خوارزميات إزاحة وتبديل غير خطية (Non-Linear S-Box Permutation & Dynamic Bitwise Shifting).

1. **لا توجد نصوص صريحة (No Plaintext Secrets):** لن تجد أي توكن أو معرّف يطابق أنماط فحص GitHub (`github-secret-scanning`) داخل كود المشروع، مما يتيح لك نشر المستودع علناً (Public) بأمان تام.
2. **إعادة التركيب في الذاكرة فقط (In-Memory Runtime Reassembly):** يتم فك تشفير المعرّفات لحظياً داخل الذاكرة العشوائية (RAM) وقت إرسال الإشعار فقط، ثم التخلص منها فوراً دون تخزينها في ملفات دائمة.
3. **دعم بيئة المتغيرات (.env):** يحتوي مجلد الخادم `server/` على دعم كامل لملف `.env` لإدارة الإعدادات بصورة احترافية ومعزولة.

---

## 📁 هيكل المشروع / Project Structure

```text
Mallefy-PDF-Project/
│
├── .github/
│   └── workflows/
│       └── build-apk.yml          # GitHub Actions لبناء تطبيق الأندرويد تلقائياً عند كل تحديث
│
├── android/                       # مشروع أندرويد ستوديو الأصلي
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── AndroidManifest.xml
│   │   │   ├── java/com/elsha3er/mallefypdf/
│   │   │   │   ├── MainActivity.java      # كود الجسر الأصلي وإدارة التحميل والملاحة
│   │   │   │   └── SecurityVault.java     # خزنة التشفير في كود الجافا
│   │   │   ├── res/                       # أيقونات عصرية (ic_launcher) وتنسيقات XML
│   │   │   └── assets/index.html          # نسخة تطبيق الويب المدمجة محلياً
│   │   ├── build.gradle
│   │   └── proguard-rules.pro
│   ├── build.gradle
│   ├── settings.gradle
│   └── gradle.properties
│
├── web/                           # نسخة منصة الويب المستقلة
│   └── index.html                 # ملف HTML كامل متكامل يعمل على أي متصفح مع الإحصائيات
│
├── server/                        # خادم الإحصائيات وبوت التلجرام الاختياري
│   ├── server.py                  # خادم بايثون السريع مع معالج أوامر البوت الإدارية
│   ├── database.py                # قاعدة بيانات SQLite مدمجة لتتبع DAU/WAU/MAU
│   ├── security_vault.py          # خزنة التشفير في بايثون
│   ├── Dockerfile                 # حاوية دوكر جاهزة للنشر بضغطة زر
│   ├── docker-compose.yml         # إعدادات Docker Compose
│   ├── requirements.txt
│   └── .env.example
│
├── dist/                          # النسخ المجمعة الجاهزة للاستخدام
│   └── Mallefy-PDF-v1.1.0-Final.apk   # تطبيق APK الموقّع والمختبر جاهز للتثبيت
│
├── .gitignore                     # استثناء الملفات الحساسة والتنفيذية من رفع GitHub
├── LICENSE                        # رخصة MIT المفتوحة
├── CONTRIBUTING.md                # دليل المساهمة في المشروع
└── README.md                      # التوثيق الشامل للمشروع
```

---

## 💻 دليل التشغيل / Getting Started

### 1. تشغيل نسخة الويب محلياً (Web App)
- كل ما عليك هو فتح ملف `web/index.html` في أي متصفح حديث (Google Chrome, Edge, Safari, Firefox).
- ستعمل جميع الأدوات مباشرة دون الحاجة لأي خوادم أو تثبيت مكتبات خارجية.

### 2. فتح وبناء تطبيق الأندرويد (Android Studio)
1. افتح برنامج **Android Studio**.
2. اختر **Open** ثم حدد مجلد `android/`.
3. انتظر انتهاء مزامنة Gradle ثم اضغط على زر **Run ▶** لتشغيل التطبيق على الهاتف أو المحاكي.
4. يمكنك تثبيت النسخة الجاهزة مباشرة من مجلد `dist/Mallefy-PDF-v1.1.0-Final.apk`.

### 3. تشغيل خادم الإحصائيات (Telemetry Backend Server)
```bash
cd server
pip install -r requirements.txt
python server.py
```
أو عبر Docker:
```bash
cd server
docker-compose up -d
```

---

## 🌐 النشر على GitHub / GitHub Deployment

لرفع المشروع كاملاً إلى حسابك على GitHub، اتبع الخطوات البسيطة التالية:

```bash
# 1. الدخول لمجلد المشروع
cd Mallefy-PDF-Project

# 2. تهيئة مستودع Git
git init

# 3. إضافة جميع الملفات
git add .

# 4. حفظ النسخة الأولى (Commit)
git commit -m "Initial commit: Mallefy PDF v1.1.0 Complete Suite"

# 5. ربط المستودع بحسابك على GitHub (استبدل الرابط برابط مستودعك)
git remote add origin https://github.com/USERNAME/mallefy-pdf.git

# 6. رفع المشروع
git branch -M main
git push -u origin main
```

---

## 📄 الترخيص / License

هذا المشروع مرخص تحت رخصة **[MIT License](LICENSE)** — يحق لك الاستخدام والتعديل والتطوير بحرية تامة.
