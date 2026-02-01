from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import logging

# --- Bot Token & Owner ID ---
TOKEN = "8561696503:AAGhIRdmo2PQCdOSWjCR_96qOeAPb7KoVJw"
OWNER_ID = 8566689610

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Global variables ---
spam_messages = [
    "မင်းက စောက်သုံးမကျတဲ့သူပါ။",
    "{name} မင်းအမေဖာသယ်မသေတာကိုလာလာမတင်ပြနဲ့စောက်ဖြစ်မရှိတဲ့ဟာလေး ✌️😜",
    "{name} မင်းမာ ‌စောက်သုံးမကျတဲ့ဦးနှောက်ကြီးရှိနေသရွှေ့တော့မင်းကဘယ်နေရာမှာမဘောင်ဝင်ဘူး 🫵😂",
    "{name} မင်းရဲ့ခေါင်းကဘယ်နေရာမာသုံးစားလို့ငါရှေ့မာလာပီးခစားပြနေတာလည်းစောက်ဝက် 🤨",
    "{name} မင်းစောက်သုံးမကျတာလူသိကုန်ပီမင်းရဲ့ brain ကို Update လေးလုပ်လိုက် 🤣🤣",
    "{name} ငါကဆရာနတ်စောင်းရဲ့လက်သုံးတော်လေမင်းထက်အဆတစ်ရာကြမ်းတယ်‌‌ကလေး 🥳🥳",
    "{name} မင်းရဲ့စောက်သုံးမကျတဲ့ brain ကိုဘယ်လိုတောင်ပြုပြင်ပေးရပ့မလဲနော 🤪🤪",
    "{name} ဟိတ်ဝက်မင်းကဖာသယ်မသားသေးသေး‌လေးဆိုဟုတ်လားမင်းစောက်ကြောင်းကလဲမလှဘူးကွာ 🙀",
    "{name} ငါရိုက်ရင်ခွေးမျိုးကန်းသွားမယ်နောမင်းရဲ့စောက်သုံးမကျတဲ့အကျင့်စရိုက်လေကိုပြင်အုန်းညီလေး 🤓🤌",
    "{name} ဖာတန်းမာဈေးမရလို့ Telegram မာလာပီးရှာစားနေတာဆိုစောက်သုံးလဲမကျဘူး 😭",
    "{name} မင်းကိုစောက်သုံးကျသွားအောင်ပြင်ပေးမယ်လေ အ ဖေလေးတော့ခေါ်ညီလေး",
    "{name} မင်းစောက်ခွက်ကိုသုတ်ရည်နဲ့ဒဲ့ဖြန်းပေးမယ် အရင်ဆုံးသတ်ထွက်အောင်မင်းညီမကိုငါ့ဆီလွတ် 👌",
    "{name} မျိုးမစစ်ကိုက်လေမျိုးမစစ်နာနာကိုက်ဟ ပျော့တယ်အားထည့်ကိုက်စောက်ခွေး",
    "{name} သွားကြိုးနေတာလားမင်းစောက်သုံးလဲမကျဘူးကွာ လမ်ဘေးခွေးတောင်မင်းထက်သာတယ်",
]

spamming = {}
admins = set()
gifted_users = set()
known_groups = set()

# --- Helper functions ---
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    return user_id in admins or is_owner(user_id)

def is_gifted(user_id: int) -> bool:
    return user_id in gifted_users or is_owner(user_id)

# --- Commands ---
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("မင်း Admin မဟုတ်ပါ")
        return
    if not context.args:
        await update.message.reply_text("အသုံးပြုနည်း: /attack <user>")
        return
    target = context.args[0]
    chat_id = update.effective_chat.id
    spamming[chat_id] = True
    await update.message.reply_text(f"{target} ကို spam လုပ်နေပါသည်")
    while spamming.get(chat_id, False):
        for msg in spam_messages:
            await update.message.reply_text(msg.replace("{name}", target))
        await asyncio.sleep(1)

async def flash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("မင်း Admin မဟုတ်ပါ")
        return
    if not context.args:
        await update.message.reply_text("အသုံးပြုနည်း: /flash <user>")
        return
    target = context.args[0]
    chat_id = update.effective_chat.id
    spamming[chat_id] = True
    await update.message.reply_text(f"{target} ကို အမြန် spam လုပ်နေပါသည်")
    while spamming.get(chat_id, False):
        for msg in spam_messages:
            await update.message.reply_text(msg.replace("{name}", target))
        await asyncio.sleep(0.5)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    spamming[chat_id] = False
    await update.message.reply_text("Spam ကို ရပ်လိုက်ပါပြီ")

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("မင်း Owner မဟုတ်ပါ")
        return
    if not context.args:
        await update.message.reply_text("အသုံးပြုနည်း: /save <message>")
        return
    msg = " ".join(context.args)
    spam_messages.append(msg)
    await update.message.reply_text(f"Spam စာသားအသစ် သိမ်းပြီးပါပြီ: {msg}")

async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("မင်း Owner မဟုတ်ပါ")
        return
    if not spam_messages:
        await update.message.reply_text("Spam စာသား မရှိသေးပါ")
        return
    text = "Spam စာသားစာရင်း:\n" + "\n".join(spam_messages)
    await update.message.reply_text(text)

# --- Main ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("flash", flash))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("save", save))
    application.add_handler(CommandHandler("list", list_messages))

    application.run_polling()

if __name__ == "__main__":
    main()
