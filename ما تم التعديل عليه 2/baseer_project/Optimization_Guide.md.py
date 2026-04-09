# ==========================
#  لا تنسى عمل هذا ال الاستعلام على قاعدة البيانات 
ALTER TABLE users ADD INDEX (role);
ALTER TABLE users ADD INDEX (is_active);
ALTER TABLE diagnosis_sessions ADD INDEX (status);
ALTER TABLE diagnosis_sessions ADD INDEX (created_at);
ALTER TABLE doctor_profiles ADD INDEX (status);
ALTER TABLE doctor_profiles ADD INDEX (is_verified);
ALTER TABLE support_tickets ADD INDEX (status);
ALTER TABLE support_tickets ADD INDEX (created_at);
# الخطوة 1: تثبيت المكتبة المطلوبة
# افتح موجه الأوامر (Terminal) في مسار المشروع ونفذ هذا الأمر:
# Bash
# pip install python-dotenv
# =======================
# الخطوة 2: إنشاء ملف .env
# قم بإنشاء ملف جديد في المجلد الرئيسي للمشروع (بجوار ملف manage.py مباشرة) وقم بتسميته .env، ثم انسخ داخله هذه المتغيرات:

# --- إعدادات جانغو (Django) ---
DJANGO_SECRET_KEY= #'ضع_هنا_مفتاح_طويل_وعشوائي_جداً'
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS= #localhost,127.0.0.1,your-domain.com

# --- إعدادات قاعدة البيانات (لجانغو و FastAPI) ---
DB_NAME= #baseer_db
DB_USER=  #root
DB_PASSWORD= #root123
DB_HOST= #localhost
DB_PORT=3306
# (ملاحظة: تأكد من تغيير DJANGO_DEBUG=False عند رفع المشروع على السيرفر الحقيقي).

# الخطوة 3: تعديل ملف baseer_project/settings.py (جانغو)
# في أعلى ملف settings.py الخاص بجانغو، قم باستدعاء المكتبة واستبدال المتغيرات الحساسة لتُقرأ من ملف البيئة:


import os
from pathlib import Path
from dotenv import load_dotenv

# 🌟 تحميل ملف الأسرار (.env)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 🌟 القراءة من ملف البيئة بدلاً من كتابتها مكشوفة
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')

# ... (باقي التطبيقات والـ Middleware كما هي) ...

# 🌟 تحديث إعدادات قاعدة البيانات
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'CONN_MAX_AGE': 60,
    }
}
# الخطوة 4: تعديل ملف database.py (FastAPI)
# في ملف الاتصال بقاعدة البيانات الخاص بـ FastAPI، قم بتحديث الأكواد لتسحب البيانات من نفس الملف:


import os
import mysql.connector
from mysql.connector import pooling
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 🌟 تحميل ملف الأسرار (.env)
load_dotenv()

# سحب المتغيرات
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

# 1. إعدادات SQLAlchemy (للذكاء الاصطناعي)
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. إعدادات MySQL العادية (للاتصالات السريعة)
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="baseer_pool",
        pool_size=15,
        pool_reset_session=True,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
except Exception as e:
    print(f"🔥 خطأ في إنشاء مسبح الاتصالات: {e}")

def get_db_connection():
    return connection_pool.get_connection()
# ⚠️ خطوة أخيرة حاسمة (لا تنساها):
# إذا كنت تستخدم Git لرفع كودك على GitHub أو غيره، يجب أن تنشئ ملفاً باسم .gitignore (إذا لم يكن موجوداً) وتكتب بداخله السطر التالي:

# Plaintext
# .env
# هذا يمنع Git من رفع ملف الأسرار إلى الإنترنت، وبذلك تضمن حماية مشروعك بالكامل.
# ==========================
#  لا تنسى عمل هذا ال الاستعلام على قاعدة البيانات 
ALTER TABLE users ADD INDEX (role);
ALTER TABLE users ADD INDEX (is_active);
ALTER TABLE diagnosis_sessions ADD INDEX (status);
ALTER TABLE diagnosis_sessions ADD INDEX (created_at);
ALTER TABLE doctor_profiles ADD INDEX (status);
ALTER TABLE doctor_profiles ADD INDEX (is_verified);
ALTER TABLE support_tickets ADD INDEX (status);
ALTER TABLE support_tickets ADD INDEX (created_at);