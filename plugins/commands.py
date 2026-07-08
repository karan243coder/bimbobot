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
import logging

# Initialize logger
logger = logging.getLogger(__name__)


# ======================= AUTO-DELETE HELPER =======================
async def auto_delete_messages(user_msg: Message, bot_msg: Message, delay: int = 15):
    """Auto-delete both user command and bot response after delay"""
    await asyncio.sleep(delay)
    try:
        await user_msg.delete()
    except Exception as e:
        pass  # Silent fail - message might already be deleted
    try:
        await bot_msg.delete()
    except Exception as e:
        pass  # Silent fail - message might already be deleted


# ======================= START =======================
@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user
    bot_msg = await message.reply_text(
        f"**👋 Hello {user.first_name}!**\n\n"
        f"Welcome to BIMBO Bot 🚀\n\n"
        f"Send any link to download!\n"
        f"Use /help for all commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Channel", url="https://t.me/Bimbo69"),
             InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/Bimbo69")]
        ])
    )
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


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
    bot_msg = await message.reply_text(text)
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


# ======================= LANGUAGE =======================
@Client.on_message(filters.command("language"))
async def language_command(client: Client, message: Message):
    keyboard = []
    for lang_code, lang_name in LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(f"{lang_name}", callback_data=f"set_lang_{lang_code}")])
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    bot_msg = await message.reply_text(
        "🌐 **Select Language / भाषा चुनें**\n\nChoose your preferred language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


# ======================= QUEUE =======================
@Client.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    stats = download_queue.get_stats()
    
    text = (
        f"📋 **Download Queue**\n\n"
        f"⏳ **Queued:** {stats['queued']}\n"
        f"⬇️ **Active:** {stats['active']}\n"
        f"✅ **Completed:** {stats['completed']}\n\n"
    )
    
    if download_queue.active:
        text += "**Active Downloads:**\n\n"
        i = 1
        for task_id, task in list(download_queue.active.items())[:5]:
            fname = getattr(task, 'filename', None) or getattr(task, 'url', 'Unknown')[:35]
            prog = getattr(task, 'progress', 0)
            spd = getattr(task, 'speed', 0)
            status = getattr(task, 'status', 'active')
            text += f"{i}. **{fname}**\n"
            text += f"   📊 {prog:.1f}% | ⚡ {spd/1024/1024:.2f} MB/s | {status}\n\n"
            i += 1
    else:
        text += "ℹ️ No active downloads.\n"
        text += "Send a link to start downloading!\n"
    
    if download_queue.queue:
        text += f"💡 {len(download_queue.queue)} tasks waiting in queue...\n"
    
    bot_msg = await message.reply_text(text)
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


# ======================= QUOTA =======================
@Client.on_message(filters.command("quota"))
async def quota_command(client: Client, message: Message):
    user_id = message.from_user.id
    from plugins.premium import get_user_limits
    
    quota = quota_manager.get_user_quota(user_id)
    limits = get_user_limits(user_id)
    
    # Calculate remaining
    remaining_downloads = limits['daily_downloads'] - quota.get('daily_downloads', 0)
    if limits['daily_downloads'] == -1:
        remaining_downloads_str = "Unlimited"
        dl_limit_str = "∞"
    else:
        remaining_downloads_str = str(remaining_downloads)
        dl_limit_str = str(limits['daily_downloads'])
    
    daily_size_mb = limits['daily_size'] / (1024 * 1024) if limits['daily_size'] > 0 else float('inf')
    used_mb = quota.get('daily_size', 0) / (1024 * 1024)
    remaining_mb = max(0, daily_size_mb - used_mb)
    
    if limits['daily_size'] == -1:
        size_limit_str = "∞"
        remaining_size_str = "∞"
    else:
        size_limit_str = f"{daily_size_mb:.0f} MB"
        remaining_size_str = f"{remaining_mb:.0f} MB"
    
    # User type
    if user_id == BIMBO_OWNER_ID:
        user_type = "👑 Owner"
    elif premium_manager.is_premium(user_id):
        user_type = "⭐ Premium"
    else:
        user_type = "👤 Free User"
    
    text = (
        f"📊 **Daily Quota**\n\n"
        f"{user_type}\n\n"
        f"📥 **Downloads:**\n"
        f"├ Used: {quota.get('daily_downloads', 0)} / {dl_limit_str}\n"
        f"└ Remaining: {remaining_downloads_str}\n\n"
        f"💾 **Data:**\n"
        f"├ Used: {used_mb:.2f} MB / {size_limit_str}\n"
        f"└ Remaining: {remaining_size_str}\n"
    )
    bot_msg = await message.reply_text(text)
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


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
    bot_msg = await message.reply_text(text)
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, bot_msg, 10))


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
    # Auto-delete after 10 seconds
    asyncio.create_task(auto_delete_messages(message, msg, 10))


