# Author:       leh-x
# AI:           Claude
# Date:         Dec 17 2025
# Purpose:      Discord bot that detects and auto moderates photosensitive content
# Last Edited:  Aug 05 2026

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
import re
import tempfile
import subprocess

from config import PhotosensitiveConfig

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


def is_youtube_url(url):
    """Check if URL is a YouTube video"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=',
        r'(?:https?://)?(?:www\.)?youtu\.be/',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/',
    ]
    return any(re.search(pattern, url) for pattern in youtube_patterns)

def is_giphy_url(url):
    """Check if URL is a Giphy link"""
    giphy_patterns = [
        r'giphy\.com/gifs/',
        r'giphy\.com/embed/',
        r'media\.giphy\.com/',
        r'i\.giphy\.com/',
    ]
    return any(re.search(pattern, url.lower()) for pattern in giphy_patterns)

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
    
    print(f"DEBUG: Processing message from {message.author}")

    # List to store URLs to check (from attachments and embeds)
    urls_to_check = []
    
    # Check if message has attachments
    if message.attachments:
        print(f"DEBUG: Found {len(message.attachments)} attachment(s)")

        for attachment in message.attachments:
            urls_to_check.append({
                'url': attachment.url,
                'filename': attachment.filename,
                'source': 'attachment'
            })
    
    # Check for Tenor GIFs and other embeds
    if message.embeds:
        print(f"DEBUG: Found embed message from {message.author}")

        for embed in message.embeds:
            # Tenor GIFs and other image/video embeds
            if embed.type in ['image', 'gifv', 'video']:
                print(f"DEBUG: Finding the type of embed message from {message.author}")
                
                # Check for image in embed
                if embed.image and embed.image.url:
                    urls_to_check.append({
                        'url': embed.image.url,
                        'filename': embed.image.url.split('/')[-1],
                        'source': 'embed_image'
                    })
                    print(f"DEBUG: Embed message is an image!")

                # Check for video in embed
                if embed.video and embed.video.url:
                    urls_to_check.append({
                        'url': embed.video.url,
                        'filename': embed.video.url.split('/')[-1],
                        'source': 'embed_video'
                    })
                    print(f"DEBUG: Embed message is a video!")

                # Check for thumbnail (sometimes used for GIFs)
                if embed.thumbnail and embed.thumbnail.url:
                    urls_to_check.append({
                        'url': embed.thumbnail.url,
                        'filename': embed.thumbnail.url.split('/')[-1],
                        'source': 'embed_thumbnail'
                    })
                    print(f"DEBUG: Embed message is a thumbnail!")
    
    # Also check for direct Tenor URLs in message content
    if 'tenor.com' in message.content.lower() or 'media.tenor.com' in message.content.lower():
        # Extract URLs from message
        url_pattern = r'https?://(?:tenor\.com/view/|media\.tenor\.com/)[^\s]+'
        found_urls = re.findall(url_pattern, message.content)
        for url in found_urls:
            urls_to_check.append({
                'url': url,
                'filename': url.split('/')[-1],
                'source': 'tenor_link'
            })
    
    # Check for YouTube URLs in message content
    if 'youtube.com' in message.content.lower() or 'youtu.be' in message.content.lower():
        # Extract URLs from message
        url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'
        found_urls = re.findall(url_pattern, message.content)
        for url in found_urls:
            urls_to_check.append({
                'url': url,
                'filename': 'youtube_video',
                'source': 'youtube'
            })
    
    # Check for Giphy URLs in message content
    if 'giphy.com' in message.content.lower():
        # Extract URLs from message
        url_pattern = r'https?://(?:media\.)?giphy\.com/[^\s]+'
        found_urls = re.findall(url_pattern, message.content)
        for url in found_urls:
            urls_to_check.append({
                'url': url,
                'filename': 'giphy.gif',
                'source': 'giphy'
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
                
                # Special handling for YouTube
                if source == 'youtube' or is_youtube_url(url):
                    # Download YouTube video (first 30 seconds only)
                    video_path = await download_youtube_video(url, max_duration=30)
                    
                    if video_path:
                        # Analyze the downloaded video
                        is_dangerous, reason, details = analyze_video_for_flashing(video_path)
                        
                        # Clean up temp file
                        try:
                            os.remove(video_path)
                            os.rmdir(os.path.dirname(video_path))
                        except:
                            pass
                        
                        if is_dangerous:
                            should_remove = True
                    else:
                        # Couldn't download - skip but log
                        print(f"Could not download YouTube video: {url}")
                        continue
                
                # Special handling for Giphy
                elif source == 'giphy' or is_giphy_url(url):
                    # Extract direct media URL from Giphy page
                    media_url = extract_giphy_media_url(url)
                    
                    if media_url:
                        print(f"Extracted Giphy media URL: {media_url}")
                        file_bytes = await download_file(media_url)
                        
                        if file_bytes:
                            is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
                            if is_dangerous:
                                should_remove = True
                        else:
                            print(f"Could not download Giphy media from: {media_url}")
                            continue
                    else:
                        print(f"Could not extract media URL from Giphy: {url}")
                        continue
                
                else:
                    # Regular file download for non-YouTube/Giphy content
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

@bot.event
async def on_message_edit(before, after):
    """Called when a message is edited (including when embeds are loaded)"""
    
    # Ignore messages from the bot itself
    if after.author == bot.user:
        return
    
    # Check if embeds changed
    if before.embeds == after.embeds:
        return  # No change in embeds, skip
    
    print(f"DEBUG: on_message_edit - Embeds changed for message from {after.author}")
    
    urls_to_check = []
    
    if after.embeds:
        print(f"DEBUG: Found {len(after.embeds)} embed(s) in edited message")
        for embed in after.embeds:
            if embed.type in ['image', 'gifv', 'video']:
                print(f"DEBUG: Finding the type of embed message from {after.author}")
                
                if embed.image and embed.image.url:
                    urls_to_check.append({
                        'url': embed.image.url,
                        'filename': embed.image.url.split('/')[-1],
                        'source': 'embed_image'
                    })
                    print(f"DEBUG: Embed message is an image!")

                if embed.video and embed.video.url:
                    urls_to_check.append({
                        'url': embed.video.url,
                        'filename': embed.video.url.split('/')[-1],
                        'source': 'embed_video'
                    })
                    print(f"DEBUG: Embed message is a video!")

                if embed.thumbnail and embed.thumbnail.url:
                    urls_to_check.append({
                        'url': embed.thumbnail.url,
                        'filename': embed.thumbnail.url.split('/')[-1],
                        'source': 'embed_thumbnail'
                    })
                    print(f"DEBUG: Embed message is a thumbnail!")
    
    if urls_to_check:
        print(f"DEBUG: Processing {len(urls_to_check)} URL(s) from edited message")
        for item in urls_to_check:
            should_remove = False
            reason = None
            
            url = item['url']
            filename = item['filename']
            source = item['source']
            
            if source == 'youtube' or is_youtube_url(url):
                video_path = await download_youtube_video(url, max_duration=30)
                if video_path:
                    is_dangerous, reason, details = analyze_video_for_flashing(video_path)
                    try:
                        os.remove(video_path)
                        os.rmdir(os.path.dirname(video_path))
                    except:
                        pass
                    if is_dangerous:
                        should_remove = True
                else:
                    continue
            elif source == 'giphy' or is_giphy_url(url):
                media_url = extract_giphy_media_url(url)
                if media_url:
                    file_bytes = await download_file(media_url)
                    if file_bytes:
                        is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
                        if is_dangerous:
                            should_remove = True
                    else:
                        continue
                else:
                    continue
            else:
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
                url_lower = url.lower()
                is_gif = file_ext == 'gif' or '.gif' in url_lower or 'gifv' in url_lower
                is_video = file_ext in ['mp4', 'webm', 'mov'] or any(ext in url_lower for ext in ['.mp4', '.webm', '.mov'])
                is_image = file_ext in ['jpg', 'jpeg', 'png', 'webp'] or any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp'])
                
                file_bytes = await download_file(url)
                if not file_bytes:
                    continue
                
                if is_gif or is_video:
                    is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
                    if is_dangerous:
                        should_remove = True
                elif is_image:
                    is_dangerous, reason = analyze_image_for_flashing(file_bytes)
                    if is_dangerous:
                        should_remove = True
            
            if should_remove:
                try:
                    await after.delete()
                    warning_embed = discord.Embed(
                        title="⚠️ Photosensitive Content Removed",
                        description=f"Content posted by {after.author.mention} was removed for safety.",
                        color=discord.Color.red()
                    )
                    warning_embed.add_field(name="Reason", value=reason or "Potential photosensitive trigger detected", inline=False)
                    warning_embed.add_field(name="Source", value=f"Detected in: {source.replace('_', ' ').title()}", inline=False)
                    warning_embed.add_field(name="Info", value="This content may trigger seizures in photosensitive individuals. Please avoid posting rapidly flashing or strobing content.", inline=False)
                    await after.channel.send(embed=warning_embed, delete_after=30)
                    print(f"Removed photosensitive content ({source}) from {after.author} in {after.guild.name} (via edit)")
                    break
                except discord.Forbidden:
                    print(f"Missing permissions to delete message in {after.guild.name}")
                except Exception as e:
                    print(f"Error removing content: {e}")

@bot.command(name='check')
async def manual_check(ctx, url: str):
    """Manually check a URL for photosensitive content"""
    await ctx.send("Analyzing content... This may take a moment.")
    
    # Check if it's a YouTube URL
    if is_youtube_url(url):
        video_path = await download_youtube_video(url, max_duration=30)
        
        if not video_path:
            await ctx.send("❌ Could not download YouTube video. It may be restricted or unavailable.")
            return
        
        # Analyze the video
        is_dangerous, reason, details = analyze_video_for_flashing(video_path)
        
        # Clean up
        try:
            os.remove(video_path)
            os.rmdir(os.path.dirname(video_path))
        except:
            pass
        
        if is_dangerous:
            await ctx.send(f"⚠️ **WARNING**: {reason}\nThis YouTube video may be dangerous for photosensitive individuals.\n\n**Analysis details:**\n• Analyzed first 30 seconds\n• Flash detection threshold exceeded")
        else:
            await ctx.send("✅ No obvious photosensitive triggers detected in the first 30 seconds. (Note: This is not a guarantee of safety for the entire video)")
    
    # Check if it's a Giphy URL
    elif is_giphy_url(url):
        media_url = extract_giphy_media_url(url)
        
        if not media_url:
            await ctx.send("❌ Could not extract media from Giphy URL.")
            return
        
        file_bytes = await download_file(media_url)
        if not file_bytes:
            await ctx.send("❌ Could not download Giphy file.")
            return
        
        # Analyze the GIF
        is_dangerous, reason, details = analyze_video_for_flashing(file_bytes)
        
        if is_dangerous:
            await ctx.send(f"⚠️ **WARNING**: {reason}\nThis Giphy GIF may be dangerous for photosensitive individuals.")
        else:
            await ctx.send("✅ No obvious photosensitive triggers detected. (Note: This is not a guarantee of safety)")
    
    else:
        # Regular file download
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