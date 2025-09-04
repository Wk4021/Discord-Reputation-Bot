import discord
from discord.ext import commands
import yaml
import time
from typing import Optional, Dict, List

CONFIG_PATH = 'data/config.yaml'

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class LoggingSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._log_messages: Dict[int, discord.Message] = {}
        self._log_events: Dict[int, Dict[str, List[str]]] = {}
        print("📋 Logging system loaded")

    async def get_log_channel(self) -> Optional[discord.TextChannel]:
        config = load_config()
        log_ch_id = config.get("log_channel")
        if not log_ch_id:
            return None
        log_ch = self.bot.get_channel(log_ch_id)
        if not log_ch:
            print(f"[WARN] log_channel {log_ch_id} not found")
            return None
        return log_ch

    async def create_thread_log(
        self,
        thread: discord.Thread,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[discord.Color] = None,
        fields: Optional[Dict[str, str]] = None
    ) -> Optional[discord.Message]:
        log_ch = await self.get_log_channel()
        if not log_ch:
            return None

        if thread.id in self._log_messages:
            try:
                return await log_ch.fetch_message(self._log_messages[thread.id].id)
            except (discord.NotFound, discord.Forbidden):
                pass

        embed = discord.Embed(
            title=title or f"📋 [Thread: {thread.name}]({thread.jump_url})",
            description=description or f"Created by <@{thread.owner_id}>",
            color=color or discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=value, inline=False)
        else:
            embed.add_field(name="Status", value="✅ Active", inline=False)
            embed.add_field(name="Events", value="*No events yet*", inline=False)

        msg = await log_ch.send(embed=embed)
        self._log_messages[thread.id] = msg
        self._log_events[thread.id] = {field: [] for field in (fields.keys() if fields else ["Events"])}
        return msg

    async def update_thread_log(
        self,
        thread: discord.Thread,
        field_updates: Optional[Dict[str, str]] = None,
        event_additions: Optional[Dict[str, str]] = None,
        embed_updates: Optional[Dict[str, any]] = None
    ):
        if thread.id not in self._log_messages:
            await self.create_thread_log(thread)
        
        msg = self._log_messages.get(thread.id)
        if not msg:
            return

        log_ch = await self.get_log_channel()
        if not log_ch:
            return

        try:
            msg = await log_ch.fetch_message(msg.id)
        except (discord.NotFound, discord.Forbidden):
            return

        embed = msg.embeds[0]
        embed.timestamp = discord.utils.utcnow()

        if embed_updates:
            if "title" in embed_updates:
                embed.title = embed_updates["title"]
            if "description" in embed_updates:
                embed.description = embed_updates["description"]
            if "color" in embed_updates:
                embed.color = embed_updates["color"]

        if field_updates:
            for field_name, field_value in field_updates.items():
                for i, field in enumerate(embed.fields):
                    if field.name == field_name:
                        embed.set_field_at(i, name=field_name, value=field_value, inline=False)
                        break
                else:
                    embed.add_field(name=field_name, value=field_value, inline=False)

        if event_additions:
            events_dict = self._log_events.setdefault(thread.id, {})
            for field_name, event in event_additions.items():
                events_list = events_dict.setdefault(field_name, [])
                timestamp_event = f"{event} at <t:{int(time.time())}:T>"
                events_list.append(timestamp_event)
                
                for i, field in enumerate(embed.fields):
                    if field.name == field_name:
                        embed.set_field_at(i, name=field_name, value="\n".join(events_list), inline=False)
                        break

        await msg.edit(embed=embed)

    async def log_simple_message(
        self,
        content: str,
        embed: Optional[discord.Embed] = None,
        channel_id: Optional[int] = None
    ):
        if channel_id:
            log_ch = self.bot.get_channel(channel_id)
        else:
            log_ch = await self.get_log_channel()
        
        if not log_ch:
            return

        if embed:
            await log_ch.send(content=content, embed=embed)
        else:
            await log_ch.send(content)

    async def create_custom_log(
        self,
        identifier: str,
        title: str,
        description: str = "",
        color: discord.Color = discord.Color.blue(),
        fields: Optional[Dict[str, str]] = None,
        channel_id: Optional[int] = None
    ) -> Optional[discord.Message]:
        if channel_id:
            log_ch = self.bot.get_channel(channel_id)
        else:
            log_ch = await self.get_log_channel()
        
        if not log_ch:
            return None

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )

        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=value, inline=False)

        msg = await log_ch.send(embed=embed)
        self._log_messages[hash(identifier)] = msg
        self._log_events[hash(identifier)] = {field: [] for field in (fields.keys() if fields else [])}
        return msg

    async def update_custom_log(
        self,
        identifier: str,
        field_updates: Optional[Dict[str, str]] = None,
        event_additions: Optional[Dict[str, str]] = None,
        embed_updates: Optional[Dict[str, any]] = None
    ):
        id_hash = hash(identifier)
        if id_hash not in self._log_messages:
            return

        msg = self._log_messages[id_hash]
        log_ch = await self.get_log_channel()
        if not log_ch:
            return

        try:
            msg = await log_ch.fetch_message(msg.id)
        except (discord.NotFound, discord.Forbidden):
            return

        embed = msg.embeds[0]
        embed.timestamp = discord.utils.utcnow()

        if embed_updates:
            if "title" in embed_updates:
                embed.title = embed_updates["title"]
            if "description" in embed_updates:
                embed.description = embed_updates["description"]
            if "color" in embed_updates:
                embed.color = embed_updates["color"]

        if field_updates:
            for field_name, field_value in field_updates.items():
                for i, field in enumerate(embed.fields):
                    if field.name == field_name:
                        embed.set_field_at(i, name=field_name, value=field_value, inline=False)
                        break
                else:
                    embed.add_field(name=field_name, value=field_value, inline=False)

        if event_additions:
            events_dict = self._log_events.setdefault(id_hash, {})
            for field_name, event in event_additions.items():
                events_list = events_dict.setdefault(field_name, [])
                timestamp_event = f"{event} at <t:{int(time.time())}:T>"
                events_list.append(timestamp_event)
                
                for i, field in enumerate(embed.fields):
                    if field.name == field_name:
                        embed.set_field_at(i, name=field_name, value="\n".join(events_list), inline=False)
                        break

        await msg.edit(embed=embed)

    def get_log_message(self, thread_id: int) -> Optional[discord.Message]:
        return self._log_messages.get(thread_id)

    def get_custom_log_message(self, identifier: str) -> Optional[discord.Message]:
        return self._log_messages.get(hash(identifier))

async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingSystem(bot))