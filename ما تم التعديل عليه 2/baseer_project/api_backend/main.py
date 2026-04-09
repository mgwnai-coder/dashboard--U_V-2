from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Request # 👈 مهم جداً لكي نعرف IP المستخدم
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import get_db, get_db_connection
from fastapi import FastAPI
from ai_engine import prepare_medical_prompt, send_to_ai_model
from passlib.hash import django_pbkdf2_sha256  
import feedparser
import re
import time 
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html

import os, uuid, shutil
from fastapi import UploadFile, File, Form

from models import (
    UserCreate, UserLogin, MedicalRecordCreate, DoctorVerificationSubmit, 
    DiagnosisSessionCreate, DoctorReview, SupportReportCreate
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import jwt
from datetime import datetime, timedelta

# =========================================================
# 🔐 إعدادات الحماية والتشفير (JWT Security)
# =========================================================
SECRET_KEY = "Baseer_Super_Secret_Key_Change_Me_In_Production_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7 

# الحارس الذي سيقوم بسحب التوكن من الهيدر (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login",auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="غير مصرح لك بالوصول، يرجى تسجيل الدخول",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
         raise credentials_exception
         
    try:
        # 1. فك تشفير التوكن (الكود الأصلي الخاص بك)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        role: str = payload.get("role")
        
        # ========================================================
        # 🌟 التعديل الجديد: فحص حالة الحساب الحية من قاعدة البيانات
        # ========================================================
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # نسأل قاعدة البيانات: هل هذا المستخدم لا يزال فعالاً (is_active=1)؟
            cursor.execute("SELECT is_active FROM users WHERE id = %s", (user_id,))
            user_record = cursor.fetchone()
            
            # إذا الحساب غير موجود أصلاً أو تم إيقافه (محظور) من الداشبورد
            if not user_record or not user_record.get('is_active'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, # نرسل كود 403
                    detail="BANNED_USER" # كلمة السر التي سيلتقطها تطبيق فلاتر
                )
        finally:
            cursor.close()
            conn.close()
        # ========================================================

        # إرجاع البيانات بنفس الشكل الذي تعتمد عليه باقي مساراتك تماماً
        return {"user_id": int(user_id), "role": role}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception
    
# =========================================================
# 🛡️ إعدادات حماية صفحة التوثيق (Docs Security)
# =========================================================
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    # 👈 ضع اسم المستخدم وكلمة المرور الخاصة بك هنا (للمبرمجين فقط)
    correct_username = secrets.compare_digest(credentials.username, "root@root")
    correct_password = secrets.compare_digest(credentials.password, "root123")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="كلمة المرور غير صحيحة",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# =========================================================
# 🌟 تجهيز لوحة توثيق الـ API (Swagger UI) للمبرمج محمد 🌟
# =========================================================
app = FastAPI(
    title="بصير API 🩺 (Secured)",
    description="""
    **مرحباً بك في واجهة برمجة تطبيقات (API) نظام بصير المحمية.**
    
    جميع المسارات الآن محمية بنظام (JWT). يجب تسجيل الدخول للحصول على Token لاستخدامه في باقي المسارات.
    """,
    version="1.0.0",
    docs_url=None,
    redoc_url="/redoc"
)

# =========================================================
# 🧱 الجدار الثالث: حماية المسارات (CORS Security)
# =========================================================
# 👈 القائمة البيضاء: ضع هنا فقط روابط المواقع المسموح لها بالتحدث مع السيرفر
ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",      # رابط الداشبورد الخاص بك (Django) أثناء التطوير
    "http://localhost:8000",      # رابط الداشبورد (شكل آخر)
    # "https://baseer-admin.com", # 👈 ترفع علامة التعليق وتضع رابط الداشبورد الحقيقي عند النشر
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, # 👈 استبدلنا النجمة [*] بالقائمة البيضاء
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"], # منعنا العمليات غير المعروفة
    allow_headers=["*"],
)
# 3. أضف هذا المسار الجديد في أي مكان لإنشاء صفحة سريعة لا تعلق
# 👈 لاحظ أننا أضفنا (username: str = Depends(get_current_username))
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )

