# main.py
# BLACK OPEN SYSTEM - TELEGRAM OSINT BOT

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, OWNER_USER_ID
import scrapers
import asyncio
import json

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التحقق من الصلاحية (whitelist)
async def check_owner(update: Update):
    user_id = update.effective_user.id
    if user_id != OWNER_USER_ID:
        await update.message.reply_text("🔒 هذا البوت خاص وموجه للمالك فقط.")
        return False
    return True

# قائمة الأزرار الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update):
        return
    keyboard = [
        [InlineKeyboardButton("📱 وسائل التواصل", callback_data='social')],
        [InlineKeyboardButton("📞 هوية رقمية", callback_data='identity')],
        [InlineKeyboardButton("🌐 تقني وجيو", callback_data='technical')],
        [InlineKeyboardButton("🧠 تحليل AI شامل", callback_data='ai_analysis')],
        [InlineKeyboardButton("❓ تعليمات", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 *بوت OSINT العملاق - BLACK OPEN SYSTEM* 🔥\n\nاختر إحدى الخدمات:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id != OWNER_USER_ID:
        await query.edit_message_text("🔒 غير مصرح.")
        return

    data = query.data
    if data == 'social':
        await query.edit_message_text("📱 أرسل اسم المستخدم لـ:\n- Instagram\n- Facebook\n- TikTok\nمثال: `instagram:john_doe`")
        context.user_data['mode'] = 'social'
    elif data == 'identity':
        await query.edit_message_text("🔢 أرسل:\n- رقم الهاتف (مثال: +1234567890)\n- بريد إلكتروني\n- اسم مستخدم للبحث الشامل")
        context.user_data['mode'] = 'identity'
    elif data == 'technical':
        await query.edit_message_text("🌍 أرسل:\n- عنوان IP\n- صورة (لتحليل EXIF والبحث العكسي)")
        context.user_data['mode'] = 'technical'
    elif data == 'ai_analysis':
        context.user_data['mode'] = 'ai_analysis'
        await query.edit_message_text("🧠 أرسل جميع البيانات التي جمعتها سابقاً كنص JSON، أو اكتب 'collect' لتجميع بيانات جديدة أولاً.")
    elif data == 'help':
        help_text = """
        *البوت العملاق لجمع المعلومات*\n
        • وسائل التواصل: اكتب `instagram:username` أو `tiktok:username`
        • هوية: اكتب `phone:+123456` أو `email:someone@example.com` أو `username:target`
        • تقني: اكتب `ip:8.8.8.8` أو أرسل صورة
        • تحليل AI: أرسل ملف JSON أو طلب تجميع تلقائي
        """
        await query.edit_message_text(help_text, parse_mode='Markdown')

# معالجة الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update):
        return
    text = update.message.text
    mode = context.user_data.get('mode', 'social')
    result = {}

    if mode == 'social':
        if text.startswith('instagram:'):
            username = text.split(':')[1]
            result = await scrapers.fetch_instagram_data(username)
        elif text.startswith('tiktok:'):
            username = text.split(':')[1]
            result = await scrapers.fetch_tiktok_data(username)
        else:
            result = {"error": "صيغة غير صحيحة. استخدم instagram:username أو tiktok:username"}
    elif mode == 'identity':
        if text.startswith('phone:'):
            phone = text.split(':')[1]
            result = scrapers.phone_lookup(phone)
        elif text.startswith('email:'):
            email = text.split(':')[1]
            result = scrapers.email_breach_check(email)
        elif text.startswith('username:'):
            uname = text.split(':')[1]
            result = await scrapers.username_osint(uname)
        else:
            result = {"error": "استخدم phone:رقم أو email:بريد أو username:اسم"}
    elif mode == 'technical':
        if text.startswith('ip:'):
            ip = text.split(':')[1]
            geo = scrapers.ip_geo_lookup(ip)
            vpn = scrapers.check_vpn_proxy(ip)
            result = {"geo": geo, "vpn_proxy": vpn}
        else:
            result = {"error": "أرسل ip:address"}
    elif mode == 'ai_analysis' and text == 'collect':
        # تجميع مثال سريع - يمكن تخصيصه
        await update.message.reply_text("جاري تجميع بيانات تجريبية...")
        fake_data = {"username": "target", "ip": "1.1.1.1", "email": "target@example.com"}
        result = await scrapers.ai_analysis(fake_data)
        await update.message.reply_text(f"🧠 *تقرير AI:*\n\n{result}", parse_mode='Markdown')
        return
    else:
        result = {"error": "يرجى اختيار خدمة من القائمة أولاً."}

    await update.message.reply_text(json.dumps(result, indent=2, ensure_ascii=False))

# معالجة الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update):
        return
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    exif = scrapers.image_exif_extraction(image_bytes)
    await update.message.reply_text(f"📸 *بيانات EXIF:*\n{json.dumps(exif, indent=2, ensure_ascii=False)}", parse_mode='Markdown')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == '__main__':
    main()
