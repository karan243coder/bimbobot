# BIMBO URL Bot - Advanced Display Progress
# Powered by BIMBO | Support: @Bimbo69

import logging
import math
import re
import time
import psutil
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Speed tracking
speed_history = {}
last_edit_time = {}
last_progress_text = {}

PROGRESS_UPDATE_INTERVAL = 3
SPEED_HISTORY_LIMIT = 12


def trim_text(text: str, limit: int = 40) -> str:
    text = str(text or "Unknown File").strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def humanbytes(size):
    if size is None:
        return "0B"
    size = float(size)
    if size <= 0:
        return "0B"
    power = 1024
    n = 0
    labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{size:.2f}{labels[n]}"


def TimeFormatter(milliseconds: int) -> str:
    milliseconds = int(milliseconds or 0)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d{hours:02d}h{minutes:02d}m"
    if hours:
        return f"{hours}h{minutes:02d}m{seconds:02d}s"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def format_speed(speed_bytes):
    if speed_bytes is None or speed_bytes == 0:
        return "0B/s"
    return f"{humanbytes(speed_bytes)}/s"


def build_progress_bar(percentage, length=12):
    """Build fancy progress bar: ■□□□□□□□□□□□"""
    percentage = max(0, min(100, percentage))
    filled = int(length * percentage / 100)
    empty = length - filled
    bar = "■" * filled + "□" * empty
    return f"[{bar}]"


def get_system_stats():
    """Get system stats for bottom section"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot = time.time() - psutil.boot_time()
        uptime_str = TimeFormatter(int(boot * 1000))
        
        # Count active tasks via active_tasks from advanced_progress
        tasks = 0
        try:
            from plugins.advanced_progress import get_task_count
            tasks = get_task_count()
        except:
            pass
        
        return {
            'cpu': cpu,
            'ram': mem.percent,
            'ram_used': mem.used,
            'ram_total': mem.total,
            'disk_free': disk.free,
            'disk_total': disk.total,
            'disk_percent': disk.percent,
            'uptime': uptime_str,
            'tasks': tasks
        }
    except:
        return {'cpu': 0, 'ram': 0, 'ram_used': 0, 'ram_total': 1,
                'disk_free': 0, 'disk_total': 1, 'disk_percent': 0,
                'uptime': '0s', 'tasks': 0}


def cleanup_progress_state(msg_id):
    """Clean up progress state"""
    speed_history.pop(msg_id, None)
    last_edit_time.pop(msg_id, None)
    last_progress_text.pop(msg_id, None)


async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start,
    file_name="",
    is_download=False
):
    """ADVANCED PROGRESS UI - BIMBO BOT STYLE
    ┃ [■□□□□□□□□□□□] 7.01%
    ┠ Processed: 56.00MB of 798.59MB
    ┠ Status: Upload | ETA: 17m16s
    ┠ Speed: 733.28KB/s | Elapsed: 5m31s
    ┠ Engine: PyroMulti v2.2.11
    ┠ Mode: #Leech | #Aria2
    ┠ User: 𝔅𝔦𝔪𝔟𝔬 | ID: 5071005351
    ┖ /cancel_62611b1eb50035d6
    """
    if not message or total == 0:
        return
    
    try:
        msg_id = message.id
    except:
        return
    
    now = time.time()
    diff = max(now - start, 0.001)
    last_time = last_edit_time.get(msg_id, 0)
    
    # Rate limiting
    if (now - last_time < PROGRESS_UPDATE_INTERVAL) and current not in (0, total) and current != total:
        return
    
    # Percentage
    percentage = (current * 100) / total
    percentage = min(max(percentage, 0), 100)
    
    # Speed smoothing
    instant_speed = current / diff if diff > 0 else 0
    history = speed_history.setdefault(msg_id, [])
    history.append(instant_speed)
    if len(history) > SPEED_HISTORY_LIMIT:
        history.pop(0)
    avg_speed = sum(history) / len(history) if history else instant_speed
    
    # ETA
    remaining_bytes = max(total - current, 0)
    eta = (remaining_bytes / avg_speed) if avg_speed > 0 else 0
    
    # Format all values
    progress_bar = build_progress_bar(percentage)
    elapsed_str = TimeFormatter(int(diff * 1000))
    eta_str = TimeFormatter(int(eta * 1000)) if eta > 0 else "-"
    transferred = humanbytes(current)
    total_str = humanbytes(total)
    speed_str = format_speed(avg_speed)
    
    # Display name
    display_name = trim_text(file_name or ud_type or "File", 40)
    
    # Mode & Engine
    mode = "Download" if is_download else "Upload"
    engine = "PyroMulti v2.2.11"
    
    # System stats
    stats = get_system_stats()
    
    # Status emoji
    if percentage >= 100:
        status_emoji = "✅"
    elif percentage >= 75:
        status_emoji = "📤" if not is_download else "📥"
    elif percentage >= 50:
        status_emoji = "🔄"
    elif percentage >= 25:
        status_emoji = "⏳"
    else:
        status_emoji = "⬇️" if is_download else "⬆️"
    
    # Status text
    if is_download:
        status_text = f"{status_emoji} Download"
    else:
        status_text = f"{status_emoji} Upload"
    
    # Build THE EXACT UI user wants
    progress_text = (
        f"***{display_name}***\n"
        f"┃ {progress_bar} {percentage:.2f}%\n"
        f"┠ **Processed:** {transferred} of {total_str}\n"
        f"┠ **Status:** {status_text} | **ETA:** {eta_str}\n"
        f"┠ **Speed:** {speed_str} | **Elapsed:** {elapsed_str}\n"
        f"┠ **Engine:** {engine}\n"
        f"┠ **Mode:** #{mode}\n"
        f"┠ **User:** `𝔅𝔦𝔪𝔟𝔬` | **ID:** `{message.chat.id if hasattr(message, 'chat') else 0}`\n"
        f"┖ /cancel\n\n"
        f"⌬ ***Bot Stats***\n"
        f"┠ **Tasks:** {stats['tasks']}\n"
        f"┠ **CPU:** {stats['cpu']:.1f}% | **F:** {humanbytes(stats['disk_free'])} [{100-stats['disk_percent']:.1f}%]\n"
        f"┠ **RAM:** {stats['ram']:.1f}% | **UPTIME:** {stats['uptime']}\n"
        f"┖ **DL:** {speed_str if is_download else '0B/s'} | **UL:** {speed_str if not is_download else '0B/s'}"
    )
    
    # Avoid duplicate edits
    if last_progress_text.get(msg_id) == progress_text and current != total:
        return
    
    try:
        await message.edit(text=progress_text)
        last_edit_time[msg_id] = now
        last_progress_text[msg_id] = progress_text
        
        if current == total:
            # Completion message
            complete_text = (
                f"✅ ***{display_name}***\n"
                f"┃ {build_progress_bar(100)} 100.0%\n"
                f"┠ **Processed:** {total_str} of {total_str}\n"
                f"┠ **Speed:** {speed_str} | **Elapsed:** {elapsed_str}\n"
                f"┖ **✅ Complete!**"
            )
            try:
                await message.edit(text=complete_text)
            except:
                pass
            cleanup_progress_state(msg_id)
            
    except Exception as e:
        error_text = str(e).upper()
        if "MESSAGE_NOT_MODIFIED" not in error_text:
            logger.error(f"Progress edit error: {e}")
        if current == total:
            cleanup_progress_state(msg_id)


def cleanup_all_progress():
    speed_history.clear()
    last_edit_time.clear()
    last_progress_text.clear()
