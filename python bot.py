# bot.py
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import logging
import json
import os

# --- CONFIG ---
TOKEN = "8569459914:AAHt1xpr48Y3AkqZ80oMKi2To3cXnSQ7hyY"

# Bot Owner ID (set to your Telegram ID)
OWNER_ID = 8566689610

# Files for persistence
DATA_DIR = "bot_data"
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
AUTHORIZED_FILE = os.path.join(DATA_DIR, "authorized.json")
KNOWN_GROUPS_FILE = os.path.join(DATA_DIR, "known_groups.json")

# Running tasks per chat (so we can stop them cleanly)
running_tasks = {}  # chat_id -> asyncio.Task

# Messages list (kept exactly as you requested)
MESSAGES = [
    " {name} မင်းအမေဖာသယ်မသေတာကိုလာလာမတင်ပြနဲ့စောက်ဖြစ်မရှိတဲ့ဟာလေး ✌️😜 ",
    " {name} မင်းမာ ‌စောက်သုံးမကျတဲ့ဦးနှောက်ကြီးရှိနေသရွှေ့တော့မင်းကဘယ်နေရာမှာမဘောင်ဝင်ဘူး 🫵😂 ",
    " {name} မင်းရဲ့ခေါင်းကဘယ်နေရာမာသုံးစားလို့ငါရှေ့မာလာပီးခစားပြနေတာလည်းစောက်ဝက် 🤨 ",
    " {name} မင်းစောက်သုံးမကျတာလူသိကုန်ပီမင်းရဲ့ brain ကို Update လေးလုပ်လိုက် 🤣🤣 ",
    " {name} ငါကဆရာနတ်စောင်းရဲ့လက်သုံးတော်လေမင်းထက်အဆတစ်ရာကြမ်းတယ်‌‌ကလေး 🥳🥳 ",
    "{name} မင်းရဲ့စောက်သုံးမကျတဲ့ brain ကိုဘယ်လိုတောင်ပြုပြင်ပေးရပ့မလဲနော 🤪🤪",
    " {name} ဟိတ်ဝက်မင်းကဖာသယ်မသားသေးသေး‌လေးဆိုဟုတ်လားမင်းစောက်ကြောင်းကလဲမလှဘူးကွာ 🙀 ",
    " {name} ငါရိုက်ရင်ခွေးမျိုးကန်းသွားမယ်နောမင်းရဲ့စောက်သုံးမကျတဲ့အကျင့်စရိုက်လေကိုပြင်အုန်းညီလေး 🤓🤌 ",
    " {name} ဖာတန်းမာဈေးမရလို့ Telegram မာလာပီးရှာစားနေတာဆိုစောက်သုံးလဲမကျဘူး 😭 ",
    " {name} မင်းကိုစောက်သုံးကျသွားအောင်ပြင်ပေးမယ်လေ အ ဖေလေးတော့ခေါ်ညီလေး ",
    " {name} မင်းစောက်ခွက်ကိုသုတ်ရည်နဲ့ဒဲ့ဖြန်းပေးမယ် အရင်ဆုံးသတ်ထွက်အောင်မင်းညီမကိုငါ့ဆီလွတ် 👌 ",
    " {name} မျိုးမစစ်ကိုက်လေမျိုးမစစ်နာနာကိုက်ဟ ပျော့တယ်အားထည့်ကိုက်စောက်ခွေး ",
    " {name} သွားကြိုးနေတာလားမင်းစောက်သုံးလဲမကျဘူးကွာ လမ်ဘေးခွေးတောင်မင်းထက်သာတယ် ",
]

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

# --- Persistence helpers ---

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_set_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(int(x) for x in data)
    except Exception:
        return set()

def save_set_to_file(s: set, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([int(x) for x in s], f)
    except Exception as e:
        logger.exception("Failed to save %s: %s", path, e)

ensure_data_dir()
ADMINS = load_set_from_file(ADMINS_FILE)
AUTHORIZED = load_set_from_file(AUTHORIZED_FILE)
KNOWN_GROUPS = load_set_from_file(KNOWN_GROUPS_FILE)

# Ensure owner is always in AUTHORIZED
AUTHORIZED.add(OWNER_ID)
save_set_to_file(AUTHORIZED, AUTHORIZED_FILE)

# --- Helpers ---

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS or is_owner(user_id)

def is_authorized(user_id: int) -> bool:
    return user_id in AUTHORIZED or is_admin(user_id)

async def resolve_target_id(context: ContextTypes.DEFAULT_TYPE, arg: str, update: Update):
    if not arg:
        if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
            u = update.message.reply_to_message.from_user
            return u.id, (u.full_name or u.username or str(u.id))
        return None, None

    if arg.isdigit():
        return int(arg), arg

    username = arg.lstrip("@")
    try:
        chat: Chat = await context.bot.get_chat(username)
        display = getattr(chat, "full_name", None) or getattr(chat, "title", None) or getattr(chat, "username", None) or username
        return int(chat.id), display
    except Exception as e:
        logger.debug("resolve_target_id: get_chat failed: %s", e)
        return None, None

async def start_spam_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int, mention_text: str, speed: float):
    i = 0
    try:
        while True:
            msg = MESSAGES[i % len(MESSAGES)].format(name=mention_text)
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            i += 1
            await asyncio.sleep(speed)
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.exception("Error in spam loop: %s", e)

