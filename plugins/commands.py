from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from plugins.advanced_progress import AdvancedProgress
from plugins.download_queue import download_queue
from plugins.language import get_user_language, set_language, LANGUAGES
from plugins.user_quota import quota_manager
from plugins.premium import premium_manager
from plugins.video_utils import video_converter, screenshot_generator
from plugins.torrent_manager import torrent_manager
from plugins.aria2_manager import aria2_manager
from config import BIMBO_OWNER_ID
import asyncio
import os
import time


# ======================= START =======================
@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user
    await message.reply_text(
        f"**👋 Hello {user.first_name}!**\n\n"
        f"Welcome to BIMBO Bot 🚀\n\n"
        f"Send any link to download!\n"
        f"Use /help for all commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Channel", url="https://t.me/Bimbo69"),
             InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/Bimbo69")]
        ])
    )


# ======================= HELP =======================
@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    text = (
        "**📚 BIMBO Bot Commands**\n\n"
        "**📥 Download:**\n"
        "• Send any link - Auto download\n"
        "• /torrent <magnet> - Torrent\n\n"
        "**⚙️ Utilities:**\n"
        "• /status - System status\n"
        "• /queue - Download queue\n"
        "• /quota - Daily limits\n"
        "• /language - Change language\n\n"
        "**⭐ Premium:**\n"
        "• /premium - Premium info\n\n"
        "**🎬 Media:**\n"
        "• /convert - Convert video\n"
        "• /screenshot - Screenshot\n\n"
        "**🛠️ Admin:**\n"
        "• /admin - Admin panel\n"
        "• /addpremium - Add premium user\n"
        "• /removepremium - Remove premium\n"
        "• /premiumlist - Premium list\n"
        "• /ban, /unban, /banlist\n\n"
        "**Powered by @Bimbo69**"
    )
    await message.reply_text(text)


