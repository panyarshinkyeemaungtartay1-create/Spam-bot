import logging
import asyncio
import sqlite3
from contextlib import closing
from typing import List
from telegram import Update, Chat
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- Config ----------
BOT_TOKEN = "8149753284:AAGB1SU53oPrAafyKhcla8oeP9rCZ_8DV3M"
OWNER_ID = 8566689610
DB_PATH = "bot_data.db"

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Database ----------
def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS saved_texts (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS running_tasks (chat_id INTEGER PRIMARY KEY, is_running INTEGER DEFAULT 0)")
        conn.commit()

def add_admin(uid: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
        conn.commit()

def remove_admin(uid: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        conn.commit()

def is_admin(uid: int) -> bool:
    if uid == OWNER_ID:
        return True
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,))
        return cur.fetchone() is not None

def save_text_append(text: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("INSERT INTO saved_texts(text) VALUES(?)", (text,))
        conn.commit()

def list_saved_texts() -> List[str]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, text FROM saved_texts ORDER BY id")
        return [f"{row[0]}: {row[1]}" for row in cur.fetchall()]

def set_running(chat_id: int, running: bool):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("INSERT OR REPLACE INTO running_tasks(chat_id, is_running) VALUES(?, ?)", (chat_id, 1 if running else 0))
        conn.commit()

def is_running(chat_id: int) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT is_running FROM running_tasks WHERE chat_id=?", (chat_id,))
        r = cur.fetchone()
        return bool(r and r[0] == 1)

# ---------- Utils ----------
def mention_user_html(uid: int, name: str) -> str:
    return f'<a href="tg://user?id={uid}">{name}</a>'

async def get_name(context: ContextTypes.DEFAULT_TYPE, chat: Chat, uid: int) -> str:
    try:
        member = await context.bot.get_chat_member(chat.id, uid)
        return member.user.full_name
    except Exception:
        return str(uid)

# ---------- Decorators ----------
def require_owner_or_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("Permission မရှိပါ။")
            return
        return await func(update, context)
    return wrapper

def require_owner(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("Owner permission လိုအပ်သည်။")
            return
        return await func(update, context)
    return wrapper

# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot အဆင်သင့်ဖြစ်ပါပြီ။")

@require_owner_or_admin
async def attack_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        target_id = int(context.args[0])
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    name = await get_name(context, chat, target_id)
    mention = mention_user_html(target_id, name)
    await update.message.reply_html(f"Attack: {mention}")

@require_owner_or_admin
async def flash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        target_id = int(context.args[0])
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    name = await get_name(context, chat, target_id)
    set_running(chat.id, True)
    for i in range(20):
        if not is_running(chat.id):
            break
        mention = mention_user_html(target_id, name)
        await context.bot.send_message(chat.id, mention, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.1)
    set_running(chat.id, False)

@require_owner_or_admin
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_running(update.effective_chat.id, False)
    await update.message.reply_text("Stopped.")

@require_owner
async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""
    if not text:
        await update.message.reply_text("စာသားမရှိပါ။")
        return
    save_text_append(text)
    await update.message.reply_text("Saved.")

@require_owner
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = list_saved_texts()
    if not items:
        await update.message.reply_text("Empty.")
        return
    await update.message.reply_text("\n".join(items))

@require_owner_or_admin
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        try:
            await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
            await update.message.reply_text("Deleted.")
        except Exception:
            await update.message.reply_text("Delete failed.")
    else:
        await update.message.reply_text("Reply to a message to delete.")

@require_owner
async def setadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        uid = int(context.args[0])
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    add_admin(uid)
    await update.message.reply_text(f"Added admin: {uid}")

@require_owner
async def deladmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        uid = int(context.args[0])
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    remove_admin(uid)
    await update.message.reply_text(f"Removed admin: {uid}")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"User: {user.full_name}\nID: {user.id}\nAdmin: {is_admin(user.id)}")

@require_owner
async def posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a post.")
        return
    await update.message.reply_text("Posting feature requires group list configuration.")

# ---------- Main ----------
from telegram.ext import Application, CommandHandler

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("attack", attack_cmd))
    app.add_handler(CommandHandler("flash", flash_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("save", save_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(CommandHandler("setadmin", setadmin_cmd))
    app.add_handler(CommandHandler("deladmin", deladmin_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("posting", posting_cmd))

    app.run_polling()


if __name__ == "__main__":
    main()
