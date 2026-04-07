# =========================
# Django Core Imports
# =========================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q, Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

# =========================
# Authentication
# =========================
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password

# =========================
# Security & Utilities
# =========================
from django.views.decorators.csrf import csrf_exempt
import json

# =========================
# Third-party Libraries
# =========================
import psutil

# =========================
# Local Models
# =========================
from .models import (
    User,
    DiagnosisSession,
    AIModel,
    DoctorProfile,
    Specialty,
    AdminNotification,
    SupportTicket,
    UserNotification,
)

# =================================================================
# 🛡️ الدرع الأمني: حماية المسارات للمدراء فقط (Server-Side Security) 🛡️
# =================================================================
def is_admin_user(user):
    """التحقق من أن المستخدم مسجل دخول وهو مدير أو سوبر يوزر"""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

# هذا المُزخرف سيتم وضعه قبل أي دالة لمنع الدخول غير المصرح به وطرد المتطفلين لصفحة تسجيل الدخول
admin_required = user_passes_test(is_admin_user, login_url='admin_login')


# 🌟 دالة تسجيل الدخول (محمية بصلاحيات الإدارة) 🌟
def admin_login(request):
    # إذا كان مسجل دخول كأدمن مسبقاً، وجهه للداشبورد مباشرة
    if request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_home')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # التأكد من صحة البيانات
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # التحقق من الصلاحيات (يجب أن يكون مدير)
            if user.role == 'admin' or user.is_superuser:
                login(request, user) # هنا يتم إنشاء الجلسة والكوكيز
                return redirect('dashboard_home')
            else:
                messages.error(request, 'اختراق مرفوض: لا تملك صلاحيات إدارية لدخول هذه البوابة.')
        else:
            messages.error(request, 'البريد الإلكتروني أو كلمة المرور غير صحيحة.')
            
    return render(request, 'dashboard/login.html')

# 🌟 دالة تسجيل الخروج (تدمير الكوكيز) 🌟
def admin_logout(request):
    logout(request) # هذه الدالة تدمر الجلسة وتمسح الكوكيز من متصفح المستخدم فوراً
    return redirect('admin_login')


