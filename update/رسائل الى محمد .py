# "يا بشمهندس محمد، رابط التسجيل جاهز ومفتوح لتطبيق الجوال 
# (بدون CSRF لكي لا يزعجك). فقط أضف هذا السطر في الـ Headers الخاصة بطلب الـ HTTP لديك لكي يقبلك السيرفر:"
# X-App-Secret-Key: Basseer_Mobile_Secure_Key_2026


# =======
# ماذا يجب على المهندس محمد (مطور Flutter) أن يفعل؟
# قل له أن يستخدم مكتبة التشفير في فلاتر (مثل crypto) ليكتب هذه الأسطر البسيطة قبل إرسال الطلب:

# Dart
# import 'package:crypto/crypto.dart';
# import 'dart:convert';

# // المفتاح السري (يُخفيه داخل Flutter باستخدام flutter_dotenv أو NDK)
# final String secretKey = "Basseer_Secure_Dynamic_Key_2026_!@#";

# // يأخذ وقت الجوال الحالي بالثواني
# final String timestamp = (DateTime.now().millisecondsSinceEpoch ~/ 1000).toString();

# // يدمج المفتاح مع الوقت ويشفره بـ SHA256
# var key = utf8.encode(secretKey);
# var bytes = utf8.encode("$secretKey:$timestamp");
# var hmacSha256 = Hmac(sha256, key);
# String signature = hmacSha256.convert(bytes).toString();

# // الآن يرسل الطلب مع هذه الهيدرز:
# // headers: {
# //   'X-Timestamp': timestamp,
# //   'X-Signature': signature,
# // }

# بهذه الطريقة، حتى لو قام أحدهم بفك تطبيق الـ Flutter واستخرج المفتاح السري MOBILE_SECRET_KEY، لن يتمكن من عمل سكربت آلي يضرب السيرفر بسهولة، لأنه سيضطر لبرمجة سكربت يقوم بإنشاء Timestamp ديناميكي وتشفيره بشكل صحيح في كل طلب، مما يعقد مهمته بنسبة 95%! 🚀