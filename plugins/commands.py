from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.advanced_progress import AdvancedProgress
from plugins.download_queue import download_queue
from plugins.language import get_user_language, set_language, LANGUAGES
from plugins.user_quota import quota_manager
from plugins.premium import premium_manager
from plugins.video_utils import video_converter, screenshot_generator
from plugins.torrent_manager import torrent_manager
from plugins.aria2_manager import aria2_manager
from pyrogram.errors import FloodWait
import asyncio
import os
import time


# ======================= START COMMAND =======================
@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user
    await message.reply_text(
        f"**👋 Hello {user.first_name}!**\n\n"
        f"Welcome to BIMBO Bot 🚀\n\n"
        f"I can download files from various sources:\n"
        f"• 📹 YouTube / Social Media\n"
        f"• 📦 Terabox / Direct Links\n"
        f"• 🧲 Torrents / Magnets\n"
        f"• 📁 Documents & Media\n\n"
        f"Use /help to see all commands!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Channel", url="https://t.me/Bimbo69"),
             InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/Bimbo69")]
        ])
    )


# ======================= HELP COMMAND =======================
@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    text = (
        "**📚 Help - BIMBO Bot Commands**\n\n"
        "**📥 Download Commands:**\n"
        "• Send any link (YouTube, Terabox, Direct) - Auto downloads\n"
        "• /torrent <magnet> - Download torrent\n\n"
        "**⚙️ Utilities:**\n"
        "• /status - System status & stats\n"
        "• /queue - View download queue\n"
        "• /quota - Check daily limits\n"
        "• /language - Change language (English/Hindi)\n\n"
        "**⭐ Premium:**\n"
        "• /premium - Premium plans & benefits\n\n"
        "**🎬 Media:**\n"
        "• /convert - Convert video (reply to video)\n"
        "• /screenshot - Generate screenshot (reply to video)\n"
        "• /setthumbnail - Set custom thumbnail (send photo)\n"
        "• /viewthumbnail - View your thumbnail\n"
        "• /delthumbnail - Delete thumbnail\n\n"
        "**🛠️ Admin Commands:**\n"
        "• /admin - Admin panel\n"
        "• /stats - Detailed statistics\n"
        "• /ban - Ban user\n"
        "• /unban - Unban user\n"
        "• /broadcast - Broadcast message\n\n"
        "**Powered by @Bimbo69**\n"
    )
    await message.reply_text(text)


# ======================= LANGUAGE COMMAND =======================
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


# ======================= QUEUE COMMAND =======================
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
            text += f"• {fname}\n"
            text += f"  Progress: {prog:.1f}% | Speed: {spd / 1024 / 1024:.2f} MB/s\n\n"

    await message.reply_text(text)


# ======================= QUOTA COMMAND =======================
@Client.on_message(filters.command("quota"))
async def quota_command(client: Client, message: Message):
    user_id = message.from_user.id
    quota = quota_manager.get_user_quota(user_id)
    lang = get_user_language(user_id)

    if lang == 'hi':
        text = "📊 **आपकी दैनिक सीमा**\n\n"
        text += f"📥 डाउनलोड: {quota.get('daily_downloads', 0)}/{quota.get('download_limit', 50)}\n"
        text += f"💾 डेटा: {quota.get('daily_size', 0) / 1024 / 1024:.2f} MB\n"
    else:
        text = "📊 **Your Daily Quota**\n\n"
        text += f"📥 Downloads Today: {quota.get('daily_downloads', 0)}\n"
        text += f"💾 Data Used: {quota.get('daily_size', 0) / 1024 / 1024:.2f} MB\n"

    await message.reply_text(text)


# ======================= PREMIUM COMMAND =======================
@Client.on_message(filters.command("premium"))
async def premium_command(client: Client, message: Message):
    user_id = message.from_user.id
    is_prem = premium_manager.is_premium(user_id)
    info = premium_manager.get_premium_info(user_id)
    lang = get_user_language(user_id)

    if is_prem and info:
        if lang == 'hi':
            text = "⭐ **प्रीमियम सदस्यता**\n\n👑 स्थिति: ✅ सक्रिय\n📅 समाप्ति: {}\n\n**.प्रीमियम लाभ:**\n✓ असीमित डाउनलोड\n✓ असीमित डेटा\n✓ वीडियो रूपांतरण\n✓ स्क्रीनशॉट\n✓ प्राथमिकता कतार".format(
                info.get('expiry', 'N/A'))
        else:
            text = "⭐ **Premium Membership**\n\n👑 Status: ✅ Active\n📅 Expires: {}\n\n**Benefits:**\n✓ Unlimited downloads\n✓ Unlimited data\n✓ Video conversion\n✓ Screenshots\n✓ Priority queue".format(
                info.get('expiry', 'N/A'))
    else:
        if lang == 'hi':
            text = "⭐ **प्रीमियम में अपग्रेड करें**\n\nअसीमित डाउनलोड और विशेष सुविधाओं का आनंद लें!\n\nसंपर्क: @Bimbo69"
        else:
            text = "⭐ **Upgrade to Premium**\n\nEnjoy unlimited downloads and exclusive features!\n\nContact: @Bimbo69"

    await message.reply_text(text)


