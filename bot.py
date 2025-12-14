import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import io
import asyncio
from PIL import Image
import numpy as np
import cv2
import requests

# Load environment variables from .env file
load_dotenv()

# Get bot token from environment variable
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    raise ValueError("No DISCORD_BOT_TOKEN found! Please set it in your .env file")

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration for photosensitive detection
class PhotosensitiveConfig:
    # Flash detection thresholds
    FLASH_THRESHOLD = 30  # Brightness change threshold (0-255 scale)
    FLASH_FREQUENCY_LIMIT = 3  # Max flashes per second (WCAG guideline)
    RED_FLASH_THRESHOLD = 20  # Threshold for dangerous red flashing
    
    # Analysis settings
    SAMPLE_RATE = 10  # Analyze every Nth frame for performance
    MIN_FLASH_AREA = 0.25  # Minimum screen area that must flash (25%)

async def download_file(url):
    """Download a file from URL and return as bytes"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def analyze_image_for_flashing(image_bytes):
    """
    Analyze a static image for high-contrast patterns that could be problematic
    Returns: (is_dangerous, reason)
    """
    try:
        img = Image.open(image_bytes)
        img_array = np.array(img.convert('RGB'))
        
        # Check for extremely high contrast patterns
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        contrast = gray.std()
        
        # Very high contrast can be problematic
        if contrast > 80:
            return True, "High contrast pattern detected"
        
        return False, None
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return False, None

def analyze_video_for_flashing(video_bytes):
    """
    Analyze a video/GIF for photosensitive triggers
    Returns: (is_dangerous, reason, details)
    """
    try:
        # Save bytes to temporary file for OpenCV
        temp_path = '/tmp/temp_video.mp4'
        with open(temp_path, 'wb') as f:
            f.write(video_bytes.read())
        
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
        
        config = PhotosensitiveConfig()
        
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

@bot.event
async def on_ready():
    """Called when bot successfully connects to Discord"""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} server(s)')

@bot.event
async def on_message(message):
    """Called whenever a message is sent in a channel the bot can see"""
    
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # List to store URLs to check (from attachments and embeds)
    urls_to_check = []
    
    # Check if message has attachments
    if message.attachments:
        for attachment in message.attachments:
            urls_to_check.append({
                'url': attachment.url,
                'filename': attachment.filename,
                'source': 'attachment'
            })
    
    # Check for Tenor GIFs and other embeds
    if message.embeds:
        for embed in message.embeds:
            # Tenor GIFs and other image/video embeds
            if embed.type in ['image', 'gifv', 'video']:
                # Check for image in embed
                if embed.image and embed.image.url:
                    urls_to_check.append({
                        'url': embed.image.url,
                        'filename': embed.image.url.split('/')[-1],
                        'source': 'embed_image'
                    })
                # Check for video in embed
                if embed.video and embed.video.url:
                    urls_to_check.append({
                        'url': embed.video.url,
                        'filename': embed.video.url.split('/')[-1],
                        'source': 'embed_video'
                    })
                # Check for thumbnail (sometimes used for GIFs)
                if embed.thumbnail and embed.thumbnail.url:
                    urls_to_check.append({
                        'url': embed.thumbnail.url,
                        'filename': embed.thumbnail.url.split('/')[-1],
                        'source': 'embed_thumbnail'
                    })
    
    # Also check for direct Tenor URLs in message content
    if 'tenor.com' in message.content.lower() or 'media.tenor.com' in message.content.lower():
        import re
        # Extract URLs from message
        url_pattern = r'https?://(?:tenor\.com/view/|media\.tenor\.com/)[^\s]+'
        found_urls = re.findall(url_pattern, message.content)
        for url in found_urls:
            urls_to_check.append({
                'url': url,
                'filename': url.split('/')[-1],
                'source': 'tenor_link'
            })
    
    # Process all found URLs
    if urls_to_check:
    # Process all found URLs
    if urls_to_check:
        for item in urls_to_check:
            should_remove = False
            reason = None
            
            url = item['url']
            filename = item['filename']
            source = item['source']
            
            # Check file type from filename or URL
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            # Also check URL for common patterns
            url_lower = url.lower()
            is_gif = file_ext == 'gif' or '.gif' in url_lower or 'gifv' in url_lower
            is_video = file_ext in ['mp4', 'webm', 'mov'] or any(ext in url_lower for ext in ['.mp4', '.webm', '.mov'])
            is_image = file_ext in ['jpg', 'jpeg', 'png', 'webp'] or any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp'])
            
            # Download the file
            file_bytes = await download_file(url)
            if not file_bytes:
                continue
            
            # Analyze based on file type
            if is_gif or is_video:
                # Video/GIF analysis
                is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
                if is_dangerous:
                    should_remove = True
                    
            elif is_image:
                # Image analysis
                is_dangerous, reason = analyze_image_for_flashing(file_bytes)
                if is_dangerous:
                    should_remove = True
            
            # Remove dangerous content
            if should_remove:
                try:
                    await message.delete()
                    
                    # Send explanation
                    warning_embed = discord.Embed(
                        title="⚠️ Photosensitive Content Removed",
                        description=f"Content posted by {message.author.mention} was removed for safety.",
                        color=discord.Color.red()
                    )
                    warning_embed.add_field(
                        name="Reason",
                        value=reason or "Potential photosensitive trigger detected",
                        inline=False
                    )
                    warning_embed.add_field(
                        name="Source",
                        value=f"Detected in: {source.replace('_', ' ').title()}",
                        inline=False
                    )
                    warning_embed.add_field(
                        name="Info",
                        value="This content may trigger seizures in photosensitive individuals. Please avoid posting rapidly flashing or strobing content.",
                        inline=False
                    )
                    
                    await message.channel.send(embed=warning_embed, delete_after=30)
                    
                    # Log to console
                    print(f"Removed photosensitive content ({source}) from {message.author} in {message.guild.name}")
                    
                    # Break after first removal (message is already deleted)
                    break
                    
                except discord.Forbidden:
                    print(f"Missing permissions to delete message in {message.guild.name}")
                except Exception as e:
                    print(f"Error removing content: {e}")

    
    # Process commands (if you add any)
    await bot.process_commands(message)

@bot.command(name='check')
async def manual_check(ctx, url: str):
    """Manually check a URL for photosensitive content"""
    await ctx.send("Analyzing content... This may take a moment.")
    
    file_bytes = await download_file(url)
    if not file_bytes:
        await ctx.send("❌ Could not download file from that URL.")
        return
    
    # Try video analysis first
    is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
    
    if is_dangerous:
        await ctx.send(f"⚠️ **WARNING**: {reason}\nThis content may be dangerous for photosensitive individuals.")
    else:
        await ctx.send("✅ No obvious photosensitive triggers detected. (Note: This is not a guarantee of safety)")

@bot.command(name='help_photo')
async def help_command(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="Photosensitive Content Moderator",
        description="This bot automatically removes content that may trigger photosensitive seizures.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="What it detects:",
        value="• Rapid flashing (>3 flashes/second)\n• High-contrast strobing\n• Dangerous red flashing\n• High-contrast patterns",
        inline=False
    )
    embed.add_field(
        name="Commands:",
        value="`!check <url>` - Manually check a URL\n`!help_photo` - Show this message",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)