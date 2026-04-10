from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from dashboard.models import AIModel, DiagnosisSession
from .utils import admin_required

# 🌟 الاستيراد الصحيح للإطار الذكي من المجلد الرئيسي للتطبيق
from dashboard.ai_key_framework import AIKeyFramework 

# =================================================================
# 🤖 إدارة نماذج الذكاء الاصطناعي (AI Models)
# =================================================================
@admin_required
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

@admin_required
def check_ai_model_status(request, model_id):
    """فحص حالة المفتاح في الخلفية (AJAX)"""
    try:
        model = AIModel.objects.get(id=model_id)
        if not model.api_key:
            return JsonResponse({"is_valid": False, "status": "error", "message": "لا يوجد مفتاح API مسجل."})

        result = AIKeyFramework.analyze_key(
            provider_name=model.provider, 
            api_key=model.api_key,
            model_name=model.model_name
        )
        return JsonResponse(result)
        
    except AIModel.DoesNotExist:
        return JsonResponse({"is_valid": False, "status": "error", "message": "النموذج غير موجود."}, status=404)
    except Exception as e:
        return JsonResponse({"is_valid": False, "status": "error", "message": str(e)}, status=500)


# =================================================================
# 🔬 إدارة الجلسات التشخيصية وملاحظات الأطباء
# =================================================================
@admin_required
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

@admin_required
def session_detail(request, session_id):
    session = get_object_or_404(DiagnosisSession.objects.select_related('patient', 'doctor', 'ai'), id=session_id)
    return render(request, 'dashboard/session_detail.html', {'session': session})

@admin_required
def doctor_notes_monitoring(request):
    notes_sessions = DiagnosisSession.objects.exclude(doctor_notes__isnull=True).exclude(doctor_notes__exact='').select_related('doctor', 'patient').order_by('-created_at')
    
    context = {
        'notes_sessions': notes_sessions,
        'total_notes': notes_sessions.count(),
    }
    return render(request, 'dashboard/doctor_notes.html', context)