"""Review cog: forum post lifecycle, review lookups and the auto-close task."""
import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import db
from utils.checks import admin_only
from utils.config import get_forum_ids, load_config
from utils.formatting import generate_star_rating, review_stars, safe_inline, star_bar
from utils.threads import close_thread, send_log
from views.review import AutoCloseView, ReviewButtonView, post_review_ui
from views.tos import (RepTOSView, get_tos_timeout, pending_tos_timestamps,
                       restore_pending_tos, schedule_tos_expiry)


class Reviews(commands.Cog):
    """Forum post lifecycle, review commands and the auto-close background task."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("🔧 Reviews cog loaded")

    async def cog_load(self):
        """Start background work when the cog loads"""
        self.auto_close_task.start()
        # Re-arm TOS prompts that were still waiting when the bot last stopped
        restore_pending_tos(self.bot)

    async def cog_unload(self):
        """Stop background tasks when the cog unloads"""
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)  # Check every 10 minutes
    async def auto_close_task(self):
        """Background task to auto-close threads that have passed their scheduled time"""
        try:
            threads_to_close = db.get_threads_to_auto_close()
        except Exception as e:
            print(f"[ERROR] Auto-close task failed: {e}")
            return

        if threads_to_close:
            print(f"[AUTO-CLOSE] Found {len(threads_to_close)} thread(s) ready for auto-close")

        for thread_data in threads_to_close:
            try:
                await self._auto_close(thread_data['thread_id'])
            except Exception as e:
                print(f"[ERROR] Failed to auto-close thread {thread_data['thread_id']}: {e}")

    async def _auto_close(self, thread_id: int):
        # The owner may have cancelled (or someone closed it) since the list was read
        if not db.is_auto_close_due(thread_id):
            return

        # get_channel only sees cached (active) threads; fetch finds archived ones too
        try:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
        except (discord.NotFound, discord.Forbidden):
            # Deleted or no longer visible; stop retrying every 10 minutes
            db.mark_thread_closed(thread_id)
            print(f"[AUTO-CLOSE] Thread {thread_id} no longer accessible; marked closed")
            return

        embed = discord.Embed(
            title="🔒 Thread Auto-Closed",
            description="This thread was automatically closed after receiving its first review.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Why did this happen?",
            value=(
                "To keep the marketplace clean, threads automatically close after receiving reviews. "
                "This helps prevent clutter from completed transactions."
            ),
            inline=False
        )
        # Locks before posting the notice, so a failure (e.g. missing Manage
        # Threads) can't make the notice repeat every 10 minutes
        await close_thread(self.bot, thread, "🤖 Auto-closed", embed)

        log_embed = discord.Embed(
            title="🤖 Thread Auto-Closed",
            description=f"Thread {thread.mention} was automatically closed",
            color=discord.Color.red()
        )
        log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
        log_embed.add_field(name="Reason", value="Auto-close timer expired", inline=True)
        log_embed.add_field(name="Action", value="Archived & Locked", inline=True)
        await send_log(self.bot, log_embed)

        print(f"[AUTO-CLOSE] Successfully closed thread {thread.id} ({thread.name})")

    @auto_close_task.before_loop
    async def before_auto_close_task(self):
        """Wait until the bot is ready before starting the auto-close task"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            if thread.parent_id not in get_forum_ids(config):
                return

            db.upsert_thread(
                thread_id=thread.id,
                channel_id=thread.parent_id,
                guild_id=thread.guild.id,
                name=thread.name,
                owner_id=thread.owner_id,
                jump_url=thread.jump_url,
                archived=thread.archived,
                locked=thread.locked
            )
            db.add_thread_participant(thread.id, thread.owner_id)

            # Join so the bot can send
            try:
                await thread.join()
            except discord.HTTPException:
                pass

            # Give Discord a moment to finish creating the post before replying
            await asyncio.sleep(2)

            timeout_secs = get_tos_timeout()
            prompted_at = time.time()
            expires_at = prompted_at + timeout_secs
            tos_message_text = config["tos_message"].replace("{timeout}", f"<t:{int(expires_at)}:R>")[:4096]

            embed = discord.Embed(
                title="📋 Marketplace Terms of Service",
                description=tos_message_text,
                color=discord.Color.blue()
            )

            # Record the prompt before sending so messages can't slip through
            db.add_pending_tos(thread.id, thread.owner_id, prompted_at, expires_at)
            pending_tos_timestamps[thread.id] = prompted_at
            try:
                await thread.send(content=f"<@{thread.owner_id}>", embed=embed, view=RepTOSView())
            except discord.HTTPException:
                # No prompt was shown, so don't hold the thread hostage
                db.resolve_pending_tos(thread.id)
                pending_tos_timestamps.pop(thread.id, None)
                raise
            schedule_tos_expiry(self.bot, thread.id, expires_at)

            logging_cog = self.bot.get_cog("LoggingSystem")
            if logging_cog:
                await logging_cog.create_thread_log(
                    thread,
                    fields={
                        "TOS Status": "⏳ Pending",
                        "Review Events": "*No events yet*",
                        "Thread Status": "✅ Open"
                    }
                )

        except Exception as e:
            print(f"[ERROR] on_thread_create: {e}")

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent):
        # Keep the stored state in step with Discord, e.g. when a moderator
        # reopens a post the bot closed. The raw event is used because
        # on_thread_update never fires for archived (uncached) threads.
        metadata = payload.data.get("thread_metadata") or {}
        if "locked" in metadata and "archived" in metadata:
            db.set_thread_state(payload.thread_id, archived=metadata["archived"], locked=metadata["locked"])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.Thread):
            return

        # Delete user messages posted after the TOS prompt until it's answered
        ts = pending_tos_timestamps.get(message.channel.id)
        if ts and message.created_at.timestamp() > ts:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            return

        # Remember who has taken part, so they're allowed to leave a review
        if message.channel.parent_id in get_forum_ids(load_config()):
            db.add_thread_participant(message.channel.id, message.author.id)

    @app_commands.command(name="reviews", description="Check a user's reviews and rating.")
    @app_commands.guild_only()
    @app_commands.describe(user="The user to check reviews for.")
    async def reviews_lookup(self, interaction: discord.Interaction, user: discord.User):
        avg_rating, total_reviews, latest_reviews = db.get_user_reviews(user.id)

        embed = discord.Embed(
            title=f"⭐ Reviews for {user.display_name}",
            color=discord.Color.blue()
        )

        if total_reviews == 0:
            embed.description = "😶 No reviews yet. Time to build that reputation!"
            embed.add_field(name="Rating", value="No rating yet", inline=True)
            embed.add_field(name="Total Reviews", value="0", inline=True)
        else:
            embed.description = generate_star_rating(avg_rating, total_reviews)
            embed.add_field(name="Average Rating", value=f"{avg_rating:.1f}/10", inline=True)
            embed.add_field(name="Total Reviews", value=str(total_reviews), inline=True)

            if latest_reviews:
                entries = []
                for review in latest_reviews:
                    entry = f"**{review_stars(review['rating'])} {review['rating']}/10** by <@{review['giver_id']}>"
                    if review['notes']:
                        entry += f"\n> {safe_inline(review['notes'], 80)}"
                    entries.append(entry)
                embed.add_field(name="Latest Reviews", value="\n\n".join(entries), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 users by rating.")
    @app_commands.guild_only()
    async def review_leaderboard(self, interaction: discord.Interaction):
        top = db.get_top_rated_users(limit=10)
        embed = discord.Embed(
            title="🏆 Top Rated Users",
            description="Here are the highest rated users:",
            color=discord.Color.gold()
        )
        if not top:
            embed.description = "No review data found."
        else:
            for i, (user_id, avg_rating, total_reviews) in enumerate(top, start=1):
                member = interaction.guild.get_member(user_id)
                # Mentions don't render in field names, so the mention goes in the value
                name = member.display_name if member else "Former member"
                embed.add_field(
                    name=f"{i}. {name}",
                    value=(
                        f"<@{user_id}> • {star_bar(avg_rating)} {avg_rating:.1f}/10 "
                        f"({total_reviews} review{'s' if total_reviews != 1 else ''})"
                    ),
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="send_review_ui",
                          description="Send the rate/close interface to the current thread (admin only).")
    @app_commands.guild_only()
    @admin_only()
    async def send_review_ui(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ This command can only be used in a thread.", ephemeral=True
            )
            return

        # Respond first: posting the panel can take longer than Discord's 3-second limit
        await interaction.response.send_message("✅ Rate/close interface sent to this thread.", ephemeral=True)
        await post_review_ui(interaction.channel, interaction.channel.owner_id)


async def setup(bot: commands.Bot):
    # Persistent views keep buttons working after a restart
    bot.add_view(ReviewButtonView())
    bot.add_view(AutoCloseView())
    bot.add_view(RepTOSView())
    await bot.add_cog(Reviews(bot))
