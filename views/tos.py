"""Terms-of-service prompt shown when a new marketplace post is created."""
import asyncio
import time

import discord

from utils import db
from utils.config import load_config
from utils.interactions import SafeView
from utils.threads import close_thread, close_thread_for, update_thread_log
from views.review import post_review_ui

# If closing a timed-out post fails for a temporary reason, try again after this long
EXPIRY_RETRY_SECONDS = 60

# Maps thread.id → timestamp when the TOS prompt was sent. Messages posted
# after that are deleted until the prompt is answered. Mirrors the
# pending_tos table so on_message doesn't need a database query.
pending_tos_timestamps: dict[int, float] = {}

# Strong references to expiry tasks so they aren't garbage-collected
_expiry_tasks: set[asyncio.Task] = set()


def get_tos_timeout() -> int:
    return load_config()["tos_timeout_seconds"]


class RepTOSView(SafeView):
    """
    Persistent view: it carries no per-thread state, so one registered
    instance handles every prompt, including ones sent before a restart.
    """

    def __init__(self):
        super().__init__(timeout=None)

    async def _claim(self, interaction: discord.Interaction) -> discord.Thread | None:
        """Validate the click and mark the prompt answered. Returns the thread, or None if rejected."""
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return None

        if interaction.user.id != thread.owner_id:
            await interaction.response.send_message(
                "Only the thread owner can respond to the TOS.", ephemeral=True
            )
            return None

        if not db.resolve_pending_tos(thread.id):
            # Already answered or timed out
            await interaction.response.edit_message(content="⌛ This prompt has expired.", embed=None, view=None)
            return None

        pending_tos_timestamps.pop(thread.id, None)
        return thread

    @discord.ui.button(label='✅ I Agree', style=discord.ButtonStyle.success, custom_id="tos_agree")
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = await self._claim(interaction)
        if not thread:
            return

        await interaction.response.defer()
        await update_thread_log(
            interaction.client, thread,
            field_updates={"TOS Status": f"✅ Accepted at <t:{int(time.time())}:T>"}
        )

        # Remove the TOS prompt and proceed to the review UI
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass
        await post_review_ui(thread, thread.owner_id)

    @discord.ui.button(label='❌ I Do Not Agree', style=discord.ButtonStyle.danger, custom_id="tos_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = await self._claim(interaction)
        if not thread:
            return

        config = load_config()
        await interaction.response.edit_message(content=config["tos_decline_response"], embed=None, view=None)
        await update_thread_log(
            interaction.client, thread,
            field_updates={"TOS Status": f"❌ Declined at <t:{int(time.time())}:T>"}
        )
        await close_thread_for(interaction, thread, "❌ Closed (TOS declined)", None)


async def expire_tos(client: discord.Client, thread_id: int) -> None:
    """Close a thread whose TOS prompt was never answered."""
    owner_id = next((row["owner_id"] for row in db.get_pending_tos() if row["thread_id"] == thread_id), 0)
    if not db.resolve_pending_tos(thread_id):
        return  # Answered in the meantime
    pending_tos_timestamps.pop(thread_id, None)

    try:
        thread = client.get_channel(thread_id) or await client.fetch_channel(thread_id)
        print(f"[TOS] Thread {thread_id} timed out. Auto-closing.")
        await close_thread(
            client, thread, "❌ Closed (TOS timeout)",
            "⏱️ No response to TOS in time. This post has been auto-closed."
        )
    except (discord.NotFound, discord.Forbidden) as e:
        # Deleted, or we lack permission: retrying won't help
        print(f"[ERROR] Could not close thread {thread_id} after TOS timeout: {e}")
        if isinstance(e, discord.NotFound):
            db.mark_thread_closed(thread_id)
        return
    except discord.HTTPException as e:
        # Temporary Discord problem: keep the post gated and try again shortly
        print(f"[WARN] TOS timeout close failed for {thread_id} ({e}); retrying in {EXPIRY_RETRY_SECONDS}s")
        now = time.time()
        db.add_pending_tos(thread_id, owner_id, now, now + EXPIRY_RETRY_SECONDS)
        pending_tos_timestamps[thread_id] = now
        schedule_tos_expiry(client, thread_id, now + EXPIRY_RETRY_SECONDS)
        return

    await update_thread_log(
        client, thread,
        field_updates={"TOS Status": f"⌛ Timed out at <t:{int(time.time())}:T>"}
    )


def schedule_tos_expiry(client: discord.Client, thread_id: int, expires_at: float) -> None:
    async def wait_then_expire():
        await client.wait_until_ready()
        await asyncio.sleep(max(0.0, expires_at - time.time()))
        await expire_tos(client, thread_id)

    task = asyncio.create_task(wait_then_expire())
    _expiry_tasks.add(task)
    task.add_done_callback(_expiry_tasks.discard)


def restore_pending_tos(client: discord.Client) -> None:
    """Reload prompts that were pending when the bot stopped and re-arm their timeouts."""
    for row in db.get_pending_tos():
        pending_tos_timestamps[row["thread_id"]] = row["prompted_at"]
        schedule_tos_expiry(client, row["thread_id"], row["expires_at"])
