from django.urls import path
from django.shortcuts import render
from django.conf.urls import handler404, handler500
from . import views
from . import api_views  # ملف واجهات الموبايل المستقل

# =================================================================
# 🗺️ خريطة روابط لوحة تحكم بصير (Dashboard URLs)
# =================================================================

urlpatterns = [
    # ---------------------------------------------------------
    # 🔐 1. مسارات المصادقة والإعدادات (Auth & Settings)
    # ---------------------------------------------------------
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('settings/', views.admin_settings, name='admin_settings'),

    # ---------------------------------------------------------
    # 🏠 2. اللوحة الرئيسية (Main Dashboard)
    # ---------------------------------------------------------
    path('', views.dashboard, name='dashboard_home'),

    # ---------------------------------------------------------
    # 👥 3. إدارة المستخدمين (Users Management)
    # ---------------------------------------------------------
    path('users/', views.users_management, name='users_management'),
    path('users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # ---------------------------------------------------------
    # 🩺 4. إدارة الأطباء والتوثيقات (Doctors & Verifications)
    # ---------------------------------------------------------
    path('doctors/', views.doctors_management, name='doctors_management'),
    path('verifications/', views.verification_requests, name='verification_requests'),
    path('verifications/process/', views.process_verification, name='process_verification'),

    # ---------------------------------------------------------
    # 🧠 5. إدارة الذكاء الاصطناعي (AI Models)
    # ---------------------------------------------------------
    path('models/', views.ai_models_management, name='ai_models_management'),
    path('models/check-status/<int:model_id>/', views.check_ai_model_status, name='check_ai_model_status'),

    # ---------------------------------------------------------
    # 📊 6. جلسات التشخيص والمراقبة (Diagnosis Sessions)
    # ---------------------------------------------------------
    path('sessions/', views.diagnostic_sessions, name='diagnostic_sessions'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('doctor-notes/', views.doctor_notes_monitoring, name='doctor_notes_monitoring'),

    # ---------------------------------------------------------
    # 🛎️ 7. الدعم الفني والتنبيهات (Support & Notifications)
    # ---------------------------------------------------------
    path('support/', views.support_tickets_management, name='support_tickets_management'),
    path('notifications/manage/', views.notifications_management, name='notifications_management'),
    path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),

    # =================================================================
    # 🌐 مسارات الـ API (Internal & External)
    # =================================================================

    # 🔄 أ. APIs داخلية (تستخدمها لوحة التحكم عبر AJAX)
    path('users/add/', views.save_user_api, name='api_add_user'),
    path('users/edit/<int:user_id>/', views.save_user_api, name='api_edit_user'),
    path('users/<int:user_id>/medical-record/', views.get_user_medical_record_ajax, name='get_medical_record_ajax'),
    
    path('doctors/add/', views.save_doctor_api, name='api_add_doctor'),
    path('doctors/edit/<int:profile_id>/', views.save_doctor_api, name='api_edit_doctor'),

    # 📱 ب. APIs خارجية (مخصصة لتطبيق الهاتف - Flutter)
    path('api/specialties/', api_views.get_specialties_api, name='api_specialties'),
    path('api/doctor/register/', api_views.doctor_register_api, name='api_doctor_register'),
    path('api/doctor/sessions/pending/', api_views.doctor_pending_sessions_api, name='api_doctor_pending_sessions'),

    # =================================================================
    # 🚨 مسارات مؤقتة لاختبار صفحات الخطأ (تُحذف قبل الإطلاق)
    # =================================================================
    path('test-404/', lambda request: render(request, 'dashboard/404.html')),
    path('test-500/', lambda request: render(request, 'dashboard/500.html')),
]

# =================================================================
# 🛑 معالجات الأخطاء المخصصة (Custom Error Handlers)
# =================================================================
handler404 = 'dashboard.views.custom_404'
handler500 = 'dashboard.views.custom_500'