# ======================= CONVERT =======================
@Client.on_message(filters.command("convert"))
async def convert_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        bot_msg = await message.reply_text("⚠️ Reply to a video with /convert")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
        return
    user_id = message.from_user.id
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        bot_msg = await message.reply_text("⭐ Premium feature! Use /premium")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
        return
    
    # Delete user command immediately
    await message.delete()
    
    video = message.reply_to_message.video
    m = await message.reply_text("⬇️ Downloading video...")
    try:
        fp = await client.download_media(video.file_id)
        await m.edit_text("🔄 Converting...")
        out = await video_converter.convert_video(fp, output_format="mp4", quality="medium")
        if out:
            await m.edit_text("⬆️ Uploading...")
            # Send converted video - THIS WILL STAY
            await client.send_document(message.chat.id, out, caption="✅ Converted!")
            # Delete only the status message, NOT the media
            await m.delete()
        else:
            await m.edit_text("❌ Conversion failed!")
            asyncio.create_task(m.delete())
            await asyncio.sleep(15)
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")
        asyncio.create_task(m.delete())
        await asyncio.sleep(15)


# ======================= SCREENSHOT =======================
@Client.on_message(filters.command("screenshot"))
async def screenshot_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        bot_msg = await message.reply_text("⚠️ Reply to a video with /screenshot [count]")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 10))
        return
    user_id = message.from_user.id
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        bot_msg = await message.reply_text("⭐ Premium feature! Use /premium")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 10))
        return

    # Check if count specified
    count = 1
    if len(message.command) > 1:
        try:
            count = int(message.command[1])
            if count < 1:
                count = 1
            if count > 10:
                count = 10
                await message.reply_text("⚠️ Max 10 screenshots allowed. Generating 10...")
        except ValueError:
            bot_msg = await message.reply_text("⚠️ Invalid number! Usage: /screenshot [count]")
            asyncio.create_task(auto_delete_messages(message, bot_msg, 10))
            return

    video = message.reply_to_message.video
    m = await message.reply_text(f"⬇️ Downloading video...")
    try:
        fp = await client.download_media(video.file_id)

        if count == 1:
            await m.edit_text("📸 Generating screenshot...")
            ss = await screenshot_generator.generate_screenshot(fp)
            if ss:
                await m.edit_text("⬆️ Uploading...")
                await client.send_photo(message.chat.id, ss, caption="✅ Screenshot!")
                await m.delete()
                await message.delete()
            else:
                await m.edit_text("❌ Failed to generate screenshot!")
                asyncio.create_task(auto_delete_messages(message, m, 10))
        else:
            await m.edit_text(f"📸 Generating {count} screenshots...")
            screenshots = await screenshot_generator.generate_multiple_screenshots(fp, count=count)
            if screenshots:
                await m.edit_text(f"⬆️ Uploading {len(screenshots)} screenshots...")
                # Send as media group (album)
                from pyrogram.types import InputMediaPhoto
                media_group = []
                for i, ss in enumerate(screenshots):
                    caption_text = f"📸 Screenshot {i+1}/{len(screenshots)}" if i == 0 else ""
                    media_group.append(InputMediaPhoto(ss, caption=caption_text))

                await client.send_media_group(message.chat.id, media_group)
                await m.delete()
                await message.delete()
            else:
                await m.edit_text("❌ Failed to generate screenshots!")
                asyncio.create_task(auto_delete_messages(message, m, 10))
    except Exception as e:
        await m.edit_text(f"❌ Error: {e}")
        asyncio.create_task(auto_delete_messages(message, m, 10))


