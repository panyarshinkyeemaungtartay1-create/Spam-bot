import asyncio
import time
import sqlite3
import os
import json

from telethon import TelegramClient, events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import FloodWaitError
from telethon.utils import get_display_name

# ==========================
# Config
# ==========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8469308844  # Bot Owner ID
DB_FILE = "bot_data.db"

# ==========================
# Database Setup
# ==========================
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS asave(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS rsave(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS tsave(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS bot_admins(id INTEGER PRIMARY KEY)""")
conn.commit()

# ==========================
# Bot Client
# ==========================

async def main():
    bot = TelegramClient("bot", API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    print("Bot Started...")

    await bot.run_until_disconnected()

# ==========================
# Permission Check
# ==========================
def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    cursor.execute("SELECT id FROM bot_admins WHERE id=?", (user_id,))
    return cursor.fetchone() is not None

def is_member(user_id):
    return not (is_owner(user_id) or is_admin(user_id))


GROUPS = set()

@bot.on(events.ChatAction)
async def save_group(event):
    if event.is_group:
        GROUPS.add(event.chat_id)

# ==========================
# RSAVE FILE SYSTEM
# ==========================

RSAVE_FILE = "rsave_data.json"
rsave_list = []

def save_rsave():
    with open(RSAVE_FILE, "w") as f:
        json.dump(rsave_list, f)

def load_rsave():
    global rsave_list
    if os.path.exists(RSAVE_FILE):
        with open(RSAVE_FILE, "r") as f:
            rsave_list = json.load(f)
    else:
        rsave_list = []

# ==========================
# Global States
# ==========================
attack_tasks = {}
troll_targets = {}
delete_targets = {}
att_targets = {}
attack_speed = 0.5

reply_task_started = False
calling_task = None
stop_calling = False

REPLY_DURATION = 86400  # 24 hours
REPLY_INTERVAL = 1

reply_targets = {}
bot_id = None

current_index = 0

# ==========================
# SPEED CONTROL
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/spee (.+)"))
async def set_speed(event):
    global attack_speed

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    try:
        attack_speed = float(event.pattern_match.group(1))
        if attack_speed < 0.1:
            attack_speed = 0.1
        await event.reply(f"အမြန်နှုန်းကို  {attack_speed} စက္ကန်သို့ချိန်ညှီလိုက်ပါပီ")
    except:
        await event.reply("Invalid number.")

# ==========================
# ATTACK
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/attack"))
async def attack_user(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    # -------- TARGET DETECT --------
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
    else:
        args = event.message.text.split()
        if len(args) < 2:
            return await event.reply("မျိုးမစစ်တွေကိုနှိမ်နှင်းစေချင်ရင်မိန့်ကိုမှန်ကန်စွာအသုံးပြုပါ /Attack (Reply_Reply_Reply) ")

        try:
            entity = await bot.get_entity(args[1])
            target_id = entity.id
        except:
            return await event.reply("မင်းပြောတဲ့ခွေးမျိုးလေးကိုရှာမတွေ့သေးပါ Try.")

    # -------- OWNER PROTECTION --------
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    # -------- GET ASAVE TEXTS --------
    texts = cursor.execute(
        "SELECT text FROM asave ORDER BY id ASC"
    ).fetchall()

    if not texts:
        return await event.reply("နှိမ်နှင်းရမဲ့စာသားတွေကိုသိမ်းဆည်းထားချင်းမရှိသောကြေင့်ပြုလုပ်၍မရပါ")

    # -------- CHECK ALREADY RUNNING --------
    if target_id in attack_tasks:
        return await event.reply("Already attacking this user.")

    user = await bot.get_entity(target_id)

    # -------- SPAM LOOP --------
    async def spam():
        index = 0
        end_time = asyncio.get_event_loop().time() + (24 * 60 * 60)

        try:
            while asyncio.get_event_loop().time() < end_time:

                if target_id not in attack_tasks:
                    break

                text = texts[index % len(texts)][0]

                message = (
                    f"<a href='tg://user?id={user.id}'>{user.first_name}</a> {text}"
                )

                try:
                    await bot.send_message(
                        event.chat_id,
                        message,
                        parse_mode="html"
                    )

                # 🔥 429 Catch (FloodWait)
                except FloodWaitError:
                    print("⚠️ 429 Detected → Sleeping 3 seconds")
                    await asyncio.sleep(3)
                    continue

                index += 1
                await asyncio.sleep(attack_speed)

        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(spam())
    attack_tasks[target_id] = task

    await event.reply("မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")

# ==========================
# STOP ALL ATTACKS
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/stops"))
async def stop_attack(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("သခင်နတ်စောင်းဆီက ခွင့်ပြုချက်မရထားပါ")

    for task in attack_tasks.values():
        task.cancel()

    attack_tasks.clear()

    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

# ==============================
# RSAVE (OWNER ONLY)
# ==============================

@bot.on(events.NewMessage(pattern=r"(?i)^/rsave (.+)"))
async def save_r(event):

    if not is_owner(event.sender_id):
        return

    text = event.pattern_match.group(1)

    rsave_list.append(text)
    save_rsave()

    await event.reply(f"Saved ✅\nTotal Saved: {len(rsave_list)}")

@bot.on(events.NewMessage(pattern=r"(?i)^/rlist$"))
async def list_r(event):

    if not is_owner(event.sender_id):
        return

    if not rsave_list:
        return await event.reply("Rsave list is empty.")

    formatted = "\n\n".join(
        [f"{i+1}. {msg}" for i, msg in enumerate(rsave_list)]
    )

    await event.reply(f"🔥 Rsave List 🔥\n\n{formatted}")

  # ================= REPLY ACTIVATE =================

@bot.on(events.NewMessage(pattern=r"(?i)^/reply$"))
async def set_reply(event):
    global bot_id

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if reply_msg.sender_id == bot_id:
        return

    if is_owner(reply_msg.sender_id):
        return

    target_id = reply_msg.sender_id
    target_entity = await bot.get_entity(target_id)

    if target_id not in reply_targets:
        reply_targets[target_id] = {
            "expire": time.time() + REPLY_DURATION,
            "base_msg_id": reply_msg.id,
            "chat_id": event.chat_id,
            "last_bot_msg": None,
            "mode": "reply",
            "username": target_entity.username,
            "index": 0
        }

    asyncio.create_task(reply_loop(target_id))

    await event.reply("မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")

# ================= UNREPLY (OWNER + ADMIN) =================

@bot.on(events.NewMessage(pattern=r"(?i)^/unreply"))
async def unset_reply(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return  # Owner/Admin မဟုတ်ရင် ignore

    # Reply မပြန်ဘဲ ရိုက်လိုက်ရင် → All Stop
    if not event.is_reply:

        if not reply_targets:
            return await event.reply("ဘယ်လိုခွေးမျိုး အမျိုးစားများကိုမှနှိမ်နှင်းထားချင်းမရှိသေးပါ")

        reply_targets.clear()
        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")

    # Reply ပြန်ပြီး ရိုက်ရင် → That user only stop
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    if target_id in reply_targets:
        del reply_targets[target_id]
        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")

    await event.reply("This user not active.")

# ================= TRACK USER NEW MESSAGE =================

@bot.on(events.NewMessage)
async def track_user(event):
    global bot_id

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if event.sender_id == bot_id:
        return

@bot.on(events.NewMessage)
async def track_user(event):
    global bot_id

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if event.sender_id == bot_id:
        return

    if event.sender_id in reply_targets:
        data = reply_targets[event.sender_id]
        data["base_msg_id"] = event.id
        data["mode"] = "reply"

# ================= DELETE DETECT =================

@bot.on(events.MessageDeleted)
async def detect_delete(event):
    for target_id, data in reply_targets.items():
        if data["last_bot_msg"] in event.deleted_ids:
            data["mode"] = "mention"


async def reply_loop(target_id):
    global current_index

    while target_id in reply_targets:

        data = reply_targets.get(target_id)
        if not data:
            break

        if not rsave_list:
            await asyncio.sleep(2)
            continue

        try:
            text = rsave_list[current_index]

            msg = await bot.send_message(
                data["chat_id"],
                text,
                reply_to=data["base_msg_id"]
            )

            data["last_bot_msg"] = msg.id

            current_index += 1

            if current_index >= len(rsave_list):
                current_index = 0

        except:
            pass

        await asyncio.sleep(REPLY_INTERVAL)


# ==========================
# TRACK DELETE
# ==========================
@bot.on(events.MessageDeleted)
async def track_delete(event):

    for uid, data in reply_targets.items():
        if data["base_msg_id"] in event.deleted_ids:
            data["base_msg_id"] = None
            data["mode"] = "mention"

# TRACK DELETE# ==========================
# REPLY ENGINE (REPLY + MENTION)
# ==========================
async def reply_engine():

    while True:
        await asyncio.sleep(REPLY_INTERVAL)

        if not rsave_list:
            continue

        for uid in list(reply_targets.keys()):

            data = reply_targets.get(uid)
            if not data:
                continue

            # ✅ EXPIRE CHECK (FIXED)
            if time.time() > data["expire"]:
                del reply_targets[uid]
                continue

            text = rsave_list[data["index"] % len(rsave_list)]
            data["index"] += 1

            try:

                # delete previous bot message
                if data["last_bot_msg"]:
                    try:
                        await bot.delete_messages(
                            data["chat_id"],
                            data["last_bot_msg"]
                        )
                    except:
                        pass

                # ==========================
                # REPLY MODE
                # ==========================
                if data["mode"] == "reply" and data["base_msg_id"]:

                    bot_msg = await bot.send_message(
                        data["chat_id"],
                        text,
                        reply_to=data["base_msg_id"]
                    )

                # ==========================
                # MENTION MODE
                # ==========================
                else:

                    if data["username"]:
                        mention_text = f"@{data['username']} {text}"
                        bot_msg = await bot.send_message(
                            data["chat_id"],
                            mention_text
                        )
                    else:
                        mention_text = f"<a href='tg://user?id={uid}'>User</a> {text}"
                        bot_msg = await bot.send_message(
                            data["chat_id"],
                            mention_text,
                            parse_mode="html"
                        )

                data["last_bot_msg"] = bot_msg.id

            except Exception as e:
                print("Reply Engine Error:", e)

# ==========================
# TROLL SYSTEM
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/troll"))
async def set_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to user to activate.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # 🚫 OWNER PROTECTION
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    troll_targets[target_id] = {
        "index": 0
    }

    await event.reply("မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")


@bot.on(events.NewMessage(pattern=r"(?i)^/untroll"))
async def unset_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

    troll_targets.clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")


# ==========================
# AUTO MONITOR
# ==========================

@bot.on(events.NewMessage(incoming=True))
async def monitor_messages(event):

    if event.sender_id is None:
        return

    # 🚫 OWNER IMMUNITY
    if is_owner(event.sender_id):
        return

    # ================= REPLY MODE =================
    if event.sender_id in reply_targets:

        texts = cursor.execute(
            "SELECT text FROM rsave ORDER BY id ASC"
        ).fetchall()

        if texts:

            data = reply_targets[event.sender_id]

            # 24h expire check
            if time.time() > data.get("expire", 0):
                del reply_targets[event.sender_id]
                return

            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1

            mention = f"<a href='tg://user?id={event.sender_id}'>User</a>"
            message = f"{mention}\n{text}"

            reply_mode = True

            # Check if last bot message deleted
            if data.get("last_bot_msg"):
                try:
                    await bot.get_messages(event.chat_id, ids=data["last_bot_msg"])
                except:
                    reply_mode = False

            try:
                if reply_mode:
                    msg = await event.reply(message, parse_mode="html")
                else:
                    msg = await bot.send_message(
                        event.chat_id,
                        message,
                        parse_mode="html"
                    )

                data["last_bot_msg"] = msg.id

            except:
                pass

            await asyncio.sleep(attack_speed)


    # ================= TROLL MODE =================
    if event.sender_id in troll_targets:

        texts = cursor.execute(
            "SELECT text FROM tsave ORDER BY id ASC"
        ).fetchall()

        if texts:

            data = troll_targets[event.sender_id]
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1

            try:
                await event.reply(text)
            except:
                pass

            await asyncio.sleep(attack_speed)

# ==========================
# DELETE ACTIVATE
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/delete"))
async def set_delete(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to target user to activate.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # 🚫 OWNER IMMUNITY
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    delete_targets[target_id] = {
        "chat_id": event.chat_id
    }

    await event.reply("အဲ့ခွေးမျိုးရဲ့စာကို တစ်ကြောင်းလေးတောင်မတွေ့စေရဘူး")


# ==========================
# UNDELETE
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/undelete"))
async def unset_delete(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("အဲ့ဖာသယ်မသားလေး မှတ်လောက်ရောပေါ့ ဘေးမဲ့လွတ်ပေးလိုက်မယ် ")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    if target_id in delete_targets:
        del delete_targets[target_id]
        await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")


# ==========================
# AUTO DELETE MONITOR
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def auto_delete_monitor(event):

    if event.sender_id is None:
        return

    # 🚫 OWNER IMMUNITY
    if is_owner(event.sender_id):
        return

    # ================= DELETE MODE =================
    if event.sender_id in delete_targets:

        try:
            await bot.delete_messages(
                event.chat_id,
                event.id
            )
        except:
            pass

# ==========================
# /ATT (BOT ADMIN ONLY)
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/att"))
async def set_att(event):

    if not is_bot_admin(event.sender_id):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # Owner immune
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    att_targets[target_id] = event.chat_id

    await event.reply("အဲ့ဒိမျိုးမစစ်လေးကို 20s ချားစာတစ်ကြောင်းပဲပေးရေးလိုက်မယ်")

# ==========================
# /UNATT (BOT ADMIN ONLY)
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/unatt"))
async def unset_att(event):

    if not is_bot_admin(event.sender_id):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    if target_id in att_targets:
        del att_targets[target_id]
        await event.reply("အဲ့ဖာသယ်မသားလေး မှတ်လောက်ရောပေါ့ ဘေးမဲ့လွတ်ပေးလိုက်မယ်")
    else:
        await event.reply("User not active.")

# ==========================
# AUTO MONITOR SYSTEM
# ==========================

@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):

    if event.sender_id is None:
        return

    if event.sender_id not in att_targets:
        return

    chat_id = att_targets.get(event.sender_id)

    if not chat_id:
        return

    try:
        # MUTE
        await bot.edit_permissions(
            chat_id,
            event.sender_id,
            send_messages=False
        )

        # 20 seconds mute
        await asyncio.sleep(20)

        # UNMUTE (only if still in att list)
        if event.sender_id in att_targets:
            await bot.edit_permissions(
                chat_id,
                event.sender_id,
                send_messages=True
            )

    except Exception as e:
        print("Mute Error:", e)

# ==========================
# CALLING COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"/Calling (.+)"))
async def start_calling(event):
    global calling_task, stop_calling

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied")

    text = event.pattern_match.group(1)

    if calling_task and not calling_task.done():
        return await event.reply("⚠️ Calling already running.")

    stop_calling = False
    calling_task = bot.loop.create_task(
        calling_engine(event.chat_id, text)
    )

    await event.reply("📢 Calling started...")


# ==========================
# STOP CALLING
# ==========================# ==========================
# AUTO DELETE MONITOR
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def auto_delete_monitor(event):

    if event.sender_id is None:
        return

    # 🚫 OWNER IMMUNITY
    if is_owner(event.sender_id):
        return

    # ================= DELETE MODE =================
    if event.sender_id in delete_targets:

        try:
            await bot.delete_messages(
                event.chat_id,
                event.id
            )
        except:
            pass

# ==========================
# /ATT (BOT ADMIN ONLY)
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/att"))
async def set_att(event):

    if not is_bot_admin(event.sender_id):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # Owner immune
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    att_targets[target_id] = event.chat_id

    await event.reply("အဲ့ဒိမျိုးမစစ်လေးကို 20s ချားစာတစ်ကြောင်းပဲပေးရေးလိုက်မယ်")

# ==========================
# /UNATT (BOT ADMIN ONLY)
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/unatt"))
async def unset_att(event):

    if not is_bot_admin(event.sender_id):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    if target_id in att_targets:
        del att_targets[target_id]
        await event.reply("အဲ့ဖာသယ်မသားလေး မှတ်လောက်ရောပေါ့ ဘေးမဲ့လွတ်ပေးလိုက်မယ်")
    else:
        await event.reply("User not active.")

# ==========================
# AUTO MONITOR SYSTEM
# ==========================

@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):

    if event.sender_id is None:
        return

    if event.sender_id not in att_targets:
        return

    chat_id = att_targets.get(event.sender_id)

    if not chat_id:
        return

    try:
        # MUTE
        await bot.edit_permissions(
            chat_id,
            event.sender_id,
            send_messages=False
        )

        # 20 seconds mute
        await asyncio.sleep(20)

        # UNMUTE (only if still in att list)
        if event.sender_id in att_targets:
            await bot.edit_permissions(
                chat_id,
                event.sender_id,
                send_messages=True
            )

    except Exception as e:
        print("Mute Error:", e)

# ==========================
# CALLING COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"/Calling (.+)"))
async def start_calling(event):
    global calling_task, stop_calling

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied")

    text = event.pattern_match.group(1)

    if calling_task and not calling_task.done():
        return await event.reply("⚠️ Calling already running.")

    stop_calling = False
    calling_task = bot.loop.create_task(
        calling_engine(event.chat_id, text)
    )

    await event.reply("📢 Calling started...")


# ==========================
# STOP CALLING
# ==========================

@bot.on(events.NewMessage(pattern=r"/Stopcall$"))
async def stop_call(event):
    global stop_calling

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied")

    stop_calling = True
    await event.reply("🛑 Calling stopped.")


# ==========================
# CALLING ENGINE
# ==========================
async def calling_engine(chat_id, text):
    global stop_calling

    members = []

    async for user in bot.iter_participants(chat_id):
        if user.bot:
            continue
        members.append(user)

    batch_size = 5

    for i in range(0, len(members), batch_size):

        if stop_calling:
            break

        batch = members[i:i + batch_size]

        mentions = []
        for user in batch:
            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
            mentions.append(mention)

        message = " ".join(mentions) + "\n\n" + text

        try:
            await bot.send_message(
                chat_id,
                message,
                parse_mode="html"
            )
        except:
            pass

        await asyncio.sleep(2)  # Anti flood delay

    stop_calling = False

# ==========================
# Database Save/List
# ==========================

@bot.on(events.NewMessage(pattern=r"/Asave (.+)"))
async def save_attack(event):
    if is_owner(event.sender_id) or is_admin(event.sender_id):
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        await event.reply("Attack text saved ✅")
    else:
        await event.reply("❌ Permission denied")

@bot.on(events.NewMessage(pattern=r"/Alist"))
async def list_attack(event):
    rows = cursor.execute("SELECT id, text FROM asave").fetchall()
    if rows:
        msg = "\n".join([f"{r[0]}: {r[1]}" for r in rows])
        await event.reply(f"🔥 Attack List:\n{msg}")
    else:
        await event.reply("No attack texts saved.")


@bot.on(events.NewMessage(pattern=r"/Tsave (.+)"))
async def save_troll(event):
    if is_owner(event.sender_id) or is_admin(event.sender_id):
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()
        await event.reply("Troll text saved ✅")
    else:
        await event.reply("❌ Permission denied")


@bot.on(events.NewMessage(pattern=r"/Tlist"))
async def list_troll(event):
    rows = cursor.execute("SELECT id, text FROM tsave").fetchall()
    if rows:
        msg = "\n".join([f"{r[0]}: {r[1]}" for r in rows])
        await event.reply(f"📜 Troll List:\n{msg}")
    else:
        await event.reply("No troll texts saved.")

# ==========================
# Info Commands
# ==========================

@bot.on(events.NewMessage(pattern=r"/Chatid"))
async def chat_info(event):
    chat = await event.get_chat()
    admins = await bot.get_participants(chat, filter=ChannelParticipantsAdmins)
    admin_list = [f"{a.id}" for a in admins]
    await event.reply(f"Group: {chat.title}\nID: {chat.id}\nOwner: {OWNER_ID}\nAdmins: {admin_list}")

@bot.on(events.NewMessage(pattern=r"/Acc"))
async def acc_info(event):
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        user = await bot.get_entity(reply_msg.sender_id)
        status = "Owner" if is_owner(user.id) else "Admin" if is_admin(user.id) else "Member"
        await event.reply(f"👤 Name: {user.first_name}\n🆔 ID: {user.id}\nStatus: {status}")

@bot.on(events.NewMessage(pattern=r"/gplist"))
async def group_list(event):
    # SQLite ထဲမှာ groups table ထည့်ထားသင့်သည်
    cursor.execute("""CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY)""")
    rows = cursor.execute("SELECT id FROM groups").fetchall()
    if rows:
        msg = "\n".join([str(r[0]) for r in rows])
        await event.reply(f"📂 Groups:\n{msg}")
    else:
        await event.reply("No groups saved.")

@bot.on(events.NewMessage(pattern=r"/Botadmlist"))
async def list_admins(event):
    rows = cursor.execute("SELECT id FROM bot_admins").fetchall()
    if rows:
        msg = "\n".join([str(r[0]) for r in rows])
        await event.reply(f"👮 Bot Admins:\n{msg}")
    else:
        await event.reply("No Bot Admins assigned.")

@bot.on(events.NewMessage(pattern=r"(?i)/share"))
async def share_message(event):

    if not is_owner(event.sender_id):
        return await event.reply("❌ Owner Only.")

    if not event.is_reply:
        return await event.reply("Reply to a message to share.")

    reply_msg = await event.get_reply_message()

    shared_count = 0
    failed_count = 0

    start_msg = await event.reply("📤 Sharing started...")

    for group_id in GROUPS:

        try:
            await bot.forward_messages(group_id, reply_msg)
            shared_count += 1
            await asyncio.sleep(1)

        except Exception:
            failed_count += 1
            continue

    await start_msg.edit(
        f"✅ Share Completed\n\n"
        f"📦 Shared to: {shared_count} groups\n"
        f"❌ Failed: {failed_count}"
    )

# ==========================
# Admin Management
# ==========================

@bot.on(events.NewMessage(pattern=r"^/Botadmin (\d+)$"))
async def add_admin(event):
    if not is_owner(event.sender_id):
        return

    uid = int(event.pattern_match.group(1))

    cursor.execute("INSERT OR IGNORE INTO bot_admins(id) VALUES(?)", (uid,))
    conn.commit()

    await event.reply(f"✅ User {uid} added as Bot Admin")


@bot.on(events.NewMessage(pattern=r"^/Readam (\d+)$"))
async def remove_admin(event):
    if not is_owner(event.sender_id):
        return

    uid = int(event.pattern_match.group(1))

    cursor.execute("DELETE FROM bot_admins WHERE id=?", (uid,))
    conn.commit()

    await event.reply(f"❌ User {uid} removed from Bot Admin")

load_rsave()

# ==========================
# Run Bot
# ==========================
if __name__ == "__main__":
    asyncio.run(main())
