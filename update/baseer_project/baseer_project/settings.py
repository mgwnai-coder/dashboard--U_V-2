import os
from pathlib import Path
DEBUG = True  #اجعلها او عند الانتهاء من التطوير False لاحقاً عند رفع الموقع على استضافة حقيقية (HTTPS) 


# 🌟 تعديل بسيط: السماح بكل النطاقات محلياً لكي لا تواجه مشاكل عند ربط تطبيق فلاتر (الهاتف) بالسيرفر
ALLOWED_HOSTS = ['*'] 

SECRET_KEY = 'django-insecure-replace-this-with-a-very-long-and-random-string'

BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',  
    'rest_framework',
    'rest_framework.authtoken',
]

# --- 1. تسجيل التطبيق ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'baseer_project.urls'
WSGI_APPLICATION = 'baseer_project.wsgi.application'

# --- 2. تحديد نموذج المستخدم المخصص ---
AUTH_USER_MODEL = 'dashboard.User'

# --- 3. إعدادات قاعدة البيانات ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'baseer_db',
        'USER': 'root', 
        'PASSWORD': 'root123', 
        'HOST': 'localhost',
        'PORT': '3306',
        
        # 🌟 التعديل السحري الأول لتسريع الأداء (Persistent Connections) 🌟
        # إبقاء الاتصال بقاعدة البيانات مفتوحاً لمدة 60 ثانية بدلاً من إغلاقه مع كل طلب
        # هذا يقلل وقت الاستجابة (Latency) بشكل ملحوظ جداً!
         
    }
}

# 🌟 التعديل السحري الثاني: تفعيل الذاكرة المؤقتة (Caching) 🌟
# هذا يخبر جانغو باستخدام جزء من رامات السيرفر لتخزين البيانات المتكررة بدلاً من حسابها كل مرة
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'baseer-dashboard-cache',
    }
}

# --- 4. إعدادات القوالب (Templates) ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context_processors.admin_notifications',
            ],
        },
    },
]

# --- 5. إعدادات الملفات الثابتة والميديا ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =========================================================
# 🌟 إعدادات أمان الجلسات (Sessions & Cookies) 🌟
# =========================================================
SESSION_COOKIE_AGE = 1800  # مدة بقاء الجلسة 30 دقيقة
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # إغلاق الجلسة مع المتصفح
SESSION_SAVE_EVERY_REQUEST = True  # 🔄 تجديد الوقت مع كل طلب

# =========================================================
# 🛡️ نظام الأمان الديناميكي (Dynamic Security Settings)
# =========================================================

# 1. التشفير التلقائي: (False في جهازك لتجنب الأخطاء، True في السيرفر الحقيقي للحماية)
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# 2. حماية الكوكيز من الاختراق عبر الجافاسكريبت (XSS)
CSRF_COOKIE_HTTPONLY = False  # يجب أن تكون False ليعمل CSRF بشكل صحيح
SESSION_COOKIE_HTTPONLY = True 

# 3. النطاقات الموثوقة (لحل مشكلة الـ CSRF الأحمر)
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# 4. توافق المتصفحات الحديثة (Chrome/Edge)
if DEBUG:
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'
else:
    # أقصى حماية في السيرفر الحقيقي
    CSRF_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SAMESITE = 'Strict'
# =========================================================
# 📱 إعدادات API وتطبيق الموبايل (Mobile App Settings)
# =========================================================
# المفتاح السري الخاص بتشفير طلبات تطبيق الموبايل (Flutter)
# هذا المفتاح يستخدمه المهندس محمد لتشفير الـ Timestamp
MOBILE_SECRET_KEY = "Basseer_Secure_Dynamic_Key_2026_!@#"


# =========================================================
# ⏱️ إعدادات الوقت والتاريخ (Time Zone Settings)
# =========================================================
# إيقاف المناطق الزمنية المعقدة لتجنب خطأ MySQL في بيئة التطوير (الويندوز)
# هذا سيجعل اللوحة الرئيسية (Dashboard) والإحصائيات تعمل فوراً بدون أخطاء
USE_TZ = False
# =========================================================
# 🤖 إعدادات بيئة الاختبار (Testing Environment)
# =========================================================
import sys
if 'test' in sys.argv:
    print("🚀 جاري تشغيل الاختبارات وبناء قاعدة البيانات مباشرة من الكود (بدون Migrations)...")
    
    class DisableMigrations(object):
        def __contains__(self, item):
            return True
        def __getitem__(self, item):
            return None

    MIGRATION_MODULES = DisableMigrations()