# ======================= CANCEL TORRENT =======================
@Client.on_message(filters.command("cancel"))
async def cancel_torrent_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Delete user command after 15 seconds
    asyncio.create_task(auto_delete_messages(message, None, 15))
    
    # Get all active torrents for this user
    from plugins.torrent_manager import torrent_manager
    
    active_torrents = []
    for info_hash, torrent_data in torrent_manager.active_torrents.items():
        if torrent_data.get('user_id') == user_id:
            active_torrents.append((info_hash, torrent_data))
    
    if not active_torrents:
        bot_msg = await message.reply_text("❌ No active torrents to cancel!")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
        return
    
    # Cancel all active torrents for this user
    cancelled_count = 0
    for info_hash, torrent_data in active_torrents:
        try:
            # Remove torrent and delete files
            await torrent_manager.remove_torrent(info_hash, delete_files=True)
            cancelled_count += 1
        except Exception as e:
            pass
    
    bot_msg = await message.reply_text(f"✅ Cancelled {cancelled_count} torrent(s) and deleted files!")
    asyncio.create_task(auto_delete_messages(message, bot_msg, 15))


# ======================= TORRENT =======================
@Client.on_message(filters.command("torrent"))
async def torrent_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is premium
    if user_id != BIMBO_OWNER_ID and not premium_manager.is_premium(user_id):
        bot_msg = await message.reply_text("⭐ Premium feature! Use /premium")
        asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
        return
    
    # Delete user command
    await message.delete()
    
    # Check if it's a magnet link or torrent file
    magnet = None
    torrent_file_path = None
    
    # Case 1: Magnet link as command argument
    if len(message.command) >= 2:
        magnet = message.command[1]
        if not magnet.startswith('magnet:'):
            bot_msg = await message.reply_text("⚠️ Invalid magnet link! Must start with 'magnet:'")
            asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
            return
    
    # Case 2: Torrent file as reply
    elif message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        if doc.file_name and doc.file_name.endswith('.torrent'):
            # Download the torrent file
            progress_msg = await message.reply_text("📥 Downloading torrent file...")
            try:
                torrent_file_path = await client.download_media(doc.file_id)
                await progress_msg.edit_text("✅ Torrent file downloaded!")
            except Exception as e:
                await progress_msg.edit_text(f"❌ Failed to download torrent file: {str(e)[:100]}")
                await asyncio.sleep(15)
                await progress_msg.delete()
                return
        else:
            bot_msg = await message.reply_text("⚠️ Please reply to a .torrent file!")
            asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
            return
    
    # Case 3: No magnet link or torrent file
    else:
        bot_msg = await message.reply_text(
            "⚠️ Usage:\n"
            "• /torrent <magnet_link>\n"
            "• Reply to .torrent file with /torrent"
        )
        asyncio.create_task(auto_delete_messages(message, bot_msg, 15))
        return
    
    progress_msg = await message.reply_text("🔄 Adding torrent...")
    
    # Import required modules
    from plugins.torrent_manager import torrent_manager
    from plugins.custom_thumbnail import Gthumb01, Gthumb02, Mdata01
    from helper_funcs.display_progress import humanbytes, TimeFormatter
    from plugins.youtube_dl_button import build_progress_bar
    from config import Config
    import time
    from datetime import datetime
    
    download_start_time = time.time()
    
    async def progress(data):
        try:
            now = time.time()
            elapsed = now - download_start_time
            # Fix: Convert to milliseconds properly
            elapsed_str = TimeFormatter(milliseconds=int(elapsed * 1000))
            
            if data.get('is_finished'):
                # Download complete
                complete_text = (
                    f"╭━━━〔 ✅ TORRENT COMPLETE 〕━━━╮\n"
                    f"┃ 📁 File: {data.get('name', 'Unknown')[:35]}\n"
                    f"┃ [████████████████████] 100.0%\n"
                    f"┃ 📦 Size: {humanbytes(data.get('total_size', 0))}\n"
                    f"┃ 🕒 Elapsed: {elapsed_str}\n"
                    f"┃ 🔄 Status: Preparing upload...\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
                )
                await progress_msg.edit_text(complete_text)
            else:
                # Download in progress
                percentage = data.get('progress', 0)
                downloaded = data.get('downloaded', 0)
                total_size = data.get('total_size', 0)
                download_rate = data.get('download_rate', 0)
                
                # Calculate ETA
                if download_rate > 0 and total_size > downloaded:
                    remaining = total_size - downloaded
                    eta_seconds = remaining / download_rate
                    eta_str = TimeFormatter(eta_seconds * 1000)
                else:
                    eta_str = "Calculating..."
                
                # Build progress card
                progress_bar = build_progress_bar(percentage)
                progress_text = (
                    f"╭━━━〔 🧲 TORRENT DOWNLOAD 〕━━━╮\n"
                    f"┃ 📁 File: {data.get('name', 'Loading...')[:35]}\n"
                    f"┃ {progress_bar} {percentage:.1f}%\n"
                    f"┃ ⬇️ Speed: {humanbytes(download_rate)}/s\n"
                    f"┃ 📦 Progress: {humanbytes(downloaded)} / {humanbytes(total_size)}\n"
                    f"┃ ⏳ ETA: {eta_str}\n"
                    f"┃ 🕒 Elapsed: {elapsed_str}\n"
                    f"┃ 👥 Peers: {data.get('num_peers', 0)} | 🌱 Seeds: {data.get('num_seeds', 0)}\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
                )
                await progress_msg.edit_text(progress_text)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            pass
    
    try:
        # Create download directory
        download_dir = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, str(user_id))
        os.makedirs(download_dir, exist_ok=True)
        
        # Log what we're adding
        if magnet:
            logger.info(f"Adding magnet link for user {user_id}: {magnet[:100]}...")
        elif torrent_file_path:
            logger.info(f"Adding torrent file for user {user_id}: {torrent_file_path}")
        
        # Add torrent (either magnet or file)
        info_hash = await torrent_manager.add_torrent(
            magnet_uri=magnet,
            torrent_file=torrent_file_path,
            save_path=download_dir,
            progress_callback=progress,
            user_id=user_id
        )
        
        if info_hash:
            logger.info(f"Torrent added successfully: {info_hash}")
            
            # Wait for torrent to complete and get files
            max_wait = 7200  # Max 2 hours
            wait_time = 0
            
            while wait_time < max_wait:
                status = await torrent_manager.get_torrent_status(info_hash)
                
                if not status:
                    logger.error(f"Torrent status not found: {info_hash}")
                    await progress_msg.edit_text("❌ Torrent not found!")
                    await asyncio.sleep(15)
                    await progress_msg.delete()
                    return
                
                if status.get('is_finished'):
                    logger.info(f"Torrent finished: {info_hash}")
                    # Get the downloaded files
                    torrent_data = torrent_manager.active_torrents.get(info_hash)
                    
                    if torrent_data and 'files' in torrent_data:
                        files = torrent_data['files']
                        logger.info(f"Found {len(files)} files in torrent")
                        break
                    else:
                        logger.warning(f"Torrent finished but no files found, waiting...")
                
                await asyncio.sleep(2)
                wait_time += 2
            
            if wait_time >= max_wait:
                await progress_msg.edit_text("❌ Torrent download timeout!")
                await asyncio.sleep(15)
                await progress_msg.delete()
                return
            
            # Get the main file (largest file)
            torrent_data = torrent_manager.active_torrents.get(info_hash)
            
            if torrent_data and 'files' in torrent_data:
                files = torrent_data['files']
                
                if not files:
                    await progress_msg.edit_text("❌ No files found in torrent!")
                    await asyncio.sleep(15)
                    await progress_msg.delete()
                    return
                
                # Find the largest file
                largest_file = max(files, key=lambda x: x['size'])
                file_path = largest_file['path']
                file_size = largest_file['size']
                
                logger.info(f"Largest file: {file_path} ({file_size} bytes)")
                
                if not os.path.exists(file_path):
                    await progress_msg.edit_text("❌ File not found on disk!")
                    await asyncio.sleep(15)
                    await progress_msg.delete()
                    return
                
                # Upload the file
                file_name = os.path.basename(file_path)
                
                # Show upload starting
                upload_text = (
                    f"╭━━━〔 📤 UPLOAD STARTING 〕━━━╮\n"
                    f"┃ 📁 File: {file_name[:35]}\n"
                    f"┃ 📦 Size: {humanbytes(file_size)}\n"
                    f"┃ 🔄 Status: Preparing upload...\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
                )
                await progress_msg.edit_text(upload_text)
                
                # Determine file type and upload
                ext = os.path.splitext(file_path)[1].lower()
                
                try:
                    if ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
                        # Video file
                        try:
                            width, height, duration = await Mdata01(file_path)
                            duration = max(duration, 1)
                        except:
                            width, height, duration = 0, 0, 0
                        
                        uploaded_msg = await client.send_video(
                            chat_id=message.chat.id,
                            video=file_path,
                            caption=f"<b>{file_name}</b>",
                            parse_mode=enums.ParseMode.HTML,
                            duration=duration,
                            width=width,
                            height=height,
                            supports_streaming=True,
                            progress=progress_for_pyrogram,
                            progress_args=("Uploading", progress_msg, time.time(), file_name, False),
                        )
                    else:
                        # Document file
                        uploaded_msg = await client.send_document(
                            chat_id=message.chat.id,
                            document=file_path,
                            caption=f"<b>{file_name}</b>",
                            parse_mode=enums.ParseMode.HTML,
                            progress=progress_for_pyrogram,
                            progress_args=("Uploading", progress_msg, time.time(), file_name, False),
                        )
                    
                    # Delete progress message
                    await progress_msg.delete()
                    
                    # Clean up
                    await torrent_manager.remove_torrent(info_hash, delete_files=True)
                    
                    # Clean up downloaded torrent file if it exists
                    if torrent_file_path and os.path.exists(torrent_file_path):
                        try:
                            os.remove(torrent_file_path)
                            logger.info(f"Cleaned up torrent file: {torrent_file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up torrent file: {e}")
                    
                    logger.info(f"Torrent upload complete: {info_hash}")
                    
                except Exception as e:
                    logger.error(f"Upload error: {e}", exc_info=True)
                    await progress_msg.edit_text(f"❌ Upload error: {str(e)[:200]}")
                    await asyncio.sleep(15)
                    await progress_msg.delete()
            else:
                await progress_msg.edit_text("❌ Torrent data not found!")
                await asyncio.sleep(15)
                await progress_msg.delete()
        else:
            logger.error(f"Failed to add torrent")
            await progress_msg.edit_text("❌ Failed to add torrent! Check if magnet link is valid.")
            await asyncio.sleep(15)
            await progress_msg.delete()
    except Exception as e:
        logger.error(f"Torrent command error: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        await asyncio.sleep(15)
        await progress_msg.delete()


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

# ======================= CALLBACK HANDLERS (for language & close buttons) =======================
@Client.on_callback_query(filters.regex(r"^set_lang_"))
async def language_callback(client: Client, callback_query):
    lang_code = callback_query.data.replace("set_lang_", "")
    user_id = callback_query.from_user.id
    if lang_code in LANGUAGES:
        set_language(user_id, lang_code)
        await callback_query.answer(f"✅ Language changed to {LANGUAGES[lang_code]}!", show_alert=True)
        await callback_query.message.edit_text(f"✅ **Language set to {LANGUAGES[lang_code]}**")
    else:
        await callback_query.answer("❌ Invalid language!", show_alert=True)

@Client.on_callback_query(filters.regex(r"^close$"))
async def close_callback(client: Client, callback_query):
    await callback_query.message.delete()
    await callback_query.answer("Closed!")
