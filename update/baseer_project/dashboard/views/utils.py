from django.contrib.auth.decorators import user_passes_test

# =================================================================
# 🛡️ الدرع الأمني: حماية المسارات للمدراء فقط (Server-Side Security) 🛡️
# =================================================================

def is_admin_user(user):
    """التحقق من أن المستخدم مسجل دخول وهو مدير أو سوبر يوزر"""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

# هذا المُزخرف سيتم استيراده في باقي الملفات لحماية الدوال
admin_required = user_passes_test(is_admin_user, login_url='admin_login')