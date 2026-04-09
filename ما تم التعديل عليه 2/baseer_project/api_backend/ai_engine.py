
# import os
# from google import genai
# from google.genai import types

# # 1. إعداد المفتاح
# # هام: يفضل استخدام متغيرات البيئة، لكن يمكنك وضعه هنا مؤقتاً
# API_KEY = "AIzaSyC96XgjH20xM43-dGIIn40paYW6o5R7nZ0"

# def prepare_medical_prompt(medical_record, symptoms, pain_location, symptoms_duration):
#     """
#     دمج مكان الألم ومدة الأعراض في النص الطبي وتجهيز البرومبت
#     """
#     # التعامل مع البيانات بأمان لتجنب الأخطاء إذا كانت القيم فارغة
#     is_smoker = medical_record.get('is_smoker', False)
#     smoker_status = "مدخن" if is_smoker else "غير مدخن"
#     age = medical_record.get('age', 'غير معروف')
#     chronic = medical_record.get('chronic_diseases', 'لا يوجد')
#     meds = medical_record.get('medications', 'لا يوجد')
#     gender = medical_record.get('gender', 'غير معروف')
#     weight = medical_record.get('weight', 'غير معروف')

#     structured_prompt = f"""
# الدور
# أنت مساعد ذكاء اصطناعي طبي متخصص يعمل بمستوى طبيب مختص، يقدم تشخيصًا طبيًا دقيقًا اعتمادًا على الأعراض والمعطيات المدخلة فقط، وبأسلوب طبي مهني واضح ومختصر.

# القواعد العامة (Rules)
# الرد يكون سرديًا ومنظمًا.
# يُسمح بعنوان رئيسي واحد فقط في بداية الرد:
# التشخيص الطبي (للغة العربية)
# Medical Diagnosis (للغة الإنجليزية)

# التفسير الطبي يكون متوسط الطول ويبدأ به الرد مباشرة بعد العنوان.
# التشخيص يكون دقيقًا وليس مبدئيًا.
# النصائح الطبية تُكتب بنقاط (Bullet Points):
# لا تقل عن 3
# لا تزيد عن 5

# التنبيه الطبي يُكتب حصريًا بهذه الصيغة دون أي تعديل:
# هذا التشخيص مبدئي ولا يغني عن مراجعة طبيب مختص.

# المصطلحات الطبية تُكتب بالعربية مع المقابل الإنجليزي بين قوسين.
# اللغة:
# إدخال عربي → إخراج عربي
# إدخال إنجليزي → إخراج إنجليزي

# يُمنع تمامًا:
# المجاملات
# أي حديث خارج المجال الطبي
# ذكر عناوين فرعية مثل (التفسير الطبي، النصائح الطبية…)
# يتم تحويل التخصص الطبي تلقائيًا حسب نوع المرض.
# إذا لم يكن للمرض تخصص مطابق في القائمة، يتم تعيين: Other
# لا يتم ذكر أكثر من تخصص واحد.

# ترتيب السرد الإلزامي داخل الرد
# بعد العنوان الرئيسي فقط، يكون المحتوى بالترتيب التالي دون تسميات:
# التفسير الطبي (فقرة أو فقرتان متوسطتان)
# التشخيص الدقيق (جملة واضحة ومباشرة)
# النصائح الطبية (نقاط Bullet Points)
# يجب ذكر - التخصص الطبي: (اسم التخصص يكون فقط بالانجليزي) - بشكل إجباري 
# التنبيه الطبي (بالصيغة الثابتة فقط)

# قائمة التخصصات المعتمدة:
# Internal Medicine – الطب الباطني
# General Surgery – الجراحة العامة
# Pediatrics – طب الأطفال
# Obstetrics and Gynecology (OB/GYN) – طب النساء والتوليد
# Ophthalmology – طب العيون
# Cardiology – طب القلب
# Dermatology – طب الجلدية
# Orthopedics – جراحة العظام
# ENT – الأنف والأذن والحنجرة
# Neurology – طب الأعصاب
# Psychiatry – الطب النفسي
# Urology – طب المسالك البولية
# Radiology – طب الأشعة
# Anesthesiology – التخدير
# Emergency Medicine – طب الطوارئ
# Family Medicine – طب الأسرة

