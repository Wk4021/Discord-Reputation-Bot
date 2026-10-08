"""In-thread review UI: review button, review modal, close flow and auto-close notice."""
import asyncio
import random
import time

import discord

from utils import db
from utils.checks import is_admin
from utils.config import load_config
from utils.formatting import generate_star_rating, review_stars, safe_inline
from utils.messages import load_rep_messages
from utils.interactions import SafeModal, SafeView
from utils.threads import close_thread_for, send_log, update_thread_log

DEFAULT_NO_REP_MESSAGE = "No reviews yet. Be the first!"
IMAGE_EXTENSIONS = (".gif", ".png", ".jpg", ".jpeg", ".webp")
# Discord allows 3 seconds before the first response (here: the review modal)
HISTORY_CHECK_TIMEOUT = 2.0


def is_thread_closed(thread: discord.abc.GuildChannel) -> bool:
    """
    True if the post has been closed. Buttons in closed threads still fire
    interactions, so every review/close action must check this.

    Closed means locked: Discord also archives quiet posts on its own, and
    those must stay usable. The database copy is kept in sync by
    on_thread_update, so a post a moderator unlocks becomes usable again.
    """
    locked = getattr(thread, "locked", None)
    if isinstance(locked, bool):
        # Discord's live state, sent with every interaction: trust it
        return locked
    info = db.get_thread_info(thread.id)
    return bool(info and info["locked"])


async def _reject_if_not_open_thread(interaction: discord.Interaction) -> bool:
    """Reply and return True if this interaction isn't in an open forum post."""
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("❌ This only works inside a forum post.", ephemeral=True)
        return True
    if is_thread_closed(interaction.channel):
        await interaction.response.send_message("🔒 This post is closed.", ephemeral=True)
        return True
    return False


def _ensure_thread_tracked(thread: discord.Thread) -> None:
    """Make sure the thread has a database row (posts made before the bot joined may not)."""
    if db.get_thread_info(thread.id) is None:
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


