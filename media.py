
# Author:       leh-x
# AI:           Claude
# Date:         Aug 05 2026
# Purpose:      Manages URL classes to classify, extract, download, and analyse
# Last Edited:  Aug 05 2026

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
        if YouTubeURL.matches(raw_url):
            return YouTubeURL(raw_url, filename, source)
        
        elif GiphyURL.matches(raw_url):
            return GiphyURL(raw_url, filename, source)
        
        elif TenorURL.matches(raw_url):
            return TenorURL(raw_url, filename, source)
        
        else:
            # Regular file download for non-YouTube/Giphy content
            # Check file type from filename or URL
            file_ext = ''
            if filename is not None and '.' in filename:
                file_ext = filename.lower().split('.')[-1]

            url_lower = raw_url.lower()
            is_gif = file_ext == 'gif' or '.gif' in url_lower or 'gifv' in url_lower
            is_video = file_ext in ['mp4', 'webm', 'mov'] or any(ext in url_lower for ext in ['.mp4', '.webm', '.mov'])

            if is_gif or is_video:
                return cls(raw_url, filename, source)

        return None

    @classmethod
    def classify_message(cls, msg):
        urls = []

            # Also check for direct Tenor URLs in message content
        if 'tenor.com' in msg.lower() or 'media.tenor.com' in msg.lower():
            # Extract Tenor URLs from message
            url_pattern = r'https?://(?:tenor\.com/view/|media\.tenor\.com/)[^\s]+'
            found_urls = re.findall(url_pattern, msg)

            for url in found_urls:
                urls.append(
                    cls.classify(
                    url, 
                    url.split('/')[-1], 
                    'tenor_link')
                )

        
        # Check for YouTube URLs in message content
        if 'youtube.com' in msg.lower() or 'youtu.be' in msg.lower():
            # Extract Youtube URLs from message
            url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'
            found_urls = re.findall(url_pattern, msg)

            for url in found_urls:
                urls.append(
                    cls.classify(
                    url, 
                    'youtube_video', 
                    'youtube')
                )
        
        # Check for Giphy URLs in message content
        if 'giphy.com' in msg.lower():
            # Extract URLs from message
            url_pattern = r'https?://(?:media\.)?giphy\.com/[^\s]+'
            found_urls = re.findall(url_pattern, msg)
            for url in found_urls:
                urls.append(
                    cls.classify(
                    url, 
                    'giphy.gif', 
                    'giphy')
                )

        return urls
        
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

        try:
            # Handle both BytesIO and file path
            if isinstance(file_bytes, str):
                # It's a file path
                temp_path = file_bytes
            else:
                # It's BytesIO, save to temp file
                temp_path = '/tmp/temp_video.mp4'
                with open(temp_path, 'wb') as f:
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

            # Clean up temp file
            try:
                os.remove(temp_path)
                os.rmdir(os.path.dirname(temp_path))
            except:
                pass
            
            return False, None, None
            
        except Exception as e:
            print(f"Error analyzing video: {e}")
            return False, None, None

    def get_url(self): return self.media_url
    def get_filename(self): return self.filename
    def get_source(self): return self.source

class YouTubeURL(MediaURL):
    @staticmethod
    def matches(url):
        return bool(re.search(r'youtu\.be/|youtube\.com/watch\?v=', url))

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


class GiphyURL(MediaURL):
    @staticmethod
    def matches(url):
        return 'giphy.com' in url.lower()

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
    def matches(url):
        return 'tenor.com' in url.lower()
    # no overrides needed — base extract()/download() are fine as-is


# def is_youtube_url(url):
#     """Check if URL is a YouTube video"""
#     youtube_patterns = [
#         r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=',
#         r'(?:https?://)?(?:www\.)?youtu\.be/',
#         r'(?:https?://)?(?:www\.)?youtube\.com/shorts/',
#     ]
#     return any(re.search(pattern, url) for pattern in youtube_patterns)

# def is_giphy_url(url):
#     """Check if URL is a Giphy link"""
#     giphy_patterns = [
#         r'giphy\.com/gifs/',
#         r'giphy\.com/embed/',
#         r'media\.giphy\.com/',
#         r'i\.giphy\.com/',
#     ]
#     return any(re.search(pattern, url.lower()) for pattern in giphy_patterns)