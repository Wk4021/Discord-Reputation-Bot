import discord
from discord.ext import commands
from discord import app_commands
import yaml
import random
import asyncio
import sqlite3
import time

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


async def post_rep_ui(thread: discord.Thread, op_id: int):
    config = load_config()
    no_rep_lines = load_funny_messages()

    pos, neg = db.get_user_rep(op_id)
    rep_display = generate_star_rating(pos, neg)

    content = (
        f"📊 {rep_display}"
        if rep_display
        else f"😶 {random.choice(no_rep_lines)}"
    )

    view = RepButtonView(op_id=op_id, thread=thread)
    await thread.send(content, view=view)


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
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        try:
            # Permission check
            if (
                interaction.user.id != self.op_id
                and not interaction.user.guild_permissions.manage_threads
            ):
                return await interaction.response.send_message(
                    "Only the OP or an admin can close this post.",
                    ephemeral=True
                )

            # Ensure OP got at least one rep
            conn = sqlite3.connect(db.DB_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM rep WHERE thread_id = ? AND user_id != ?",
                (self.thread.id, self.op_id)
            )
            count = c.fetchone()[0]
            conn.close()

            if interaction.user.id == self.op_id and count == 0:
                return await interaction.response.send_message(
                    "You must receive a rep before closing.",
                    ephemeral=True
                )

            # Archive & lock
            await self.thread.edit(archived=True, locked=True)
            await interaction.response.send_message(
                "Thread closed.",
                ephemeral=False
            )

        except Exception as e:
            print(f"[ERROR] close button handler: {e}")
            return await interaction.response.send_message(
                "⚠️ Something went wrong. Please try again later.",
                ephemeral=True
            )


class Rep(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("🔧 Rep cog loaded")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            # Parse forums
            forums = [int(f) for f in config.get("forums", []) if str(f).isdigit()]
            if thread.parent_id not in forums:
                return
            # Try to join so we can send
            try:
                await thread.join()
            except Exception:
                pass

            # Build TOS prompt
            timeout_secs = 30
            ts = int(time.time()) + timeout_secs
            countdown = f"<t:{ts}:R>"
            tos_line = config["tos_message"].replace("{timeout}", countdown)

            # Send with timeout
            view = RepTOSView(thread=thread, op_id=thread.owner_id, timeout=timeout_secs)
            await thread.send(content=tos_line, view=view)
            pending_tos_timestamps[thread.id] = time.time()

        except Exception as e:
            print(f"[ERROR] on_thread_create: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # only in threads waiting on TOS
        ts = pending_tos_timestamps.get(message.channel.id)
        if (
            ts
            and isinstance(message.channel, discord.Thread)
            and not message.author.bot
            # only delete messages sent after the prompt time
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
        if 'forums' not in config:
            config['forums'] = []
        if channel.id not in config['forums']:
            config['forums'].append(channel.id)
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(config, f)
            await interaction.response.send_message(f"✅ Channel {channel.mention} added to rep tracking.", ephemeral=True)
        else:
            await interaction.response.send_message("This channel is already tracked.", ephemeral=True)

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
        leaderboard = db.get_top_positive_rep(limit=10)
        embed = discord.Embed(
            title="🏆 Top +Rep Leaderboard",
            description="Here are the top repped users:",
            color=discord.Color.gold()
        )
        if not leaderboard:
            embed.description = "No rep data found."
        else:
            for i, (user_id, pos) in enumerate(leaderboard, start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                embed.add_field(name=f"{i}. {name}", value=f"+{pos} rep", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="log", description="Set a channel for rep logs.")
    @app_commands.describe(channel="The channel to send rep logs to.")
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        config["log_channel"] = channel.id
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f)
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Rep logs will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rep(bot))