class AutoCloseView(SafeView):
    """Persistent view: the thread comes from the interaction, so it works after restarts."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="cancel_auto_close", label="I have multiple items - Keep thread open",
                       style=discord.ButtonStyle.secondary)
    async def cancel_auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _reject_if_not_open_thread(interaction):
            return
        thread: discord.Thread = interaction.channel

        # Only the thread owner can cancel auto-close
        if interaction.user.id != thread.owner_id:
            return await interaction.response.send_message(
                "Only the thread owner can cancel auto-close.", ephemeral=True
            )

        db.cancel_thread_auto_close(thread.id)

        embed = discord.Embed(
            title="🔓 Auto-close Cancelled",
            description="This thread will no longer be automatically closed. You can close it manually when ready.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

        log_embed = discord.Embed(
            title="🔓 Auto-Close Cancelled",
            description=f"{interaction.user.mention} cancelled auto-close for {thread.mention}",
            color=discord.Color.green()
        )
        log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
        log_embed.add_field(name="Reason", value="Multiple items in listing", inline=True)
        await send_log(interaction.client, log_embed)

        print(f"[AUTO-CLOSE] {interaction.user} cancelled auto-close for thread {thread.id} ({thread.name})")


class ReviewModal(SafeModal):
    def __init__(self, thread: discord.Thread, receiver_id: int, panel_message: discord.Message | None = None):
        super().__init__(title="Leave a Review")
        self.thread = thread
        self.receiver_id = receiver_id
        # The review panel the button was clicked on; refreshed in place after the review
        self.panel_message = panel_message

        self.rating = discord.ui.TextInput(
            label="Rating (1-10)",
            placeholder="Enter a number between 1 and 10",
            required=True,
            max_length=2
        )
        self.add_item(self.rating)

        self.notes = discord.ui.TextInput(
            label="Review Notes (Optional)",
            placeholder="Share your experience... (optional)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        # The post may have been closed while the modal was open; the
        # submit interaction carries the thread's current state
        if is_thread_closed(interaction.channel or self.thread):
            return await interaction.response.send_message("🔒 This post is closed.", ephemeral=True)

        try:
            rating_value = int(self.rating.value)
            if not (1 <= rating_value <= 10):
                raise ValueError("Rating must be between 1 and 10")
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid rating between 1 and 10.",
                ephemeral=True
            )
            return

        notes_value = self.notes.value.strip() or None

        success = db.add_review(
            interaction.user.id,
            self.receiver_id,
            self.thread.id,
            rating_value,
            notes_value
        )
        if not success:
            await interaction.response.send_message(
                "❌ You've already reviewed this user in this thread.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="✅ Review Submitted",
            description=(
                f"{interaction.user.mention} gave a **{rating_value}/10** rating "
                f"to <@{self.receiver_id}> in [this thread]({self.thread.jump_url})"
            ),
            color=discord.Color.green()
        )
        if notes_value:
            embed.add_field(name="Review Notes", value=safe_inline(notes_value, 100), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Notify the thread owner; the first review also starts the auto-close timer
        mention_message = f"<@{self.receiver_id}> You received a **{rating_value}/10** review!"
        config = load_config()
        auto_close_hours = config["auto_close_hours"]
        close_time = time.time() + auto_close_hours * 60 * 60

        # Posts made before the bot joined have no row yet; the log and auto-close need one
        _ensure_thread_tracked(self.thread)
        scheduled = False
        if config["auto_close_enabled"]:
            scheduled = db.schedule_thread_auto_close(self.thread.id, close_time)

        if scheduled:
            auto_close_embed = discord.Embed(
                title="⏰ Auto-Close Scheduled",
                description=f"This thread will automatically close <t:{int(close_time)}:R> unless you cancel it below.",
                color=discord.Color.orange()
            )
            auto_close_embed.add_field(
                name="Why?",
                value=(
                    "Threads auto-close after the first review to keep the marketplace clean. "
                    "If you have multiple items in this listing, click the button below."
                ),
                inline=False
            )
            await self.thread.send(content=mention_message, embed=auto_close_embed, view=AutoCloseView())

            log_embed = discord.Embed(
                title="⏰ Auto-Close Scheduled",
                description=(
                    f"Thread {self.thread.mention} "
                    f"scheduled to auto-close <t:{int(close_time)}:R>"
                ),
                color=discord.Color.orange()
            )
            log_embed.add_field(name="Thread Owner", value=f"<@{self.receiver_id}>", inline=True)
            log_embed.add_field(name="Trigger", value="First review received", inline=True)
            log_embed.add_field(name="Timer", value=f"{auto_close_hours} hours", inline=True)
            await send_log(interaction.client, log_embed)

            print(f"[AUTO-CLOSE] Scheduled thread {self.thread.id} ({self.thread.name}) to close in {auto_close_hours} hours")
        else:
            await self.thread.send(content=mention_message)

        await update_thread_log(
            interaction.client, self.thread,
            event_additions={"Review Events": f"{interaction.user.mention} gave {rating_value}/10 rating"}
        )
        await send_log(interaction.client, embed)

        # Refresh the review panel in place instead of posting a new one each time
        panel_embed = build_review_panel(self.receiver_id)
        if self.panel_message:
            try:
                await self.panel_message.edit(embed=panel_embed, view=ReviewButtonView())
                return
            except discord.HTTPException:
                pass  # Deleted or not editable; post a fresh one
        await self.thread.send(embed=panel_embed, view=ReviewButtonView())


class CloseConfirmationModal(SafeModal):
    def __init__(self, thread: discord.Thread):
        super().__init__(title="Close Post Confirmation")
        self.thread = thread

        self.confirmation = discord.ui.TextInput(
            label="Type 'Yes' to confirm closing without reviews",
            placeholder="Yes",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmation)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().lower() != "yes":
            await interaction.response.send_message(
                "❌ Post closure cancelled. You must type 'Yes' to confirm.",
                ephemeral=True
            )
            return

        # Someone may have closed it while the modal was open
        if is_thread_closed(interaction.channel or self.thread):
            return await interaction.response.send_message("🔒 This post is already closed.", ephemeral=True)

        await close_thread_for(
            interaction, self.thread, "❌ Closed without reviews",
            "🔒 This thread is now closed by its creator (no reviews received)."
        )


class AdminCloseConfirmationModal(SafeModal):
    def __init__(self, thread: discord.Thread, admin_user: discord.Member):
        super().__init__(title="Admin Close Post Confirmation")
        self.thread = thread
        self.admin_user = admin_user

        self.confirmation = discord.ui.TextInput(
            label="Type 'Yes' to confirm admin closure",
            placeholder="Yes",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmation)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().lower() != "yes":
            await interaction.response.send_message(
                "❌ Admin closure cancelled. You must type 'Yes' to confirm.",
                ephemeral=True
            )
            return

        if is_thread_closed(interaction.channel or self.thread):
            return await interaction.response.send_message("🔒 This post is already closed.", ephemeral=True)

        await admin_close(interaction, self.thread, self.admin_user)


async def admin_close(interaction: discord.Interaction, thread: discord.Thread, admin_user: discord.Member) -> None:
    """Force-close a thread on behalf of an admin and log it."""
    closed = await close_thread_for(
        interaction, thread, f"❌ Force closed by admin {admin_user.mention}",
        f"🔒 This thread has been closed by admin {admin_user.mention}."
    )
    if not closed:
        return
    client = interaction.client

    log_embed = discord.Embed(
        title="🔒 Admin Force Close",
        description=f"{admin_user.mention} force-closed thread {thread.mention}",
        color=discord.Color.red()
    )
    log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
    log_embed.add_field(name="Action", value="Force closed by admin", inline=True)
    await send_log(client, log_embed)

    print(f"[ADMIN-CLOSE] {admin_user} force-closed thread {thread.id} ({thread.name})")


def build_review_panel(op_id: int) -> discord.Embed:
    """Build the review panel embed summarising the thread owner's reputation."""
    config = load_config()
    rep_msgs = load_rep_messages()
    no_rep_lines = config["no_rep_messages"] or [DEFAULT_NO_REP_MESSAGE]

    avg_rating, total_reviews, latest_reviews = db.get_user_reviews(op_id)
    gif_url = None

    if total_reviews == 0:
        content = f"😶 {random.choice(no_rep_lines)}"
    else:
        # Pick a flavour line based on the average rating
        if avg_rating >= 7.0:
            pool = rep_msgs["good"]
        elif avg_rating <= 4.0:
            pool = rep_msgs["bad"]
        else:
            pool = rep_msgs["neutral"]

        raw = random.choice(pool) if pool else ""
        # A trailing image URL (see IMAGE_EXTENSIONS) is shown as the embed image
        parts = raw.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].lower().endswith(IMAGE_EXTENSIONS):
            content, gif_url = parts[0], parts[1]
        else:
            content = raw

        content = f"📊 {generate_star_rating(avg_rating, total_reviews)}\n\n{content}"

    embed = discord.Embed(description=content, color=discord.Color.green())
    if gif_url:
        embed.set_image(url=gif_url)

    if latest_reviews:
        reviews_text = ""
        for review in latest_reviews[:3]:
            reviews_text += f"**{review_stars(review['rating'])} {review['rating']}/10** by <@{review['giver_id']}>"
            if review['notes']:
                reviews_text += f"\n> {safe_inline(review['notes'], 50)}"
            reviews_text += "\n\n"

        embed.add_field(name="📝 Latest Reviews", value=reviews_text.strip(), inline=False)

    return embed