@admin_required
def dashboard(request):
    # --- 1. الإحصائيات الأساسية (العد المباشر السريع وتوحيد الفلاتر) ---
    total_sessions = DiagnosisSession.objects.count()
    
    # حساب المرضى
    total_users = User.objects.filter(role='patient').count()
    
    # 🌟 التعديل هنا: جعل الحساب يعتمد على التوثيق فقط ليطابق صفحة الكادر الطبي بدقة
    total_doctors = DoctorProfile.objects.filter(is_verified=True).count()
    
    pending_requests = DoctorProfile.objects.filter(status='pending').count()
    open_tickets = SupportTicket.objects.filter(status='open').count()
    
    cpu_usage = int(psutil.cpu_percent(interval=None))
    ram_usage = int(psutil.virtual_memory().percent)
    recent_sessions = DiagnosisSession.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # تأكد أن التوزيع الديموغرافي يستخدم نفس المتغيرات الموحدة
    total_admins = User.objects.filter(is_superuser=True).count()
    demographic_labels = json.dumps(['أطباء', 'مرضى', 'إدارة'])
    demographic_values = json.dumps([total_doctors, total_users, total_admins])

    # =========================================================
    # 🌟 الحل السحري لتجاوز مشكلة (MySQL Timezones) 🌟
    # سنجلب التواريخ فقط (عملية خفيفة جداً) ونجمعها داخل بايثون
    # =========================================================
    all_sessions = DiagnosisSession.objects.values('id', 'created_at', 'doctor_id')
    
    current_year = timezone.now().year
    months_data = [0] * 12
    total_by_year_dict = {}
    interventions_by_year_dict = {}
    doctor_interventions = 0

    for session in all_sessions:
        date = session['created_at']
        if date:
            year = date.year
            month = date.month
            year_str = str(year)
            
            # 1. تجميع المخطط الشهري للعام الحالي
            if year == current_year:
                months_data[month - 1] += 1
            
            # 2. تجميع المخطط السنوي العام
            total_by_year_dict[year_str] = total_by_year_dict.get(year_str, 0) + 1
            
            # 3. حساب تدخلات الأطباء
            if session['doctor_id']:
                doctor_interventions += 1
                interventions_by_year_dict[year_str] = interventions_by_year_dict.get(year_str, 0) + 1

    doctor_intervention_rate = int((doctor_interventions / total_sessions) * 100) if total_sessions > 0 else 0 

    months_labels = json.dumps(['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'])
    monthly_sessions_values = json.dumps(months_data)
    sessions_this_year = sum(months_data)

    # ترتيب السنوات تصاعدياً للمخطط
    sorted_years = sorted(list(total_by_year_dict.keys()))
    if not sorted_years:
        sorted_years = [str(current_year)]
        total_by_year_dict[str(current_year)] = 0
        
    all_years_labels = sorted_years
    all_years_values = [total_by_year_dict[y] for y in sorted_years]

    intervention_rates_values = []
    for y in sorted_years:
        total_year = total_by_year_dict.get(y, 0)
        interventions_year = interventions_by_year_dict.get(y, 0)
        rate = int((interventions_year / total_year) * 100) if total_year > 0 else 0
        intervention_rates_values.append(rate)

    context = {
        'total_sessions': total_sessions,
        'total_doctors': total_doctors,
        'total_users': total_users,
        'pending_requests': pending_requests,
        'open_tickets': open_tickets,
        'doctor_intervention_rate': doctor_intervention_rate,
        'cpu_usage': cpu_usage,
        'ram_usage': ram_usage,
        'recent_sessions': recent_sessions,
        
        'demographic_labels': demographic_labels,
        'demographic_values': demographic_values,
        'months_labels': months_labels,
        'monthly_sessions_values': monthly_sessions_values,
        
        'current_year': current_year,
        'sessions_this_year': sessions_this_year,
        
        'all_years_labels': json.dumps(all_years_labels),
        'all_years_values': json.dumps(all_years_values),
        'intervention_years_labels': json.dumps(all_years_labels),
        'intervention_rates_values': json.dumps(intervention_rates_values),
    }
    return render(request, 'dashboard/dashboard.html', context)


# =================================================================
# 🌟🌟🌟 بداية التعديل لتسريع صفحة إدارة المستخدمين 🌟🌟🌟
# =================================================================
from django.db.models import Q
from django.core.paginator import Paginator

