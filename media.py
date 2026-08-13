
# Author:       leh-x
# AI:           Claude
# Date:         Aug 05 2026
# Purpose:      Manages URL classes to classify, extract, download, and analyse
# Last Edited:  Aug 06 2026

import tempfile
import requests
import asyncio
import numpy as np
import re
import os
import io
import cv2

from config import PhotosensitiveConfig

class MediaURL:

    def __init__(self, raw_url, filename = None, source = None):
        self.raw_url = raw_url
        self.filename = filename
        self.media_url = raw_url                    # default: no extracting means it's the same thing
        self.source = source
        self.raw_bytes = None
        self.result = None

    @classmethod
    def classify(cls, raw_url, filename = None, source = None):
        if YouTubeURL._match(raw_url):
            return YouTubeURL(raw_url, filename, source)
        
        elif GiphyURL._match(raw_url):
            return GiphyURL(raw_url, filename, source)
        
        elif TenorURL._match(raw_url):
            return TenorURL(raw_url, filename, source)
        
        elif MediaURL._match(raw_url, filename):
            return MediaURL(raw_url, filename, source)

        return None

    @classmethod
    def classify_message(cls, msg):
        urls = []

        urls.extend(YouTubeURL._matches(msg) or [])
        urls.extend(GiphyURL._matches(msg) or [])
        urls.extend(TenorURL._matches(msg) or [])
        urls.extend(MediaURL._matches(msg) or [])
                
        return urls
    
    @staticmethod
    def _match(url, filename = None):
        text = f"{filename or ''} {url}".lower()
        return bool(re.search(r'\.(gif|gifv|mp4|webm|mov)', text))

    @staticmethod
    def _matches(str):
        found_urls = re.findall(r'https?://\S+', str)

        urls = []
        for u in found_urls:

            if any(sub._match(u) for sub in MediaURL.__subclasses__()):
                continue

            if MediaURL._match(u):
                urls.append(MediaURL(u, u.split('/')[-1], 'plain_link'))

        return urls or None
            
    async def download(self):
        """Download a file from URL and return as bytes"""
        try:
            response = await asyncio.to_thread(requests.get, self.media_url, timeout = 10)
            response.raise_for_status()
            self.raw_bytes = io.BytesIO(response.content)

        except Exception as e:
            print(f"Error downloading file: {e}")
            self.raw_bytes = None

        return self

    def analyze(self, file_bytes = None):
        """
        Analyze a video/GIF for photosensitive triggers
        Returns: (is_dangerous, reason, details)
        """
        if file_bytes is None:
            file_bytes = self.raw_bytes

        owns_temp_file = not isinstance(file_bytes, str)
        temp_path = None

        try:
            # Handle both BytesIO and file path
            if isinstance(file_bytes, str):
                # It's a file path
                temp_path = file_bytes
            else:
                # It's BytesIO, save to temp file
                fd, temp_path = tempfile.mkstemp(suffix = '.mp4', dir = '/tmp')
                with os.fdopen(fd, 'wb') as f:
                    f.write(file_bytes.read())
            
            cap = cv2.VideoCapture(temp_path)
            
            if not cap.isOpened():
                return False, None, None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 30  # Default if FPS cannot be determined
            
            frame_count = 0
            prev_frame = None
            flashes = []
            red_flashes = []
            
            config = PhotosensitiveConfig(fps)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Sample frames for performance
                if frame_count % config.SAMPLE_RATE != 0:
                    continue
                
                # Convert to grayscale for brightness analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate brightness difference
                    diff = cv2.absdiff(gray, prev_frame)
                    mean_diff = np.mean(diff)
                    
                    # Calculate area of significant change
                    significant_change = np.sum(diff > config.FLASH_THRESHOLD) / diff.size
                    
                    # Check for general flashing
                    if mean_diff > config.FLASH_THRESHOLD and significant_change > config.MIN_FLASH_AREA:
                        flashes.append(frame_count)
                    
                    # Check for red flashing (particularly dangerous)
                    red_channel = frame[:, :, 2]  # BGR format, so index 2 is red
                    prev_red = prev_frame_color[:, :, 2] if 'prev_frame_color' in locals() else red_channel
                    red_diff = cv2.absdiff(red_channel, prev_red)
                    red_mean_diff = np.mean(red_diff)
                    
                    if red_mean_diff > config.RED_FLASH_THRESHOLD:
                        red_flashes.append(frame_count)
                
                prev_frame = gray.copy()
                prev_frame_color = frame.copy()
            
            cap.release()
            
            # Calculate flash frequency
            if len(flashes) > 1:
                # Convert frame numbers to time
                flash_times = [f / fps for f in flashes]
                
                # Check for flashes within 1-second windows
                for i in range(len(flash_times)):
                    flashes_in_window = sum(1 for t in flash_times if flash_times[i] <= t < flash_times[i] + 1)
                    
                    if flashes_in_window > config.FLASH_FREQUENCY_LIMIT:
                        return True, f"Dangerous flash frequency detected ({flashes_in_window} flashes/second)", {
                            'flashes': len(flashes),
                            'red_flashes': len(red_flashes),
                            'fps': fps
                        }
            
            # Check for red flashing
            if len(red_flashes) > config.FLASH_FREQUENCY_LIMIT:
                return True, "Dangerous red flashing detected", {
                    'red_flashes': len(red_flashes),
                    'fps': fps
                }
            
            return False, None, None

          
        except Exception as e:
            print(f"Error analyzing video: {e}")
            return False, None, None

        finally:
            if owns_temp_file and temp_path:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass

    def cleanup(self):
        return True

    def get_url(self): return self.media_url
    def get_filename(self): return self.filename
    def get_source(self): return self.source

