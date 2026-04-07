سوي هذا الاستعلام على قاعدة البيانات عندك
=
ALTER TABLE users ADD INDEX (role);
ALTER TABLE users ADD INDEX (is_active);
ALTER TABLE diagnosis_sessions ADD INDEX (status);
ALTER TABLE diagnosis_sessions ADD INDEX (created_at);
ALTER TABLE doctor_profiles ADD INDEX (status);
ALTER TABLE doctor_profiles ADD INDEX (is_verified);
ALTER TABLE support_tickets ADD INDEX (status);
ALTER TABLE support_tickets ADD INDEX (created_at);
=

انسح الملف كامل و سوي استبدال الى في حال كان في معك في احد هذي المللفات تعديل 
1
\baseer_project\api_backend\database.py
\baseer_project\api_backend\main.py
\baseer_project\api_backend\ai_engine.py
2
\baseer_project\baseer_project\settings.py
3
\baseer_project\dashboard\models.py
\baseer_project\dashboard\urls.py
\baseer_project\dashboard\views.py
4
\baseer_project\templates\dashboard\dashboard.html
\baseer_project\templates\dashboard\session_detail.html
\baseer_project\templates\dashboard\users_management.html
\baseer_project\templates\dashboard\base.html
4.5
\baseer_project\templates\dashboard\components\chart_card.html
======================
اقرا هذا الملف 
Optimization_Guide.md.py
