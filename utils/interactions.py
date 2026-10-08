"""Helpers for replying to interactions safely."""
import discord

GENERIC_ERROR = "❌ Something went wrong. Please try again."


async def reply_ephemeral(interaction: discord.Interaction, message: str) -> None:
    """
    Send a private reply whether or not the interaction was already answered.
    Never raises: the interaction may have expired by the time this runs.
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


async def report_error(interaction: discord.Interaction, error: Exception, where: str) -> None:
    """Log an unexpected error and tell the user something went wrong."""
    print(f"[ERROR] {where} failed: {error!r}")
    await reply_ephemeral(interaction, GENERIC_ERROR)


class SafeView(discord.ui.View):
    """View that tells the user when a button handler fails instead of showing "interaction failed"."""

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await report_error(interaction, error, f"{type(self).__name__} button")


class SafeModal(discord.ui.Modal):
    """Modal that tells the user when submitting fails."""

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await report_error(interaction, error, f"{type(self).__name__}")
