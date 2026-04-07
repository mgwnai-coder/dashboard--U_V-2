from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, get_db_connection
from fastapi import FastAPI, HTTPException
from ai_engine import prepare_medical_prompt, send_to_ai_model
from passlib.hash import django_pbkdf2_sha256  
import feedparser
import re
import time 
from database import get_db

import os, uuid, shutil
from fastapi import UploadFile, File, Form, HTTPException

from models import (
    UserCreate, UserLogin, MedicalRecordCreate, DoctorVerificationSubmit, 
    DiagnosisSessionCreate, DoctorReview, SupportReportCreate
)
from fastapi.middleware.cors import CORSMiddleware

# =========================================================
# 🌟 تجهيز لوحة توثيق الـ API (Swagger UI) للمبرمج يوسف 🌟
# =========================================================
app = FastAPI(
    title="بصير API 🩺",
    description="""
    **مرحباً بك في واجهة برمجة تطبيقات (API) نظام بصير.**
    
    هذا التوثيق مصمم لمبرمجي الواجهات الأمامية (تطبيقات فلاتر). 
    يمكنك هنا اختبار جميع المسارات (Endpoints)، معرفة البيانات المطلوبة (Request Body)، والاطلاع على شكل الردود (Responses).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
@app.post("/register", tags=["المصادقة (Auth)"], summary="تسجيل مستخدم جديد", description="إنشاء حساب جديد في النظام (كمريض). سيتم تشفير كلمة المرور وتفعيل الحساب مباشرة.")
def register_user(user: UserCreate):
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

@app.post("/login", tags=["المصادقة (Auth)"], summary="تسجيل الدخول", description="تسجيل الدخول للمرضى والأطباء. يعيد بيانات المستخدم الأساسية بالإضافة إلى ID التخصص إذا كان المستخدم طبيباً.")
def login_user(login_data: UserLogin):
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

        dummy_token = f"baseer-token-{user['id']}"

        return {
            "status": "success", "message": "تم تسجيل الدخول بنجاح", "id": user['id'],
            "user_id": user['id'], "full_name": user['full_name'], "email": user['email'],
            "role": user['role'], "department_id": specialty_id, "department_name": specialty_name, 
            "token": dummy_token
        }
    except Exception as e:
        if type(e) is HTTPException: raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- 2. السجلات الطبية (Medical Records) ---
@app.post("/add_medical_record", tags=["السجل الطبي (Medical Records)"], summary="إنشاء سجل طبي", description="إنشاء السجل الطبي الأولي للمريض (الوزن، العمر، الأمراض المزمنة...). يجب التأكد من عدم وجود سجل سابق قبل الاستدعاء.")
def add_medical_record(record: MedicalRecordCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/medical_record/{user_id}", tags=["السجل الطبي (Medical Records)"], summary="جلب السجل الطبي", description="جلب بيانات السجل الطبي الكامل لمريض معين عن طريق الـ User ID الخاص به.")
def get_medical_record(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM medical_records WHERE user_id = %s", (user_id,))
        record = cursor.fetchone()
        if record:
            return {"status": "success", "data": record}
        return {"status": "not_found", "message": "لا يوجد سجل طبي لهذا المستخدم"}
    finally:
        cursor.close()
        conn.close()

@app.put("/update_medical_record/{user_id}", tags=["السجل الطبي (Medical Records)"], summary="تحديث السجل الطبي", description="تحديث بيانات سجل طبي موجود مسبقاً.")
def update_medical_record(user_id: int, record: MedicalRecordCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- 3. عمليات الذكاء الاصطناعي والجلسات (Diagnosis & AI) ---
@app.post("/create_diagnosis_session", tags=["التشخيص والذكاء الاصطناعي (AI Diagnosis)"], summary="بدء جلسة تشخيص جديدة", description="يرسل الأعراض للذكاء الاصطناعي، يحللها، يحدد التخصص، ينشئ الجلسة، ويرسل إشعاراً لأطباء التخصص المعني.")
def create_diagnosis_session(session: DiagnosisSessionCreate, db: Session = Depends(get_db)):
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
@app.get("/patient/sessions/{patient_id}", tags=["واجهة المرضى (Patient Views)"], summary="جلب جلسات المريض", description="يجلب تاريخ جميع الجلسات (السابقة والمعلقة) الخاصة بمريض معين مرتبة من الأحدث للأقدم.")
def get_patient_sessions(patient_id: int):
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

@app.get("/case/details/{session_id}", tags=["واجهة المرضى (Patient Views)"], summary="جلب تفاصيل جلسة محددة", description="يجلب كل تفاصيل الجلسة (الأعراض، رد الذكاء الاصطناعي، وملاحظات الطبيب إن وجدت).")
def get_case_details(session_id: int):
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
@app.post("/doctor/submit_verification", tags=["واجهة الأطباء (Doctor Views)"], summary="رفع وثائق التوثيق للطبيب", description="مسار مخصص لتطبيق الهاتف يتيح للطبيب رفع صوره وشهاداته الطبية ليتم مراجعتها من قبل الإدارة.")
def submit_verification(data: DoctorVerificationSubmit):
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

@app.get("/doctor/sessions/{department_id}", tags=["واجهة الأطباء (Doctor Views)"], summary="جلب الجلسات المعلقة للتخصص", description="يجلب جميع الجلسات المفتوحة التي تخص تخصص طبيب معين لكي يقوم بمراجعتها.")
def get_doctor_sessions(department_id: int):
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

@app.post("/doctor/add_review", tags=["واجهة الأطباء (Doctor Views)"], summary="إضافة تشخيص وملاحظات الطبيب", description="يستخدمه الطبيب لإضافة ملاحظاته الطبية على جلسة المريض، وتغيير حالة الجلسة إلى (مُراجعة).")
def add_doctor_review(review: DoctorReview):
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

@app.get("/history/{doctor_id}", tags=["واجهة الأطباء (Doctor Views)"], summary="سجل الطبيب الخاص", description="يجلب تاريخ الحالات التي قام هذا الطبيب بمراجعتها والرد عليها مسبقاً.")
def get_doctor_history(doctor_id: int):
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
@app.get("/notifications/{user_id}", tags=["الإشعارات (Notifications)"], summary="جلب إشعارات المستخدم", description="يجلب قائمة الإشعارات الخاصة بمستخدم معين (طبيب أو مريض).")
def get_notifications(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/doctor/pending_notifications/{department_id}", tags=["الإشعارات (Notifications)"], summary="جلب إشعارات التخصص", description="يجلب إشعارات الحالات الجديدة (المعلقة) في تخصص معين لتنبيه الأطباء المتواجدين.")
def get_doctor_pending_notifications(department_id: int):
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

@app.get("/articles", tags=["عام (General)"], summary="جلب المقالات الطبية", description="يجلب أحدث 15 مقال طبي من موقع روسيا اليوم (RT). الرد يتم كاشته لمدة ساعة لضمان أقصى سرعة لتطبيق الهاتف.")
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