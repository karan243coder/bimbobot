import os
import logging
import threading
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import Config
from pyrogram import Client as BimboBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Koyeb health check ke liye simple HTTP server
HEALTH_PORT = int(os.environ.get("PORT", 8080))

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    logger.info(f"✅ Health check server running on port {HEALTH_PORT}")
    server.serve_forever()


def start_aria2_daemon():
    """Start Aria2 daemon for RPC"""
    try:
        # Check if aria2 is installed
        subprocess.run(["aria2c", "--version"], capture_output=True, check=True)
        
        # Create config dir
        os.makedirs("/app/.aria2", exist_ok=True)
        
        # Kill any existing aria2 process
        subprocess.run(["pkill", "-f", "aria2c"], capture_output=True)
        time.sleep(1)
        
        # Start aria2 daemon
        cmd = [
            "aria2c", "--daemon",
            "--enable-rpc", "--rpc-listen-all=true",
            "--rpc-allow-origin-all", "--rpc-listen-port=6800",
            "--max-concurrent-downloads=10",
            "--max-connection-per-server=16",
            "--split=16", "--min-split-size=10M",
            "--continue=true",
            "--max-overall-download-limit=0",
            "--max-download-limit=0",
            "--file-allocation=none",
            "--dir=/app/downloads",
            "--log=/app/.aria2/aria2.log",
            "--log-level=error"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Aria2 daemon started successfully on port 6800")
            return True
        else:
            logger.warning(f"⚠️ Aria2 daemon start returned: {result.stderr}")
            return False
            
    except FileNotFoundError:
        logger.warning("⚠️ Aria2 not installed. Install with: apt-get install aria2")
        return False
    except Exception as e:
        logger.error(f"❌ Aria2 startup error: {e}")
        return False


if __name__ == "__main__":
    # create download directory
    if not os.path.isdir(Config.BIMBO_DOWNLOAD_LOCATION):
        os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION)
    
    # Start health check server
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Start Aria2 daemon in background
    aria2_thread = threading.Thread(target=start_aria2_daemon, daemon=True)
    aria2_thread.start()
    time.sleep(2)  # Wait for aria2 to start
    
    plugins = dict(root="plugins")
    
    BIMBO_CLIENT = BimboBot(
        name="BIMBO_BOT",
        bot_token=Config.BIMBO_BOT_TOKEN,
        api_id=Config.BIMBO_API_ID,
        api_hash=Config.BIMBO_API_HASH,
        plugins=plugins
    )
    
    BIMBO_CLIENT.run()
