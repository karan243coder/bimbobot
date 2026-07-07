# -*- coding: utf-8 -*-
# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import os
import json
import math
import time
import re
import shutil
import asyncio
import logging
import html
from datetime import datetime

from config import Config
from translation import Translation
from plugins.custom_thumbnail import Gthumb01, Gthumb02, Mdata01, Mdata02, Mdata03, get_flocation
from pyrogram import enums
from helper_funcs.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

PROGRESS_UPDATE_INTERVAL = 5


def escape_html(text):
    return html.escape(str(text or ""), quote=False)


def sanitize_file_name(file_name: str) -> str:
    file_name = str(file_name or "file").strip()
    file_name = re.sub(r'[\\/:*?"<>|]+', ' ', file_name)
    file_name = re.sub(r'\s+', ' ', file_name).strip()
    return (file_name[:180] if file_name else f"file_{int(time.time())}")


def trim_text(text: str, limit: int = 32) -> str:
    text = str(text or "Unknown File")
    return text if len(text) <= limit else text[:limit - 3] + "..."


def get_status_emoji(percentage: float) -> str:
    if percentage < 25:
        return "🟡"
    if percentage < 50:
        return "🟠"
    if percentage < 75:
        return "🔵"
    if percentage < 100:
        return "🟢"
    return "✅"


def build_progress_bar(percentage: float, total_blocks: int = 20) -> str:
    percentage = max(0.0, min(100.0, percentage))
    completed_blocks = min(total_blocks, math.floor(percentage / (100 / total_blocks)))
    remaining_blocks = total_blocks - completed_blocks
    return "█" * completed_blocks + "░" * remaining_blocks


def size_text_to_bytes(size_text: str) -> int:
    if not size_text:
        return 0
    match = re.search(r'([\d.]+)\s*([KMGTP]?i?B)', size_text, re.IGNORECASE)
    if not match:
        return 0

    value = float(match.group(1))
    unit = match.group(2).upper()
    power_map = {
        "B": 0,
        "KIB": 1,
        "KB": 1,
        "MIB": 2,
        "MB": 2,
        "GIB": 3,
        "GB": 3,
        "TIB": 4,
        "TB": 4,
        "PIB": 5,
        "PB": 5,
    }
    power = power_map.get(unit, 0)
    return int(value * (1024 ** power))


