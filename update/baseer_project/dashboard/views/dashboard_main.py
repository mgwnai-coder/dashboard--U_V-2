import json
import psutil
from django.shortcuts import render
from django.utils import timezone
from dashboard.models import User, DoctorProfile, DiagnosisSession, SupportTicket
from .utils import admin_required

# =================================================================
# 🏠 اللوحة الرئيسية (الإحصائيات والرسوم البيانية المتقدمة)
# =================================================================
@admin_required
def dashboard(request):
    # --- 1. الإحصائيات الأساسية (العد المباشر السريع وتوحيد الفلاتر) ---
    total_sessions = DiagnosisSession.objects.count()
    
    # حساب المرضى
    total_users = User.objects.filter(role='patient').count()
    
    # 🌟 الحساب يعتمد على التوثيق فقط ليطابق صفحة الكادر الطبي بدقة
    total_doctors = DoctorProfile.objects.filter(is_verified=True).count()
    
    pending_requests = DoctorProfile.objects.filter(status='pending').count()
    
    # إذا كان لديك حقل status في SupportTicket، استخدمه. إذا كان الحقل مختلفاً، عدله بما يتناسب مع المودل.
    open_tickets = SupportTicket.objects.filter(status='pending').count() 
    
    cpu_usage = int(psutil.cpu_percent(interval=None))
    ram_usage = int(psutil.virtual_memory().percent)
    recent_sessions = DiagnosisSession.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # تأكد أن التوزيع الديموغرافي يستخدم نفس المتغيرات الموحدة
    total_admins = User.objects.filter(is_superuser=True).count()
    demographic_labels = json.dumps(['أطباء', 'مرضى', 'إدارة'])
    demographic_values = json.dumps([total_doctors, total_users, total_admins])

    # =========================================================
    # 🌟 الحل السحري لتجاوز مشكلة (MySQL Timezones) 🌟
    # جلب التواريخ فقط (عملية خفيفة جداً) وجمعها داخل بايثون
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
    
    # تأكدنا هنا أن الرابط يشير لاسم القالب الصحيح
    return render(request, 'dashboard/dashboard.html', context)


# =================================================================
# 🚨 صفحات الخطأ المخصصة (404 و 500)
# =================================================================
def custom_404(request, exception):
    return render(request, 'dashboard/404.html', status=404)

def custom_500(request):
    return render(request, 'dashboard/500.html', status=500)