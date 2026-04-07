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
SESSION_COOKIE_AGE = 1800  # مدة بقاء الجلسة بالثواني (1800 = 30 دقيقة) وبعدها يُطرد تلقائياً
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # مسح الكوكيز وإغلاق الجلسة فور إغلاق المتصفح
SESSION_COOKIE_SECURE = False  # اجعلها True لاحقاً عند رفع الموقع على استضافة حقيقية (HTTPS)
SESSION_COOKIE_HTTPONLY = True # منع الجافاسكربت من سرقة الكوكيز (حماية من ثغرات XSS)
SESSION_SAVE_EVERY_REQUEST = True # 🔄 تحديث وقت انتهاء الجلسة مع كل طلب