def build_download_card(display_name, percentage, speed_text, total_size_text, eta_text, elapsed_text, downloaded_text="--"):
    status_emoji = get_status_emoji(percentage)
    progress_bar = build_progress_bar(percentage)
    return (
        f"╭━━━〔 {status_emoji} YT-DLP DOWNLOAD 〕━━━╮\n"
        f"┃ 📁 File      : {trim_text(display_name, 34)}\n"
        f"┃ {progress_bar} {percentage:.2f}%\n"
        f"┃ ⚡ Speed     : {speed_text}\n"
        f"┃ 📦 Progress  : {downloaded_text} / {total_size_text}\n"
        f"┃ ⏳ ETA       : {eta_text}\n"
        f"┃ 🕒 Elapsed   : {elapsed_text}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )


def build_stage_card(display_name, stage_text, elapsed_text):
    return (
        f"╭━━━〔 ⚙️ PROCESSING 〕━━━╮\n"
        f"┃ 📁 File      : {trim_text(display_name, 34)}\n"
        f"┃ 🔄 Stage     : {stage_text}\n"
        f"┃ 🕒 Elapsed   : {elapsed_text}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )


async def safe_edit(message, text):
    try:
        await message.edit(text=text)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e).upper():
            logger.debug(f"Message edit skipped: {e}")


async def send_log_media(
    bot,
    user,
    file_path,
    link,
    file_name,
    media_type,
    file_size,
    thumbnail=None,
    duration=0,
    width=0,
    height=0,
):
    """Log channel mein media file aur details bhejega."""
    if not Config.BIMBO_LOG_CHANNEL or Config.BIMBO_LOG_CHANNEL == 0:
        return

    try:
        username = f"@{user.username}" if getattr(user, "username", None) else "N/A"
        first_name = escape_html(getattr(user, "first_name", None) or "User")
        user_mention = f'<a href="tg://user?id={user.id}">{first_name}</a>'

        safe_link = escape_html(link)[:1500]
        safe_file_name = escape_html(file_name)[:300]
        safe_media_type = escape_html(media_type)

        caption = (
            "<b>📥 Media Downloaded Successfully</b>\n\n"
            f"<b>👤 User:</b> {user_mention} (<code>{user.id}</code>)\n"
            f"<b>🔖 Username:</b> {escape_html(username)}\n"
            f"<b>🔗 Source Link:</b> <code>{safe_link}</code>\n"
            f"<b>📁 Original Name:</b> <code>{safe_file_name}</code>\n"
            f"<b>🎬 Media Type:</b> {safe_media_type}\n"
            f"<b>📦 Size:</b> {humanbytes(file_size)}\n"
            f"<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await bot.send_message(
            chat_id=Config.BIMBO_LOG_CHANNEL,
            text=caption,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )

        if not os.path.exists(file_path):
            return

        thumb_to_use = thumbnail if thumbnail and os.path.exists(thumbnail) else None

        if media_type == "audio":
            kwargs = {
                "chat_id": Config.BIMBO_LOG_CHANNEL,
                "audio": file_path,
                "caption": "<b>🎵 Audio File</b>",
                "parse_mode": enums.ParseMode.HTML,
            }
            if thumb_to_use:
                kwargs["thumb"] = thumb_to_use
            if duration and duration > 0:
                kwargs["duration"] = duration
            await bot.send_audio(**kwargs)

        elif media_type == "video":
            kwargs = {
                "chat_id": Config.BIMBO_LOG_CHANNEL,
                "video": file_path,
                "caption": "<b>🎬 Video File</b>",
                "parse_mode": enums.ParseMode.HTML,
                "supports_streaming": True,
            }
            if thumb_to_use:
                kwargs["thumb"] = thumb_to_use
            if duration and duration > 0:
                kwargs["duration"] = duration
            if width and width > 0:
                kwargs["width"] = width
            if height and height > 0:
                kwargs["height"] = height
            await bot.send_video(**kwargs)

        else:
            kwargs = {
                "chat_id": Config.BIMBO_LOG_CHANNEL,
                "document": file_path,
                "caption": "<b>📁 Document File</b>",
                "parse_mode": enums.ParseMode.HTML,
            }
            if thumb_to_use:
                kwargs["thumb"] = thumb_to_use
            await bot.send_document(**kwargs)

    except Exception as e:
        logger.error(f"Log channel media error: {e}")


async def youtube_dl_call_back(bot, update):
    try:
        cb_data = update.data
        logger.info(f"Callback received: {cb_data[:100]}")
        
        # Extract task_id from callback data (format: type|format|ext|task_id)
        parts = cb_data.split("|")
        logger.info(f"Callback parts: {parts}")
        
        if len(parts) < 3:
            logger.error(f"Invalid callback format: {cb_data}")
            await update.message.edit_text("❌ **Error:** Invalid callback format. Please try again.")
            return
        
        tg_send_type, youtube_dl_format, youtube_dl_ext = parts[0], parts[1], parts[2]
        task_id = parts[3] if len(parts) > 3 else ""
        
        logger.info(f"Extracted: type={tg_send_type}, format={youtube_dl_format}, ext={youtube_dl_ext}, task_id={task_id}")
        
        # Show processing message immediately
        try:
            await update.message.edit_text("⚙️ **Processing...**\n\n🔄 Starting download...")
        except Exception as e:
            logger.warning(f"Could not edit message: {e}")
        
        save_ytdl_json_path = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, f"{update.from_user.id}_{task_id}.json")
        logger.info(f"Looking for JSON file: {save_ytdl_json_path}")
        
        # Check if file exists
        if not os.path.exists(save_ytdl_json_path):
            # Try old format (without task_id) for backward compatibility
            old_path = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, f"{update.from_user.id}.json")
            if os.path.exists(old_path):
                save_ytdl_json_path = old_path
                logger.warning(f"Using old JSON format (without task_id): {old_path}")
            else:
                logger.error(f"JSON file not found: {save_ytdl_json_path}")
                await update.message.edit_text(
                    "❌ **Error:** Session expired!\n\n"
                    "Please send the link again and select quality."
                )
                return
        
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
            logger.info(f"Successfully loaded JSON: {response_json.get('title', 'Unknown')}")
    
    except Exception as e:
        logger.error(f"youtube_dl_call_back error: {e}", exc_info=True)
        try:
            await update.message.edit_text(
                f"❌ **Error:** {str(e)[:200]}\n\n"
                "Please try again or contact support."
            )
        except:
            pass
        return

    youtube_dl_url = update.message.reply_to_message.text or ""
    custom_file_name = f"{str(response_json.get('title') or 'file')[:50]}_{youtube_dl_format}"
    youtube_dl_username = None
    youtube_dl_password = None

    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url = url_parts[0]
            custom_file_name = url_parts[1]
        elif len(url_parts) == 4:
            youtube_dl_url = url_parts[0]
            custom_file_name = url_parts[1]
            youtube_dl_username = url_parts[2]
            youtube_dl_password = url_parts[3]
        else:
            for entity in (update.message.reply_to_message.entities or []):
                entity_type = str(getattr(entity, "type", "")).lower()
                if "text_link" in entity_type:
                    youtube_dl_url = entity.url
                elif entity_type.endswith("url") or entity_type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]

        if youtube_dl_url is not None:
            youtube_dl_url = youtube_dl_url.strip()
        if custom_file_name is not None:
            custom_file_name = custom_file_name.strip()
        if youtube_dl_username is not None:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password is not None:
            youtube_dl_password = youtube_dl_password.strip()
    else:
        for entity in (update.message.reply_to_message.entities or []):
            entity_type = str(getattr(entity, "type", "")).lower()
            if "text_link" in entity_type:
                youtube_dl_url = entity.url
            elif entity_type.endswith("url") or entity_type == "url":
                o = entity.offset
                l = entity.length
                youtube_dl_url = youtube_dl_url[o:o + l]

    original_link = youtube_dl_url
    original_name = custom_file_name

    description_text = response_json.get("fulltitle") or response_json.get("title") or original_name or "Uploaded File"
    description = f"<b>{escape_html(str(description_text)[:1021])}</b>"

    tmp_directory_for_each_user = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, str(update.from_user.id))
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)

    file_name = sanitize_file_name(custom_file_name)
    display_name = trim_text(file_name, 30)
    download_directory = os.path.join(tmp_directory_for_each_user, f"{file_name}.{youtube_dl_ext}")

    await safe_edit(update.message, build_stage_card(display_name, "Preparing download...", "0 s"))

    common_ytdlp_args = [
        "yt-dlp", "-c",
        "--no-warnings",
        "--newline",
        "--geo-bypass",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]

    if Config.BIMBO_HTTP_PROXY != "":
        common_ytdlp_args.extend(["--proxy", Config.BIMBO_HTTP_PROXY])

    if os.path.exists("cookies.txt"):
        common_ytdlp_args.extend(["--cookies", "cookies.txt"])

    # ============================================================
    #  xHamster (apna engine): JSON me xh_qualities hote hain ->
    #  seedha chosen quality ka .m3u8 URL yt-dlp+ffmpeg ko do
    #  (page URL ki zaroorat nahi, yt-dlp ka xhamster extractor bypass).
    # ============================================================
    xh_qualities = response_json.get("xh_qualities") if isinstance(response_json, dict) else None
    xh_headers = response_json.get("xh_headers") if isinstance(response_json, dict) else None
    is_xh_engine = bool(response_json.get("_xhamster")) and bool(xh_qualities)

    if is_xh_engine and youtube_dl_format.startswith("xh-"):
        # height nikaalo
        try:
            _h = int(youtube_dl_format.split("-", 1)[1])
        except Exception:
            _h = 720
        # us height ka m3u8, warna sabse paas wali quality
        m3u8_url = xh_qualities.get(str(_h))
        if not m3u8_url:
            avail = sorted((int(k) for k in xh_qualities.keys()))
            pick = min(avail, key=lambda x: abs(x - _h)) if avail else None
            m3u8_url = xh_qualities.get(str(pick)) if pick is not None else None

        if not m3u8_url:
            await safe_edit(update.message, "ERROR: xHamster quality URL not found 🙁")
            asyncio.create_task(clendir(tmp_directory_for_each_user))
            return

        # header args (Referer/Origin) — xHamster CDN ke liye zaroori
        hdr_args = []
        ref = (xh_headers or {}).get("Referer")
        org = (xh_headers or {}).get("Origin")
        if ref:
            hdr_args += ["--add-header", f"Referer:{ref}"]
        if org:
            hdr_args += ["--add-header", f"Origin:{org}"]

        if tg_send_type == "audio":
            command_to_exec = common_ytdlp_args + hdr_args + [
                "--prefer-ffmpeg", "--extract-audio",
                "--audio-format", youtube_dl_ext,
                "--audio-quality", youtube_dl_format if youtube_dl_format.isdigit() else "192K",
                "--hls-prefer-ffmpeg",
                "-o", download_directory,
                m3u8_url,
            ]
        else:
            command_to_exec = common_ytdlp_args + hdr_args + [
                "--hls-prefer-ffmpeg",
                "--merge-output-format", "mp4",
                "-o", download_directory,
                m3u8_url,
            ]
    elif tg_send_type == "audio":
        command_to_exec = common_ytdlp_args + [
            "--prefer-ffmpeg", "--extract-audio",
            "--audio-format", youtube_dl_ext,
            "--audio-quality", youtube_dl_format,
            "-o", download_directory,
            youtube_dl_url
        ]
    else:
        minus_f_format = youtube_dl_format
        if "youtu" in youtube_dl_url:
            minus_f_format = youtube_dl_format + "+bestaudio/best"
        # ---- xHamster (yt-dlp fallback) ----
        # agar kabhi engine fail hua aur yt-dlp se buttons bane the,
        # to format_id "xh-<height>" pe HEIGHT-BASED h264+audio HLS chuno.
        if youtube_dl_format.startswith("xh-"):
            try:
                _h = int(youtube_dl_format.split("-", 1)[1])
            except Exception:
                _h = 720
            minus_f_format = (
                f"b[height<={_h}][vcodec^=avc1][protocol^=m3u8]/"
                f"bv*[height<={_h}][vcodec^=avc1][protocol^=m3u8]+ba/"
                f"b[height<={_h}][vcodec^=avc1]/"
                f"bv*[height<={_h}]+ba/b[height<={_h}]/b"
            )
        command_to_exec = common_ytdlp_args + [
            "--embed-subs", "-f", minus_f_format,
            "--hls-prefer-ffmpeg",
            "--merge-output-format", "mp4",
            "-o", download_directory,
            youtube_dl_url
        ]

    if youtube_dl_username is not None:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password is not None:
        command_to_exec.extend(["--password", youtube_dl_password])

    start = datetime.now()
    asyncio.create_task(clendir(save_ytdl_json_path))

    download_start_time = time.time()
    try:
        process = await asyncio.create_subprocess_exec(
            *command_to_exec,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        await safe_edit(update.message, "**ERROR:** `yt-dlp` install nahi hai. Requirements install/deploy dobara karo.")
        return

    last_progress_update = 0
    ytdlp_output = ""

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        decoded_line = line.decode(errors="ignore").strip()
        if decoded_line:
            ytdlp_output += decoded_line + "\n"

        now = time.time()
        elapsed_str = TimeFormatter(milliseconds=int((now - download_start_time) * 1000)) or "0 s"

        if "[download]" in decoded_line and "%" in decoded_line:
            try:
                if now - last_progress_update >= PROGRESS_UPDATE_INTERVAL:
                    percent_match = re.search(r'(\d+\.?\d*)%', decoded_line)
                    percentage = float(percent_match.group(1)) if percent_match else 0.0

                    speed_match = re.search(r'at\s+(.+?)(?:\s+ETA|$)', decoded_line)
                    speed = speed_match.group(1).strip() if speed_match else "Calculating..."

                    size_match = re.search(r'of\s+~?\s*([\d\.]+\s*[KMGTP]?i?B)', decoded_line)
                    total_size = size_match.group(1).strip() if size_match else "Unknown"

                    eta_match = re.search(r'ETA\s+([0-9:]+)', decoded_line)
                    eta = eta_match.group(1).strip() if eta_match else "Calculating..."

                    downloaded_text = "--"
                    total_bytes = size_text_to_bytes(total_size)
                    if total_bytes > 0:
                        downloaded_bytes = int((percentage / 100) * total_bytes)
                        downloaded_text = humanbytes(downloaded_bytes)

                    progress_text = build_download_card(
                        display_name=display_name,
                        percentage=percentage,
                        speed_text=speed,
                        total_size_text=total_size,
                        eta_text=eta,
                        elapsed_text=elapsed_str,
                        downloaded_text=downloaded_text,
                    )
                    await safe_edit(update.message, progress_text)
                    last_progress_update = now
            except Exception as e:
                logger.error(f"Progress parse error: {e}")

        elif ("Merging formats into" in decoded_line or "[Merger]" in decoded_line) and now - last_progress_update >= 3:
            await safe_edit(update.message, build_stage_card(display_name, "Merging audio + video streams...", elapsed_str))
            last_progress_update = now

        elif ("[ExtractAudio]" in decoded_line or "Destination:" in decoded_line) and tg_send_type == "audio" and now - last_progress_update >= 3:
            await safe_edit(update.message, build_stage_card(display_name, "Extracting audio stream...", elapsed_str))
            last_progress_update = now

        elif ("[EmbedSubtitle]" in decoded_line or "[SubtitlesConvertor]" in decoded_line) and now - last_progress_update >= 3:
            await safe_edit(update.message, build_stage_card(display_name, "Embedding subtitles...", elapsed_str))
            last_progress_update = now

        elif "[download]" in decoded_line and now - last_progress_update >= 3:
            stage_text = "Downloading video data..."
            lower_line = decoded_line.lower()
            if "resum" in lower_line:
                stage_text = "Resuming partial download..."
            elif "destination" in lower_line:
                stage_text = "Saving file to disk..."
            elif "webpage" in lower_line:
                stage_text = "Fetching webpage info..."
            elif "m3u8" in lower_line:
                stage_text = "Fetching stream playlist..."
            elif "fragment" in lower_line:
                stage_text = "Downloading stream fragments..."
            await safe_edit(update.message, build_stage_card(display_name, stage_text, elapsed_str))
            last_progress_update = now

    await process.wait()
    ytdlp_output = ytdlp_output.strip()

    if process.returncode != 0:
        last_error = "\n".join(ytdlp_output.splitlines()[-8:]) or "Unknown yt-dlp error"

        # xHamster safety fallback: agar apna direct m3u8 engine download fail ho,
        # to turant original page URL par yt-dlp h264-HLS fallback try karo.
        if is_xh_engine:
            await safe_edit(update.message, build_stage_card(display_name, "Custom engine failed, trying yt-dlp fallback...", TimeFormatter(milliseconds=int((time.time() - download_start_time) * 1000)) or "0 s"))
            try:
                try:
                    _h = int(youtube_dl_format.split("-", 1)[1])
                except Exception:
                    _h = 720
                fallback_format = (
                    f"b[height<={_h}][vcodec^=avc1][protocol^=m3u8]/"
                    f"bv*[height<={_h}][vcodec^=avc1][protocol^=m3u8]+ba/"
                    f"b[height<={_h}][vcodec^=avc1]/"
                    f"bv*[height<={_h}]+ba/b[height<={_h}]/b"
                )
                fallback_cmd = common_ytdlp_args + [
                    "--embed-subs", "-f", fallback_format,
                    "--hls-prefer-ffmpeg",
                    "--merge-output-format", "mp4",
                    "-o", download_directory,
                    youtube_dl_url
                ]
                if youtube_dl_username is not None:
                    fallback_cmd.extend(["--username", youtube_dl_username])
                if youtube_dl_password is not None:
                    fallback_cmd.extend(["--password", youtube_dl_password])

                fb = await asyncio.create_subprocess_exec(
                    *fallback_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                fb_output = ""
                while True:
                    line = await fb.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode(errors="ignore").strip()
                    if decoded_line:
                        fb_output += decoded_line + "\n"
                    now = time.time()
                    elapsed_str = TimeFormatter(milliseconds=int((now - download_start_time) * 1000)) or "0 s"
                    if "[download]" in decoded_line and "%" in decoded_line and now - last_progress_update >= PROGRESS_UPDATE_INTERVAL:
                        try:
                            percent_match = re.search(r'(\d+\.?\d*)%', decoded_line)
                            percentage = float(percent_match.group(1)) if percent_match else 0.0
                            speed_match = re.search(r'at\s+(.+?)(?:\s+ETA|$)', decoded_line)
                            speed = speed_match.group(1).strip() if speed_match else "Calculating..."
                            size_match = re.search(r'of\s+~?\s*([\d\.]+\s*[KMGTP]?i?B)', decoded_line)
                            total_size = size_match.group(1).strip() if size_match else "Unknown"
                            eta_match = re.search(r'ETA\s+([0-9:]+)', decoded_line)
                            eta = eta_match.group(1).strip() if eta_match else "Calculating..."
                            await safe_edit(update.message, build_download_card(display_name, percentage, speed, total_size, eta, elapsed_str))
                            last_progress_update = now
                        except Exception:
                            pass
                    elif "[download]" in decoded_line and now - last_progress_update >= 3:
                        await safe_edit(update.message, build_stage_card(display_name, "Fallback downloading stream...", elapsed_str))
                        last_progress_update = now

                await fb.wait()
                if fb.returncode != 0:
                    fb_last_error = "\n".join(fb_output.strip().splitlines()[-8:]) or "Unknown fallback error"
                    asyncio.create_task(clendir(tmp_directory_for_each_user))
                    await bot.edit_message_text(
                        chat_id=update.message.chat.id,
                        message_id=update.message.id,
                        text=f"**ERROR: Download failed ⚠️**\n`Custom engine:\n{last_error[:420]}\n\nFallback:\n{fb_last_error[:420]}`",
                    )
                    return
            except Exception as e:
                asyncio.create_task(clendir(tmp_directory_for_each_user))
                await bot.edit_message_text(
                    chat_id=update.message.chat.id,
                    message_id=update.message.id,
                    text=f"**ERROR: Download failed ⚠️**\n`{last_error[:650]}\n\nFallback exception: {str(e)[:200]}`",
                )
                return
        else:
            asyncio.create_task(clendir(tmp_directory_for_each_user))
            await bot.edit_message_text(
                chat_id=update.message.chat.id,
                message_id=update.message.id,
                text=f"**ERROR: Download failed ⚠️**\n`{last_error[:900]}`",
            )
            return

    file_size, file_location = await get_flocation(download_directory, youtube_dl_ext)

    if file_size == 0:
        await safe_edit(update.message, "ERROR: File not found 🙁")
        asyncio.create_task(clendir(tmp_directory_for_each_user))
        return

    # Show upload starting message
    upload_start_text = (
        f"╭━━━〔 📤 UPLOAD STARTING 〕━━━╮\n"
        f"┃ 📁 File: {trim_text(file_name, 35)}\n"
        f"┃ 📦 Size: {humanbytes(file_size)}\n"
        f"┃ 🔄 Status: Preparing upload...\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )
    await safe_edit(update.message, upload_start_text)
    
    # Set this message for upload progress tracking
    from helper_funcs.display_progress import set_user_message
    set_user_message(update.from_user.id, update.message)

    thumbnail = None
    duration = 0
    width = 0
    height = 0

    try:
        start_time = time.time()

        if tg_send_type == "audio":
            duration = await Mdata03(file_location)
            thumbnail = await Gthumb01(bot, update, task_id)
            await bot.send_audio(
                chat_id=update.message.chat.id,
                audio=file_location,
                caption=description,
                parse_mode=enums.ParseMode.HTML,
                duration=duration,
                thumb=thumbnail,
                reply_to_message_id=update.message.reply_to_message.id,
                progress=progress_for_pyrogram,
                progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
            )

        elif tg_send_type == "file":
            thumbnail = await Gthumb01(bot, update, task_id)
            await bot.send_document(
                chat_id=update.message.chat.id,
                document=file_location,
                thumb=thumbnail,
                caption=description,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=update.message.reply_to_message.id,
                progress=progress_for_pyrogram,
                progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
            )

        elif tg_send_type == "vm":
            width, duration = await Mdata02(file_location)
            duration = max(duration, 1)
            thumbnail = await Gthumb02(bot, update, duration, file_location, task_id)
            await bot.send_video_note(
                chat_id=update.message.chat.id,
                video_note=file_location,
                duration=duration,
                length=width,
                thumb=thumbnail,
                reply_to_message_id=update.message.reply_to_message.id,
                progress=progress_for_pyrogram,
                progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
            )

        elif tg_send_type == "video":
            width, height, duration = await Mdata01(file_location)
            duration = max(duration, 1)
            thumbnail = await Gthumb02(bot, update, duration, file_location, task_id)
            await bot.send_video(
                chat_id=update.message.chat.id,
                video=file_location,
                caption=description,
                parse_mode=enums.ParseMode.HTML,
                duration=duration,
                width=width,
                height=height,
                thumb=thumbnail,
                supports_streaming=True,
                reply_to_message_id=update.message.reply_to_message.id,
                progress=progress_for_pyrogram,
                progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
            )

        else:
            thumbnail = await Gthumb01(bot, update, task_id)
            await bot.send_document(
                chat_id=update.message.chat.id,
                document=file_location,
                thumb=thumbnail,
                caption=description,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=update.message.reply_to_message.id,
                progress=progress_for_pyrogram,
                progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
            )

        await send_log_media(
            bot=bot,
            user=update.from_user,
            file_path=file_location,
            link=original_link,
            file_name=original_name,
            media_type=tg_send_type,
            file_size=file_size,
            thumbnail=thumbnail,
            duration=duration,
            width=width,
            height=height,
        )

        if thumbnail:
            asyncio.create_task(clendir(thumbnail))
        asyncio.create_task(clendir(file_location))

        success_text = (
            "<b>✅ Uploaded successfully</b>\n\n"
            f"<b>📁 File:</b> <code>{escape_html(trim_text(file_name, 60))}</code>\n"
            f"<b>📦 Size:</b> {humanbytes(file_size)}\n"
            f"<b>⏱ Download Time:</b> {(datetime.now() - start).seconds}s\n\n"
            "<b>Join:</b> @Bimbobot69"
        )
        await bot.edit_message_text(
            text=success_text,
            chat_id=update.message.chat.id,
            message_id=update.message.id,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )

    except Exception as e:
        asyncio.create_task(clendir(file_location))
        if thumbnail:
            asyncio.create_task(clendir(thumbnail))
        await bot.edit_message_text(
            text=Translation.BIMBO_ERROR.format(escape_html(str(e))),
            chat_id=update.message.chat.id,
            message_id=update.message.id,
            parse_mode=enums.ParseMode.HTML,
        )




async def terabox_call_back(bot, update):
    """Handle Terabox download callback using TeraboxDL package"""
    try:
        # Parse callback data: terabox=type|task_id
        cb_data = update.data
        parts = cb_data.split("|")
        tg_send_type = parts[0].split("=")[1]  # video, file, or audio
        task_id = parts[1] if len(parts) > 1 else ""
        
        if not url:
            # Try to get URL from JSON file (old method compatibility)
            save_ytdl_json_path = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, f"{update.from_user.id}.json")
            if os.path.exists(save_ytdl_json_path):
                with open(save_ytdl_json_path, "r", encoding="utf8") as f:
                    tb_json = json.load(f)
                url = tb_json.get("tb_share_url", "")
        
        if not url:
            await update.message.edit("❌ Invalid Terabox session. Please send the link again.")
            return
        
        logger.info(f"Terabox callback: type={tg_send_type}, url={url}")
        
        # Send processing message
        await safe_edit(update.message, 
            "🔄 **Processing Terabox Link**\n\n"
            "Extracting file information...\n"
            "⏳ Please wait..."
        )
        
        # Import terabox engine
        from plugins.terabox_engine import extract_terabox_info, download_terabox_file
        
        # Extract file info
        file_info = extract_terabox_info(url)
        
        if not file_info or not file_info.get('success'):
            error_msg = file_info.get('error', 'Unknown error') if file_info else 'Failed to extract info'
            error_type = file_info.get('error_type', 'unknown') if file_info else 'unknown'
            
            if error_type == 'config_missing':
                error_text = (
                    "❌ **Configuration Error**\n\n"
                    "Terabox cookie not configured.\n\n"
                    "📝 **How to fix:**\n"
                    "1. Login to Terabox in browser\n"
                    "2. Open DevTools (F12)\n"
                    "3. Go to Application → Cookies\n"
                    "4. Copy 'lang' and 'ndus' values\n"
                    "5. Set BIMBO_TERABOX_COOKIE in environment:\n"
                    "   `lang=en; ndus=YOUR_VALUE;`\n\n"
                    "Contact bot owner to configure this."
                )
            elif error_type == 'package_missing':
                error_text = (
                    "❌ **Package Not Installed**\n\n"
                    "TeraboxDL package is missing.\n\n"
                    "Contact bot owner to install:\n"
                    "`pip install terabox-downloader`"
                )
            else:
                error_text = (
                    f"❌ **Terabox Error**\n\n"
                    f"Failed to extract file info:\n"
                    f"`{escape_html(error_msg[:200])}`\n\n"
                    "This might be due to:\n"
                    "• Invalid or expired link\n"
                    "• Invalid cookie configuration\n"
                    "• Terabox API issues\n"
                    "• File not accessible"
                )
            
            await update.message.edit(error_text, parse_mode=enums.ParseMode.HTML)
            return
        
        # Update message with file info
        file_name = file_info.get('file_name', 'Unknown')
        file_size = file_info.get('file_size', 0)
        thumbnail_url = file_info.get('thumbnail', '')
        
        # Format file size
        if file_size:
            size_mb = file_size / (1024 * 1024)
            if size_mb >= 1024:
                size_text = f"{size_mb / 1024:.2f} GB"
            else:
                size_text = f"{size_mb:.2f} MB"
        else:
            size_text = "Unknown"
        
        display_name = trim_text(file_name, 30)
        
        await safe_edit(update.message, build_stage_card(display_name, "Downloading from Terabox...", "0 s"))
        
        # Download file
        tmp_directory = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, str(update.from_user.id))
        os.makedirs(tmp_directory, exist_ok=True)
        
        terabox_instance = file_info.get('teraboxdl_instance')
        file_path = download_terabox_file(terabox_instance, file_info, tmp_directory)
        
        if not file_path or not os.path.exists(file_path):
            await update.message.edit(
                "❌ **Download Failed**\n\n"
                "Failed to download file from Terabox.\n"
                "Please try again later.",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        actual_file_size = os.path.getsize(file_path)
        
        # Check Telegram file size limit
        if actual_file_size > Config.BIMBO_TG_MAX_FILE_SIZE:
            await update.message.edit(
                f"❌ File too large ({humanbytes(actual_file_size)}). "
                f"Telegram limit: {humanbytes(Config.BIMBO_TG_MAX_FILE_SIZE)}"
            )
            asyncio.create_task(clendir(file_path))
            return
        
        # Upload to Telegram
        await safe_edit(update.message, Translation.BIMBO_UPLOAD_START)
        
        thumbnail = None
        duration = 0
        width = 0
        height = 0
        
        try:
            start_time = time.time()
            description = f"<b>{escape_html(str(file_name)[:1021])}</b>"
            
            if tg_send_type == "audio":
                duration = await Mdata03(file_path)
                thumbnail = await Gthumb01(bot, update, task_id)
                await bot.send_audio(
                    chat_id=update.message.chat.id,
                    audio=file_path,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    duration=duration,
                    thumb=thumbnail,
                    reply_to_message_id=update.message.reply_to_message.id,
                    progress=progress_for_pyrogram,
                    progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
                )
            
            elif tg_send_type == "file":
                thumbnail = await Gthumb01(bot, update, task_id)
                await bot.send_document(
                    chat_id=update.message.chat.id,
                    document=file_path,
                    thumb=thumbnail,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    reply_to_message_id=update.message.reply_to_message.id,
                    progress=progress_for_pyrogram,
                    progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
                )
            
            elif tg_send_type == "video":
                width, height, duration = await Mdata01(file_path)
                duration = max(duration, 1)
                thumbnail = await Gthumb02(bot, update, duration, file_path, task_id)
                await bot.send_video(
                    chat_id=update.message.chat.id,
                    video=file_path,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumbnail,
                    supports_streaming=True,
                    reply_to_message_id=update.message.reply_to_message.id,
                    progress=progress_for_pyrogram,
                    progress_args=(Translation.BIMBO_UPLOAD_START, update.message, start_time, file_name, False),
                )
            
            # Send to log channel
            try:
                await send_log_media(
                    bot=bot,
                    user=update.from_user,
                    file_path=file_path,
                    link=url,
                    file_name=file_name,
                    media_type=tg_send_type,
                    file_size=actual_file_size,
                    thumbnail=thumbnail,
                    duration=duration,
                    width=width,
                    height=height,
                )
            except Exception as e:
                logger.warning(f"Log channel error: {e}")
            
            # Cleanup
            if thumbnail:
                asyncio.create_task(clendir(thumbnail))
            asyncio.create_task(clendir(file_path))
            
            # Success message
            upload_time = int(time.time() - start_time)
            success_text = (
                "<b>✅ Uploaded successfully</b>\n\n"
                f"<b>📁 File:</b> <code>{escape_html(trim_text(file_name, 60))}</code>\n"
                f"<b>📦 Size:</b> {humanbytes(actual_file_size)}\n"
                f"<b>⏱ Upload Time:</b> {upload_time}s\n\n"
                "<b>Join:</b> @Bimbobot69"
            )
            await bot.edit_message_text(
                text=success_text,
                chat_id=update.message.chat.id,
                message_id=update.message.id,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        
        except Exception as e:
            asyncio.create_task(clendir(file_path))
            if thumbnail:
                asyncio.create_task(clendir(thumbnail))
            await bot.edit_message_text(
                text=Translation.BIMBO_ERROR.format(escape_html(str(e))),
                chat_id=update.message.chat.id,
                message_id=update.message.id,
                parse_mode=enums.ParseMode.HTML,
            )
    
    except Exception as e:
        logger.error(f"Terabox callback error: {e}", exc_info=True)
        try:
            await update.message.edit(f"❌ Error: {escape_html(str(e)[:200])}")
        except:
            pass



async def clendir(directory):
    try:
        os.remove(directory)
    except Exception:
        pass
    try:
        shutil.rmtree(directory)
    except Exception:
        pass
