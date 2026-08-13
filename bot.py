# Author:       leh-x
# AI:           Claude
# Date:         Dec 17 2025
# Purpose:      Discord bot that detects and auto moderates photosensitive content
# Last Edited:  Aug 05 2026

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from media import MediaURL

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
            urls_to_check.append(
                MediaURL.classify(
                    attachment.url, 
                    attachment.filename, 
                    'attachment')
            )
    
    # Check for GIFs and other embeds
    if message.embeds:
        print(f"DEBUG: Found embed message from {message.author}")

        for embed in message.embeds:
            # GIFs and other video embeds
            if embed.type in ['gifv', 'video']:
                print(f"DEBUG: Finding the type of embed message from {message.author}")

                # Check for video in embed
                if embed.video and embed.video.url:
                    urls_to_check.append(
                        MediaURL.classify(
                        embed.video.url,
                        embed.video.url.split('/')[-1],
                        'embed_video')
                    )
                    print(f"DEBUG: Embed message is a video!")

    # check for any other URLs that are not rendered
    urls_to_check.extend(MediaURL.classify_message(message.content))

    
    # Process all found URLs
    if urls_to_check:
        for item in urls_to_check:
            should_remove = False
            reason = None
            
            url = item.get_url
            filename = item.get_filename
            source = item.get_source

            await item.download()
            is_dangerous, reason, details = item.analyze()

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

                if embed.video and embed.video.url:
                    urls_to_check.append(
                        MediaURL.classify(
                        embed.video.url,
                        embed.video.url.split('/')[-1],
                        'embed_video')
                    )
                    print(f"DEBUG: Embed message is a video!")

    
    if urls_to_check:
        print(f"DEBUG: Processing {len(urls_to_check)} URL(s) from edited message")
        for item in urls_to_check:
            should_remove = False
            reason = None
            
            url = item.get_url
            filename = item.get_filename
            source = item.get_source

            await item.download()
            is_dangerous, reason, details = item.analyze()

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
    
    target = MediaURL.classify(url)
    await target.download()
    is_dangerous, reason, details = target.analyze()

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