# =========================================================
# 🛑 الجدار الرابع: مكافحة الاستنزاف (Rate Limiting)
# =========================================================
# إنشاء شرطي المرور الذي يراقب عن طريق الـ IP
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# =========================================================
#                    الدوال المساعدة (Helpers)
# =========================================================

def extract_specialty_from_ai(text):
    match = re.search(r"التخصص الطبي:\s*(.*)", text)
    if match:
        specialty = match.group(1).strip()
        specialty = specialty.split('.')[0].strip()
        return specialty
    return "Other"

def create_notification(cursor, user_id, title, message):
    sql = "INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)"
    cursor.execute(sql, (user_id, title, message))

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


# =========================================================
#                    نقاط الاتصال (Endpoints)
# =========================================================
# --- 1. المصادقة (Authentication) ---

@app.post("/register", tags=["المصادقة (Auth)"])
# 👈 وضعنا 3 أقفال: 5 في الدقيقة، 20 في الساعة، 50 في اليوم
@limiter.limit("5/minute;20/hour;50/day")
def register_user(request: Request, user: UserCreate): # 👈 أضفنا (request: Request) هنا
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        clean_role = user.role.lower().strip()
        hashed_password = django_pbkdf2_sha256.hash(user.password)

        sql = """INSERT INTO users (full_name, email, password, phone, country_id, role, is_active) 
                 VALUES (%s, %s, %s, %s, %s, %s, 1)"""
        cursor.execute(sql, (user.full_name, user.email, hashed_password, user.phone, user.country_id, clean_role))
        new_user_id = cursor.lastrowid
        
        conn.commit()
        return {"status": "success", "user_id": new_user_id, "message": "تم إنشاء الحساب بنجاح"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.post("/login", tags=["المصادقة (Auth)"])
# 👈 وضعنا 3 أقفال: 5 في الدقيقة، 20 في الساعة، 50 في اليوم
@limiter.limit("5/minute;20/hour;50/day") # 👈 أضفنا الشرطي هنا أيضاً لحماية تسجيل الدخول
def login_user(request: Request, login_data: UserLogin): # 👈 أضفنا (request: Request) هنا
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql_user = "SELECT id, full_name, email, password, role, is_active FROM users WHERE email = %s"
        cursor.execute(sql_user, (login_data.email,))
        user = cursor.fetchone()

        if not user or not django_pbkdf2_sha256.verify(login_data.password, user['password']):
            raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")
            
        if not user.get('is_active', True):
            raise HTTPException(status_code=403, detail="هذا الحساب موقوف من قبل الإدارة")

        specialty_id = None
        specialty_name = None

        if user['role'] == 'doctor':
            sql_specialty = """
                SELECT dp.specialty_id, s.name as specialty_name 
                FROM doctor_profiles dp
                LEFT JOIN specialties s ON dp.specialty_id = s.id
                WHERE dp.user_id = %s
            """
            cursor.execute(sql_specialty, (user['id'],))
            specialty_data = cursor.fetchone()
            
            if specialty_data:
                specialty_id = specialty_data['specialty_id']
                specialty_name = specialty_data['specialty_name']

        # 🌟 توليد التوكن الحقيقي المشفر بدلاً من التوكن الوهمي 🌟
        access_token = create_access_token(data={"sub": str(user['id']), "role": user['role']})

        return {
            "status": "success", "message": "تم تسجيل الدخول بنجاح", "id": user['id'],
            "user_id": user['id'], "full_name": user['full_name'], "email": user['email'],
            "role": user['role'], "department_id": specialty_id, "department_name": specialty_name, 
            "token": access_token  # 👈 إرسال التوكن الحقيقي هنا
        }
    except Exception as e:
        if type(e) is HTTPException: raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- 2. السجلات الطبية (Medical Records) ---

@app.post("/add_medical_record", tags=["السجل الطبي (Medical Records)"])
def add_medical_record(record: MedicalRecordCreate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # ==========================================
        # 🛡️ الجدار الداخلي: التحقق من الصلاحيات (IDOR)
        # ==========================================
        user_role = current_user.get('role')
        raw_id = current_user.get('id') or current_user.get('sub') or current_user.get('user_id')
        
        if raw_id is None:
            raise HTTPException(status_code=401, detail=f"خطأ في التوكن، البيانات المتاحة هي: {current_user}")
            
        current_id = int(raw_id)
        target_id = int(record.user_id)

        if user_role == 'patient' and current_id != target_id:
            raise HTTPException(status_code=403, detail="اختراق مرفوض: لا يمكنك إنشاء سجل طبي لمريض آخر.")
            
        elif user_role == 'doctor':
            check_session = "SELECT id FROM diagnosis_sessions WHERE doctor_id = %s AND patient_id = %s LIMIT 1"
            cursor.execute(check_session, (current_id, target_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="مرفوض: لا يمكنك إضافة بيانات لمريض ليس لديك جلسة تشخيص معه.")
        # ==========================================

        sql = """INSERT INTO medical_records 
                 (user_id, gender, age, weight, social_status, chronic_diseases, medications, 
                 uses_blood_thinners, blood_thinner_name, is_smoker, drinks_alcohol, uses_drugs, previous_tests_diagnoses) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            record.user_id, record.gender, record.age, record.weight, record.social_status,
            record.chronic_diseases, record.medications, record.uses_blood_thinners,
            record.blood_thinner_name, record.is_smoker, record.drinks_alcohol,
            record.uses_drugs, record.previous_tests_diagnoses
        ))
        conn.commit()
        return {"status": "success", "message": "تم حفظ السجل الطبي بنجاح"}
    except Exception as e:
        conn.rollback()
        if type(e) is HTTPException: raise e
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/medical_record/{user_id}", tags=["السجل الطبي (Medical Records)"])
def get_medical_record(user_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # ==========================================
        # 🛡️ الجدار الداخلي: التحقق من الصلاحيات (IDOR)
        # ==========================================
        user_role = current_user.get('role')
        raw_id = current_user.get('id') or current_user.get('sub') or current_user.get('user_id')
        
        if raw_id is None:
            raise HTTPException(status_code=401, detail=f"خطأ في التوكن، البيانات المتاحة هي: {current_user}")
            
        current_id = int(raw_id)

        if user_role == 'patient' and current_id != user_id:
            raise HTTPException(status_code=403, detail="اختراق مرفوض: لا يحق لك الاطلاع على السجلات الطبية لمرضى آخرين.")
            
        elif user_role == 'doctor':
            check_session = "SELECT id FROM diagnosis_sessions WHERE doctor_id = %s AND patient_id = %s LIMIT 1"
            cursor.execute(check_session, (current_id, user_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="مرفوض: لا يحق لك الاطلاع على هذا السجل لعدم وجود جلسة تشخيص بينك وبين هذا المريض.")
        # ==========================================

        cursor.execute("SELECT * FROM medical_records WHERE user_id = %s", (user_id,))
        record = cursor.fetchone()
        if record:
            return {"status": "success", "data": record}
        return {"status": "not_found", "message": "لا يوجد سجل طبي لهذا المستخدم"}
    except Exception as e:
        if type(e) is HTTPException: raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.put("/update_medical_record/{user_id}", tags=["السجل الطبي (Medical Records)"])
def update_medical_record(user_id: int, record: MedicalRecordCreate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # ==========================================
        # 🛡️ الجدار الداخلي: التحقق من الصلاحيات (IDOR)
        # ==========================================
        user_role = current_user.get('role')
        raw_id = current_user.get('id') or current_user.get('sub') or current_user.get('user_id')
        
        if raw_id is None:
            raise HTTPException(status_code=401, detail=f"خطأ في التوكن، البيانات المتاحة هي: {current_user}")
            
        current_id = int(raw_id)

        if user_role == 'patient' and current_id != user_id:
            raise HTTPException(status_code=403, detail="اختراق مرفوض: لا يحق لك تعديل السجلات الطبية لمرضى آخرين.")
            
        elif user_role == 'doctor':
            check_session = "SELECT id FROM diagnosis_sessions WHERE doctor_id = %s AND patient_id = %s LIMIT 1"
            cursor.execute(check_session, (current_id, user_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="مرفوض: لا يحق لك تعديل بيانات مريض ليس لديك جلسة تشخيص معه.")
        # ==========================================

        sql = """UPDATE medical_records 
                 SET gender=%s, age=%s, weight=%s, social_status=%s, 
                     chronic_diseases=%s, medications=%s, uses_blood_thinners=%s, 
                     blood_thinner_name=%s, is_smoker=%s, drinks_alcohol=%s, 
                     uses_drugs=%s, previous_tests_diagnoses=%s
                 WHERE user_id=%s"""
        cursor.execute(sql, (
            record.gender, record.age, record.weight, record.social_status,
            record.chronic_diseases, record.medications, record.uses_blood_thinners,
            record.blood_thinner_name, record.is_smoker, record.drinks_alcohol,
            record.uses_drugs, record.previous_tests_diagnoses, user_id
        ))
        conn.commit()
        return {"status": "success", "message": "تم تحديث السجل الطبي بنجاح"}
    except Exception as e:
        conn.rollback()
        if type(e) is HTTPException: raise e
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- 3. عمليات الذكاء الاصطناعي والجلسات (Diagnosis & AI) ---
@app.post("/create_diagnosis_session", tags=["التشخيص والذكاء الاصطناعي (AI Diagnosis)"])
def create_diagnosis_session(session: DiagnosisSessionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    conn_pre = get_db_connection()
    cursor_pre = conn_pre.cursor(dictionary=True)
    try:
        cursor_pre.execute("SELECT * FROM medical_records WHERE user_id = %s", (session.patient_id,))
        medical_record = cursor_pre.fetchone()
        
        cursor_pre.execute("SELECT id FROM ai_models LIMIT 1")
        ai_model_row = cursor_pre.fetchone()
        db_ai_id = ai_model_row['id'] if ai_model_row else None
    finally:
        cursor_pre.close()
        conn_pre.close() 

    try:
        ai_result = send_to_ai_model(
            db=db,
            medical_record=medical_record or {},
            symptoms=session.symptoms,
            pain_location=session.pain_location,
            symptoms_duration=session.symptoms_duration
        )
        extracted_dept_name = extract_specialty_from_ai(ai_result)
    except Exception as ai_e:
        raise HTTPException(status_code=500, detail=f"حدث خطأ في محرك الذكاء الاصطناعي: {str(ai_e)}")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM specialties WHERE name = %s", (extracted_dept_name,))
        specialty_row = cursor.fetchone()

        if specialty_row:
            detected_id = specialty_row['id']
        else:
            cursor.execute("INSERT INTO specialties (name) VALUES (%s)", (extracted_dept_name,))
            conn.commit()
            detected_id = cursor.lastrowid

        sql_session = """INSERT INTO diagnosis_sessions 
                         (patient_id, ai_id, symptoms, pain_location, symptoms_duration, 
                          department_id, ai_diagnosis, status) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(sql_session, (
            session.patient_id, db_ai_id, session.symptoms, 
            (session.pain_location[:250] if session.pain_location else None), 
            (session.symptoms_duration[:250] if session.symptoms_duration else None), 
            detected_id, ai_result, 'pending'
        ))
        new_id = cursor.lastrowid
        
        cursor.execute("SELECT user_id FROM doctor_profiles WHERE specialty_id = %s AND is_verified = 1", (detected_id,))
        doctors = cursor.fetchall()
        for doc in doctors:
            create_notification(cursor, doc['user_id'], "حالة جديدة", f"جلسة رقم {new_id} بانتظارك في تخصص {extracted_dept_name}")
        
        conn.commit()

        return {
            "status": "success", "session_id": new_id, 
            "department": extracted_dept_name, "ai_diagnosis": ai_result
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- 4. عمليات المرضى (Patient Views) ---
@app.get("/patient/sessions/{patient_id}", tags=["واجهة المرضى (Patient Views)"])
def get_patient_sessions(patient_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT ds.id as session_id, ds.symptoms, ds.ai_diagnosis, ds.status, 
                   ds.created_at, ds.doctor_notes, s.name as department_name
            FROM diagnosis_sessions ds
            LEFT JOIN specialties s ON ds.department_id = s.id
            WHERE ds.patient_id = %s ORDER BY ds.created_at DESC
        """
        cursor.execute(sql, (patient_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/case/details/{session_id}", tags=["واجهة المرضى (Patient Views)"])
def get_case_details(session_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql_session = """
            SELECT ds.*, u.full_name as patient_name 
            FROM diagnosis_sessions ds
            LEFT JOIN users u ON ds.patient_id = u.id
            WHERE ds.id = %s
        """
        cursor.execute(sql_session, (session_id,))
        session_data = cursor.fetchone()

        if not session_data:
            raise HTTPException(status_code=404, detail="الحالة غير موجودة")

        sql_notes = "SELECT * FROM doctor_notes WHERE session_id = %s ORDER BY created_at ASC"
        cursor.execute(sql_notes, (session_id,))
        session_data['notes'] = cursor.fetchall()
        
        return session_data
    finally:
        cursor.close()
        conn.close()

# --- 5. عمليات الأطباء (Doctor Views) ---
@app.post("/doctor/submit_verification", tags=["واجهة الأطباء (Doctor Views)"])
def submit_verification(data: DoctorVerificationSubmit, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql_profile = """INSERT INTO doctor_profiles 
                         (user_id, specialty_id, license_img, degree_img, id_card_img, selfie_with_id, is_verified, status) 
                         VALUES (%s, %s, %s, %s, %s, %s, 0, 'pending')"""
        cursor.execute(sql_profile, (
            data.doctor_id, data.specialty_id, data.license_img, 
            data.degree_img, data.id_card_img, data.selfie_with_id
        ))
        
        notify_title = "طلب انضمام جديد 👨‍⚕️"
        notify_message = f"يوجد طلب انضمام جديد من الطبيب رقم {data.doctor_id} بانتظار المراجعة والاعتماد."
        
        sql_notify = """
            INSERT INTO admin_notifications (title, message, admin_id, is_read, created_at) 
            SELECT %s, %s, id, 0, NOW() FROM users WHERE role = 'admin'
        """
        cursor.execute(sql_notify, (notify_title, notify_message))
        conn.commit()
        return {"status": "success", "message": "تم رفع ملفات التوثيق بنجاح وإشعار الإدارة"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/doctor/sessions/{department_id}", tags=["واجهة الأطباء (Doctor Views)"])
def get_doctor_sessions(department_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT ds.id as session_id, ds.patient_id, u.full_name as patient_name,
                   ds.symptoms, ds.ai_diagnosis, ds.status, ds.created_at, ds.doctor_notes, s.name as department_name
            FROM diagnosis_sessions ds
            LEFT JOIN specialties s ON ds.department_id = s.id
            LEFT JOIN users u ON ds.patient_id = u.id
            WHERE ds.department_id = %s ORDER BY ds.created_at DESC
        """
        cursor.execute(sql, (department_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.post("/doctor/add_review", tags=["واجهة الأطباء (Doctor Views)"])
def add_doctor_review(review: DoctorReview, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql_note_table = "INSERT INTO doctor_notes (session_id, doctor_id, note_content) VALUES (%s, %s, %s)"
        cursor.execute(sql_note_table, (review.session_id, review.doctor_id, review.doctor_notes))

        sql_update = "UPDATE diagnosis_sessions SET status = 'reviewed', doctor_id = %s, doctor_notes = %s WHERE id = %s"
        cursor.execute(sql_update, (review.doctor_id, review.doctor_notes, review.session_id))

        cursor.execute("SELECT patient_id FROM diagnosis_sessions WHERE id = %s", (review.session_id,))
        session_data = cursor.fetchone()
        
        if session_data:
            notification_msg = f"قام الطبيب بإضافة ملاحظاته على جلستك رقم {review.session_id}"
            create_notification(cursor, session_data['patient_id'], "تم تحديث تشخيصك", notification_msg)

        conn.commit()
        return {"status": "success", "message": "تم حفظ الملاحظات بنجاح"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/history/{doctor_id}", tags=["واجهة الأطباء (Doctor Views)"])
def get_doctor_history(doctor_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT dn.id as note_id, dn.session_id, dn.note_content, dn.created_at,
                   ds.ai_diagnosis, u.full_name as patient_name
            FROM doctor_notes dn
            JOIN diagnosis_sessions ds ON dn.session_id = ds.id
            JOIN users u ON ds.patient_id = u.id
            WHERE dn.doctor_id = %s ORDER BY dn.created_at DESC
        """
        cursor.execute(sql, (doctor_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

# --- 6. الإشعارات (Notifications) ---
@app.get("/notifications/{user_id}", tags=["الإشعارات (Notifications)"])
def get_notifications(user_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/doctor/pending_notifications/{department_id}", tags=["الإشعارات (Notifications)"])
def get_doctor_pending_notifications(department_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT ds.id as session_id, ds.patient_id, u.full_name as patient_name,
                   ds.ai_diagnosis, ds.created_at
            FROM diagnosis_sessions ds
            LEFT JOIN users u ON ds.patient_id = u.id
            WHERE ds.department_id = %s AND ds.status = 'pending'
            ORDER BY ds.created_at DESC
        """
        cursor.execute(sql, (department_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


# --- 7. عام ومقالات طبية (General & RSS) ---
rss_cache = {
    "data": [],
    "last_updated": 0
}
CACHE_DURATION_SECONDS = 3600

# مسار عام لا يحتاج إلى تسجيل دخول
@app.get("/articles", tags=["عام (General)"])
def get_medical_articles():
    global rss_cache
    current_time = time.time()

    if rss_cache["data"] and (current_time - rss_cache["last_updated"] < CACHE_DURATION_SECONDS):
        return rss_cache["data"]

    try:
        rss_url = "https://arabic.rt.com/rss/health/" 
        feed = feedparser.parse(rss_url)
        articles_for_flutter = []
        
        for i, entry in enumerate(feed.entries[:15]):
            summary_clean = clean_html(entry.description)
            if len(summary_clean) > 120: summary_clean = summary_clean[:120] + "..."
                
            image_url = ""
            if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                image_url = entry.enclosures[0].get('href', '')
            if not image_url:
                image_url = "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=500&auto=format&fit=crop"

            published_date = entry.published if hasattr(entry, 'published') else "تاريخ حديث"
            clean_date = published_date.split(',')[1].split()[0:3] if ',' in published_date else published_date.split()[:3]
            clean_date_str = " ".join(clean_date) if isinstance(clean_date, list) else clean_date

            articles_for_flutter.append({
                "id": i, "title": entry.title, "summary": summary_clean,
                "author": "مقال طبي", "date": clean_date_str,
                "image_url": image_url, "url": entry.link
            })
            
        rss_cache["data"] = articles_for_flutter
        rss_cache["last_updated"] = current_time
        
        return articles_for_flutter
    except Exception as e:
        if rss_cache["data"]:
            return rss_cache["data"]
        raise HTTPException(status_code=500, detail="تعذر جلب المقالات من المصدر الطبي")