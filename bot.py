# bot_main.py
import logging
import asyncio
import sqlite3
from contextlib import closing
from typing import List
from telegram import Update, Chat, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- Config ----------
BOT_TOKEN = "8149753284:AAGB1SU53oPrAafyKhcla8oeP9rCZ_8DV3M"
OWNER_ID = 8566689610
DB_PATH = "bot_data.db"

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(name)

# ---------- Database helpers ----------
def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS running_tasks (
            chat_id INTEGER PRIMARY KEY,
            is_running INTEGER DEFAULT 0
        )""")
        conn.commit()

def add_admin(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (user_id,))
        conn.commit()

def remove_admin(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        conn.commit()

def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
        return cur.fetchone() is not None

def save_text_append(text: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO saved_texts(text) VALUES(?)", (text,))
        conn.commit()

def list_saved_texts() -> List[str]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, text FROM saved_texts ORDER BY id")
        return [f"{row[0]}: {row[1]}" for row in cur.fetchall()]

def delete_saved_text(idx: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_texts WHERE id=?", (idx,))
        conn.commit()

def set_running(chat_id: int, running: bool):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO running_tasks(chat_id, is_running) VALUES(?, ?)", (chat_id, 1 if running else 0))
        conn.commit()

def is_running(chat_id: int) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT is_running FROM running_tasks WHERE chat_id=?", (chat_id,))
        r = cur.fetchone()
        return bool(r and r[0] == 1)

# ---------- Utilities ----------
def mention_user_html(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'

async def get_official_name(context: ContextTypes.DEFAULT_TYPE, chat: Chat, user_id: int) -> str:
    try:
        member = await context.bot.get_chat_member(chat.id, user_id)
        name = member.user.full_name
        return name
    except Exception:
        return str(user_id)

# ---------- Command checks ----------

def require_owner_or_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("သင့်မှာ permission မရှိပါ။")
            return
        return await func(update, context)
    return wrapper

def require_owner(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text("Owner permission လိုအပ်သည်။")
            return
        return await func(update, context)
    return wrapper

# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot အဆင်သင့်ဖြစ်ပါပြီ။")

@require_owner_or_admin
async def attack_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /attack <user_id or reply>
    chat = update.effective_chat
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID မှန်ကန်စွာထည့်ပါ။")
            return
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return

    name = await get_official_name(context, chat, target_id)
    mention = mention_user_html(target_id, name)
    await update.message.reply_html(f"Attack: {mention}")

@require_owner_or_admin
async def flash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /flash <user_id or reply> [count]
    chat = update.effective_chat
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID မှန်ကန်စွာထည့်ပါ။")
            return
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return

    count = 10
    if len(context.args) >= 2:
        try:
            count = int(context.args[1])
        except Exception:
            pass

    name = await get_official_name(context, chat, target_id)
    set_running(chat.id, True)
    try:
        for i in range(count):
            if not is_running(chat.id):
                break
            mention = mention_user_html(target_id, name)
            await context.bot.send_message(chat.id, mention, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.exception("flash error")
        await update.message.reply_text("Flash မှာ error ဖြစ်ခဲ့သည်။")
    finally:
        set_running(chat.id, False)

@require_owner_or_admin
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Owner or admin can stop running mention loops in this chat
    set_running(update.effective_chat.id, False)
    await update.message.reply_text("Stopped.")

@require_owner
async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /save <text>  OR reply with /save
    if update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    else:
        text = " ".join(context.args)
    if not text:
        await update.message.reply_text("ထည့်ရန်စာသားမရှိပါ။")
        return
    save_text_append(text)
    await update.message.reply_text("Saved.")

@require_owner
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = list_saved_texts()
    if not items:
        await update.message.reply_text("Saved list is empty.")
        return
    await update.message.reply_text("\n".join(items))

@require_owner_or_admin
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: reply to message then /delete  OR /delete <message_id>
    if update.message.reply_to_message:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            await update.message.reply_text("Message deleted.")
        except Exception as e:
            logger.exception("delete error")
            await update.message.reply_text("Cannot delete message. Make sure bot has delete permission.")
    elif context.args:
        try:
            mid = int(context.args[0])
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=mid)
            await update.message.reply_text("Message deleted.")
        except Exception:
            await update.message.reply_text("Failed to delete message.")
    else:
        await update.message.reply_text("Reply to a message or provide message id.")

@require_owner
async def setadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /setadmin <user_id> or reply
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID မှန်ကန်စွာထည့်ပါ။")
            return
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    add_admin(uid)
    await update.message.reply_text(f"Added admin: {uid}")

@require_owner
async def deladmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /deladmin <user_id> or reply
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID မှန်ကန်စွာထည့်ပါ။")
            return
    else:
        await update.message.reply_text("Reply သို့မဟုတ် user id ထည့်ပါ။")
        return
    remove_admin(uid)
    await update.message.reply_text(f"Removed admin: {uid}")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: /id or reply
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0])
            user = await context.bot.get_chat(uid)
        except Exception:
            await update.message.reply_text("Cannot find user.")
            return
    else:
        user = update.effective_user

    # bot permissions in chat
    chat = update.effective_chat
    try:
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        bot_status = member.status
    except Exception:
        bot_status = "unknown"

    text = f"User: {user.full_name}\nID: {user.id}\nBot status in this chat: {bot_status}"
    await update.message.reply_text(text)

@require_owner
async def posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # usage: reply to a message with /posting
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the post you want to forward.")
        return
    # find groups where bot is admin? We cannot list all groups easily.
    # We'll forward to groups listed in admins' groups or to a configured list.
    await update.message.reply_text("Posting: forwarding to configured groups is not implemented in this simple example. Add your group list in code or DB.")

# ---------- Error handler ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("Internal error occurred.")
    except Exception:
        pass

# ---------- Main ----------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

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

    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling()

if name == "main":
    main()
