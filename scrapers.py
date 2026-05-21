# scrapers.py
# BLACK OPEN SYSTEM - OSINT & AI ENGINE

import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import re
import json
from phonenumbers import parse, is_valid_number, carrier, geocoder
from email_validator import validate_email, EmailNotValidError
from pysherlock import Sherlock
import whois
import dns.resolver
from ip2geotools.databases.noncommercial import DbIpCity
from PIL import Image
import exifread
import io
import base64
from groq import Groq
import google.generativeai as genai
from config import GROQ_API_KEY, GEMINI_API_KEY

# تهيئة الذكاء الاصطناعي
if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
else:
    gemini_model = None

# ===============================
# 1. منصة وسائل التواصل الاجتماعي
# ===============================

async def fetch_instagram_data(username):
    """جمع بيانات عامة من Instagram"""
    try:
        url = f"https://www.instagram.com/{username}/"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # استخراج البيانات من JSON المضمن
                    match = re.search(r'window\._sharedData\s*=\s*({.*?});', html)
                    if match:
                        data = json.loads(match.group(1))
                        user_data = data.get('entry_data', {}).get('ProfilePage', [{}])[0].get('graphql', {}).get('user', {})
                        return {
                            "full_name": user_data.get('full_name'),
                            "biography": user_data.get('biography'),
                            "follower_count": user_data.get('edge_followed_by', {}).get('count'),
                            "following_count": user_data.get('edge_follow', {}).get('count'),
                            "is_private": user_data.get('is_private'),
                            "profile_pic_url": user_data.get('profile_pic_url_hd')
                        }
    except:
        pass
    return {"error": "Instagram: لا يمكن جلب البيانات أو الحساب خاص/غير موجود"}

async def fetch_facebook_data(username):
    """جمع بيانات عامة من Facebook"""
    # Facebook يصعب كشطه بدون API رسمي
    return {"info": "Facebook يتطلب API مدفوع أو تسجيل دخول"}

async def fetch_tiktok_data(username):
    """جمع بيانات عامة من TikTok"""
    try:
        url = f"https://www.tiktok.com/@{username}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # استخراج المعرفات
                    user_id_match = re.search(r'"uniqueId":"([^"]+)"', html)
                    name_match = re.search(r'"nickname":"([^"]+)"', html)
                    bio_match = re.search(r'"signature":"([^"]+)"', html)
                    return {
                        "username": user_id_match.group(1) if user_id_match else None,
                        "display_name": name_match.group(1) if name_match else None,
                        "bio": bio_match.group(1) if bio_match else None,
                    }
    except:
        pass
    return {"error": "TikTok: لا يمكن جلب البيانات"}

# ===============================
# 2. منظومة الاتصالات والهوية
# ===============================

def phone_lookup(phone_number):
    """التحقق من رقم الهاتف"""
    try:
        parsed = parse(phone_number, None)
        if is_valid_number(parsed):
            country = geocoder.description_for_number(parsed, "en")
            operator = carrier.name_for_number(parsed, "en")
            return {
                "valid": True,
                "country": country,
                "operator": operator,
                "international_format": f"+{parsed.country_code}{parsed.national_number}"
            }
    except:
        pass
    return {"valid": False, "error": "رقم غير صالح"}

def email_breach_check(email):
    """التحقق من ظهور البريد في خروقات البيانات"""
    try:
        # استخدام API مجاني من 'haveibeenpwned'
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {"hibp-api-key": ""}  # التسجيل مطلوب للحصول على مفتاح مجاني
        # ملاحظة: بدون مفتاح، العدد محدود
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return {"breached": True, "sites": [b["Name"] for b in resp.json()]}
        elif resp.status_code == 404:
            return {"breached": False, "message": "لم يتم العثور في التسريبات"}
    except:
        pass
    return {"breached": "unknown", "error": "فشل التحقق"}

async def username_osint(username):
    """البحث عن اسم المستخدم في 300+ منصة باستخدام Sherlock"""
    try:
        sherlock = Sherlock()
        results = await sherlock.check_username(username)
        active_accounts = [platform for platform, data in results.items() if data.get("status") == 200]
        return {"active_on": active_accounts[:50], "total_found": len(active_accounts)}
    except:
        return {"error": "فشل البحث عن اسم المستخدم"}

# ===============================
# 3. منظومة التحقيق التقني والجغرافي
# ===============================

def ip_geo_lookup(ip):
    """التحقيق في عنوان IP"""
    try:
        resp = DbIpCity.get(ip, api_key="free")
        return {
            "ip": ip,
            "city": resp.city,
            "region": resp.region,
            "country": resp.country,
            "latitude": resp.latitude,
            "longitude": resp.longitude,
            "isp": resp.service
        }
    except:
        return {"error": "تعذر تحديد موقع IP"}

def check_vpn_proxy(ip):
    """فحص VPN/Proxy"""
    try:
        url = f"https://ipinfo.io/{ip}/json"
        resp = requests.get(url)
        data = resp.json()
        is_proxy = data.get('proxy') or data.get('hosting') or False
        return {"is_vpn_or_proxy": is_proxy, "org": data.get('org')}
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
        # محاولة استخراج الإحداثيات
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lon = tags.get('GPS GPSLongitude')
        if gps_lat and gps_lon:
            lat = float(gps_lat.values[0]) + float(gps_lat.values[1])/60 + float(gps_lat.values[2])/3600
            lon = float(gps_lon.values[0]) + float(gps_lon.values[1])/60 + float(gps_lon.values[2])/3600
            exif_data["coordinates"] = f"{lat}, {lon}"
        return exif_data
    except:
        return {"error": "لا توجد بيانات EXIF أو تعذر قراءتها"}

def reverse_image_search(image_url):
    """البحث العكسي عن الصورة (مجاني باستخدام Google Images مع محاكاة)"""
    # ملاحظة: هذا يتطلب حلاً معقداً، نقدم واجهة أساسية
    return {"note": "البحث العكسي المجاني يتطلب تنفيذ معقد مع Google Dorks. يمكن استخدام API مدفوع مثل Google Vision."}

# ===============================
# 4. المحلل الاستخباراتي بالذكاء الاصطناعي
# ===============================

async def ai_analysis(all_data):
    """تحليل جميع البيانات المجمعة وإنتاج تقرير استخباراتي"""
    if not groq_client and not gemini_model:
        return "❌ لا توجد خدمة ذكاء اصطناعي متاحة. يرجى إضافة Groq أو Gemini API."

    prompt = f"""
    أنت محلل جنائي رقمي خبير. بناءً على البيانات التالية المجمعة عن الهدف، قم بتحليل السلوك الرقمي، ربط المعلومات، وإصدار تقرير استخباراتي منظم.

    البيانات:
    {json.dumps(all_data, indent=2, ensure_ascii=False)}

    المطلوب:
    1. الهوية الرقمية المحتملة (الاسم، الموقع، الوظيفة)
    2. المخاطر الأمنية المرتبطة (ما يمكن استغلاله)
    3. أنماط السلوك (نشاط، تفضيلات)
    4. توصيات للمستخدم لمزيد من التحقيق
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
        return f"⚠️ خطأ في تحليل الذكاء الاصطناعي: {str(e)}"
