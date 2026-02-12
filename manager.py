import os
import zipfile
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

MANAGER_TOKEN = os.getenv("MANAGER_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Pro Hosting Manager 🔥\n\n"
        "Zip ဖိုင်ပို့ပါ\n"
        "ပြီးရင် /run"
    )

# =====================
async def receive_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    file = await update.message.document.get_file()
    await file.download_to_drive("bot.zip")

    with zipfile.ZipFile("bot.zip", 'r') as zip_ref:
        zip_ref.extractall("bot")

    await update.message.reply_text("✅ Zip Extracted")

# =====================
async def run_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not os.path.exists("bot"):
        await update.message.reply_text("❌ Zip မရှိသေးဘူး")
        return

    subprocess.Popen(["python3", "bot/bot.py"])
    await update.message.reply_text("🚀 Bot Running...")

# =====================
def main():
    app = ApplicationBuilder().token(MANAGER_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_bot))
    app.add_handler(MessageHandler(filters.Document.ALL, receive_zip))

    print("Manager Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
