import discord
from discord.ext import commands
from discord import app_commands
import yaml
import random
import asyncio
import sqlite3
import time
import re
from utils import db

CONFIG_PATH = 'data/config.yaml'

# Tracks threads waiting on TOS acceptance
# new — maps thread.id → timestamp when TOS prompt was sent
pending_tos_timestamps: dict[int, float] = {}

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_funny_messages():
    try:
        with open("assets/rep_messages.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return ["Damn, get your rep up!"]


class RepTOSView(discord.ui.View):
    def __init__(
        self,
        thread: discord.Thread,
        op_id: int,
        timeout: float = 30.0
    ):
        # timeout is in seconds
        super().__init__(timeout=timeout)
        self.thread = thread
        self.op_id = op_id

    @discord.ui.button(label='✅ I Agree', style=discord.ButtonStyle.success)
    async def agree(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can accept the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        # Remove the TOS prompt and proceed to the rep UI
        await interaction.message.delete()
        await post_rep_ui(self.thread, self.op_id)

    @discord.ui.button(label='❌ I Do Not Agree', style=discord.ButtonStyle.danger)
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can decline the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        config = load_config()
        # Edit the prompt to the decline response
        await interaction.message.edit(
            content=config['tos_decline_response'],
            view=None
        )

        # Archive & lock the thread
        await self.thread.edit(archived=True, locked=True)

    async def on_timeout(self):
        # Called if neither button is pressed within timeout
        pending_tos_timestamps.pop(self.thread.id, None)

        try:
            print(f"[TOS] Thread {self.thread.id} timed out. Auto-closing.")

            # Notify in-thread
            await self.thread.send(
                "⏱️ No response to TOS in time. This post has been auto-closed."
            )

            # Archive & lock
            await self.thread.edit(archived=True, locked=True)

        except Exception as e:
            print(f"[ERROR] Auto-close on timeout failed: {e}")


def generate_star_rating(positive: int, negative: int) -> str | None:
    total = positive + negative
    if total == 0:
        return None
    score = round((positive / total) * 10)
    stars = "⭐" * (score // 2) + "☆" * (5 - (score // 2))
    return f"Rating: {stars} ({positive}👍 / {negative}👎)"

# Load the category→messages mapping
def load_rep_messages():
    cats = {"good": [], "neutral": [], "bad": []}
    try:
        with open("assets/rep_messages.txt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    cat, msg = line.split("|", 1)
                    cat = cat.strip().lower()
                    msg = msg.strip()
                    if cat in cats:
                        cats[cat].append(msg)
    except FileNotFoundError:
        # fallback to a minimal set
        cats["neutral"].append("No rep data…")
    return cats

GIF_URL_RE = re.compile(
    r'(https?://\S+?\.(?:gif|mp4|webm))(?=[\s"\'<]|$)', 
    flags=re.IGNORECASE
)

async def post_rep_ui(thread: discord.Thread, op_id: int):
    config = load_config()
    rep_msgs = load_rep_messages()
    no_rep_lines = config.get("no_rep_messages", [])

    pos, neg = db.get_user_rep(op_id)
    total = pos + neg

    # 1) No rep yet
    if total == 0:
        content = f"😶 {random.choice(no_rep_lines)}"
        gif_url = None

    # 2) Otherwise pick a line
    else:
        ratio = pos / total
        if ratio >= 0.7:
            pool = rep_msgs["good"]
        elif ratio <= 0.3:
            pool = rep_msgs["bad"]
        else:
            pool = rep_msgs["neutral"]

        raw = random.choice(pool) if pool else ""
        # Split on last space
        parts = raw.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].lower().endswith((".gif", ".mp4", ".webm")):
            text, gif_url = parts[0], parts[1]
        else:
            text, gif_url = raw, None

        content = text

    # 3) Prepend star rating if any
    rep_display = generate_star_rating(pos, neg)
    if rep_display and total > 0:
        content = f"📊 {rep_display}\n\n{content}"

    # 4) Build the embed
    embed = discord.Embed(description=content, color=discord.Color.green())
    if gif_url:
        embed.set_image(url=gif_url)
        print(f"[DEBUG] Embedding GIF: {gif_url}")  # for your logs

    view = RepButtonView(op_id=op_id, thread=thread)
    await thread.send(embed=embed, view=view)


class RepButtonView(discord.ui.View):
    def __init__(self, op_id: int, thread: discord.Thread):
        super().__init__(timeout=None)
        self.op_id = op_id
        self.thread = thread

    async def rep_user(
        self,
        interaction: discord.Interaction,
        rep_type: str
    ):
        if interaction.user.id == self.op_id:
            return await interaction.response.send_message(
                "You can't rep yourself.",
                ephemeral=True
            )

        # Ensure user has posted in the thread first
        has_spoken = False
        async for msg in self.thread.history(limit=100):
            if msg.author.id == interaction.user.id:
                has_spoken = True
                break
        if not has_spoken:
            return await interaction.response.send_message(
                "You need to interact in the thread first.",
                ephemeral=True
            )

        # Record the rep
        success = db.add_rep(
            interaction.user.id,  # giver
            self.op_id,           # receiver
            self.thread.id,
            rep_type
        )
        if not success:
            return await interaction.response.send_message(
                "You've already repped in this thread.",
                ephemeral=True
            )

        # Confirmation embed
        embed = discord.Embed(
            title="✅ Rep Given",
            description=(
                f"{interaction.user.mention} gave a **{rep_type}rep** "
                f"to <@{self.op_id}> in [this thread]({self.thread.jump_url})"
            ),
            color=discord.Color.green() if rep_type == '+' else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log it if configured
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                await log_ch.send(embed=embed)

    @discord.ui.button(label='+ Rep', style=discord.ButtonStyle.success)
    async def plus(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.rep_user(interaction, '+')

    @discord.ui.button(label='- Rep', style=discord.ButtonStyle.danger)
    async def minus(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.rep_user(interaction, '-')

    @discord.ui.button(label='Close Post', style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # 1) Only the OP can close
            if interaction.user.id != self.op_id:
                return await interaction.response.send_message(
                    "Only the thread creator can close this post.",
                    ephemeral=True
                )

            # 2) Must have at least one rep
            conn = sqlite3.connect(db.DB_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM rep WHERE thread_id = ? AND giver_id != ?",
                (self.thread.id, self.op_id)
            )
            count = c.fetchone()[0]
            conn.close()

            if count == 0:
                return await interaction.response.send_message(
                    "You must receive at least one rep before closing your post.",
                    ephemeral=True
                )

            # 3) Announce closure in‐thread (normal message)
            await interaction.response.send_message(
                "🔒 This thread is now closed by its creator.",
                ephemeral=False
            )

            # 4) Archive & lock the thread
            await self.thread.edit(archived=True, locked=True)

        except Exception as e:
            print(f"[ERROR] close button handler: {e}")
            # If we haven't responded yet, send an ephemeral failure
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ Something went wrong. Please try again later.",
                    ephemeral=True
                )

class Rep(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In‐memory storage of log messages & rep events per thread
        self._log_messages: dict[int, discord.Message] = {}
        self._rep_events: dict[int, list[str]] = {}
        print("🔧 Rep cog loaded")

    async def _ensure_thread_log(self, thread: discord.Thread) -> discord.Message | None:
        """
        Ensure there is a single embed message in the configured log channel
        for this thread, and return it.
        """
        config = load_config()
        log_ch_id = config.get("log_channel")
        if not log_ch_id:
            return None

        log_ch = self.bot.get_channel(log_ch_id)
        if not log_ch:
            return None

        # If we already sent and stored a message, try to fetch it
        if thread.id in self._log_messages:
            try:
                msg = await log_ch.fetch_message(self._log_messages[thread.id].id)
                return msg
            except (discord.NotFound, discord.Forbidden):
                pass  # fallback to sending a new one

        # Build initial embed
        embed = discord.Embed(
            title=f"📋 Thread Log: {thread.name}",
            description=f"Thread created by <@{thread.owner_id}>",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="TOS Status", value="Pending ⏳", inline=False)
        embed.add_field(name="Rep Events", value="*No events yet*", inline=False)

        msg = await log_ch.send(embed=embed)
        self._log_messages[thread.id] = msg
        self._rep_events[thread.id] = []
        return msg

    async def _update_thread_log(self, thread: discord.Thread, *, tos_status=None, rep_event=None, timestamp=None):
        """
        Update the thread log embed. 
        Params:
          - tos_status: str (new TOS status)
          - rep_event: str (single new rep line)
          - timestamp: datetime.datetime (new embed timestamp)
        """
        msg = await self._ensure_thread_log(thread)
        if not msg:
            return

        embed = msg.embeds[0]

        if tos_status is not None:
            embed.set_field_at(0, name="TOS Status", value=tos_status, inline=False)

        if rep_event is not None:
            events = self._rep_events.setdefault(thread.id, [])
            events.append(rep_event)
            embed.set_field_at(1, name="Rep Events", value="\n".join(events), inline=False)

        if timestamp is not None:
            embed.timestamp = timestamp

        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            forums = [int(f) for f in config.get("forums", []) if str(f).isdigit()]
            if thread.parent_id not in forums:
                return

            # Join so the bot can send
            try:
                await thread.join()
            except Exception:
                pass

            # Prepare TOS prompt
            timeout_secs = 30
            ts = int(time.time()) + timeout_secs
            countdown = f"<t:{ts}:R>"
            tos_line = config["tos_message"].replace("{timeout}", countdown)
            
            view = RepTOSView(thread=thread, op_id=thread.owner_id, timeout=timeout_secs)
            await asyncio.sleep(2)
            await thread.send(content=tos_line, view=view)
            pending_tos_timestamps[thread.id] = time.time()

            # Initialize log embed
            await self._update_thread_log(
                thread,
                tos_status=f"Prompt sent at <t:{ts}:T>",
                timestamp=discord.utils.utcnow()
            )

        except Exception as e:
            print(f"[ERROR] on_thread_create: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Delete user messages posted after TOS prompt until it's handled
        ts = pending_tos_timestamps.get(message.channel.id)
        if (
            ts
            and isinstance(message.channel, discord.Thread)
            and not message.author.bot
            and message.created_at.timestamp() > ts
        ):
            try:
                await message.delete()
            except discord.Forbidden:
                pass

    @app_commands.command(name="channel_set", description="Add a forum channel for tracking reps.")
    @app_commands.describe(channel="Forum channel to activate rep tracking on.")
    async def channel_set(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        config = load_config()
        config.setdefault("forums", [])
        if channel.id not in config["forums"]:
            config["forums"].append(channel.id)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)
            await interaction.response.send_message(
                f"✅ Channel {channel.mention} added to rep tracking.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "This channel is already tracked.", ephemeral=True
            )

    @app_commands.command(name="rep", description="Check a user's rep status.")
    @app_commands.describe(user="The user to check rep for.")
    async def rep_lookup(self, interaction: discord.Interaction, user: discord.Member):
        pos, neg = db.get_user_rep(user.id)
        rep_display = generate_star_rating(pos, neg)
        embed = discord.Embed(
            title=f"📊 Reputation for {user.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Positive Rep", value=f"👍 {pos}", inline=True)
        embed.add_field(name="Negative Rep", value=f"👎 {neg}", inline=True)
        if rep_display:
            embed.set_footer(text=rep_display)
        else:
            embed.set_footer(text="😶 No rep yet. Damn, get your rep up!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="repleaderboard", description="Show the top 10 users by +rep.")
    async def rep_leaderboard(self, interaction: discord.Interaction):
        top = db.get_top_positive_rep(limit=10)
        embed = discord.Embed(
            title="🏆 Top +Rep Leaderboard",
            description="Here are the top repped users:",
            color=discord.Color.gold()
        )
        if not top:
            embed.description = "No rep data found."
        else:
            for i, (user_id, pos) in enumerate(top, start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                embed.add_field(name=f"{i}. {name}", value=f"+{pos} rep", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="log", description="Set a channel for rep logs.")
    @app_commands.describe(channel="The channel to send rep logs to.")
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        config["log_channel"] = channel.id
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Rep logs will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rep(bot))

