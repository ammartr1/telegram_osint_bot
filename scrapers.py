# scrapers.py
# BLACK OPEN SYSTEM - OSINT & AI ENGINE

import aiohttp
import asyncio
import requests
import re
import json
import hashlib
from bs4 import BeautifulSoup
from phonenumbers import parse, is_valid_number, carrier, geocoder
from email_validator import validate_email, EmailNotValidError
import whois
import dns.resolver
from PIL import Image
import exifread
import io
from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY, USER_AGENT, REQUEST_TIMEOUT

# تهيئة الذكاء الاصطناعي
groq_client = None
gemini_model = None

if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
    groq_client = Groq(api_key=GROQ_API_KEY)

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')

headers = {"User-Agent": USER_AGENT}

# ===============================
# 1. وسائل التواصل الاجتماعي
# ===============================

async def fetch_instagram_data(username):
    """جمع بيانات عامة من Instagram"""
    try:
        url = f"https://www.instagram.com/{username}/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    match = re.search(r'window\._sharedData\s*=\s*({.*?});', html)
                    if match:
                        data = json.loads(match.group(1))
                        user_data = data.get('entry_data', {}).get('ProfilePage', [{}])[0].get('graphql', {}).get('user', {})
                        return {
                            "platform": "Instagram",
                            "username": username,
                            "full_name": user_data.get('full_name'),
                            "bio": user_data.get('biography'),
                            "followers": user_data.get('edge_followed_by', {}).get('count'),
                            "following": user_data.get('edge_follow', {}).get('count'),
                            "is_private": user_data.get('is_private'),
                            "profile_pic": user_data.get('profile_pic_url_hd')
                        }
    except:
        pass
    return {"platform": "Instagram", "username": username, "error": "لا يمكن جلب البيانات"}

async def fetch_tiktok_data(username):
    """جمع بيانات عامة من TikTok"""
    try:
        url = f"https://www.tiktok.com/@{username}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    user_id = re.search(r'"uniqueId":"([^"]+)"', html)
                    name = re.search(r'"nickname":"([^"]+)"', html)
                    bio = re.search(r'"signature":"([^"]+)"', html)
                    return {
                        "platform": "TikTok",
                        "username": username,
                        "display_name": name.group(1) if name else None,
                        "bio": bio.group(1) if bio else None
                    }
    except:
        pass
    return {"platform": "TikTok", "username": username, "error": "لا يمكن جلب البيانات"}

async def fetch_facebook_data(username):
    """Facebook - بيانات محدودة بدون API"""
    return {"platform": "Facebook", "username": username, "info": "يتطلب API مدفوع أو تسجيل دخول"}

# ===============================
# 2. الهوية الرقمية
# ===============================

def phone_lookup(phone_number):
    """التحقق من رقم الهاتف"""
    try:
        parsed = parse(phone_number, None)
        if is_valid_number(parsed):
            return {
                "valid": True,
                "country": geocoder.description_for_number(parsed, "en"),
                "operator": carrier.name_for_number(parsed, "en"),
                "international": f"+{parsed.country_code}{parsed.national_number}"
            }
    except:
        pass
    return {"valid": False, "error": "رقم غير صالح"}

def email_breach_check(email):
    """التحقق من ظهور البريد في خروقات البيانات (HaveIBeenPwned)"""
    try:
        email_hash = hashlib.sha1(email.encode()).hexdigest().upper()
        url = f"https://api.pwnedpasswords.com/range/{email_hash[:5]}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            hashes = [line.split(':')[0] for line in resp.text.splitlines()]
            if email_hash[5:] in hashes:
                return {"breached": True, "message": "تم العثور في تسريبات البيانات"}
        return {"breached": False, "message": "لم يتم العثور"}
    except:
        return {"breached": "unknown", "error": "فشل التحقق"}

async def username_osint(username):
    """البحث عن اسم المستخدم في منصات متعددة"""
    platforms = {
        "github": f"https://github.com/{username}",
        "twitter": f"https://twitter.com/{username}",
        "instagram": f"https://instagram.com/{username}",
        "tiktok": f"https://tiktok.com/@{username}",
        "reddit": f"https://reddit.com/user/{username}",
        "youtube": f"https://youtube.com/@{username}",
        "pinterest": f"https://pinterest.com/{username}",
        "linkedin": f"https://linkedin.com/in/{username}",
        "facebook": f"https://facebook.com/{username}",
        "telegram": f"https://t.me/{username}"
    }
    active = []
    async with aiohttp.ClientSession() as session:
        for name, url in platforms.items():
            try:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        active.append(name)
            except:
                pass
    return {"username": username, "active_on": active, "total": len(active)}

# ===============================
# 3. التحقيق التقني والجغرافي
# ===============================

def ip_geo_lookup(ip):
    """التحقيق في عنوان IP باستخدام ip-api.com"""
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get('status') == 'success':
            return {
                "ip": ip,
                "city": data.get('city'),
                "region": data.get('regionName'),
                "country": data.get('country'),
                "lat": data.get('lat'),
                "lon": data.get('lon'),
                "isp": data.get('isp')
            }
    except:
        pass
    return {"error": "تعذر تحديد موقع IP"}

def check_vpn_proxy(ip):
    """فحص VPN/Proxy"""
    try:
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=REQUEST_TIMEOUT)
        data = resp.json()
        return {"is_vpn_or_proxy": data.get('proxy') or data.get('hosting') or False, "org": data.get('org')}
    except:
        return {"is_vpn_or_proxy": "unknown"}

def image_exif_extraction(image_bytes):
    """استخراج EXIF من الصورة"""
    try:
        tags = exifread.process_file(io.BytesIO(image_bytes))
        exif_data = {}
        for tag, value in tags.items():
            if "GPS" in tag or "Image" in tag or "EXIF" in tag:
                exif_data[str(tag)] = str(value)
        return exif_data
    except:
        return {"error": "لا توجد بيانات EXIF"}

def reverse_image_search(image_bytes):
    """البحث العكسي عن الصورة (Google Images)"""
    return {"note": "يتطلب API مدفوع أو تنفيذ معقد"}

# ===============================
# 4. الذكاء الاصطناعي - المحلل الجنائي
# ===============================

async def ai_analysis(all_data):
    """تحليل جميع البيانات المجمعة وإنتاج تقرير استخباراتي"""
    if not groq_client and not gemini_model:
        return "❌ لا توجد خدمة ذكاء اصطناعي. أضف Groq أو Gemini API."

    prompt = f"""
أنت محلل جنائي رقمي خبير. بناءً على البيانات التالية، قم بتحليل السلوك الرقمي وإصدار تقرير استخباراتي:

{json.dumps(all_data, indent=2, ensure_ascii=False)}

المطلوب:
1. الهوية الرقمية المحتملة
2. المخاطر الأمنية
3. أنماط السلوك
4. توصيات للتحقيق
"""

    try:
        if groq_client:
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        elif gemini_model:
            response = gemini_model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"⚠️ خطأ: {str(e)}"