# ---
# 1. السجل المرضي:
# - العمر: {age} | الأمراض: {chronic}
# - التدخين: {smoker_status} | الأدوية: {meds}
# - الجنس: {gender} | الوزن: {weight}

# 2. تفاصيل الشكوى الحالية:
# - العرض الرئيسي: {symptoms}
# - مكان الألم بالتحديد: {pain_location}
# - متى بدأت هذه الأعراض: {symptoms_duration}
# ---
# المطلوب: تقديم تحليل دقيق للحالة بناءً على موقع الألم ومدته، مع ذكر التوصيات.
#     """
#     return structured_prompt

# def send_to_ai_model(prepared_text):
#     """
#     إرسال النص إلى Gemini باستخدام مكتبة google-genai الحديثة
#     """
#     try:
#         # 1. إنشاء العميل (Client)
#         # يتم تمرير المفتاح مباشرة هنا
#         client = genai.Client(api_key=API_KEY)
        
#         # 2. إرسال الطلب
#         # نستخدم gemini-2.0-flash لأنه النموذج القياسي الجديد والسريع
#         response = client.models.generate_content(
#             model="gemini-2.0-flash",
#             contents=prepared_text
#         )
        
#         # 3. التحقق من الاستجابة وإعادتها
#         if response.text:
#             return response.text
#         else:
#             return "عذراً، لم يتمكن الذكاء الاصطناعي من توليد إجابة."

#     except Exception as e:
#         # طباعة الخطأ في التيرمينال للمطور
#         print(f"Error connecting to Gemini: {e}")
#         return "عذراً، حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي."

# التعديل الجديد 

import os
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

  
# 🌟 استورد الموديل الخاص بك هنا (تأكد من استبدال 'your_app' باسم تطبيقك الفعلي الذي يحتوي على models.py)
from models import AIModel

def prepare_medical_prompt(medical_record, symptoms, pain_location, symptoms_duration, system_rules):
    """
    دمج القواعد القادمة من قاعدة البيانات مع بيانات المريض الحالية
    """
    is_smoker = medical_record.get('is_smoker', False)
    smoker_status = "مدخن" if is_smoker else "غير مدخن"
    age = medical_record.get('age', 'غير معروف')
    chronic = medical_record.get('chronic_diseases', 'لا يوجد')
    meds = medical_record.get('medications', 'لا يوجد')
    gender = medical_record.get('gender', 'غير معروف')
    weight = medical_record.get('weight', 'غير معروف')

    # دمج تعليمات النظام (system_rules) مع بيانات المريض
    structured_prompt = f"""
{system_rules}

---
1. السجل المرضي:
- العمر: {age} | الأمراض: {chronic}
- التدخين: {smoker_status} | الأدوية: {meds}
- الجنس: {gender} | الوزن: {weight}

2. تفاصيل الشكوى الحالية:
- العرض الرئيسي: {symptoms}
- مكان الألم بالتحديد: {pain_location}
- متى بدأت هذه الأعراض: {symptoms_duration}
---
المطلوب: تقديم تحليل دقيق للحالة بناءً على موقع الألم ومدته، مع ذكر التوصيات.
    """
    return structured_prompt

# def send_to_ai_model(db: Session, medical_record, symptoms, pain_location, symptoms_duration):
#     """
#     إرسال النص إلى الذكاء الاصطناعي باستخدام الإعدادات الديناميكية من قاعدة البيانات
#     """
#     try:
#         # 1. جلب النموذج "النشط حالياً" من قاعدة البيانات
#         # active_model = AIModel.objects.filter(is_active=True).first()
#         active_model = db.query(AIModel).filter(AIModel.is_active == True).first()
        
#         if not active_model or not active_model.api_key:
#             return "عذراً، لم يتم تفعيل أي نموذج ذكاء اصطناعي أو مفتاح الـ API مفقود في لوحة التحكم."
            
#         if active_model.tokens_remaining <= 0:
#             return "عذراً، لقد استنفدت المنصة الحد الأقصى المسموح به من التوكنز."