# ======================= STATUS COMMAND =======================
@Client.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    msg = await message.reply_text("📊 Fetching system status...")

    stats = download_queue.get_stats()
    active_count = stats['active']
    queued_count = stats['queued']

    # Get torrents
    try:
        torrents = await torrent_manager.get_all_torrents()
        torrent_count = len(torrents)
    except Exception:
        torrent_count = 0

    # System info
    import psutil
    import platform
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot = time.time() - psutil.boot_time()
    boot_str = f"{int(boot // 3600)}h {int((boot % 3600) // 60)}m"

    text = (
        f"📊 **System Status**\n\n"
        f"🖥️ **Server**\n"
        f"├ OS: {platform.system()}\n"
        f"└ Uptime: {boot_str}\n\n"
        f"📈 **Resources**\n"
        f"├ CPU: {cpu:.1f}%\n"
        f"├ RAM: {mem.used / 1024**3:.1f}GB / {mem.total / 1024**3:.1f}GB ({mem.percent}%)\n"
        f"└ Disk: {disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB ({disk.percent}%)\n\n"
        f"📊 **Bot Stats**\n"
        f"├ Active Downloads: {active_count}\n"
        f"├ Queued: {queued_count}\n"
        f"├ Torrents: {torrent_count}\n"
        f"└ Status: ✅ Online\n"
    )

    await msg.edit_text(text)


# ======================= CONVERT COMMAND =======================
@Client.on_message(filters.command("convert"))
async def convert_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video file with /convert")
        return

    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Premium feature!\nUse /premium for info.")
        return

    video = message.reply_to_message.video
    m = await message.reply_text("⬇️ Downloading video...")

    try:
        file_path = await client.download_media(video.file_id)
        await m.edit_text("🔄 Converting...")
        output = await video_converter.convert_video(file_path, output_format="mp4", quality="medium")

        if output:
            await m.edit_text("⬆️ Uploading...")
            await client.send_document(message.chat.id, output, caption="✅ Converted!")
            await m.delete()
        else:
            await m.edit_text("❌ Conversion failed!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")


# ======================= SCREENSHOT COMMAND =======================
@Client.on_message(filters.command("screenshot"))
async def screenshot_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video with /screenshot")
        return

    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Premium feature!\nUse /premium for info.")
        return

    video = message.reply_to_message.video
    m = await message.reply_text("⬇️ Downloading video...")

    try:
        file_path = await client.download_media(video.file_id)
        await m.edit_text("📸 Generating screenshot...")
        ss_path = await screenshot_generator.generate_screenshot(file_path)

        if ss_path:
            await m.edit_text("⬆️ Uploading...")
            await client.send_photo(message.chat.id, ss_path, caption="✅ Screenshot!")
            await m.delete()
        else:
            await m.edit_text("❌ Failed!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")


# ======================= TORRENT COMMAND =======================
@Client.on_message(filters.command("torrent"))
async def torrent_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: /torrent <magnet_link>")
        return

    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Torrents require Premium!\nUse /premium for info.")
        return

    magnet = message.command[1]
    m = await message.reply_text("🔄 Adding torrent...")

    async def progress(data):
        try:
            if data.get('is_finished'):
                await m.edit_text(f"✅ Torrent done!\n{data.get('name', '')}")
            else:
                txt = (
                    f"⬇️ **{data.get('name', 'Loading...')}**\n\n"
                    f"Progress: {data.get('progress', 0):.1f}%\n"
                    f"⬇️ {data.get('download_rate', 0) / 1024**2:.2f} MB/s\n"
                    f"⬆️ {data.get('upload_rate', 0) / 1024**2:.2f} MB/s\n"
                    f"Peers: {data.get('num_peers', 0)} | Seeds: {data.get('num_seeds', 0)}\n"
                    f"State: {data.get('state', 'Unknown')}"
                )
                await m.edit_text(txt)
        except FloodWait as e:
            await asyncio.sleep(e.value)

    try:
        info_hash = await torrent_manager.add_torrent(magnet_uri=magnet, progress_callback=progress)
        if info_hash:
            await m.edit_text(f"✅ Torrent added!\nHash: `{info_hash}`")
        else:
            await m.edit_text("❌ Failed to add torrent!")
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")
