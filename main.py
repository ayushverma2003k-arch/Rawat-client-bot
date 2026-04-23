import json
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8728676554:AAHUzz9NXWK4b_UASN9Y0SACNGC9SBdyaGM"

OWNER_ID = 8044682416
ADMINS = [OWNER_ID]

# ✅ Multiple channels (public + private)
CHANNELS = [
    "@freefirehck999",
    "@HUPPA_MODZ"
    # -1001234567890  # private channel id
]

apps = {}
users = {}
pending_upload = {}

# ---------- LOAD ----------
def load_data():
    global apps, users
    try:
        with open("apps.json") as f:
            apps = json.load(f)
    except:
        apps = {}

    try:
        with open("users.json") as f:
            users = json.load(f)
    except:
        users = {}

# ---------- SAVE ----------
def save_apps():
    with open("apps.json", "w") as f:
        json.dump(apps, f, indent=4)

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# ---------- ROLE ----------
def is_admin(uid): return uid in ADMINS
def is_owner(uid): return uid == OWNER_ID

# ---------- JOIN CHECK ----------
async def is_joined(bot, user_id):
    if is_owner(user_id):
        return True

    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

# ---------- ANIMATION ----------
async def animate(msg, steps):
    for s in steps:
        await asyncio.sleep(0.7)
        await msg.edit_text(s)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    users[str(uid)] = users.get(str(uid), {"downloads":[]})
    save_users()

    msg = await update.message.reply_text(
        "👋 *Welcome to Premium App Store*\n\n⚡ Initializing...",
        parse_mode="Markdown"
    )

    await animate(msg, [
        "🔄 Checking access...",
        "⏳ Verifying channels..."
    ])

    if not await is_joined(context.bot, uid):
        buttons = []

        for ch in CHANNELS:
            if str(ch).startswith("@"):
                link = f"https://t.me/{ch.replace('@','')}"
                buttons.append([InlineKeyboardButton(f"📢 Join {ch}", url=link)])

        buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="check")])

        await msg.edit_text(
            "🚫 *Access Locked*\n\n👉 Join all channels to continue",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await msg.edit_text("🎉 *Access Granted!*\n\n🛒 Opening Store...", parse_mode="Markdown")
    await asyncio.sleep(1)
    await show_apps(msg)

# ---------- SHOW APPS ----------
async def show_apps(msg):
    if not apps:
        await msg.edit_text("📭 No apps available")
        return

    buttons = []
    for a in apps:
        buttons.append([
            InlineKeyboardButton(apps[a]["name"], callback_data=a)
        ])

    await msg.edit_text(
        "🛒 *App Store*\n\nSelect app:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------- CHECK ----------
async def check(update, context):
    q = update.callback_query
    uid = q.from_user.id

    if await is_joined(context.bot, uid):
        await q.message.edit_text("🎉 Verified!\nOpening store...")
        await show_apps(q.message)
    else:
        await q.answer("❌ Join required", show_alert=True)

# ---------- APP CLICK ----------
async def app_click(update, context):
    q = update.callback_query
    uid = q.from_user.id
    app_id = q.data

    if not await is_joined(context.bot, uid):
        await q.answer("❌ Join required", show_alert=True)
        return

    msg = await q.message.edit_text("📦 Opening app...")

    await animate(msg, [
        "📦 Preparing...",
        "⬇️ Downloading...",
        "🔑 Generating key..."
    ])

    app = apps.get(app_id)

    if not app:
        await msg.edit_text("❌ App not found")
        return

    if app.get("file_id"):
        await context.bot.send_document(uid, app["file_id"])

    await context.bot.send_message(
        uid,
        f"🔑 *Key:*\n`{app.get('key','No key')}`",
        parse_mode="Markdown"
    )

    users[str(uid)]["downloads"].append(app_id)
    save_users()

    await msg.edit_text("✅ Done!")

# ---------- ADD APP ----------
async def addapp(update, context):
    if not is_admin(update.effective_user.id):
        return

    app_id = context.args[0]

    pending_upload[update.effective_user.id] = {
        "app_id": app_id
    }

    await update.message.reply_text("📝 Send display name (e.g. 🔥 Netflix Premium)")

# ---------- HANDLE TEXT ----------
async def handle_text(update, context):
    uid = update.effective_user.id

    if uid not in pending_upload:
        return

    data = pending_upload[uid]

    # Step 1: name
    if "name" not in data:
        name = update.message.text.replace("&", "＆")  # fix & issue
        data["name"] = name
        await update.message.reply_text("📁 Send file")
        return

    # Step 3: key
    if "file_id" in data:
        key = update.message.text

        apps[data["app_id"]] = {
            "name": data["name"],
            "file_id": data["file_id"],
            "key": key
        }

        save_apps()
        del pending_upload[uid]

        await update.message.reply_text("✅ App added!")

# ---------- HANDLE FILE ----------
async def handle_file(update, context):
    uid = update.effective_user.id

    if uid not in pending_upload:
        return

    pending_upload[uid]["file_id"] = update.message.document.file_id
    await update.message.reply_text("🔑 Send key")

# ---------- DELETE ----------
async def deleteapp(update, context):
    if not is_admin(update.effective_user.id):
        return

    app = context.args[0]

    if app in apps:
        del apps[app]
        save_apps()
        await update.message.reply_text("🗑️ Deleted")
    else:
        await update.message.reply_text("❌ Not found")

# ---------- SET KEY ----------
async def setkey(update, context):
    if not is_admin(update.effective_user.id):
        return

    app = context.args[0]
    key = context.args[1]

    if app in apps:
        apps[app]["key"] = key
        save_apps()
        await update.message.reply_text("🔑 Updated")

# ---------- STATS ----------
async def stats(update, context):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        f"📊 Users: {len(users)}\n📦 Apps: {len(apps)}"
    )

# ---------- BROADCAST ----------
async def broadcast(update, context):
    if not is_admin(update.effective_user.id):
        return

    msg = " ".join(context.args)

    for u in users:
        try:
            await context.bot.send_message(u, msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent")

# ---------- USERS TXT ----------
async def users_cmd(update, context):
    if not is_admin(update.effective_user.id):
        return

    with open("users.txt", "w") as f:
        for u in users:
            f.write(str(u)+"\n")

    await context.bot.send_document(update.effective_user.id, open("users.txt","rb"))

# ---------- MAIN ----------
def main():
    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check, pattern="check"))
    app.add_handler(CallbackQueryHandler(app_click))

    app.add_handler(CommandHandler("addapp", addapp))
    app.add_handler(CommandHandler("deleteapp", deleteapp))
    app.add_handler(CommandHandler("setkey", setkey))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users_cmd))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
