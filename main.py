import os
import json
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# -------- ENV --------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHANNELS = os.getenv("CHANNELS", "").split(",")

ADMINS = [OWNER_ID]

apps = {}
users = {}
pending_upload = {}

# -------- LOAD SAVE --------
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

def save_apps():
    with open("apps.json", "w") as f:
        json.dump(apps, f, indent=4)

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# -------- ROLE --------
def is_admin(uid): return uid in ADMINS
def is_owner(uid): return uid == OWNER_ID

# -------- JOIN CHECK --------
async def is_joined(bot, user_id):
    if is_owner(user_id):
        return True

    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

# -------- ANIMATION --------
async def animate(msg, steps):
    for s in steps:
        await asyncio.sleep(0.7)
        await msg.edit_text(s)

# -------- START --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[str(uid)] = users.get(str(uid), {"downloads":[]})
    save_users()

    msg = await update.message.reply_text("👋 Welcome...\n🔄 Starting system...")

    await animate(msg, [
        "🔄 Checking access...",
        "⏳ Verifying channels..."
    ])

    if not await is_joined(context.bot, uid):
        buttons = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNELS[0].replace('@','')}")],
            [InlineKeyboardButton("✅ I Joined", callback_data="check")]
        ]
        await msg.edit_text(
            "⚠️ Access Locked!\n\n👉 Please join all channels first.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await msg.edit_text("🎉 Access Granted!\n🛒 Opening Store...")
    await show_apps(msg)

# -------- SHOW APPS --------
async def show_apps(msg):
    if not apps:
        await msg.edit_text("📭 No apps available")
        return

    buttons = []
    for a in apps:
        buttons.append([InlineKeyboardButton(apps[a]["name"], callback_data=a)])

    await msg.edit_text(
        "🛒 *App Store*\n\nSelect app to download:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# -------- CHECK JOIN --------
async def check(update, context):
    q = update.callback_query
    uid = q.from_user.id

    if await is_joined(context.bot, uid):
        await q.message.edit_text("🎉 Verified!\nOpening store...")
        await show_apps(q.message)
    else:
        await q.answer("❌ Still not joined!", show_alert=True)

# -------- APP CLICK --------
async def app_click(update, context):
    q = update.callback_query
    uid = q.from_user.id
    app_id = q.data

    if not await is_joined(context.bot, uid):
        await q.answer("❌ Join required", show_alert=True)
        return

    msg = await q.message.edit_text("📦 Opening app...")

    await animate(msg, [
        "📦 Preparing file...",
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
        f"🔑 *Your Key:*\n`{app.get('key','No key')}`",
        parse_mode="Markdown"
    )

    users[str(uid)]["downloads"].append(app_id)
    save_users()

    await msg.edit_text("✅ Done!")

# -------- ADD APP --------
async def addapp(update, context):
    if not is_admin(update.effective_user.id): return

    name = context.args[0]
    pending_upload[update.effective_user.id] = {"app": name}

    await update.message.reply_text("📁 Send file now")

# -------- HANDLE FILE --------
async def handle_file(update, context):
    uid = update.effective_user.id
    if uid not in pending_upload: return

    pending_upload[uid]["file_id"] = update.message.document.file_id
    await update.message.reply_text("🔑 Send key now")

# -------- HANDLE KEY --------
async def handle_text(update, context):
    uid = update.effective_user.id
    if uid not in pending_upload: return

    data = pending_upload[uid]

    apps[data["app"]] = {
        "name": data["app"],
        "file_id": data["file_id"],
        "key": update.message.text
    }

    save_apps()
    del pending_upload[uid]

    await update.message.reply_text("✅ App added successfully")

# -------- DELETE --------
async def deleteapp(update, context):
    if not is_admin(update.effective_user.id): return

    app = context.args[0]

    if app in apps:
        del apps[app]
        save_apps()
        await update.message.reply_text("🗑️ Deleted")
    else:
        await update.message.reply_text("❌ Not found")

# -------- SET KEY --------
async def setkey(update, context):
    if not is_admin(update.effective_user.id): return

    app = context.args[0]
    key = context.args[1]

    if app in apps:
        apps[app]["key"] = key
        save_apps()
        await update.message.reply_text("🔑 Updated")

# -------- STATS --------
async def stats(update, context):
    if not is_admin(update.effective_user.id): return

    await update.message.reply_text(
        f"📊 Stats\n👤 Users: {len(users)}\n📦 Apps: {len(apps)}"
    )

# -------- BROADCAST --------
async def broadcast(update, context):
    if not is_admin(update.effective_user.id): return

    msg = " ".join(context.args)

    for u in users:
        try:
            await context.bot.send_message(u, msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent")

# -------- USERS TXT --------
async def users_cmd(update, context):
    if not is_admin(update.effective_user.id): return

    with open("users.txt", "w") as f:
        for u in users:
            f.write(str(u)+"\n")

    await context.bot.send_document(update.effective_user.id, open("users.txt","rb"))

# -------- MAIN --------
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
