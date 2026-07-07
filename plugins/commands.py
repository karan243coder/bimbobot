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
import asyncio

# Language command
@Client.on_message(filters.command("language"))
async def language_command(client: Client, message: Message):
    """Change user language"""
    keyboard = []
    
    for lang_code, lang_name in LANGUAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{lang_name}",
                callback_data=f"set_lang_{lang_code}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("❌ Close", callback_data="close")
    ])
    
    await message.reply_text(
        "🌐 **Select Language / भाषा चुनें**\n\n"
        "Choose your preferred language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Queue command
@Client.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    """Show download queue"""
    queue_stats = download_queue.get_queue_stats()
    
    text = "📋 **Download Queue**\n\n"
    text += f"⏳ Waiting: {queue_stats['waiting']}\n"
    text += f"⬇️ Active: {queue_stats['active']}\n"
    text += f"✅ Completed: {queue_stats['completed']}\n"
    text += f"❌ Failed: {queue_stats['failed']}\n\n"
    
    # Show active downloads
    active = download_queue.get_active_downloads()
    if active:
        text += "**Active Downloads:**\n"
        for task_id, task in list(active.items())[:5]:
            text += f"• {task.get('filename', 'Unknown')}\n"
            text += f"  Progress: {task.get('progress', 0):.1f}%\n"
            text += f"  Speed: {task.get('speed', 0) / 1024 / 1024:.2f} MB/s\n\n"
    
    await message.reply_text(text)

# Quota command
@Client.on_message(filters.command("quota"))
async def quota_command(client: Client, message: Message):
    """Show user quota"""
    user_id = message.from_user.id
    quota = quota_manager.get_user_quota(user_id)
    lang = get_user_language(user_id)
    
    if lang == 'hi':
        text = "📊 **आपकी दैनिक सीमा**\n\n"
        text += f"📥 डाउनलोड: {quota['downloads_used']}/{quota['download_limit']}\n"
        text += f"💾 डेटा: {quota['data_used'] / 1024 / 1024:.2f} MB / {quota['data_limit'] / 1024 / 1024:.0f} MB\n"
        text += f"🎬 वीडियो: {quota['video_conversions_used']}/{quota['video_conversion_limit']}\n"
        text += f"📸 स्क्रीनशॉट: {quota['screenshots_used']}/{quota['screenshot_limit']}\n\n"
        text += f"⏰ रीसेट: {quota['reset_time'].strftime('%H:%M')}"
    else:
        text = "📊 **Your Daily Quota**\n\n"
        text += f"📥 Downloads: {quota['downloads_used']}/{quota['download_limit']}\n"
        text += f"💾 Data: {quota['data_used'] / 1024 / 1024:.2f} MB / {quota['data_limit'] / 1024 / 1024:.0f} MB\n"
        text += f"🎬 Video Conversions: {quota['video_conversions_used']}/{quota['video_conversion_limit']}\n"
        text += f"📸 Screenshots: {quota['screenshots_used']}/{quota['screenshot_limit']}\n\n"
        text += f"⏰ Resets at: {quota['reset_time'].strftime('%H:%M')}"
    
    await message.reply_text(text)

# Premium command
@Client.on_message(filters.command("premium"))
async def premium_command(client: Client, message: Message):
    """Show premium info"""
    user_id = message.from_user.id
    premium_info = premium_manager.get_user_premium(user_id)
    lang = get_user_language(user_id)
    
    if premium_info['is_premium']:
        if lang == 'hi':
            text = "⭐ **प्रीमियम सदस्यता**\n\n"
            text += f"👑 स्थिति: सक्रिय\n"
            text += f"📅 समाप्ति: {premium_info['expiry'].strftime('%d %B %Y')}\n"
            text += f"⏰ शेष दिन: {premium_info['days_remaining']}\n\n"
            text += "**प्रीमियम लाभ:**\n"
            text += "✓ असीमित डाउनलोड\n"
            text += "✓ असीमित डेटा\n"
            text += "✓ वीडियो रूपांतरण\n"
            text += "✓ स्क्रीनशॉट जनरेशन\n"
            text += "✓ प्राथमिकता कतार\n"
            text += "✓ विज्ञापन मुक्त"
        else:
            text = "⭐ **Premium Membership**\n\n"
            text += f"👑 Status: Active\n"
            text += f"📅 Expires: {premium_info['expiry'].strftime('%d %B %Y')}\n"
            text += f"⏰ Days remaining: {premium_info['days_remaining']}\n\n"
            text += "**Premium Benefits:**\n"
            text += "✓ Unlimited downloads\n"
            text += "✓ Unlimited data\n"
            text += "✓ Video conversion\n"
            text += "✓ Screenshot generation\n"
            text += "✓ Priority queue\n"
            text += "✓ Ad-free experience"
    else:
        if lang == 'hi':
            text = "⭐ **प्रीमियम में अपग्रेड करें**\n\n"
            text += "असीमित डाउनलोड और विशेष सुविधाओं का आनंद लें!\n\n"
            text += "**प्रीमियम लाभ:**\n"
            text += "✓ असीमित डाउनलोड\n"
            text += "✓ असीमित डेटा\n"
            text += "✓ वीडियो रूपांतरण\n"
            text += "✓ स्क्रीनशॉट जनरेशन\n"
            text += "✓ प्राथमिकता कतार\n\n"
            text += "संपर्क करें: @BIMBO_Support"
        else:
            text = "⭐ **Upgrade to Premium**\n\n"
            text += "Enjoy unlimited downloads and exclusive features!\n\n"
            text += "**Premium Benefits:**\n"
            text += "✓ Unlimited downloads\n"
            text += "✓ Unlimited data\n"
            text += "✓ Video conversion\n"
            text += "✓ Screenshot generation\n"
            text += "✓ Priority queue\n\n"
            text += "Contact: @BIMBO_Support"
    
    await message.reply_text(text)

# Status command with real-time stats
@Client.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Show real-time system status"""
    msg = await message.reply_text("📊 Fetching system status...")
    
    progress = AdvancedProgress(message.from_user.id, "Status")
    
    # Get all active downloads
    active_downloads = download_queue.get_active_downloads()
    active_torrents = await torrent_manager.get_all_torrents()
    
    # Calculate total speeds
    total_dl_speed = 0
    total_ul_speed = 0
    
    for task_id, task in active_downloads.items():
        total_dl_speed += task.get('speed', 0)
    
    for info_hash, torrent in active_torrents.items():
        total_dl_speed += torrent.get('download_rate', 0)
        total_ul_speed += torrent.get('upload_rate', 0)
    
    # Build status message
    status_text = progress.build_status_message(
        total_downloads=len(active_downloads),
        total_torrents=len(active_torrents),
        download_speed=total_dl_speed,
        upload_speed=total_ul_speed
    )
    
    await msg.edit_text(status_text)

# Convert command
@Client.on_message(filters.command("convert"))
async def convert_command(client: Client, message: Message):
    """Convert video format"""
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video file with /convert")
        return
    
    # Check premium
    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ This feature requires Premium membership!\nUse /premium for more info.")
        return
    
    # Check quota
    if not quota_manager.can_use_feature(user_id, 'video_conversion'):
        await message.reply_text("⚠️ Daily video conversion limit reached!")
        return
    
    video = message.reply_to_message.video
    msg = await message.reply_text("⬇️ Downloading video...")
    
    # Download video
    file_path = await client.download_media(video.file_id)
    
    await msg.edit_text("🔄 Converting video...")
    
    # Convert
    output_path = await video_converter.convert_video(
        file_path,
        output_format="mp4",
        quality="medium"
    )
    
    if output_path:
        await msg.edit_text("⬆️ Uploading converted video...")
        await client.send_document(
            message.chat.id,
            output_path,
            caption="✅ Video converted successfully!"
        )
        
        # Update quota
        quota_manager.use_feature(user_id, 'video_conversion')
        
        await msg.delete()
    else:
        await msg.edit_text("❌ Video conversion failed!")

# Screenshot command
@Client.on_message(filters.command("screenshot"))
async def screenshot_command(client: Client, message: Message):
    """Generate screenshot from video"""
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video file with /screenshot")
        return
    
    # Check premium
    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ This feature requires Premium membership!\nUse /premium for more info.")
        return
    
    # Check quota
    if not quota_manager.can_use_feature(user_id, 'screenshot'):
        await message.reply_text("⚠️ Daily screenshot limit reached!")
        return
    
    video = message.reply_to_message.video
    msg = await message.reply_text("⬇️ Downloading video...")
    
    # Download video
    file_path = await client.download_media(video.file_id)
    
    await msg.edit_text("📸 Generating screenshot...")
    
    # Generate screenshot
    screenshot_path = await screenshot_generator.generate_screenshot(file_path)
    
    if screenshot_path:
        await msg.edit_text("⬆️ Uploading screenshot...")
        await client.send_photo(
            message.chat.id,
            screenshot_path,
            caption="✅ Screenshot generated!"
        )
        
        # Update quota
        quota_manager.use_feature(user_id, 'screenshot')
        
        await msg.delete()
    else:
        await msg.edit_text("❌ Screenshot generation failed!")

# Torrent command
@Client.on_message(filters.command("torrent"))
async def torrent_command(client: Client, message: Message):
    """Add torrent download"""
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: /torrent <magnet_link>")
        return
    
    # Check premium
    user_id = message.from_user.id
    if not premium_manager.is_premium(user_id):
        await message.reply_text("⭐ Torrent downloads require Premium membership!\nUse /premium for more info.")
        return
    
    magnet_uri = message.command[1]
    
    msg = await message.reply_text("🔄 Adding torrent...")
    
    # Add torrent
    async def progress_callback(data):
        if data.get('is_finished'):
            await msg.edit_text(f"✅ Torrent completed!\n{data.get('name', 'Unknown')}")
        else:
            progress_text = (
                f"⬇️ **{data.get('name', 'Fetching metadata...')}**\n\n"
                f"Progress: {data.get('progress', 0):.1f}%\n"
                f"⬇️ {data.get('download_rate', 0) / 1024 / 1024:.2f} MB/s\n"
                f"⬆️ {data.get('upload_rate', 0) / 1024 / 1024:.2f} MB/s\n"
                f"Peers: {data.get('num_peers', 0)} | Seeds: {data.get('num_seeds', 0)}\n"
                f"State: {data.get('state', 'Unknown')}"
            )
            await msg.edit_text(progress_text)
    
    info_hash = await torrent_manager.add_torrent(
        magnet_uri=magnet_uri,
        progress_callback=progress_callback
    )
    
    if info_hash:
        await msg.edit_text(f"✅ Torrent added!\nHash: `{info_hash}`")
    else:
        await msg.edit_text("❌ Failed to add torrent!")
