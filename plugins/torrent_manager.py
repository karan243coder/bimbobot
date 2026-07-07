import os
import asyncio
import logging
from typing import Optional, Dict
import libtorrent as lt

logger = logging.getLogger(__name__)

class TorrentManager:
    def __init__(self):
        self.session = None
        self.active_torrents = {}
        self._init_session()
    
    def _init_session(self):
        """Initialize libtorrent session"""
        try:
            settings = {
                'user_agent': 'BIMBO Bot',
                'listen_interfaces': '0.0.0.0:6881',
                'download_rate_limit': 0,  # Unlimited
                'upload_rate_limit': 0,    # Unlimited
                'alert_mask': lt.alert.category_t.status_notification | 
                             lt.alert.category_t.error_notification |
                             lt.alert.category_t.storage_notification,
                'enable_dht': True,
                'enable_lsd': True,
                'enable_natpmp': True,
                'enable_upnp': True,
            }
            
            self.session = lt.session(settings)
            logger.info("Torrent session initialized")
        except Exception as e:
            logger.error(f"Failed to initialize torrent session: {e}")
    
    async def add_torrent(self, magnet_uri: str = None, torrent_file: str = None,
                         save_path: str = './downloads', progress_callback=None) -> Optional[str]:
        """Add torrent from magnet URI or .torrent file"""
        
        if not self.session:
            logger.error("Torrent session not initialized")
            return None
        
        try:
            params = {
                'save_path': save_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'flags': lt.add_torrent_params_flags_t.flag_paused
            }
            
            if magnet_uri:
                params['url'] = magnet_uri
                logger.info(f"Adding magnet: {magnet_uri[:50]}...")
            elif torrent_file:
                if not os.path.exists(torrent_file):
                    logger.error(f"Torrent file not found: {torrent_file}")
                    return None
                
                with open(torrent_file, 'rb') as f:
                    torrent_data = lt.bdecode(f.read())
                
                info = lt.torrent_info(torrent_data)
                params['ti'] = info
                logger.info(f"Adding torrent file: {info.name()}")
            else:
                logger.error("No magnet URI or torrent file provided")
                return None
            
            # Add torrent to session
            handle = self.session.add_torrent(params)
            
            # Get torrent info
            info_hash = str(handle.info_hash())
            
            # Store in active torrents
            self.active_torrents[info_hash] = {
                'handle': handle,
                'progress_callback': progress_callback,
                'save_path': save_path
            }
            
            # Resume torrent
            handle.resume()
            
            logger.info(f"Torrent added: {info_hash}")
            
            # Start monitoring in background
            asyncio.create_task(self._monitor_torrent(info_hash))
            
            return info_hash
        
        except Exception as e:
            logger.error(f"Add torrent error: {e}")
            return None
    
    async def _monitor_torrent(self, info_hash: str):
        """Monitor torrent progress"""
        
        if info_hash not in self.active_torrents:
            return
        
        torrent_data = self.active_torrents[info_hash]
        handle = torrent_data['handle']
        callback = torrent_data.get('progress_callback')
        
        try:
            while info_hash in self.active_torrents:
                status = handle.status()
                
                # Call progress callback
                if callback:
                    progress_data = {
                        'info_hash': info_hash,
                        'name': status.name if status.has_metadata else 'Fetching metadata...',
                        'progress': status.progress * 100,
                        'download_rate': status.download_rate,
                        'upload_rate': status.upload_rate,
                        'total_size': status.total_wanted,
                        'downloaded': status.total_wanted_done,
                        'uploaded': status.total_payload_upload,
                        'num_peers': status.num_peers,
                        'num_seeds': status.num_seeds,
                        'state': self._get_state_name(status.state),
                        'is_finished': status.is_seeding or (status.progress == 1.0 and status.has_metadata)
                    }
                    
                    await callback(progress_data)
                
                # Check if finished
                if status.is_seeding or (status.progress == 1.0 and status.has_metadata):
                    logger.info(f"Torrent completed: {info_hash}")
                    
                    # Get downloaded files
                    if status.has_metadata:
                        torrent_info = handle.torrent_file()
                        files = []
                        for i in range(torrent_info.num_files()):
                            file_path = os.path.join(
                                torrent_data['save_path'],
                                torrent_info.file_path(i)
                            )
                            files.append({
                                'path': file_path,
                                'size': torrent_info.file_size(i)
                            })
                        
                        # Call callback with completion
                        if callback:
                            await callback({
                                'info_hash': info_hash,
                                'name': status.name,
                                'progress': 100,
                                'is_finished': True,
                                'files': files
                            })
                    
                    break
                
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Monitor torrent error: {e}")
    
    def _get_state_name(self, state) -> str:
        """Get state name"""
        states = {
            lt.torrent_status.checking_files: 'Checking',
            lt.torrent_status.downloading_metadata: 'Fetching metadata',
            lt.torrent_status.downloading: 'Downloading',
            lt.torrent_status.finished: 'Finished',
            lt.torrent_status.seeding: 'Seeding',
            lt.torrent_status.allocating: 'Allocating',
            lt.torrent_status.checking_resume_data: 'Checking resume data'
        }
        return states.get(state, 'Unknown')
    
    async def pause_torrent(self, info_hash: str) -> bool:
        """Pause torrent"""
        if info_hash in self.active_torrents:
            try:
                handle = self.active_torrents[info_hash]['handle']
                handle.pause()
                logger.info(f"Torrent paused: {info_hash}")
                return True
            except Exception as e:
                logger.error(f"Pause torrent error: {e}")
        return False
    
    async def resume_torrent(self, info_hash: str) -> bool:
        """Resume torrent"""
        if info_hash in self.active_torrents:
            try:
                handle = self.active_torrents[info_hash]['handle']
                handle.resume()
                logger.info(f"Torrent resumed: {info_hash}")
                return True
            except Exception as e:
                logger.error(f"Resume torrent error: {e}")
        return False
    
    async def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """Remove torrent"""
        if info_hash in self.active_torrents:
            try:
                handle = self.active_torrents[info_hash]['handle']
                
                # Remove from session
                self.session.remove_torrent(handle, 
                    lt.session.delete_files if delete_files else 0)
                
                # Remove from active torrents
                del self.active_torrents[info_hash]
                
                logger.info(f"Torrent removed: {info_hash}")
                return True
            except Exception as e:
                logger.error(f"Remove torrent error: {e}")
        return False
    
    async def get_torrent_status(self, info_hash: str) -> Optional[Dict]:
        """Get torrent status"""
        if info_hash not in self.active_torrents:
            return None
        
        try:
            handle = self.active_torrents[info_hash]['handle']
            status = handle.status()
            
            return {
                'info_hash': info_hash,
                'name': status.name if status.has_metadata else 'Fetching metadata...',
                'progress': status.progress * 100,
                'download_rate': status.download_rate,
                'upload_rate': status.upload_rate,
                'total_size': status.total_wanted,
                'downloaded': status.total_wanted_done,
                'uploaded': status.total_payload_upload,
                'num_peers': status.num_peers,
                'num_seeds': status.num_seeds,
                'state': self._get_state_name(status.state),
                'is_finished': status.is_seeding or (status.progress == 1.0 and status.has_metadata)
            }
        except Exception as e:
            logger.error(f"Get torrent status error: {e}")
            return None
    
    async def get_all_torrents(self) -> Dict:
        """Get all active torrents"""
        torrents = {}
        
        for info_hash in self.active_torrents:
            status = await self.get_torrent_status(info_hash)
            if status:
                torrents[info_hash] = status
        
        return torrents
    
    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        if not self.session:
            return {}
        
        try:
            stats = self.session.status()
            
            return {
                'download_rate': stats.download_rate,
                'upload_rate': stats.upload_rate,
                'total_download': stats.total_download,
                'total_upload': stats.total_upload,
                'num_peers': stats.num_peers,
                'dht_nodes': stats.dht_nodes,
                'active_torrents': len(self.active_torrents)
            }
        except Exception as e:
            logger.error(f"Get session stats error: {e}")
            return {}


# Global instance
torrent_manager = TorrentManager()

# Convenience functions
async def add_torrent(magnet_uri: str = None, torrent_file: str = None, **kwargs) -> Optional[str]:
    """Add torrent"""
    return await torrent_manager.add_torrent(magnet_uri, torrent_file, **kwargs)

async def pause_torrent(info_hash: str) -> bool:
    """Pause torrent"""
    return await torrent_manager.pause_torrent(info_hash)

async def resume_torrent(info_hash: str) -> bool:
    """Resume torrent"""
    return await torrent_manager.resume_torrent(info_hash)

async def remove_torrent(info_hash: str, **kwargs) -> bool:
    """Remove torrent"""
    return await torrent_manager.remove_torrent(info_hash, **kwargs)

async def get_torrent_status(info_hash: str) -> Optional[Dict]:
    """Get torrent status"""
    return await torrent_manager.get_torrent_status(info_hash)

async def get_all_torrents() -> Dict:
    """Get all torrents"""
    return await torrent_manager.get_all_torrents()

def get_torrent_stats() -> Dict:
    """Get torrent stats"""
    return torrent_manager.get_session_stats()