@admin_required
def users_management(request):
    # 1. التقاط المدخلات من الرابط (مربع البحث، الدور، الحالة)
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', 'all')
    status = request.GET.get('status', 'all')

    # 2. الاستعلام الأساسي (نجلب كل المستخدمين)
    users = User.objects.select_related('doctor_profile__specialty').all().order_by('-created_at')

    # ==========================================
    # 🌟 3. محرك الفلترة (الذي كان مفقوداً) 🌟
    # ==========================================
    # فلتر البحث النصي (يبحث في الاسم، الإيميل، أو رقم الهاتف)
    if query:
        users = users.filter(
            Q(full_name__icontains=query) | 
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    
    # فلتر الدور (مريض، طبيب، مدير)
    if role != 'all':
        users = users.filter(role=role)
    
    # فلتر الحالة (نشط، موقوف)
    if status != 'all':
        is_active = (status == 'active')
        users = users.filter(is_active=is_active)

    # ==========================================
    # 4. العدادات العلوية (تعرض إحصائيات المنصة)
    # ==========================================
    total_all = User.objects.count()
    total_patients = User.objects.filter(role='patient').count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_inactive = User.objects.filter(is_active=False).count()

    # 5. الترقيم (Pagination) - 10 مستخدمين في كل صفحة
    paginator = Paginator(users, 10) 
    page_number = request.GET.get('page') 
    page_obj = paginator.get_page(page_number) 

    # 6. إرسال البيانات للواجهة
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


@admin_required # 🛡️ تم تفعيل الدرع هنا
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

@admin_required # 🛡️ تم تفعيل الدرع هنا
def get_user_medical_record_ajax(request, user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM medical_records WHERE user_id = %s", [user_id])
        row = cursor.fetchone()
        
        if row:
            columns = [col[0] for col in cursor.description]
            record = dict(zip(columns, row))
            return JsonResponse({'status': 'success', 'data': record})
        
        return JsonResponse({'status': 'not_found'})


@admin_required # 🛡️ تم تفعيل الدرع هنا
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


@admin_required # 🛡️ تم تفعيل الدرع هنا
def ai_models_management(request):
    if request.method == 'POST':
        model_id = request.POST.get('model_id') 
        model_name = request.POST.get('model_name')
        version = request.POST.get('version', '')
        description = request.POST.get('description', '')
        provider = request.POST.get('provider', 'google')
        api_key = request.POST.get('api_key')
        api_base_url = request.POST.get('api_base_url', '')
        system_prompt = request.POST.get('system_prompt', '')
        temperature = float(request.POST.get('temperature', 0.2))
        top_p = float(request.POST.get('top_p', 0.95))
        max_tokens = int(request.POST.get('max_tokens', 2048))
        token_limit = int(request.POST.get('token_limit', 1000000))
        is_active = request.POST.get('is_active') == 'on'

        if model_id:
            model = AIModel.objects.get(id=model_id)
            model.model_name = model_name
            model.version = version
            model.description = description
            model.provider = provider
            
            if api_key:
                model.api_key = api_key
                
            model.api_base_url = api_base_url
            model.system_prompt = system_prompt
            model.temperature = temperature
            model.top_p = top_p
            model.max_tokens = max_tokens
            model.token_limit = token_limit
            model.is_active = is_active
            model.save()
            
            messages.success(request, f'تم تحديث إعدادات النموذج ({model_name}) بنجاح.')
            
        else:
            if not api_key:
                messages.error(request, 'عفواً، يجب إدخال مفتاح API عند إضافة نموذج جديد.')
                return redirect('ai_models_management')
                
            AIModel.objects.create(
                model_name=model_name, version=version, description=description,
                provider=provider, api_key=api_key, api_base_url=api_base_url,
                system_prompt=system_prompt, temperature=temperature, top_p=top_p,
                max_tokens=max_tokens, token_limit=token_limit, is_active=is_active
            )
            messages.success(request, f'تم إضافة محرك الذكاء ({model_name}) بنجاح.')

        return redirect('ai_models_management')

    ai_models = AIModel.objects.all().order_by('-id')
    context = {
        'ai_models': ai_models,
        'total_models': ai_models.count(),
    }
    return render(request, 'dashboard/ai_models.html', context)


@admin_required # 🛡️ تم تفعيل الدرع هنا
def diagnostic_sessions(request):
    sessions = DiagnosisSession.objects.select_related(
        'patient', 'doctor', 'ai'
    ).order_by('-created_at')
    
    doctor_id = request.GET.get('doctor_id')
    if doctor_id:
        sessions = sessions.filter(doctor_id=doctor_id)

    context = {
        'sessions': sessions,
        'total_sessions': sessions.count(),
        'pending_sessions': sessions.filter(status='pending').count(),
        'reviewed_sessions': sessions.filter(status='reviewed').count(),
        'completed_sessions': sessions.filter(status='completed').count(),
    }
    
    return render(request, 'dashboard/sessions.html', context)

@admin_required # 🛡️ تم تفعيل الدرع هنا
def session_detail(request, session_id):
    session = get_object_or_404(DiagnosisSession.objects.select_related('patient', 'doctor', 'ai'), id=session_id)
    return render(request, 'dashboard/session_detail.html', {'session': session})

@admin_required # 🛡️ تم تفعيل الدرع هنا
def doctor_notes_monitoring(request):
    notes_sessions = DiagnosisSession.objects.exclude(doctor_notes__isnull=True).exclude(doctor_notes__exact='').select_related('doctor', 'patient').order_by('-created_at')
    
    context = {
        'notes_sessions': notes_sessions,
        'total_notes': notes_sessions.count(),
    }
    return render(request, 'dashboard/doctor_notes.html', context)

@admin_required # 🛡️ تم تفعيل الدرع هنا
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

@admin_required # 🛡️ تم تفعيل الدرع هنا
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

@admin_required # 🛡️ تم تفعيل الدرع هنا
def mark_notification_read(request, notif_id):
    if request.method == 'POST':
        try:
            notif = AdminNotification.objects.get(id=notif_id, admin=request.user)
            notif.is_read = True
            notif.save()
            return JsonResponse({'status': 'success'})
        except AdminNotification.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=404)
    return JsonResponse({'status': 'invalid method'}, status=400)

# هذا المسار API مخصص لتطبيق الهاتف، لذلك نتركه مفتوحاً للاستقبال بـ @csrf_exempt
@csrf_exempt 
def doctor_register_api(request):
    if request.method == 'POST':
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

@admin_required # 🛡️ تم تفعيل الدرع هنا
def support_tickets_management(request):
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')

        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        old_status = ticket.status 
        
        ticket.status = new_status
        ticket.admin_notes = admin_notes
        ticket.save()

        if old_status != new_status or admin_notes:
            status_dict = dict(SupportTicket.STATUS_CHOICES)
            status_ar = status_dict.get(new_status, new_status)
            
            notif_message = f"تم تحديث حالة بلاغك إلى: {status_ar}."
            if admin_notes:
                notif_message += f"\nملاحظة الإدارة: {admin_notes}"

            UserNotification.objects.create(
                user=ticket.user,
                title=f"تحديث بخصوص البلاغ #{ticket.id}",
                message=notif_message
            )

        messages.success(request, f'تم تحديث البلاغ رقم #{ticket.id} وإرسال إشعار للمستخدم بنجاح.')
        return redirect('support_tickets_management')

    all_tickets = SupportTicket.objects.select_related('user').order_by('-created_at')
    
    context = {
        'tickets': all_tickets,
        'pending_count': all_tickets.filter(status='pending').count(),
        'in_progress_count': all_tickets.filter(status='in_progress').count(),
        'resolved_count': all_tickets.filter(status='resolved').count(),
    }
    return render(request, 'dashboard/support_tickets.html', context)

@admin_required # 🛡️ تم تفعيل الدرع هنا
def notifications_management(request):
    if request.method == 'POST':
        target = request.POST.get('target')
        title = request.POST.get('title')
        message = request.POST.get('message')

        users_to_notify = []
        if target == 'all':
            users_to_notify = User.objects.all()
        elif target == 'doctors':
            users_to_notify = User.objects.filter(role='doctor')
        elif target == 'patients':
            users_to_notify = User.objects.filter(role='patient')

        notifications = [
            UserNotification(user=u, title=title, message=message) for u in users_to_notify
        ]
        UserNotification.objects.bulk_create(notifications)

        messages.success(request, f'تم إرسال الإشعار إلى {len(users_to_notify)} مستخدم بنجاح!')
        return redirect('notifications_management')

    recent_notifications = UserNotification.objects.select_related('user').order_by('-created_at')[:50]
    
    context = {
        'recent_notifications': recent_notifications,
        'total_users': User.objects.count(),
    }
    return render(request, 'dashboard/notifications_management.html', context)

@admin_required # 🛡️ تم تفعيل الدرع هنا
def admin_settings(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'كلمة المرور الحالية غير صحيحة.')
        
        elif new_password != confirm_password:
            messages.error(request, 'كلمة المرور الجديدة غير متطابقة في الحقلين.')
            
        elif len(new_password) < 8:
            messages.error(request, 'كلمة المرور يجب أن تتكون من 8 أحرف على الأقل.')
            
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'تم تغيير كلمة المرور بنجاح!')
            return redirect('admin_settings')

    return render(request, 'dashboard/settings.html')

# 🌟 دوال صفحات الأخطاء المخصصة 🌟
def custom_404(request, exception):
    return render(request, 'dashboard/404.html', status=404)

def custom_500(request):
    return render(request, 'dashboard/500.html', status=500)

@admin_required # 🚨 تم تأمين هذه الدالة (كانت مفتوحة للجميع وتمثل ثغرة)
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
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    role=role,
                    password=make_password(password)
                )
                user.save()

            if role == 'doctor':
                DoctorProfile.objects.get_or_create(user=user)

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid method'}, status=405)

@admin_required # 🚨 تم تأمين هذه الدالة (كانت مفتوحة للجميع وتمثل ثغرة)
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