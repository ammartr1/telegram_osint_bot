import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from scrapers import OSINTEngine
from groq import Groq

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# AI client
ai_client = Groq(api_key=GROQ_API_KEY)

# Whitelist check
def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Unauthorized. This bot is private.")
        return
    keyboard = [
        [InlineKeyboardButton("🔍 Instagram", callback_data="ig"),
         InlineKeyboardButton("📞 Phone", callback_data="phone")],
        [InlineKeyboardButton("📧 Email", callback_data="email"),
         InlineKeyboardButton("👤 Username", callback_data="username")],
        [InlineKeyboardButton("🌐 IP", callback_data="ip"),
         InlineKeyboardButton("🖼️ Photo EXIF", callback_data="photo")],
        [InlineKeyboardButton("🧠 AI Analysis", callback_data="ai"),
         InlineKeyboardButton("🔎 Reverse Image", callback_data="reverse")]
    ]
    await update.message.reply_text("🕵️‍♂️ OSINT Master Bot Ready\nSelect target:", reply_markup=InlineKeyboardMarkup(keyboard))

# Callback handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.callback_query.answer("Unauthorized", show_alert=True)
        return
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data["last_action"] = data
    await query.edit_message_text(f"📝 Send {data.upper()} target:")
    context.user_data["awaiting"] = data

# Message handler
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if "awaiting" not in context.user_data:
        return
    action = context.user_data["awaiting"]
    target = update.message.text.strip()
    await update.message.reply_text(f"⏳ Processing {action}...")
    
    result = {}
    if action == "ig":
        result = await OSINTEngine.instagram_scrape(target)
    elif action == "phone":
        result = await OSINTEngine.phone_lookup(target)
    elif action == "email":
        result = await OSINTEngine.email_breach_check(target)
    elif action == "username":
        result = await OSINTEngine.username_search(target)
    elif action == "ip":
        result = await OSINTEngine.ip_geo(target)
    elif action == "photo":
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            photo_bytes = await file.download_as_bytearray()
            result = await OSINTEngine.photo_exif(photo_bytes)
        else:
            result = {"error": "send photo"}
    elif action == "reverse":
        if update.message.photo:
            # process reverse image
            result = await OSINTEngine.reverse_image_search("photo")
        else:
            result = {"error": "send photo"}
    
    output = f"📊 {action.upper()} Results:\n" + "\n".join([f"{k}: {v}" for k, v in result.items()])
    await update.message.reply_text(output[:4000])
    del context.user_data["awaiting"]
    
    # Store for AI analysis
    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({action: result})

# AI Analysis
async def ai_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    history = context.user_data.get("history", [])
    if not history:
        await update.message.reply_text("No data collected yet. Run some OSINT first.")
        return
    prompt = f"You are a forensic digital analyst. Analyze this OSINT data and create a intelligence report:\n{str(history)}"
    completion = ai_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    report = completion.choices[0].message.content
    await update.message.reply_text(f"🧠 AI REPORT:\n{report[:4000]}")

# Main
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(MessageHandler(filters.PHOTO, handle_input))
    app.add_handler(CommandHandler("analyze", ai_analysis))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
