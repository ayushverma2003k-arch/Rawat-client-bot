import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1003980205023
INVITE_LINK = "https://t.me/+OnH8MepS0LhjNTc1"

OWNER_ID = 8044682416
ADMIN_IDS = [8044682416]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    coins INTEGER DEFAULT 0,
    referrer INTEGER,
    referrals INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    user_id INTEGER,
    price INTEGER
)
""")

conn.commit()

# ================= MEMORY =================
pending_keys = {}

# ================= FUNCTIONS =================
def get_user(uid):
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cur.fetchone()

def add_user(uid, name, username, ref=None):
    cur.execute("INSERT INTO users VALUES (?, ?, ?, 0, ?, 0)",
                (uid, name, username, ref))
    conn.commit()

def add_coins(uid, amt):
    cur.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amt, uid))
    conn.commit()

def remove_coins(uid, amt):
    cur.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amt, uid))
    conn.commit()

def add_ref(uid):
    cur.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (uid,))
    conn.commit()

def total_users():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

# ================= JOIN CHECK =================
async def check_join(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "creator", "administrator"]
    except:
        return False

# ================= UI =================
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💰 Buy Key", callback_data="buy")],
        [InlineKeyboardButton("🔗 Referral", callback_data="ref")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="top")]
    ])

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_join(message.from_user.id):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Join Channel", url=INVITE_LINK),
            InlineKeyboardButton("✅ Check Again", callback_data="check")
        )
        return await message.answer("🚫 Join channel first!", reply_markup=kb)

    user = get_user(message.from_user.id)
    args = message.get_args()

    if not user:
        ref = int(args) if args.isdigit() else None

        if ref == message.from_user.id:
            ref = None

        add_user(
            message.from_user.id,
            message.from_user.full_name,
            message.from_user.username or "NoUsername",
            ref
        )

        if ref:
            add_coins(ref, 10)
            add_ref(ref)

    await message.answer(f"👋 Welcome {message.from_user.full_name}", reply_markup=menu())

# ================= PROFILE =================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call):
    u = get_user(call.from_user.id)

    text = f"""
👤 Profile

🆔 ID: {u[0]}
📛 Name: {u[1]}
🔗 Username: @{u[2]}
💰 Coins: {u[3]}
👥 Referrals: {u[5]}
"""
    await call.message.edit_text(text, reply_markup=menu())

# ================= REF =================
@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(call):
    link = f"https://t.me/YOUR_BOT_USERNAME?start={call.from_user.id}"

    await call.message.edit_text(
        f"🔗 Referral Link:\n{link}\n\n💸 Earn 10 coins/referral",
        reply_markup=menu()
    )

# ================= BUY MENU =================
@dp.callback_query_handler(lambda c: c.data == "buy")
async def buy(call):

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("⚡ 25 Coins (5 Hours)", callback_data="buy_25")],
        [InlineKeyboardButton("🔥 60 Coins (1 Day)", callback_data="buy_60")],
        [InlineKeyboardButton("📅 150 Coins (7 Days)", callback_data="buy_150")],
        [InlineKeyboardButton("📅 280 Coins (15 Days)", callback_data="buy_280")],
        [InlineKeyboardButton("📅 500 Coins (30 Days)", callback_data="buy_500")],
        [InlineKeyboardButton("🚀 900 Coins (60 Days)", callback_data="buy_900")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

    await call.message.edit_text("💰 Choose Plan:", reply_markup=kb)

# ================= BUY PROCESS =================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process(call):

    prices = {
        "buy_25": 25,
        "buy_60": 60,
        "buy_150": 150,
        "buy_280": 280,
        "buy_500": 500,
        "buy_900": 900
    }

    price = prices.get(call.data)
    u = get_user(call.from_user.id)

    if u[3] < price:
        return await call.answer("❌ Not enough coins", show_alert=True)

    remove_coins(call.from_user.id, price)

    cur.execute("INSERT INTO requests VALUES (?, ?)", (call.from_user.id, price))
    conn.commit()

    for admin in ADMIN_IDS:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Approve", callback_data=f"ok_{call.from_user.id}_{price}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"no_{call.from_user.id}_{price}")
        )

        await bot.send_message(admin,
            f"📥 Request\n👤 @{call.from_user.username}\n💰 {price}",
            reply_markup=kb)

    await call.message.edit_text("📩 Request sent!")

# ================= APPROVE =================
@dp.callback_query_handler(lambda c: c.data.startswith("ok_"))
async def approve(call):
    _, uid, price = call.data.split("_")
    uid = int(uid)

    pending_keys[call.from_user.id] = uid
    await call.message.answer("✍️ Send key now:")

# ================= KEY SEND =================
@dp.message_handler(lambda m: m.from_user.id in pending_keys)
async def send_key(msg: types.Message):
    uid = pending_keys[msg.from_user.id]

    await bot.send_message(uid,
        f"✅ Approved!\n\n🔑 {msg.text}\n\n🚀 GET ACCESS")

    del pending_keys[msg.from_user.id]

# ================= REJECT =================
@dp.callback_query_handler(lambda c: c.data.startswith("no_"))
async def reject(call):
    _, uid, price = call.data.split("_")
    uid = int(uid)
    price = int(price)

    add_coins(uid, price)

    await bot.send_message(uid, "❌ Rejected. Coins refunded.")

    cur.execute("DELETE FROM requests WHERE user_id=?", (uid,))
    conn.commit()

# ================= LEADERBOARD =================
@dp.callback_query_handler(lambda c: c.data == "top")
async def top(call):
    cur.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
    data = cur.fetchall()

    text = "🏆 Top Users\n\n"
    for i, u in enumerate(data, 1):
        name = u[0] if u[0] != "NoUsername" else "User"
        text += f"{i}. @{name} — {u[1]}\n"

    await call.message.edit_text(text)

# ================= BACK =================
@dp.callback_query_handler(lambda c: c.data == "back")
async def back(call):
    await call.message.edit_text("🏠 Menu", reply_markup=menu())

# ================= ADMIN =================
@dp.message_handler(commands=['stats'])
async def stats(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    await m.reply(f"👥 Users: {total_users()}")

@dp.message_handler(commands=['broadcast'])
async def broadcast(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    text = m.text.replace("/broadcast ", "")
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

    await m.reply("📣 Sent")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
