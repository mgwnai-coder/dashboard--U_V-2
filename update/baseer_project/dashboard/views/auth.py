from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django_ratelimit.decorators import ratelimit
from .utils import admin_required

# 🌟 دالة تسجيل الدخول (محمية بالأقفال الثلاثة) 🌟
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
@ratelimit(key='ip', rate='20/h', method='POST', block=False)
@ratelimit(key='ip', rate='50/d', method='POST', block=False)
def admin_login(request):
    # 🛡️ التحقق من الأقفال أولاً
    if getattr(request, 'limited', False):
        messages.error(request, '🚨 تم تجاوز الحد الأقصى لمحاولات الدخول! تم حظر عنوانك مؤقتاً لحماية النظام.')
        return render(request, 'dashboard/login.html')

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
                login(request, user)
                return redirect('dashboard_home')
            else:
                messages.error(request, 'اختراق مرفوض: لا تملك صلاحيات إدارية لدخول هذه البوابة.')
        else:
            messages.error(request, 'البريد الإلكتروني أو كلمة المرور غير صحيحة.')
            
    return render(request, 'dashboard/login.html')

# 🌟 دالة تسجيل الخروج 🌟
def admin_logout(request):
    logout(request) 
    return redirect('admin_login')

# 🌟 دالة الإعدادات (تغيير كلمة المرور) 🌟
@admin_required
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