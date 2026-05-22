import os
import re
import aiohttp
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import exifread
from PIL import Image
import hashlib
from email_validator import validate_email, EmailNotValidError
from groq import Groq

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ai_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)

def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    keyboard = [
        [InlineKeyboardButton("🔍 Instagram", callback_data="ig")],
        [InlineKeyboardButton("📞 Phone", callback_data="phone")],
        [InlineKeyboardButton("📧 Email", callback_data="email")],
        [InlineKeyboardButton("👤 Username (100+ sites)", callback_data="username")],
        [InlineKeyboardButton("🌐 IP Geolocation", callback_data="ip")],
        [InlineKeyboardButton("🖼️ Photo EXIF", callback_data="photo")],
        [InlineKeyboardButton("🧠 AI Forensic Report", callback_data="ai")]
    ]
    await update.message.reply_text("🕵️ OSINT Bot Ready\nSelect option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.callback_query.answer("Unauthorized")
        return
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = query.data
    await query.edit_message_text(f"Send {query.data.upper()} target:")

async def username_search_all(target):
    sites = {
        "github": f"https://github.com/{target}",
        "twitter": f"https://twitter.com/{target}",
        "reddit": f"https://www.reddit.com/user/{target}",
        "instagram": f"https://instagram.com/{target}",
        "tiktok": f"https://tiktok.com/@{target}",
        "youtube": f"https://youtube.com/@{target}",
        "pinterest": f"https://pinterest.com/{target}",
        "twitch": f"https://twitch.tv/{target}",
        "medium": f"https://medium.com/@{target}"
    }
    results = {}
    async with aiohttp.ClientSession() as session:
        for name, url in sites.items():
            try:
                async with session.get(url, timeout=5) as resp:
                    results[name] = "found" if resp.status == 200 else "not found"
            except:
                results[name] = "error"
    return results

async def instagram_scrape(username):
    try:
        url = f"https://www.instagram.com/{username}/?__a=1&__d=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get('graphql', {}).get('user', {})
                    bio = user.get('biography', '')
                    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', bio)
                    phone = re.search(r'(\+?\d{10,15})', bio)
                    return {
                        "full_name": user.get('full_name'),
                        "bio": bio[:200],
                        "followers": user.get('edge_followed_by', {}).get('count'),
                        "is_private": user.get('is_private'),
                        "email": email.group(0) if email else None,
                        "phone": phone.group(0) if phone else None
                    }
    except:
        pass
    return {"error": "private or not accessible"}

async def phone_lookup(phone):
    try:
        parsed = phonenumbers.parse(phone, None)
        return {
            "valid": phonenumbers.is_valid_number(parsed),
            "country": geocoder.description_for_number(parsed, "en"),
            "carrier": carrier.name_for_number(parsed, "en"),
            "timezones": str(timezone.time_zones_for_number(parsed))
        }
    except:
        return {"error": "invalid number"}

async def email_breach_check(email):
    try:
        validate_email(email)
        h = hashlib.sha1(email.encode()).hexdigest().upper()
        url = f"https://api.pwnedpasswords.com/range/{h[:5]}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.text()
                    return {"breached": h[5:] in data, "breach_check": "completed"}
    except:
        pass
    return {"error": "check failed"}

async def ip_geo(ip):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://ip-api.com/json/{ip}") as resp:
            data = await resp.json()
            return {
                "country": data.get("country"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "isp": data.get("isp"),
                "proxy_vpn": data.get("proxy", False)
            }

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if "awaiting" not in context.user_data:
        return
    
    action = context.user_data.pop("awaiting")
    target = update.message.text.strip()
    await update.message.reply_text(f"⏳ Scanning {action}...")
    
    result = {}
    if action == "ig":
        result = await instagram_scrape(target)
    elif action == "phone":
        result = await phone_lookup(target)
    elif action == "email":
        result = await email_breach_check(target)
    elif action == "username":
        result = await username_search_all(target)
    elif action == "ip":
        result = await ip_geo(target)
    elif action == "photo" and update.message.photo:
        file = await update.message.photo[-1].get_file()
        photo_bytes = await file.download_as_bytearray()
        tags = exifread.process_file(photo_bytes)
        result = {k: str(v) for k, v in tags.items() if k.startswith("Image") or k.startswith("EXIF")}
    
    output = f"📊 {action.upper()} RESULTS:\n" + "\n".join([f"{k}: {v}" for k, v in result.items()])
    await update.message.reply_text(output[:4000])
    
    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({action: result})

async def ai_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    history = context.user_data.get("history", [])
    if not history:
        await update.message.reply_text("No data yet. Run OSINT commands first.")
        return
    prompt = f"""You are a forensic digital analyst. Analyze this OSINT data and create a structured intelligence report with:
1. Summary of findings
2. Digital footprint analysis
3. Correlations between data points
4. Threat/risk assessment
5. Recommendations

Data: {str(history)}"""
    completion = ai_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    await update.message.reply_text(f"🧠 FORENSIC REPORT:\n{completion.choices[0].message.content[:4000]}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(MessageHandler(filters.PHOTO, handle_input))
    app.add_handler(CommandHandler("analyze", ai_analysis))
    app.run_polling()

if __name__ == "__main__":
    main()
