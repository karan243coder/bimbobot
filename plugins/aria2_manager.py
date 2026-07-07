import xmlrpc.client
import os
import time
import asyncio
import logging
from config import Config

logger = logging.getLogger(__name__)

class Aria2Manager:
    def __init__(self):
        self.uri = "http://localhost:6800/jsonrpc"
        self.secret = getattr(Config, 'ARIA2_SECRET', '')
        self.server = None
        self.connected = False
        
    async def connect(self):
        """Connect to Aria2 RPC server"""
        try:
            self.server = xmlrpc.client.ServerProxy(self.uri, allow_none=True)
            # Test connection
            self.server.aria2.getVersion(self.secret)
            self.connected = True
            logger.info("Aria2 connected successfully")
            return True
        except Exception as e:
            logger.error(f"Aria2 connection failed: {e}")
            self.connected = False
            return False
    
    async def add_download(self, url, download_dir, filename=None, headers=None):
        """Add download to Aria2"""
        if not self.connected:
            if not await self.connect():
                return None
        
        try:
            options = {
                'dir': download_dir,
                'max-connection-per-server': '16',
                'split': '16',
                'min-split-size': '10M',
                'continue': 'true',
                'max-overall-download-limit': '0',
                'max-download-limit': '0',
                'file-allocation': 'none',
                'allow-overwrite': 'true',
                'auto-file-renaming': 'false'
            }
            
            if filename:
                options['out'] = filename
            
            if headers:
                options['header'] = headers
            
            # Add download
            gid = self.server.aria2.addUri(self.secret, [url], options)
            logger.info(f"Aria2 download added: {gid}")
            return gid
            
        except Exception as e:
            logger.error(f"Aria2 add download error: {e}")
            return None
    
    async def get_status(self, gid):
        """Get download status"""
        if not self.connected:
            return None
        
        try:
            status = self.server.aria2.tellStatus(
                self.secret, gid,
                ['gid', 'status', 'totalLength', 'completedLength', 
                 'downloadSpeed', 'uploadSpeed', 'connections', 
                 'dir', 'files', 'errorCode', 'errorMessage']
            )
            return status
        except Exception as e:
            logger.error(f"Aria2 get status error: {e}")
            return None
    
    async def pause_download(self, gid):
        """Pause download"""
        if not self.connected:
            return False
        
        try:
            self.server.aria2.pause(self.secret, gid)
            return True
        except Exception as e:
            logger.error(f"Aria2 pause error: {e}")
            return False
    
    async def resume_download(self, gid):
        """Resume download"""
        if not self.connected:
            return False
        
        try:
            self.server.aria2.unpause(self.secret, gid)
            return True
        except Exception as e:
            logger.error(f"Aria2 resume error: {e}")
            return False
    
    async def remove_download(self, gid, force=False):
        """Remove download"""
        if not self.connected:
            return False
        
        try:
            if force:
                self.server.aria2.forceRemove(self.secret, gid)
            else:
                self.server.aria2.remove(self.secret, gid)
            return True
        except Exception as e:
            logger.error(f"Aria2 remove error: {e}")
            return False
    
    async def get_all_downloads(self):
        """Get all active downloads"""
        if not self.connected:
            return []
        
        try:
            active = self.server.aria2.tellActive(self.secret)
            waiting = self.server.aria2.tellWaiting(self.secret, 0, 100)
            stopped = self.server.aria2.tellStopped(self.secret, 0, 100)
            
            return {
                'active': active,
                'waiting': waiting,
                'stopped': stopped
            }
        except Exception as e:
            logger.error(f"Aria2 get all error: {e}")
            return {'active': [], 'waiting': [], 'stopped': []}
    
    async def get_global_status(self):
        """Get global Aria2 status"""
        if not self.connected:
            return None
        
        try:
            status = self.server.aria2.getGlobalStat(self.secret)
            return status
        except Exception as e:
            logger.error(f"Aria2 global status error: {e}")
            return None
    
    def format_status(self, status):
        """Format status for display"""
        if not status:
            return "Unknown"
        
        status_map = {
            'active': '⬇️ Downloading',
            'paused': '⏸️ Paused',
            'waiting': '⏳ Waiting',
            'complete': '✅ Complete',
            'error': '❌ Error',
            'removed': '🗑️ Removed'
        }
        
        return status_map.get(status.get('status', ''), 'Unknown')

# Global instance
aria2_manager = Aria2Manager()

async def init_aria2():
    """Initialize Aria2"""
    return await aria2_manager.connect()

async def download_with_aria2(url, download_dir, filename=None, progress_callback=None):
    """Download file using Aria2 with progress"""
    gid = await aria2_manager.add_download(url, download_dir, filename)
    
    if not gid:
        return None
    
    try:
        while True:
            status = await aria2_manager.get_status(gid)
            
            if not status:
                await asyncio.sleep(1)
                continue
            
            current_status = status.get('status', '')
            
            # Call progress callback
            if progress_callback:
                total = int(status.get('totalLength', 0))
                completed = int(status.get('completedLength', 0))
                speed = int(status.get('downloadSpeed', 0))
                
                await progress_callback(
                    gid=gid,
                    total=total,
                    completed=completed,
                    speed=speed,
                    status=current_status
                )
            
            # Check if complete
            if current_status == 'complete':
                # Get file path
                files = status.get('files', [])
                if files:
                    file_path = files[0]['path']
                    return file_path
                break
            
            # Check if error
            if current_status == 'error':
                error_msg = status.get('errorMessage', 'Unknown error')
                logger.error(f"Aria2 download error: {error_msg}")
                return None
            
            # Check if removed
            if current_status == 'removed':
                return None
            
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"Aria2 download exception: {e}")
        await aria2_manager.remove_download(gid, force=True)
        return None

def is_aria2_available():
    """Check if Aria2 is available"""
    return aria2_manager.connected
