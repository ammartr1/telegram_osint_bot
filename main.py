# main.py
# BLACK OPEN SYSTEM - TELEGRAM OSINT BOT

import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, OWNER_USER_ID
import scrapers

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التحقق من الصلاحية
async def check_owner(update: Update):
    if update.effective_user.id != OWNER_USER_ID:
        await update.message.reply_text("🔒 هذا البوت خاص بالمالك فقط.")
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
    await update.message.reply_text(
        "🔥 *بوت OSINT العملاق - BLACK OPEN SYSTEM* 🔥\n\nاختر خدمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != OWNER_USER_ID:
        await query.edit_message_text("🔒 غير مصرح.")
        return
    data = query.data
    if data == 'social':
        await query.edit_message_text("📱 أرسل:\n`instagram:username`\n`tiktok:username`", parse_mode='Markdown')
        context.user_data['mode'] = 'social'
    elif data == 'identity':
        await query.edit_message_text("🔢 أرسل:\n`phone:+1234567890`\n`email:example@mail.com`\n`username:target`", parse_mode='Markdown')
        context.user_data['mode'] = 'identity'
    elif data == 'technical':
        await query.edit_message_text("🌍 أرسل:\n`ip:8.8.8.8`\nأو أرسل صورة لتحليل EXIF", parse_mode='Markdown')
        context.user_data['mode'] = 'technical'
    elif data == 'ai_analysis':
        context.user_data['mode'] = 'ai_analysis'
        await query.edit_message_text("🧠 أرسل البيانات كـ JSON، أو اكتب `collect` لجمع بيانات تجريبية")
    elif data == 'help':
        await query.edit_message_text("استخدم الأزرار للتنقل. كل خدمة تطلب مدخلات محددة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update):
        return
    text = update.message.text
    mode = context.user_data.get('mode', 'social')
    result = {}

    if mode == 'social':
        if text.startswith('instagram:'):
            result = await scrapers.fetch_instagram_data(text.split(':')[1])
        elif text.startswith('tiktok:'):
            result = await scrapers.fetch_tiktok_data(text.split(':')[1])
        else:
            result = {"error": "استخدم instagram:username أو tiktok:username"}
    elif mode == 'identity':
        if text.startswith('phone:'):
            result = scrapers.phone_lookup(text.split(':')[1])
        elif text.startswith('email:'):
            result = scrapers.email_breach_check(text.split(':')[1])
        elif text.startswith('username:'):
            result = await scrapers.username_osint(text.split(':')[1])
        else:
            result = {"error": "استخدم phone:رقم أو email:بريد أو username:اسم"}
    elif mode == 'technical':
        if text.startswith('ip:'):
            ip = text.split(':')[1]
            geo = scrapers.ip_geo_lookup(ip)
            vpn = scrapers.check_vpn_proxy(ip)
            result = {"geo": geo, "vpn_proxy": vpn}
        else:
            result = {"error": "استخدم ip:address"}
    elif mode == 'ai_analysis' and text == 'collect':
        fake_data = {"username": "target", "ip": "1.1.1.1", "email": "target@example.com"}
        result = await scrapers.ai_analysis(fake_data)
        await update.message.reply_text(f"🧠 *تقرير AI:*\n\n{result}", parse_mode='Markdown')
        return
    else:
        result = {"error": "اختر خدمة من القائمة أولاً"}

    await update.message.reply_text(json.dumps(result, indent=2, ensure_ascii=False))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update):
        return
    photo = await update.message.photo[-1].get_file()
    img_bytes = await photo.download_as_bytearray()
    exif = scrapers.image_exif_extraction(img_bytes)
    await update.message.reply_text(f"📸 *EXIF:*\n{json.dumps(exif, indent=2, ensure_ascii=False)}", parse_mode='Markdown')

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
