from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings  # 🌟 التعديل 1: استيراد الإعدادات لجلب نموذج المستخدم بشكل آمن

# =================================================================
# 1. مدير المستخدمين (User Manager)
# =================================================================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('يجب إدخال البريد الإلكتروني')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

# =================================================================
# 2. النماذج الأساسية (Core Models)
# =================================================================
class Specialty(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم التخصص")

    class Meta:
        db_table = 'specialties'
        managed = False  
        
    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, max_length=191)
    phone = models.CharField(max_length=20, null=True, blank=True)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient', db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🌟 التعديل 2: استخدام النص 'Specialty' بدلاً من الكلاس مباشرة لتجنب التشابك
    specialty = models.ForeignKey(
        'Specialty', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='doctors',
        verbose_name="التخصص الطبي",
        db_column='specialty_id'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        managed = False  

    @property
    def specialty_name(self):
        try:
            if self.role == 'doctor' and hasattr(self, 'doctor_profile') and self.doctor_profile.specialty:
                return self.doctor_profile.specialty.name
        except Exception:
            pass
        return None  

class DoctorProfile(models.Model):
    # 🌟 التعديل 3: استخدام settings.AUTH_USER_MODEL في كل المفاتيح الأجنبية الخاصة بالمستخدمين
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True)
    
    license_img = models.CharField(max_length=255, null=True, blank=True)
    degree_img = models.CharField(max_length=255, null=True, blank=True)
    id_card_img = models.CharField(max_length=255, null=True, blank=True)
    selfie_with_id = models.CharField(max_length=255, null=True, blank=True)
    
    is_verified = models.BooleanField(default=False, db_index=True)
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('banned', 'محظور'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    class Meta:
        db_table = 'doctor_profiles'
        managed = False

# =================================================================
# 3. نماذج الذكاء الاصطناعي والجلسات (AI & Diagnosis Models)
# =================================================================
class AIModel(models.Model):
    model_name = models.CharField(max_length=100, verbose_name="اسم النموذج")
    version = models.CharField(max_length=50, null=True, blank=True, verbose_name="الإصدار")
    description = models.TextField(null=True, blank=True, verbose_name="الوصف")
    
    provider = models.CharField(max_length=50, default='google', verbose_name="مزود الخدمة")
    api_key = models.CharField(max_length=255, null=True, blank=True, verbose_name="مفتاح API")
    api_base_url = models.CharField(max_length=255, null=True, blank=True, verbose_name="الرابط الأساسي")
    is_active = models.BooleanField(default=False, verbose_name="نشط حالياً")
    
    system_prompt = models.TextField(null=True, blank=True, verbose_name="أمر التوجيه (System Prompt)")
    temperature = models.FloatField(default=0.2, verbose_name="مستوى الإبداع (Temperature)")
    top_p = models.FloatField(default=0.95, verbose_name="التحكم بالتنوع (Top-P)")
    max_tokens = models.IntegerField(default=1024, verbose_name="الحد الأقصى للرد")
    
    token_limit = models.BigIntegerField(default=1000000, verbose_name="الحد الأقصى المسموح للاستهلاك")
    tokens_used = models.BigIntegerField(default=0, verbose_name="إجمالي التوكنز المستهلكة")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ آخر تعديل")

    class Meta:
        db_table = 'ai_models'
        managed = False  
        verbose_name = "نموذج ذكاء اصطناعي"
        verbose_name_plural = "نماذج الذكاء الاصطناعي"

    def __str__(self):
        status = "[نشط]" if getattr(self, 'is_active', False) else "[غير نشط]"
        return f"{self.model_name} - {status}"

    @property
    def tokens_remaining(self):
        return max(0, getattr(self, 'token_limit', 1000000) - getattr(self, 'tokens_used', 0))

    def save(self, *args, **kwargs):
        if self.is_active:
            # 🌟 حماية إضافية: إيقاف باقي النماذج ما عدا النموذج الحالي الذي يتم حفظه
            AIModel.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super(AIModel, self).save(*args, **kwargs)

class DiagnosisSession(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    ai = models.ForeignKey('AIModel', on_delete=models.SET_NULL, null=True)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reviewed_sessions')
    symptoms = models.TextField(null=True, blank=True)
    pain_location = models.CharField(max_length=255, null=True, blank=True)
    symptoms_duration = models.CharField(max_length=255, null=True, blank=True)
    ai_diagnosis = models.TextField(null=True, blank=True)
    doctor_notes = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=50, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'diagnosis_sessions'
        managed = False  

# =================================================================
# 4. نماذج الدعم والتنبيهات (Support & Notifications Models)
# =================================================================
class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'جاري العمل عليها'),
        ('resolved', 'تم الحل'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at'] 
        managed = False  # 🌟 التعديل 4: تمت إضافتها لتوحيد قاعدة البيانات ومنع انهيار MySQL

class AdminNotification(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notifications')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='triggered_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_notifications'
        managed = False  

class UserNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_notifications'
        ordering = ['-created_at']
        managed = False  # 🌟 التعديل 4: تمت إضافتها لتتوافق مع باقي الجداول