# ======================= LANGUAGE =======================
@Client.on_message(filters.command("language"))
async def language_command(client: Client, message: Message):
    keyboard = []
    for lang_code, lang_name in LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(f"{lang_name}", callback_data=f"set_lang_{lang_code}")])
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    await message.reply_text(
        "🌐 **Select Language / भाषा चुनें**\n\nChoose your preferred language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ======================= QUEUE =======================
@Client.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    stats = download_queue.get_stats()
    text = "📋 **Download Queue**\n\n"
    text += f"⏳ Queued: {stats['queued']}\n"
    text += f"⬇️ Active: {stats['active']}\n"
    text += f"✅ Completed: {stats['completed']}\n\n"
    if download_queue.active:
        text += "**Active Downloads:**\n"
        for task_id, task in list(download_queue.active.items())[:5]:
            fname = getattr(task, 'filename', None) or getattr(task, 'url', 'Unknown')[:40]
            prog = getattr(task, 'progress', 0)
            spd = getattr(task, 'speed', 0)
            text += f"• {fname}\n  Progress: {prog:.1f}% | Speed: {spd/1024/1024:.2f} MB/s\n\n"
    await message.reply_text(text)


# ======================= QUOTA =======================
@Client.on_message(filters.command("quota"))
async def quota_command(client: Client, message: Message):
    quota = quota_manager.get_user_quota(message.from_user.id)
    text = "📊 **Your Daily Quota**\n\n"
    text += f"📥 Downloads Today: {quota.get('daily_downloads', 0)}\n"
    text += f"💾 Data Used: {quota.get('daily_size', 0) / 1024 / 1024:.2f} MB\n"
    await message.reply_text(text)


# ======================= PREMIUM =======================
@Client.on_message(filters.command("premium"))
async def premium_command(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id == BIMBO_OWNER_ID:
        text = "👑 **Owner Account**\n\n✅ Aapko saari features unlimited milengi!\n✓ Unlimited downloads\n✓ Video convert\n✓ Screenshot\n✓ Torrent\n✓ Everything unlocked!"
    elif premium_manager.is_premium(user_id):
        info = premium_manager.get_premium_info(user_id)
        text = f"⭐ **Premium Active!**\n\n👑 Status: ✅ Active\n📅 Expires: {info.get('expiry', 'N/A')}\n\n✓ Unlimited downloads\n✓ Video convert\n✓ Screenshot\n✓ Torrent"
    else:
        text = "⭐ **Upgrade to Premium**\n\nEnjoy unlimited features!\nContact: @Bimbo69"
    await message.reply_text(text)


# ======================= STATUS =======================
@Client.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    msg = await message.reply_text("📊 Fetching system status...")
    stats = download_queue.get_stats()
    try:
        torrents = await torrent_manager.get_all_torrents()
        t_count = len(torrents)
    except:
        t_count = 0
    import psutil, platform
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot = time.time() - psutil.boot_time()
    boot_str = f"{int(boot//3600)}h {int((boot%3600)//60)}m"
    text = (
        f"📊 **System Status**\n\n"
        f"🖥️ OS: {platform.system()} | Uptime: {boot_str}\n"
        f"📈 CPU: {cpu:.1f}% | RAM: {mem.used/1024**3:.1f}/{mem.total/1024**3:.1f}GB ({mem.percent}%)\n"
        f"💾 Disk: {disk.used/1024**3:.1f}/{disk.total/1024**3:.1f}GB ({disk.percent}%)\n\n"
        f"📊 Active: {stats['active']} | Queued: {stats['queued']} | Torrents: {t_count}\n"
        f"└ Status: ✅ Online"
    )
    await msg.edit_text(text)


# ======================= CONVERT =======================
@Client.on_message(filters.command("convert"))
async def convert_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video with /convert")
        return
    user_id = message.from_user.id
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Premium feature! Use /premium")
        return
    video = message.reply_to_message.video
    m = await message.reply_text("⬇️ Downloading video...")
    try:
        fp = await client.download_media(video.file_id)
        await m.edit_text("🔄 Converting...")
        out = await video_converter.convert_video(fp, output_format="mp4", quality="medium")
        if out:
            await m.edit_text("⬆️ Uploading...")
            await client.send_document(message.chat.id, out, caption="✅ Converted!")
            await m.delete()
        else:
            await m.edit_text("❌ Conversion failed!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")


# ======================= SCREENSHOT =======================
@Client.on_message(filters.command("screenshot"))
async def screenshot_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video with /screenshot")
        return
    user_id = message.from_user.id
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Premium feature! Use /premium")
        return
    video = message.reply_to_message.video
    m = await message.reply_text("⬇️ Downloading video...")
    try:
        fp = await client.download_media(video.file_id)
        await m.edit_text("📸 Screenshot...")
        ss = await screenshot_generator.generate_screenshot(fp)
        if ss:
            await m.edit_text("⬆️ Uploading...")
            await client.send_photo(message.chat.id, ss, caption="✅ Screenshot!")
            await m.delete()
        else:
            await m.edit_text("❌ Failed!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")


# ======================= TORRENT =======================
@Client.on_message(filters.command("torrent"))
async def torrent_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: /torrent <magnet_link>")
        return
    user_id = message.from_user.id
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Premium feature! Use /premium")
        return
    magnet = message.command[1]
    m = await message.reply_text("🔄 Adding torrent...")
    async def progress(data):
        try:
            if data.get('is_finished'):
                await m.edit_text(f"✅ Torrent done!\n{data.get('name', '')}")
            else:
                txt = f"⬇️ **{data.get('name', 'Loading...')}**\n\nProgress: {data.get('progress', 0):.1f}%\n⬇️ {data.get('download_rate',0)/1024**2:.2f} MB/s\n⬆️ {data.get('upload_rate',0)/1024**2:.2f} MB/s\nPeers: {data.get('num_peers',0)} | Seeds: {data.get('num_seeds',0)}\nState: {data.get('state','Unknown')}"
                await m.edit_text(txt)
        except FloodWait as e:
            await asyncio.sleep(e.value)
    try:
        info_hash = await torrent_manager.add_torrent(magnet_uri=magnet, progress_callback=progress)
        if info_hash:
            await m.edit_text(f"✅ Torrent added! Hash: `{info_hash}`")
        else:
            await m.edit_text("❌ Failed!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")


# ======================= ADD PREMIUM (ADMIN) =======================
@Client.on_message(filters.command("addpremium") & filters.user(BIMBO_OWNER_ID))
async def add_premium_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/addpremium <user_id> [days]`\nExample: `/addpremium 123456789 30`")
        return
    try:
        user_id = int(message.command[1])
        days = int(message.command[2]) if len(message.command) > 2 else 30
        premium_manager.add_premium_user(user_id, days=days)
        await message.reply_text(f"✅ **Premium Added!**\n\n👤 User: `{user_id}`\n📅 Days: {days}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# ======================= REMOVE PREMIUM (ADMIN) =======================
@Client.on_message(filters.command("removepremium") & filters.user(BIMBO_OWNER_ID))
async def remove_premium_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/removepremium <user_id>`\nExample: `/removepremium 123456789`")
        return
    try:
        user_id = int(message.command[1])
        premium_manager.remove_premium_user(user_id)
        await message.reply_text(f"✅ Premium removed for user `{user_id}`!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# ======================= PREMIUM LIST (ADMIN) =======================
@Client.on_message(filters.command("premiumlist") & filters.user(BIMBO_OWNER_ID))
async def premium_list_command(client: Client, message: Message):
    users = premium_manager.get_all_premium_users()
    if not users:
        await message.reply_text("📋 No premium users found.")
        return
    text = "⭐ **Premium Users**\n\n"
    for uid, data in users.items():
        text += f"👤 `{uid}` | {data.get('tier','premium')} | Exp: {data.get('expiry','Lifetime')}\n"
    if len(text) > 4000:
        text = text[:4000] + "\n\n...truncated"
    await message.reply_text(text)
