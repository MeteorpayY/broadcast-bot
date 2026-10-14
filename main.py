import logging
import json
import os
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# --- FLASK WEB SERVER (Render Port Compatible) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Broadcast Bot is active on Cloud 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

BOT_TOKEN = "8657603287:AAFclzrne-z3AGOTAmFu08_uSL96bg7kvpw"
ADMIN_ID = 6804321185

DATA_FILE = "chats.json"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "groups": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()

async def register_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id
    chat_type = chat.type
    data_changed = False

    if chat_type == "private":
        if chat_id not in db["users"]:
            db["users"].append(chat_id)
            data_changed = True
            if update.message and update.message.text and update.message.text.startswith("/start"):
                await update.message.reply_text("Namaste! Aap broadcast list me register ho chuke hain.")

    elif chat_type in ["group", "supergroup"]:
        if chat_id not in db["groups"]:
            db["groups"].append(chat_id)
            data_changed = True
            await context.bot.send_message(chat_id=chat_id, text="Namaste! Ye group broadcast list me add ho chuka hai.")

    if data_changed:
        save_data(db)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    report = (
        "📊 **BROADCAST STATS**\n\n"
        f"👤 **Private Users:** `{len(db['users'])}`\n"
        f"👥 **Groups Joined:** `{len(db['groups'])}`\n"
        f"🚀 **Total Reached Chats:** `{len(db['users']) + len(db['groups'])}`"
    )
    await update.message.reply_text(report, parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or update.effective_chat.type != "private":
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Kripya us message ko **Reply** karke `/broadcast` likhein jise aap bhejna chahte hain.")
        return

    context.user_data['broadcast_msg_id'] = update.message.reply_to_message.message_id

    keyboard = [
        [
            InlineKeyboardButton("👤 Personal Users Only", callback_data="bc_users"),
            InlineKeyboardButton("👥 Groups Only", callback_data="bc_groups")
        ],
        [
            InlineKeyboardButton("🚀 Broadcast to All", callback_data="bc_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🎯 **Broadcast Option Select Karein:**", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    target_type = query.data
    msg_id = context.user_data.get('broadcast_msg_id')

    if not msg_id:
        await query.edit_message_text("❌ Process expire ho gaya hai, dubara reply karke `/broadcast` try karein.")
        return

    if target_type == "bc_users":
        targets = db["users"]
        label = "Private Users"
    elif target_type == "bc_groups":
        targets = db["groups"]
        label = "Groups"
    elif target_type == "bc_all":
        targets = list(set(db["users"] + db["groups"]))
        label = "All Chats (Users + Groups)"
    else:
        return

    if not targets:
        await query.edit_message_text(f"❌ Database me koi {label} nahi milne ke karan broadcast cancel hua.")
        return

    await query.edit_message_text(f"⏳ Broadcasting to `{len(targets)}` {label}...", parse_mode="Markdown")

    successful = 0
    failed = 0

    for cid in list(targets):
        try:
            await context.bot.copy_message(chat_id=cid, from_chat_id=query.message.chat_id, message_id=msg_id)
            successful += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"✅ **{label} Broadcast Complete!**\n\n"
            f"🎯 Successful: `{successful}`\n"
            f"🚫 Failed: `{failed}`"
        ),
        parse_mode="Markdown"
    )

def main():
    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", register_chat))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, register_chat))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, register_chat))

    print("Broadcast Bot Cloud par chalu ho gaya hai...")
    app.run_polling()

if __name__ == '__main__':
    main()
