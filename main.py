import os
import asyncio
import subprocess
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.idle import idle
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped, InputStream
from pytgcalls.types import StreamType
from yt_dlp import YoutubeDL
from pymongo import MongoClient

# === CONFIGURATION ===
API_ID = int(os.environ.get("20678144"))
API_HASH = os.environ.get("53a508a38171fc32fd4bfa835966266e")
BOT_TOKEN = os.environ.get("7979668317:AAHL2ue8zf5h-OPvpry1omKQshg03NsvQto")
OWNER_ID = int(os.environ.get("5670174770"))
CHANNEL_LINK = os.environ.get("https://t.me/dg_gaming_1m0")
MONGO_URI = os.environ.get("mongodb+srv://dggaming:dggaming@cluster0.qnfxnzm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# === SETUP ===
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)
downloads_dir = "downloads"
os.makedirs(downloads_dir, exist_ok=True)

# === MongoDB Connection ===
mongo = MongoClient(MONGO_URI)
db = mongo["tg_music_bot"]
users_col = db["users"]

# === COMMANDS ===
@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("बोट ऑनलाइन है! /play भेजें गाना सुनने के लिए।")

@app.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        return await message.reply("गाने का नाम लिखें।")
    query = message.text.split(maxsplit=1)[1]
    msg = await message.reply(f"`{query}` ढूंढ रहे हैं...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'outtmpl': f'{downloads_dir}/%(title)s.%(ext)s',
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)['entries'][0]
            title = info['title']
            file_path = ydl.prepare_filename(info)
        except Exception as e:
            return await msg.edit(f"एरर: {e}")

    await pytgcalls.join_group_call(
        message.chat.id,
        InputStream(AudioPiped(file_path)),
        stream_type=StreamType().local_stream,
    )

    # === MongoDB में यूज़र डेटा सेव करें ===
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    users_col.update_one(
        {"_id": user_id},
        {
            "$set": {"name": user_name},
            "$inc": {"plays": 1},
            "$push": {"songs": {"title": title, "time": datetime.utcnow()}}
        },
        upsert=True
    )

    await msg.edit(f"अब चला रहे हैं: **{title}**")

@app.on_message(filters.command("stop"))
async def stop(_, message):
    try:
        await pytgcalls.leave_group_call(message.chat.id)
        await message.reply("प्लेबैक बंद कर दिया गया है।")
    except:
        await message.reply("पहले से ही बंद है या कुछ गड़बड़ है।")

@app.on_message(filters.command("promote") & filters.user(OWNER_ID))
async def promote(_, message):
    await message.reply(f"हमारे चैनल को सब्सक्राइब करें: {CHANNEL_LINK}")

@app.on_message(filters.command("autopromo"))
async def auto_promo(_, msg):
    if "join" in msg.text.lower():
        await msg.reply(f"स्वागत है! हमारे चैनल से जुड़ें: {CHANNEL_LINK}")

@app.on_message(filters.command("kidnap"))
async def kidnap(_, message):
    if not message.reply_to_message:
        return await message.reply("किसी के रिप्लाई में ये कमांड भेजें।")
    user = message.reply_to_message.from_user
    delay = random.randint(2, 10)
    await message.reply(f"{user.mention} को {delay} सेकंड में किडनैप कर रहे हैं...")

@app.on_message(filters.command("vplay"))
async def video_play(_, message):
    if len(message.command) < 2:
        return await message.reply("वीडियो का नाम दें।")
    query = message.text.split(maxsplit=1)[1]
    msg = await message.reply(f"`{query}` के लिए वीडियो ढूंढ रहे हैं...")

    try:
        with YoutubeDL({'format': 'bestvideo[ext=mp4]+bestaudio/best', 'outtmpl': 'video_temp.%(ext)s'}) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)['entries'][0]
            filename = ydl.prepare_filename(info)
    except Exception as e:
        return await msg.edit(f"फ़ेल: {e}")

    await msg.edit(
        f"**{info['title']}** स्ट्रीम हो रही है।\n\n"
        f"Telegram Desktop में OBS Virtual Camera चुनें।"
    )

    try:
        subprocess.Popen([
            "ffmpeg", "-re", "-i", filename, "-f", "dshow", "-vcodec", "rawvideo",
            "-pix_fmt", "yuv420p", "-video_size", "1280x720", "-framerate", "30",
            "-i", "video=OBS-Camera", "-map", "0:v", "-map", "0:a", "-f", "dshow", "video=OBS-Camera"
        ])
    except FileNotFoundError:
        await msg.reply("FFmpeg या OBS VirtualCam इंस्टॉल नहीं है।")

# === ADMIN COMMAND TO SEE USER STATS ===
@app.on_message(filters.command("users") & filters.user(OWNER_ID))
async def user_stats(_, message):
    count = users_col.count_documents({})
    top_users = users_col.find().sort("plays", -1).limit(5)
    text = f"कुल यूज़र: {count}\n\n**टॉप 5 यूज़र्स:**\n"
    for u in top_users:
        text += f"- {u['name']}: {u['plays']} plays\n"
    await message.reply(text)

# === MAIN FUNCTION TO RUN ON RENDER ===
async def main():
    await app.start()
    await pytgcalls.start()
    print("Bot चल रहा है...")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())