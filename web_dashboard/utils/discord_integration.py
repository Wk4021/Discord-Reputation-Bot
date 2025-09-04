"""
Discord API integration utilities for the web dashboard.
This module provides functions to fetch user and thread information from Discord.
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
import yaml
from typing import Optional, Dict, Any

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DiscordDataFetcher:
    """Handles Discord API calls for the web dashboard"""
    
    def __init__(self, token: str, guild_id: int):
        self.token = token
        self.guild_id = guild_id
        self.bot = None
        self._setup_bot()
    
    def _setup_bot(self):
        """Initialize the Discord bot client"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        @self.bot.event
        async def on_ready():
            print(f"Discord API connected as {self.bot.user}")
    
    async def start_bot(self):
        """Start the Discord bot connection"""
        try:
            await self.bot.start(self.token)
        except Exception as e:
            print(f"Error starting Discord bot: {e}")
            return False
        return True
    
    async def stop_bot(self):
        """Stop the Discord bot connection"""
        if self.bot:
            await self.bot.close()
    
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch Discord user information
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with user information or None if not found
        """
        try:
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
            
            if not user:
                return None
            
            guild = self.bot.get_guild(self.guild_id)
            member = None
            if guild:
                try:
                    member = guild.get_member(user_id)
                    if not member:
                        member = await guild.fetch_member(user_id)
                except:
                    pass
            
            # Build user data
            user_data = {
                'id': user.id,
                'username': user.name,
                'discriminator': user.discriminator if hasattr(user, 'discriminator') else '0000',
                'display_name': user.display_name,
                'avatar_url': str(user.display_avatar.url) if user.display_avatar else str(user.default_avatar.url),
                'banner_url': str(user.banner.url) if user.banner else None,
                'status': 'unknown',
                'joined_at': None,
                'roles': []
            }
            
            # Add member-specific data if available
            if member:
                user_data['display_name'] = member.display_name
                user_data['status'] = str(member.status) if member.status else 'unknown'
                user_data['joined_at'] = member.joined_at.isoformat() if member.joined_at else None
                user_data['roles'] = [{'id': role.id, 'name': role.name, 'color': str(role.color)} 
                                     for role in member.roles if role.name != '@everyone']
            
            return user_data
            
        except Exception as e:
            print(f"Error fetching user {user_id}: {e}")
            return None
    
    async def get_thread_info(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch Discord thread information
        
        Args:
            thread_id: Discord thread ID
            
        Returns:
            Dictionary with thread information or None if not found
        """
        try:
            # Try to get the thread from all guilds the bot is in
            thread = None
            for guild in self.bot.guilds:
                try:
                    thread = guild.get_thread(thread_id)
                    if thread:
                        break
                    
                    # Try to fetch if not in cache
                    for text_channel in guild.text_channels:
                        try:
                            thread = await text_channel.fetch_thread(thread_id)
                            if thread:
                                break
                        except:
                            continue
                    
                    if thread:
                        break
                        
                except Exception as e:
                    continue
            
            if not thread:
                return None
            
            # Build thread data
            thread_data = {
                'id': thread.id,
                'name': thread.name,
                'url': f"https://discord.com/channels/{thread.guild.id}/{thread.parent_id}/{thread.id}",
                'created_at': thread.created_at.isoformat() if thread.created_at else None,
                'archived': thread.archived if hasattr(thread, 'archived') else False,
                'locked': thread.locked if hasattr(thread, 'locked') else False,
                'owner_id': thread.owner_id if hasattr(thread, 'owner_id') else None,
                'parent_id': thread.parent_id if hasattr(thread, 'parent_id') else None,
                'guild_id': thread.guild.id,
                'message_count': thread.message_count if hasattr(thread, 'message_count') else 0
            }
            
            return thread_data
            
        except Exception as e:
            print(f"Error fetching thread {thread_id}: {e}")
            return None
    
    async def get_guild_info(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Discord guild information
        
        Returns:
            Dictionary with guild information or None if not found
        """
        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                return None
            
            guild_data = {
                'id': guild.id,
                'name': guild.name,
                'icon_url': str(guild.icon.url) if guild.icon else None,
                'banner_url': str(guild.banner.url) if guild.banner else None,
                'member_count': guild.member_count,
                'created_at': guild.created_at.isoformat() if guild.created_at else None,
                'description': guild.description,
                'features': guild.features
            }
            
            return guild_data
            
        except Exception as e:
            print(f"Error fetching guild {self.guild_id}: {e}")
            return None

# Global Discord fetcher instance
_discord_fetcher: Optional[DiscordDataFetcher] = None

def get_discord_fetcher() -> Optional[DiscordDataFetcher]:
    """Get the global Discord fetcher instance"""
    return _discord_fetcher

async def initialize_discord_integration(token: str, guild_id: int) -> bool:
    """
    Initialize Discord integration
    
    Args:
        token: Discord bot token
        guild_id: Discord guild ID
        
    Returns:
        True if successful, False otherwise
    """
    global _discord_fetcher
    
    try:
        _discord_fetcher = DiscordDataFetcher(token, guild_id)
        # Note: Bot connection would be handled separately in a background task
        return True
    except Exception as e:
        print(f"Error initializing Discord integration: {e}")
        return False

def load_config():
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

# Utility functions for template usage
def format_discord_timestamp(timestamp_str: str) -> str:
    """Format Discord timestamp for display"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M UTC')
    except:
        return timestamp_str

def get_status_color(status: str) -> str:
    """Get CSS color class for Discord status"""
    status_colors = {
        'online': 'text-success',
        'idle': 'text-warning', 
        'dnd': 'text-danger',
        'offline': 'text-secondary',
        'unknown': 'text-muted'
    }
    return status_colors.get(status, 'text-muted')

def get_default_avatar_url(user_id: int) -> str:
    """Generate default Discord avatar URL"""
    return f"https://cdn.discordapp.com/embed/avatars/{user_id % 5}.png"