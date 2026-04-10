from django.test import TestCase, Client
from django.urls import reverse
from dashboard.models import User

class DashboardRoutingTests(TestCase):
    def setUp(self):
        # 1. تهيئة بيئة الاختبار وإنشاء مدير وهمي
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='testadmin@basser.com',
            password='TestPassword123!',
            full_name='Test Admin'
        )

    def test_all_main_pages_load_successfully(self):
        # 2. تسجيل الدخول نيابة عنك
        self.client.login(username='testadmin@basser.com', password='TestPassword123!')

        # 3. أسماء الصفحات الرئيسية في ملف urls.py (التي استخدمناها في الـ HTML)
        url_names_to_check = [
            'dashboard_home',
            'users_management',
            'doctors_management',
            'ai_models_management',
            'diagnostic_sessions',
            'support_tickets_management',
            'notifications_management'
        ]

        # 4. الروبوت يختبر كل صفحة
        for url_name in url_names_to_check:
            try:
                # تحويل الاسم إلى رابط حقيقي
                url = reverse(url_name)
                # زيارة الرابط
                response = self.client.get(url)
                
                # التحقق من أن الصفحة تعمل بنجاح (الكود 200 يعني OK)
                self.assertEqual(response.status_code, 200, f"🚨 حدث خطأ (Status: {response.status_code}) عند فتح صفحة: {url_name}")
                
            except Exception as e:
                self.fail(f"🚨 المسار غير موجود أو انهار الكود في صفحة '{url_name}': {str(e)}")