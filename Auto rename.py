import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

DB_FILE = "users.json"

# Load / Save DB
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

db = load_db()

def get_user(user_id):
    if str(user_id) not in db:
        db[str(user_id)] = {
            "prefix": "",
            "suffix": "",
            "rename": "",
            "ext": "",
            "episode": 1,
            "caption": "🎬 {filename}",
            "thumb": None
        }
    return db[str(user_id)]

# Start UI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📌 Prefix", callback_data="prefix"),
         InlineKeyboardButton("📌 Suffix", callback_data="suffix")],
        [InlineKeyboardButton("✏️ Rename", callback_data="rename"),
         InlineKeyboardButton("🎞 Extension", callback_data="ext")],
        [InlineKeyboardButton("🔢 Episode", callback_data="episode"),
         InlineKeyboardButton("🖼 Thumbnail", callback_data="thumb")],
        [InlineKeyboardButton("📝 Caption", callback_data="caption")]
    ]

    await update.message.reply_text(
        "⚙️ PRO Rename Bot\nChoose setting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data
    await query.message.reply_text(f"Send value for {query.data}")

# Text handler
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    user = get_user(update.effective_user.id)

    if not mode:
        return

    if mode == "episode":
        user["episode"] = int(update.message.text)
    else:
        user[mode] = update.message.text

    save_db(db)
    await update.message.reply_text(f"✅ {mode} updated!")

# Thumbnail handler
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    file_id = update.message.photo[-1].file_id
    user["thumb"] = file_id
    save_db(db)

    await update.message.reply_text("✅ Thumbnail saved!")

# File handler
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    file = update.message.document or update.message.video
    file_id = file.file_id

    original_name = getattr(file, "file_name", "video.mp4")
    name, ext = os.path.splitext(original_name)

    # Rename logic
    if user["rename"]:
        name = user["rename"]

    name = f"{user['prefix']}{name}{user['suffix']}"

    # Episode
    name += f"_Ep{str(user['episode']).zfill(2)}"
    user["episode"] += 1

    # Extension
    if user["ext"]:
        ext = "." + user["ext"].replace(".", "")

    new_name = name + ext

    # Caption
    caption = user["caption"].replace("{filename}", new_name)

    save_db(db)

    await update.message.reply_text(f"📂 {new_name}")

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_id,
        filename=new_name,
        caption=caption,
        thumbnail=user["thumb"]
    )

# App
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, handle_file))

print("🚀 Pro Bot Running...")
app.run_polling()
