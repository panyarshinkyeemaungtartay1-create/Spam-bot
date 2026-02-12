import os
import zipfile
import subprocess
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

MANAGER_TOKEN = os.getenv("MANAGER_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

user_data_store = {}

# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Pro Hosting Manager Bot 🔥\n\n"
        "1️⃣ Zip File ပို့ပါ\n"
        "2️⃣ Bot Token ပို့ပါ\n"
        "3️⃣ Owner ID ပို့ပါ\n"
        "ပြီးရင် /run နှိပ်ပါ"
    )

# =========================
# Zip Receive
# =========================
async def receive_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    file = await update.message.document.get_file()
    await file.download_to_drive("bot.zip")

    with zipfile.ZipFile("bot.zip", 'r') as zip_ref:
        zip_ref.extractall("bot")

    await update.message.reply_text("✅ Zip Extracted")

# =========================
# Save Token
# =========================
async def save_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    user_data_store["bot_token"] = update.message.text.strip()
    await update.message.reply_text("✅ Bot Token Saved")

# =========================
# Run Bot
# =========================
async def run_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not os.path.exists("bot"):
        await update.message.reply_text("❌ Zip မရှိသေးဘူး")
        return

    await update.message.reply_text("🚀 Bot Running...")

    subprocess.Popen(["python", "bot/bot.py"])

# =========================
# Main
# =========================
async def main():
    app = ApplicationBuilder().token(MANAGER_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_bot))
    app.add_handler(MessageHandler(filters.Document.ALL, receive_zip))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_token))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