class YouTubeURL(MediaURL):
    @staticmethod
    def _match(url):
        return bool(re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+', url))

    @staticmethod
    def _matches(str):

        # Check for YouTube URLs in message content
        if 'youtube.com' not in str.lower() and 'youtu.be' not in str.lower():
            return None
        
        # Extract Youtube URLs from message
        url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'
        found_urls = re.findall(url_pattern, str)

        urls = [
            MediaURL.classify(u, 'youtube-video', 'youtube')
            for u in found_urls
        ]

        return urls or None

    async def download(self):
        """
        Download a YouTube video for analysis
        Only downloads first max_duration seconds to save time/bandwidth
        Returns: path to downloaded video file or None
        """
        max_duration = 30
        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, 'video.mp4')
            
            # Use yt-dlp to download (first N seconds only for efficiency)
            cmd = [
                'yt-dlp',
                '--format', 'worst',  # Get lowest quality to save bandwidth
                '--download-sections', f'*0-{max_duration}',  # Only first N seconds
                '--output', output_path,
                '--no-playlist',
                '--quiet',
                self.media_url
            ]
            
            # Run yt-dlp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout = 60)
            
            if process.returncode == 0 and os.path.exists(output_path):
                self.raw_bytes = output_path
            else:
                print(f"yt-dlp error: {stderr.decode()}")
                self.raw_bytes = None
                
        except asyncio.TimeoutError:
            print("YouTube download timed out")
            self.raw_bytes = None

        except Exception as e:
            print(f"Error downloading YouTube video: {e}")
            self.raw_bytes = None

        return self

    def cleanup(self):
        if isinstance(self.raw_bytes, str) and os.path.exists(self.raw_bytes):
            try:
                os.remove(self.raw_bytes)
                os.rmdir(os.path.dirname(self.raw_bytes))
                
                return True

            except:
                return False

class GiphyURL(MediaURL):
    @staticmethod
    def _match(url):
        return 'giphy.com' in url.lower()

    @staticmethod
    def _matches(str):

        # Check for Giphy URLs in message content
        if 'giphy.com' not in str.lower():
            return None
        
        # Extract URLs from message
        url_pattern = r'https?://(?:media\.)?giphy\.com/[^\s]+'
        found_urls = re.findall(url_pattern, str)

        urls = [
            MediaURL.classify(u, 'giphy-gif', 'giphy')
            for u in found_urls
        ]

        return urls or None

    async def download(self):
        """
        Extract the direct media URL from a Giphy page URL
        Example: https://giphy.com/gifs/xxx -> https://media.giphy.com/media/xxx/giphy.gif
        """
        try:
            # Extract GIF ID from various Giphy URL formats
            # Format: https://giphy.com/gifs/name-ID or https://giphy.com/gifs/ID
            match = re.search(r'gifs/(?:[\w-]+-)?([a-zA-Z0-9]+)/?', self.raw_url)
            if match:
                gif_id = match.group(1)
                # Try the direct media URL
                self.media_url = f'https://media.giphy.com/media/{gif_id}/giphy.gif'
            
            # Already a direct media URL
            elif 'media.giphy.com' in self.raw_url or 'i.giphy.com' in self.raw_url:
                self.media_url = self.raw_url

            else:
                self.media_url = None

            if self.media_url == None:
                print(f"Could not extract media URL from Giphy: {self.raw_url}")
                return self
            
            await super().download()
            return self
        
        except Exception as e:
            print(f"Error extracting Giphy media URL: {e}")
            return self

class TenorURL(MediaURL):
    @staticmethod
    def _match(url):
        return 'tenor.com' in url.lower()

    @staticmethod
    def _matches(str):

        # Also check for direct Tenor URLs in message content
        if 'tenor.com' not in str.lower() and 'media.tenor.com' not in str.lower():
            return None
        
        # Extract Tenor URLs from message
        url_pattern = r'https?://(?:tenor\.com/view/|media\.tenor\.com/)[^\s]+'
        found_urls = re.findall(url_pattern, str)

        urls = [
            MediaURL.classify(u, u.split('/')[-1], 'tenor-link')
            for u in found_urls
        ]

        return urls or None

    # no overrides needed — base extract()/download() are fine as-is