async def ensure_known_group(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        me = await context.bot.get_me()
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        if member.status in ("administrator", "creator"):
            KNOWN_GROUPS.add(chat_id)
            save_set_to_file(KNOWN_GROUPS, KNOWN_GROUPS_FILE)
    except Exception:
        pass

# --- Commands ---

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ You don't have permission to use /save.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /save <message>")
        return
    new_msg = " ".join(context.args)
    MESSAGES.append(new_msg)
    await update.message.reply_text(f"✅ Saved new message. Total messages: {len(MESSAGES)}")

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the Bot Owner can give permission.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /gift <user_id_or_username>")
        return
    target_arg = context.args[0]
    target_id, display = await resolve_target_id(context, target_arg, update)
    if not target_id:
        await update.message.reply_text("❌ Could not resolve target. Use numeric id, @username, or reply to a user.")
        return
    AUTHORIZED.add(target_id)
    save_set_to_file(AUTHORIZED, AUTHORIZED_FILE)
    await update.message.reply_text(f"✅ Permission granted to {display} (ID: {target_id})")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use /attack.")
        return

    chat_id = update.effective_chat.id
    await ensure_known_group(context, chat_id)

    target_arg = context.args[0] if len(context.args) >= 1 else ""
    target_id, display = await resolve_target_id(context, target_arg, update)
    if not target_id:
        await update.message.reply_text("❌ Could not resolve target. Use numeric id, @username, or reply to a user.")
        return

    mention_text = f'<a href="tg://user?id={target_id}">{display}</a>'

    if chat_id in running_tasks and not running_tasks[chat_id].done():
        await update.message.reply_text("⚠️ A loop is already running in this chat. Use /stop to stop it first.")
        return

    task = asyncio.create_task(start_spam_loop(context, chat_id, mention_text, 0.2))
    running_tasks[chat_id] = task
    await update.message.reply_text(f"▶️ Attack started on {display}.")

async def flash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use /flash.")
        return

    chat_id = update.effective_chat.id
    await ensure_known_group(context, chat_id)

    target_arg = context.args[0] if len(context.args) >= 1 else ""
    target_id, display = await resolve_target_id(context, target_arg, update)
    if not target_id:
        await update.message.reply_text("❌ Could not resolve target. Use numeric id, @username, or reply to a user.")
        return

    mention_text = f'<a href="tg://user?id={target_id}">{display}</a>'

if chat_id in running_tasks and not running_tasks[chat_id].done():
        await update.message.reply_text("⚠️ A loop is already running in this chat. Use /stop to stop it first.")
        return

    task = asyncio.create_task(start_spam_loop(context, chat_id, mention_text, 0.2))
    running_tasks[chat_id] = task
    await update.message.reply_text(f"▶️ Flash started on {display}.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use /stop.")
        return

    task = running_tasks.get(chat_id)
    if task and not task.done():
        task.cancel()
        await asyncio.sleep(0.1)
        running_tasks.pop(chat_id, None)
        await update.message.reply_text("⏹ Stopped.")
    else:
        await update.message.reply_text("ℹ️ Nothing is running in this chat.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 1:
        arg = context.args[0]
        target_id, display = await resolve_target_id(context, arg, update)
        if not target_id:
            await update.message.reply_text("❌ Could not resolve that user.")
            return
        await update.message.reply_text(f"User: {display}\nID: {target_id}")
        return

    if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
        u = update.message.reply_to_message.from_user
        await update.message.reply_text(f"User: {u.full_name or u.username}\nID: {u.id}")
        return

    await update.message.reply_text("Usage: /id (reply) or /id @username or /id <id>")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the Bot Owner can use /post.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /post <message>")
        return
    text = " ".join(context.args)
    if not KNOWN_GROUPS:
        await update.message.reply_text("ℹ️ No known groups where bot is admin.")
        return

    sent = 0
    for gid in list(KNOWN_GROUPS):
        try:
            await context.bot.send_message(chat_id=gid, text=text)
            sent += 1
        except Exception as e:
            logger.debug("Failed to post to %s: %s", gid, e)
    await update.message.reply_text(f"✅ Posted to {sent} groups.")

async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the Bot Owner can set admins.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /setadmin <user_id_or_username>")
        return
    target_arg = context.args[0]
    target_id, display = await resolve_target_id(context, target_arg, update)
    if not target_id:
        await update.message.reply_text("❌ Could not resolve target.")
        return
    ADMINS.add(target_id)
    save_set_to_file(ADMINS, ADMINS_FILE)
    await update.message.reply_text(f"✅ {display} (ID: {target_id}) added to admins.")

async def deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the Bot Owner can remove admins.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /deladmin <user_id_or_username>")
        return
    target_arg = context.args[0]
    target_id, display = await resolve_target_id(context, target_arg, update)
    if not target_id:
        await update.message.reply_text("❌ Could not resolve target.")
        return
    ADMINS.discard(target_id)
    save_set_to_file(ADMINS, ADMINS_FILE)
    await update.message.reply_text(f"✅ {display} (ID: {target_id}) removed from admins.")

async def any_command_hook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        await ensure_known_group(context, chat_id)
    except Exception:
        pass

# --- App setup ---
def main():
    app = Application.builder().token(TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("save", save_message))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("flash", flash))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("post", post))

    # Admin management
    app.add_handler(CommandHandler("setadmin", setadmin))
    app.add_handler(CommandHandler("deladmin", deladmin))

    # Hook to register chats
    app.add_handler(CommandHandler(["save", "gift", "attack", "flash", "stop", "id", "post", "setadmin", "deladmin"], any_command_hook))

    print("Bot is running...")
    app.run_polling()

if name == "main":
    main()
