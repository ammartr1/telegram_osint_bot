# config.py
# BLACK OPEN SYSTEM - OSINT BOT CONFIGURATION

import os

# TOKEN من BotFather
BOT_TOKEN = "8808843672:AAGKN0k52tXzTQDzSOtw_okhwI4BXPA9uK8"

# معرف المستخدم المسموح له فقط (whitelist)
# ضع معرف حسابك هنا - استخدم @userinfobot لمعرفة معرفك
OWNER_USER_ID = 2140385904  # غيّر هذا إلى معرفك

# API Keys مجانية
GROQ_API_KEY = "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"  # من console.groq.com
GEMINI_API_KEY = "AIzaSyDDBqVpc7eZ4e8Wz2z0sxHUAZ_7yHpO2aQ"  # من makersuite.google.com

# وكيل للطلبات (اختياري للاختبار)
PROXY = None  # مثال: {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}

# مسارات الملفات
SESSION_FILE = "session_data.json"
BREACH_DB_PATH = "breach_data.json"
