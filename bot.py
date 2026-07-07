import os
import logging
import threading
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
        pass  # health check logs mat dikhao

def run_health_server():
    """Koyeb TCP health check ke liye ek chhota HTTP server"""
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    logger.info(f"✅ Health check server running on port {HEALTH_PORT}")
    server.serve_forever()

if __name__ == "__main__":
    # create download directory, if not exist
    if not os.path.isdir(Config.BIMBO_DOWNLOAD_LOCATION):
        os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION)
    
    # Koyeb health check ke liye thread mein HTTP server start karo
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    plugins = dict(root="plugins")
    
    BIMBO_CLIENT = BimboBot(
        name="BIMBO_BOT",
        bot_token=Config.BIMBO_BOT_TOKEN,
        api_id=Config.BIMBO_API_ID,
        api_hash=Config.BIMBO_API_HASH,
        plugins=plugins
    )
    
    BIMBO_CLIENT.run()
