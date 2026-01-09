import logging
import asyncio
import yt_dlp
import os
import time
from typing import Optional, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class InstagramDownloadThrottler:
    """Throttle Instagram downloads per user to prevent abuse and rate limiting"""

    def __init__(self, min_interval: float = 5.0, max_concurrent: int = 2):
        """
        Args:
            min_interval: Minimum seconds between downloads per user
            max_concurrent: Maximum concurrent downloads globally
        """
        self.min_interval = min_interval
        self.max_concurrent = max_concurrent
        self.user_last_download: Dict[int, float] = {}
        self.active_downloads = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily create the lock when first needed"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def can_download(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can download now"""
        async with self._get_lock():
            current_time = time.time()

            # Check concurrent downloads
            if self.active_downloads >= self.max_concurrent:
                return False, "Too many active downloads. Please wait a moment."

            # Check user cooldown
            if user_id in self.user_last_download:
                time_since_last = current_time - self.user_last_download[user_id]
                if time_since_last < self.min_interval:
                    wait_time = self.min_interval - time_since_last
                    return False, f"Please wait {int(wait_time)} seconds before downloading another video."

            return True, ""

    async def start_download(self, user_id: int):
        """Mark download as started"""
        async with self._get_lock():
            self.active_downloads += 1
            self.user_last_download[user_id] = time.time()
            logger.info(f"Started download for user {user_id}. Active downloads: {self.active_downloads}")

    async def finish_download(self, user_id: int):
        """Mark download as finished"""
        async with self._get_lock():
            self.active_downloads = max(0, self.active_downloads - 1)
            logger.info(f"Finished download for user {user_id}. Active downloads: {self.active_downloads}")


class InstagramDownloader:
    """Download Instagram videos and reels"""

    def __init__(self, download_dir: str = "downloads", throttle_interval: float = 5.0):
        """
        Args:
            download_dir: Directory to save downloaded videos
            throttle_interval: Minimum seconds between downloads per user
        """
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.throttler = InstagramDownloadThrottler(min_interval=throttle_interval)

    def is_instagram_url(self, text: str) -> bool:
        """
        Check if text contains Instagram URL.
        Using startswith for simplicity as requested.
        """
        if not text:
            return False

        text = text.strip().lower()

        # Check for various Instagram URL patterns
        instagram_patterns = [
            'https://www.instagram.com/',
            'http://www.instagram.com/',
            'https://instagram.com/',
            'http://instagram.com/',
            'www.instagram.com/',
            'instagram.com/',
        ]

        for pattern in instagram_patterns:
            if text.startswith(pattern):
                return True

        return False

    async def download_video(self, url: str, user_id: int) -> Optional[Dict]:
        """
        Download Instagram video/reel with throttling.

        Args:
            url: Instagram post/reel URL
            user_id: Telegram user ID (for throttling)

        Returns:
            Dict with 'file_path', 'title', 'description' or None if failed
        """
        # Check throttling
        can_download, reason = await self.throttler.can_download(user_id)
        if not can_download:
            logger.warning(f"Download throttled for user {user_id}: {reason}")
            return {"error": reason}

        try:
            # Mark download as started
            await self.throttler.start_download(user_id)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = os.path.join(self.download_dir, f"instagram_{timestamp}_%(id)s.%(ext)s")

            # yt-dlp options
            ydl_opts = {
                'format': 'best',  # Best quality video
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                # Don't download thumbnails, subtitles, etc
                'writethumbnail': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }

            # Download in thread pool (yt-dlp is blocking)
            logger.info(f"Starting Instagram download for user {user_id}: {url}")
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._download_sync,
                url,
                ydl_opts
            )

            logger.info(f"Instagram download completed for user {user_id}: {result.get('file_path')}")
            return result

        except Exception as e:
            logger.error(f"Error downloading Instagram video: {e}")
            return {"error": f"Failed to download video: {str(e)}"}

        finally:
            # Mark download as finished
            await self.throttler.finish_download(user_id)

    def _download_sync(self, url: str, ydl_opts: dict) -> Dict:
        """Synchronous download function to run in thread pool"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=True)

                if info is None:
                    return {"error": "Could not extract video information"}

                # Get the downloaded file path
                if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                    file_path = info['requested_downloads'][0]['filepath']
                else:
                    # Construct file path from template
                    file_path = ydl.prepare_filename(info)

                # Extract metadata
                title = info.get('title', 'Instagram Video')
                description = info.get('description', '')
                uploader = info.get('uploader', '')

                # Check if file exists
                if not os.path.exists(file_path):
                    return {"error": f"Downloaded file not found: {file_path}"}

                # Check file size (Telegram limit is 50MB for bot API)
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > 50:
                    # Clean up the file
                    os.remove(file_path)
                    return {"error": f"Video is too large ({file_size_mb:.1f}MB). Telegram limit is 50MB."}

                return {
                    'file_path': file_path,
                    'title': title,
                    'description': description,
                    'uploader': uploader,
                    'file_size_mb': file_size_mb
                }

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download error: {e}")
            error_msg = str(e)
            if "Private" in error_msg or "login" in error_msg.lower():
                return {"error": "This Instagram post is private or requires login."}
            elif "not found" in error_msg.lower() or "404" in error_msg:
                return {"error": "Instagram post not found. It may have been deleted."}
            else:
                return {"error": f"Download failed: {error_msg}"}

        except Exception as e:
            logger.error(f"Unexpected error in _download_sync: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    def cleanup_file(self, file_path: str):
        """Clean up downloaded file"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")

    def cleanup_old_files(self, max_age_hours: int = 1):
        """Clean up old downloaded files"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_hours * 3600:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
