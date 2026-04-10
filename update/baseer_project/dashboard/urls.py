from django.urls import path
from . import views
from django.shortcuts import render # للاختبار 404 و500 
from django.conf.urls import handler404, handler500
from . import api_views # استدعاء ملف الـ API 

urlpatterns = [
    # 🌟 التعديل هنا: استخدام views.dashboard_home 🌟
    path('', views.dashboard, name='dashboard_home'),
    path('users/', views.users_management, name='users_management'),
    path('doctors/', views.doctors_management, name='doctors_management'),
    path('models/', views.ai_models_management, name='ai_models_management'),

    # 🌟 التعديل هنا: المسار الجديد لفحص حالة المفتاح (AJAX) 🌟
    path('models/check-status/<int:model_id>/', views.check_ai_model_status, name='check_ai_model_status'),
    # =======================================================
    
    path('sessions/', views.diagnostic_sessions, name='diagnostic_sessions'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('doctor-notes/', views.doctor_notes_monitoring, name='doctor_notes_monitoring'),
    
    path('verifications/', views.verification_requests, name='verification_requests'),
    path('verifications/process/', views.process_verification, name='process_verification'),

    # مسارات تطبيق الهاتف (APIs) 
    path('api/specialties/', api_views.get_specialties_api, name='api_specialties'),
    path('api/doctor/register/', api_views.doctor_register_api, name='api_doctor_register'),
    path('api/doctor/sessions/pending/', api_views.doctor_pending_sessions_api, name='api_doctor_pending_sessions'),

    path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('support/', views.support_tickets_management, name='support_tickets_management'),
    path('notifications/manage/', views.notifications_management, name='notifications_management'),
    path('users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # 🌟 مسارات الدخول والخروج 🌟
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    path('settings/', views.admin_settings, name='admin_settings'),

    # 🌟 روابط مؤقتة لاختبار صفحات الأخطاء (احذفها لاحقاً قبل رفع المشروع) 🌟
    path('test-404/', lambda request: render(request, 'dashboard/404.html')),
    path('test-500/', lambda request: render(request, 'dashboard/500.html')),

    # مسارات الـ API الخاصة بإضافة وتعديل المستخدمين (التي ينتظرها الجافاسكريبت)
    path('users/add/', views.save_user_api, name='api_add_user'),
    path('users/edit/<int:user_id>/', views.save_user_api, name='api_edit_user'),

    path('doctors/add/', views.save_doctor_api, name='api_add_doctor'),
    path('doctors/edit/<int:profile_id>/', views.save_doctor_api, name='api_edit_doctor'),

    path('users/<int:user_id>/medical-record/', views.get_user_medical_record_ajax, name='get_medical_record_ajax'),

]
handler404 = 'dashboard.views.custom_404'
handler500 = 'dashboard.views.custom_500'