#         # 2. تجهيز النص الكامل باستخدام البرومبت المخزن في القاعدة
#         prepared_text = prepare_medical_prompt(
#             medical_record, symptoms, pain_location, symptoms_duration, active_model.system_prompt
#         )

#         # 3. فحص نوع المزود (حالياً الكود يدعم Google Gemini)
#         if active_model.provider.lower() == 'google':
            
#             # إنشاء العميل بالمفتاح المخزن في القاعدة
#             client = genai.Client(api_key=active_model.api_key)
            
#             # تجهيز إعدادات التوليد (Temperature, Top-P, Max Tokens)
#             config = types.GenerateContentConfig(
#                 temperature=active_model.temperature,
#                 top_p=active_model.top_p,
#                 max_output_tokens=active_model.max_tokens,
#             )
            
#             # إرسال الطلب
#             response = client.models.generate_content(
#                 model=active_model.model_name,
#                 contents=prepared_text,
#                 config=config
#             )
            
#             # 4. خصم التوكنز المستهلكة (عداد الاستهلاك)
#             if response.usage_metadata:
#                 used_tokens = response.usage_metadata.total_token_count
#                 active_model.tokens_used += used_tokens
#                 active_model.save()
            
#             # 5. إرجاع الرد
#             if response.text:
#                 return response.text
#             else:
#                 return "عذراً، لم يتمكن الذكاء الاصطناعي من توليد إجابة."
                
#         else:
#             return f"عذراً، مزود الخدمة '{active_model.provider}' غير مدعوم في الكود الحالي."

#     except Exception as e:
#         print(f"Error connecting to AI: {e}")
#         return "عذراً، حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي. يرجى مراجعة إعدادات الـ API."

def send_to_ai_model(db: Session, medical_record, symptoms, pain_location, symptoms_duration):
    """
    إرسال النص إلى الذكاء الاصطناعي باستخدام الإعدادات الديناميكية من قاعدة البيانات
    """
    try:
        # 1. جلب النموذج "النشط حالياً" من قاعدة البيانات
        active_model = db.query(AIModel).filter(AIModel.is_active == True).first()
        
        if not active_model or not active_model.api_key:
            return "عذراً، لم يتم تفعيل أي نموذج ذكاء اصطناعي أو مفتاح الـ API مفقود في لوحة التحكم."
            
        # 🌟 التعديل الأول: حساب التوكنز المتبقية برمجياً
        if (active_model.token_limit - active_model.tokens_used) <= 0:
            return "عذراً، لقد استنفدت المنصة الحد الأقصى المسموح به من التوكنز."

        # 2. تجهيز النص الكامل باستخدام البرومبت المخزن في القاعدة
        prepared_text = prepare_medical_prompt(
            medical_record, symptoms, pain_location, symptoms_duration, active_model.system_prompt
        )

        # 3. فحص نوع المزود (حالياً الكود يدعم Google Gemini)
        if active_model.provider.lower() == 'google':
            
            # إنشاء العميل بالمفتاح المخزن في القاعدة
            client = genai.Client(api_key=active_model.api_key)
            
            # تجهيز إعدادات التوليد (Temperature, Top-P, Max Tokens)
            config = types.GenerateContentConfig(
                temperature=active_model.temperature,
                top_p=active_model.top_p,
                max_output_tokens=active_model.max_tokens,
            )
            
            # إرسال الطلب
            response = client.models.generate_content(
                model=active_model.model_name,
                contents=prepared_text,
                config=config
            )
            
            # 4. خصم التوكنز المستهلكة (عداد الاستهلاك)
            if response.usage_metadata:
                used_tokens = response.usage_metadata.total_token_count
                active_model.tokens_used += used_tokens
                # 🌟 التعديل الثاني: الحفظ باستخدام SQLAlchemy بدلاً من Django
                db.commit()
                db.refresh(active_model)
            
            # 5. إرجاع الرد
            if response.text:
                return response.text
            else:
                return "عذراً، لم يتمكن الذكاء الاصطناعي من توليد إجابة."
                
        else:
            return f"عذراً، مزود الخدمة '{active_model.provider}' غير مدعوم في الكود الحالي."

    except Exception as e:
        print(f"Error connecting to AI: {e}")
        return "عذراً، حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي. يرجى مراجعة إعدادات الـ API."