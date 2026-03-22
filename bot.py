import os
import asyncio
from telethon import TelegramClient, events

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = TelegramClient("hostbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Running processes store
running_bots = {}

# ======================
# START
# ======================
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🤖 Hosting Bot Ready!\n\n"
        "📌 Send .py file to run your bot\n"
        "📌 Use /add to add more bots"
    )

# ======================
# ADD COMMAND
# ======================
@client.on(events.NewMessage(pattern="/add"))
async def add_bot(event):
    await event.reply("📥 Send another .py file to add new bot.")

# ======================
# HANDLE FILE
# ======================
@client.on(events.NewMessage(func=lambda e: e.file))
async def handle_file(event):
    user_id = event.sender_id
    file = await event.download_media()

    if not file.endswith(".py"):
        return await event.reply("❌ Only .py files allowed!")

    bot_name = f"bot_{user_id}_{len(running_bots)+1}.py"
    os.rename(file, bot_name)

    await event.reply(f"🚀 Running {bot_name}...")

    process = await asyncio.create_subprocess_exec(
        "python", bot_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    running_bots[bot_name] = process

    await event.reply(f"✅ {bot_name} is now running!")

# ======================
# LIST RUNNING
# ======================
@client.on(events.NewMessage(pattern="/list"))
async def list_bots(event):
    if not running_bots:
        return await event.reply("❌ No bots running.")

    msg = "🤖 Running Bots:\n"
    for name in running_bots:
        msg += f"• {name}\n"

    await event.reply(msg)

# ======================
# STOP ALL
# ======================
@client.on(events.NewMessage(pattern="/stop"))
async def stop_all(event):
    for name, proc in running_bots.items():
        proc.kill()
    running_bots.clear()

    await event.reply("🛑 All bots stopped!")

print("✅ Hosting Bot Running...")
client.run_until_disconnected()
