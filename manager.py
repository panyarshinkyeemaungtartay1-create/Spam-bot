import os
import zipfile
import subprocess
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

MANAGER_TOKEN = os.getenv("MANAGER_TOKEN")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

user_data_store = {}
running_process = None

# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Pro Hosting Manager\n\n"
        "1️⃣ Send ZIP file\n"
        "2️⃣ Send Bot Token\n"
        "3️⃣ Send Owner ID\n"
        "4️⃣ Use /run"
    )

# =========================
# ZIP Upload
# =========================
async def handle_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document.file_name.endswith(".zip"):
        return await update.message.reply_text("❌ ZIP file only.")

    file = await update.message.document.get_file()
    zip_path = os.path.join(UPLOAD_DIR, "bot.zip")
    await file.download_to_drive(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(UPLOAD_DIR)

    user_data_store["zip"] = True
    await update.message.reply_text("✅ ZIP Extracted.\nNow send Bot Token.")

# =========================
# Token + Owner Save
# =========================
async def save_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "zip" not in user_data_store:
        return await update.message.reply_text("❌ Send ZIP first.")

    if "token" not in user_data_store:
        user_data_store["token"] = text.strip()
        return await update.message.reply_text("✅ Token Saved.\nNow send Owner ID.")

    if "owner" not in user_data_store:
        user_data_store["owner"] = text.strip()
        return await update.message.reply_text("✅ Owner Saved.\nNow use /run")

# =========================
# /run
# =========================
async def run_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running_process

    if not all(k in user_data_store for k in ("zip", "token", "owner")):
        return await update.message.reply_text("❌ Complete setup first.")

    files = os.listdir(UPLOAD_DIR)

    target_file = None
    if "main.py" in files:
        target_file = "main.py"
    elif "bot.py" in files:
        target_file = "bot.py"

    if not target_file:
        return await update.message.reply_text("❌ No main.py or bot.py found.")

    env = os.environ.copy()
    env["BOT_TOKEN"] = user_data_store["token"]
    env["OWNER_ID"] = user_data_store["owner"]

    running_process = subprocess.Popen(
        ["python", os.path.join(UPLOAD_DIR, target_file)],
        env=env
    )

    await update.message.reply_text("🚀 Bot Running Successfully!")

# =========================
# Main
# =========================
async def main():
    app = ApplicationBuilder().token(MANAGER_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_bot))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_zip))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_text))

    print("🔥 Hosting Manager Online")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
