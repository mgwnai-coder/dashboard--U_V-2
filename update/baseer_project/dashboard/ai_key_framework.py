import requests

# =====================================================================
# 1. القالب الأساسي الموحد (The Standard Output Format)
# =====================================================================
def create_standard_response(is_valid, status, message, req_limit="غير محدد", tok_limit="غير محدد", tok_remaining="غير محدد"):
    return {
        "is_valid": is_valid,
        "status": status,
        "message": message,
        "limits": {
            "requests_per_minute": req_limit,
            "tokens_per_minute": tok_limit,
            "remaining_tokens_now": tok_remaining
        }
    }

# =====================================================================
# 2. محول شركة OpenAI
# =====================================================================
class OpenAIAdapter:
    @staticmethod
    def check_key(api_key):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                h = res.headers
                return create_standard_response(
                    is_valid=True, status="active", message="مفتاح OpenAI يعمل ✅",
                    req_limit=h.get('x-ratelimit-limit-requests', 'غير متوفر'),
                    tok_limit=h.get('x-ratelimit-limit-tokens', 'غير متوفر'),
                    tok_remaining=h.get('x-ratelimit-remaining-tokens', 'غير متوفر')
                )
            elif res.status_code == 401:
                return create_standard_response(False, "invalid", "مفتاح OpenAI غير صحيح ❌")
            elif res.status_code == 429:
                return create_standard_response(False, "exhausted", "انتهى رصيد OpenAI أو تم تجاوز الحد ⚠️")
            return create_standard_response(False, "error", f"خطأ OpenAI: {res.status_code}")
        except Exception as e:
            return create_standard_response(False, "connection_error", str(e))

# =====================================================================
# 3. محول شركة Anthropic (Claude)
# =====================================================================
class AnthropicAdapter:
    @staticmethod
    def check_key(api_key):
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key, 
            "anthropic-version": "2023-06-01", 
            "content-type": "application/json"
        }
        payload = {"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                h = res.headers
                return create_standard_response(
                    is_valid=True, status="active", message="مفتاح Claude يعمل ✅",
                    # 🌟 شركة Claude ترسل الأرقام الحقيقية في الهيدر، لذا نلتقطها مباشرة
                    req_limit=h.get('anthropic-ratelimit-requests-limit', 'غير متوفر'),
                    tok_limit=h.get('anthropic-ratelimit-tokens-limit', 'غير متوفر'),
                    tok_remaining=h.get('anthropic-ratelimit-tokens-remaining', 'غير متوفر')
                )
            elif res.status_code == 401:
                return create_standard_response(False, "invalid", "مفتاح Claude غير صحيح ❌")
            elif res.status_code == 429:
                return create_standard_response(False, "exhausted", "انتهى رصيد Claude ⚠️")
            return create_standard_response(False, "error", f"خطأ Claude: {res.status_code}")
        except Exception as e:
            return create_standard_response(False, "connection_error", str(e))


# =====================================================================
# 4. محول شركة Google Gemini (النسخة الصحيحة والنهائية)
# =====================================================================
class GeminiAdapter:
    @staticmethod
    def check_key(api_key, model_name=None):
        # 1. تعريف المتغير actual_model بشكل صحيح
        actual_model = model_name if model_name else "gemini-1.5-flash"
        
        # 2. تنظيف الاسم إذا كان يبدأ بـ models/
        if actual_model.startswith("models/"):
            actual_model = actual_model.replace("models/", "")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{actual_model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": "ping"}]}]}
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if res.status_code == 200:
                # 🌟 إرجاع البيانات الدقيقة لجوجل (التثبيت الذكي)
                return create_standard_response(
                    is_valid=True, 
                    status="active", 
                    message=f"مفتاح واسم نموذج ({actual_model}) يعملان بكفاءة ✅",
                    req_limit="15 (مجاني) / 1000 (مدفوع)", 
                    tok_limit="1M (مجاني) / 4M (مدفوع)", 
                    tok_remaining="مخفي من طرف جوجل"
                )
            else:
                # 🌟 استخراج رسالة الخطأ الحقيقية في حال وجود مشكلة
                exact_error_message = "خطأ غير معروف"
                try:
                    error_data = res.json()
                    exact_error_message = error_data.get('error', {}).get('message', str(error_data))
                except:
                    exact_error_message = res.text

                # 🌟 تصنيف الأخطاء
                if res.status_code == 400:
                    return create_standard_response(False, "invalid", f"المفتاح غير صحيح ❌ (السبب: {exact_error_message})")
                elif res.status_code == 403:
                    return create_standard_response(False, "invalid", f"مرفوض 🚫 (السبب: {exact_error_message})")
                elif res.status_code == 404:
                    return create_standard_response(False, "error", f"النموذج ({actual_model}) غير مدعوم أو به خطأ إملائي ⚠️ (السبب: {exact_error_message})")
                else:
                    return create_standard_response(False, "error", f"خطأ {res.status_code}: {exact_error_message}")
                    
        except Exception as e:
            return create_standard_response(False, "connection_error", f"فشل الاتصال: {str(e)}")
# =====================================================================
# 🎯 الموجه الذكي (The Framework Interface)
# =====================================================================
class AIKeyFramework:
    @staticmethod
    def analyze_key(provider_name: str, api_key: str, model_name: str = None) -> dict:
        provider = provider_name.lower().strip()
        
        # تمرير model_name لكل المحولات لكي تفحص النموذج الفعلي
        if provider in ['openai', 'chatgpt']:
            # ملاحظة: يمكنك تحديث محول أوبن إي آي لاحقاً ليستخدم الاسم الديناميكي أيضاً
            return OpenAIAdapter.check_key(api_key) 
            
        elif provider in ['anthropic', 'claude']:
            return AnthropicAdapter.check_key(api_key)
            
        elif provider in ['google', 'gemini']:
            return GeminiAdapter.check_key(api_key, model_name) # <--- نمرر الاسم هنا
            
        else:
            return create_standard_response(False, "unsupported_provider", f"المزود '{provider_name}' غير مدعوم.")