async def post_review_ui(thread: discord.Thread, op_id: int):
    """Post a new review panel (with Leave a Review / Close Post buttons) in the thread."""
    await thread.send(embed=build_review_panel(op_id), view=ReviewButtonView())


async def _has_spoken_in(thread: discord.Thread, user_id: int) -> bool:
    """True if the user has posted in the thread."""
    if db.has_participated(thread.id, user_id):
        return True

    # Messages from before participation tracking existed: check recent
    # history, but never so long that the review modal can't be shown in time
    async def search_history() -> bool:
        async for msg in thread.history(limit=100):
            if msg.author.id == user_id:
                return True
        return False

    try:
        found = await asyncio.wait_for(search_history(), HISTORY_CHECK_TIMEOUT)
    except (asyncio.TimeoutError, discord.HTTPException):
        return False
    if found:
        db.add_thread_participant(thread.id, user_id)
    return found


class ReviewButtonView(SafeView):
    def __init__(self):
        # persistent across restarts
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="leave_review", label="⭐ Leave a Review", style=discord.ButtonStyle.primary)
    async def leave_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _reject_if_not_open_thread(interaction):
            return
        thread: discord.Thread = interaction.channel
        op_id = thread.owner_id

        # 1) Prevent self-review
        if interaction.user.id == op_id:
            return await interaction.response.send_message(
                "You can't review yourself.", ephemeral=True
            )

        # 2) Check if already reviewed
        if db.has_user_reviewed(interaction.user.id, op_id, thread.id):
            return await interaction.response.send_message(
                "You've already reviewed this user in this thread.", ephemeral=True
            )

        # 3) Require the user to have spoken in the thread
        if not await _has_spoken_in(thread, interaction.user.id):
            return await interaction.response.send_message(
                "You need to interact in the thread first before leaving a review.", ephemeral=True
            )

        # 4) Show the review modal
        await interaction.response.send_modal(ReviewModal(thread, op_id, interaction.message))

    @discord.ui.button(custom_id="close_post", label="Close Post", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _reject_if_not_open_thread(interaction):
            return
        thread: discord.Thread = interaction.channel
        op_id = thread.owner_id

        is_owner = interaction.user.id == op_id
        is_user_admin = is_admin(interaction.user)

        # 1) Only the OP or admins may close
        if not is_owner and not is_user_admin:
            return await interaction.response.send_message(
                "Only the thread creator or admins can close this post.", ephemeral=True
            )

        # 2) Admins closing someone else's post
        if is_user_admin and not is_owner:
            if load_config()["admin_close_confirmation"]:
                await interaction.response.send_modal(AdminCloseConfirmationModal(thread, interaction.user))
            else:
                await admin_close(interaction, thread, interaction.user)
            return

        # 3) The owner must confirm closing a post nobody reviewed
        if db.count_thread_reviews(thread.id, exclude_giver_id=op_id) == 0:
            await interaction.response.send_modal(CloseConfirmationModal(thread))
            return

        # 4) Owner closing a reviewed post
        await close_thread_for(interaction, thread, "❌ Closed", "🔒 This thread is now closed by its creator.")
