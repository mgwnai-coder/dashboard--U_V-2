import mysql.connector
from mysql.connector import pooling
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ====================================================================
# 1. إعدادات SQLAlchemy (للذكاء الاصطناعي) مع تفعيل (Connection Pooling)
# ====================================================================
DATABASE_URL = "mysql+mysqlconnector://root:root123@localhost/baseer_db"

# 🌟 التعديل الأول: أضفنا إعدادات تجمع الاتصالات لمنع اختناق السيرفر
engine = create_engine(
    DATABASE_URL,
    pool_size=10,         # عدد الاتصالات المفتوحة والمستعدة دائماً (تكسيات جاهزة)
    max_overflow=20,      # اتصالات إضافية مسموح بها وقت الضغط الشديد
    pool_recycle=3600     # إعادة تنشيط الاتصال كل ساعة لتجنب خطأ (MySQL server has gone away)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====================================================================
# 2. إعدادات MySQL العادية (لباقي النظام) باستخدام (MySQLConnectionPool)
# ====================================================================
db_config = {
    "host": "localhost",      
    "user": "root",          
    "password": "root123",          
    "database": "baseer_db"   
}

# 🌟 التعديل الثاني: إنشاء مسبح الاتصالات مرة واحدة عند تشغيل السيرفر
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="baseer_pool",
        pool_size=15,             # 15 اتصال جاهز لخدمة طلبات فلاتر في أجزاء من الثانية
        pool_reset_session=True,  # تنظيف الجلسة بعد كل استخدام لتكون جاهزة للمستخدم التالي
        **db_config
    )
except Exception as e:
    print(f"🔥 خطأ فادح في إنشاء مسبح الاتصالات: {e}")


def get_db_connection():
    """
    هذه الدالة لم تعد تنشئ اتصالاً من الصفر، بل تسحب اتصالاً جاهزاً من المسبح
    مما يسرع استجابة تطبيقات فلاتر بشكل خرافي!
    """
    return connection_pool.get_connection()