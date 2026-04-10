from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from dashboard.models import User, DoctorProfile, Specialty, AdminNotification
import json
import hmac
import hashlib
import time
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings # لجلب المفتاح السري لو أردت
from .utils import admin_required
from django.conf import settings

# =================================================================
# 👥 إدارة المستخدمين (المرضى)
# =================================================================
@admin_required
def users_management(request):
    # التقاط المدخلات من الرابط (مربع البحث، الدور، الحالة)
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', 'all')
    status = request.GET.get('status', 'all')

    users = User.objects.select_related('doctor_profile__specialty').all().order_by('-created_at')

    # محرك الفلترة
    if query:
        users = users.filter(
            Q(full_name__icontains=query) | 
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    
    if role != 'all':
        users = users.filter(role=role)
    
    if status != 'all':
        is_active = (status == 'active')
        users = users.filter(is_active=is_active)

    # العدادات العلوية
    total_all = User.objects.count()
    total_patients = User.objects.filter(role='patient').count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_inactive = User.objects.filter(is_active=False).count()

    # الترقيم (Pagination)
    paginator = Paginator(users, 10) 
    page_number = request.GET.get('page') 
    page_obj = paginator.get_page(page_number) 

    context = {
        'users': page_obj, 
        'search_query': query,
        'selected_role': role,
        'selected_status': status,
        'total_all': total_all,
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_inactive': total_inactive,
    }
    return render(request, 'dashboard/users_management.html', context)


@admin_required
def toggle_user_status(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        
        if target_user == request.user:
            messages.error(request, 'لا يمكنك إيقاف حسابك الشخصي.')
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            
            status_text = "تفعيل" if target_user.is_active else "إيقاف"
            user_display_name = target_user.full_name or target_user.email
            messages.success(request, f'تم {status_text} حساب {user_display_name} بنجاح.')
            
    return redirect('users_management')


# =================================================================
# 🩺 إدارة الأطباء والكادر الطبي
# =================================================================
@admin_required
def doctors_management(request):
    doctors_profiles = DoctorProfile.objects.select_related('user', 'specialty').order_by('-user__created_at')
    
    search_query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'all')

    if search_query:
        doctors_profiles = doctors_profiles.filter(
            Q(user__full_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(specialty__name__icontains=search_query)
        )

    if selected_status == 'active':
        doctors_profiles = doctors_profiles.filter(user__is_active=True)
    elif selected_status == 'inactive':
        doctors_profiles = doctors_profiles.filter(user__is_active=False)

    specialties = Specialty.objects.all()
    total_verified = DoctorProfile.objects.filter(is_verified=True).count()
    active_doctors = DoctorProfile.objects.filter(is_verified=True, user__is_active=True).count()
    
    context = {
        'doctors': doctors_profiles,
        'specialties': specialties,
        'total_doctors': total_verified,
        'active_doctors': active_doctors,
        'search_query': search_query,      
        'selected_status': selected_status, 
    }
    return render(request, 'dashboard/doctors.html', context)


# =================================================================
# 🛡️ إدارة طلبات توثيق الأطباء (Verification)
# =================================================================
@admin_required
def verification_requests(request):
    all_profiles = DoctorProfile.objects.select_related('user', 'specialty').order_by('-id')
    
    pending_profiles = all_profiles.filter(status='pending')
    approved_profiles = all_profiles.filter(status='approved')
    rejected_profiles = all_profiles.filter(status='rejected')
    banned_profiles = all_profiles.filter(status='banned')
    
    context = {
        'pending_profiles': pending_profiles,
        'pending_count': pending_profiles.count(),
        'approved_profiles': approved_profiles,
        'approved_count': approved_profiles.count(),
        'rejected_profiles': rejected_profiles,
        'rejected_count': rejected_profiles.count(),
        'banned_profiles': banned_profiles,
        'banned_count': banned_profiles.count(),
    }
    return render(request, 'dashboard/verification_requests.html', context)


@admin_required
def process_verification(request):
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action') 
        reason = request.POST.get('rejection_reason', '')

        profile = get_object_or_404(DoctorProfile, id=profile_id)
        doctor_user = profile.user

        if action == 'approve':
            profile.status = 'approved'
            profile.is_verified = True
            profile.save()
            doctor_user.is_active = True
            doctor_user.save()
            AdminNotification.objects.create(admin=request.user, doctor=doctor_user, title="تم الاعتماد", message="تم اعتماد حسابك.")
            messages.success(request, f'تم اعتماد الطبيب {doctor_user.full_name} بنجاح.')
        
        elif action == 'reject':
            profile.status = 'rejected'
            profile.is_verified = False
            profile.save()
            doctor_user.is_active = False
            doctor_user.save()
            AdminNotification.objects.create(admin=request.user, doctor=doctor_user, title="تم الرفض", message=f"سبب الرفض: {reason}.")
            messages.error(request, f'تم رفض الطلب وإرسال السبب للطبيب {doctor_user.full_name}.')
            
        elif action == 'ban':
            profile.status = 'banned'
            profile.is_verified = False
            profile.save()
            doctor_user.is_active = False
            doctor_user.save()
            AdminNotification.objects.create(admin=request.user, doctor=doctor_user, title="حظر الحساب", message=f"تم حظر حسابك: {reason}.")
            messages.error(request, f'تم حظر الطبيب {doctor_user.full_name}.')
            
        elif action == 'unban' or action == 'unreject':
            profile.status = 'pending'
            profile.save()
            messages.success(request, f'تم إعادة فتح طلب الطبيب {doctor_user.full_name} للمراجعة.')

        return redirect('verification_requests')


# =================================================================
# ⚙️ دوال الـ API للحفظ (AJAX) 
# =================================================================
from django.contrib.auth.hashers import make_password

@admin_required
def save_user_api(request, user_id=None):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            full_name = data.get('full_name', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            role = data.get('role', 'patient')
            password = data.get('password', '')

            if user_id:
                user = User.objects.get(id=user_id)
                user.full_name = full_name
                user.email = email
                user.phone = phone
                user.role = role
                if password: 
                    user.password = make_password(password)
                user.save()
            else:
                user = User(
                    full_name=full_name, email=email, phone=phone,
                    role=role, password=make_password(password)
                )
                user.save()

            if role == 'doctor':
                DoctorProfile.objects.get_or_create(user=user)

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid method'}, status=405)


@admin_required
def save_doctor_api(request, profile_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile = DoctorProfile.objects.get(id=profile_id)
            user = profile.user
            
            if data.get('specialty_id'):
                specialty = Specialty.objects.get(id=data.get('specialty_id'))
                profile.specialty = specialty
            
            profile.is_verified = data.get('is_verified', False)
            profile.save()
            
            user.is_active = data.get('is_active', False)
            user.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@admin_required
def get_user_medical_record_ajax(request, user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM medical_records WHERE user_id = %s", [user_id])
        row = cursor.fetchone()
        
        if row:
            columns = [col[0] for col in cursor.description]
            record = dict(zip(columns, row))
            return JsonResponse({'status': 'success', 'data': record})
        
        return JsonResponse({'status': 'not_found'})
    


# =================================================================
# 📝 API تسجيل الأطباء الجدد (مخصص لتطبيق الجوال ومحمي بـ API Key)
# =================================================================

# =================================================================
# 📝 API تسجيل الأطباء الجدد (آمن ومحمي بـ HMAC)
# =================================================================
@csrf_exempt 
def doctor_register_api(request):
    if request.method == 'POST':
        # 1. جلب المفتاح السري من الإعدادات بأمان
        try:
            # نقوم بتسمية المتغير بنفس الاسم الذي يستخدمه كود التشفير بالأسفل
            MOBILE_SECRET_KEY = settings.MOBILE_SECRET_KEY
        except AttributeError:
            return JsonResponse({'status': 'error', 'message': 'إعدادات السيرفر غير مكتملة (Missing Key)'}, status=500)

        # 2. استلام الوقت والتوقيع المشفر من الجوال
        client_timestamp = request.headers.get('X-Timestamp')
        client_signature = request.headers.get('X-Signature')

        if not client_timestamp or not client_signature:
            return JsonResponse({'status': 'error', 'message': 'مرفوض: بيانات التحقق مفقودة'}, status=403)

        try:
            # 3. حماية ضد هجمات إعادة الإرسال (مهلة 60 ثانية)
            current_time = int(time.time())
            if abs(current_time - int(client_timestamp)) > 60:
                return JsonResponse({'status': 'error', 'message': 'مرفوض: انتهت صلاحية الطلب'}, status=403)

            # 4. التشفير والمقارنة (باستخدام المفتاح السري القادم من settings)
            message = f"{MOBILE_SECRET_KEY}:{client_timestamp}".encode('utf-8')
            expected_signature = hmac.new(MOBILE_SECRET_KEY.encode('utf-8'), message, hashlib.sha256).hexdigest()

            if not hmac.compare_digest(expected_signature, client_signature):
                return JsonResponse({'status': 'error', 'message': 'مرفوض: التوقيع غير صالح'}, status=403)
                
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'صيغة الوقت غير صالحة'}, status=400)

        # ==========================================
        # 🔥 إذا وصلنا إلى هنا، فالطلب آمن 100% 🔥
        # ==========================================
        try:
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            password = request.POST.get('password')
            specialty_id = request.POST.get('specialty_id')

            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'البريد الإلكتروني مسجل مسبقاً'}, status=400)

            doctor_user = User.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                password=make_password(password),
                role='doctor',
                is_active=False 
            )

            specialty = Specialty.objects.get(id=specialty_id) if specialty_id else None
            
            DoctorProfile.objects.create(
                user=doctor_user,
                specialty=specialty,
                license_img=request.FILES.get('license_img'),
                degree_img=request.FILES.get('degree_img'),
                id_card_img=request.FILES.get('id_card_img'),
                selfie_with_id=request.FILES.get('selfie_with_id'),
                status='pending',
                is_verified=False
            )

            return JsonResponse({
                'status': 'success', 
                'message': 'تم استلام طلبك بنجاح. يرجى الانتظار حتى تقوم الإدارة بمراجعة ملفاتك وتفعيل حسابك.'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'يجب إرسال البيانات كـ POST request'}, status=405)