# config.py
# BLACK OPEN SYSTEM - OSINT BOT CONFIGURATION

import os

# TOKEN من BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# معرف المستخدم المسموح له فقط (whitelist)
# ضع معرف حسابك هنا - استخدم @userinfobot لمعرفة معرفك
OWNER_USER_ID = 123456789  # غيّر هذا إلى معرفك

# API Keys مجانية
GROQ_API_KEY = "YOUR_GROQ_API_KEY"  # من console.groq.com
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # من makersuite.google.com

# وكيل للطلبات (اختياري للاختبار)
PROXY = None  # مثال: {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}

# مسارات الملفات
SESSION_FILE = "session_data.json"
BREACH_DB_PATH = "breach_data.json"
