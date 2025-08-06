"""
enhancements.py

This cog contains placeholder implementations for miscellaneous bot
enhancements such as reminder pings, feedback prompts, rep tags,
rate limiting, and silent post mode. These features are planned
future improvements and are currently stubbed out.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import db


class BotEnhancements(commands.Cog):
    """Cog scaffolding various bot enhancements."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="silentmode", description="Toggle silent post mode (placeholder)")
    async def silent_mode(self, interaction: discord.Interaction):
        """
        Toggle silent post mode for the invoking user. In the future
        this command will allow trusted sellers to bypass the TOS
        gating flow for faster posting.
        """
        await interaction.response.send_message(
            "🔕 Silent post mode is not yet implemented.",
            ephemeral=True
        )

    # ------------------------------------------------------------------
    # Rep Tagging
    #
    # After giving rep, users may optionally attach a descriptive tag
    # summarising the transaction (e.g. "Fast shipping", "Great
    # communication"). This command must be invoked within the thread
    # where the rep occurred. It records the tag in the database via
    # utils.db.add_rep_tag.
    @app_commands.command(name="addtag", description="Add a descriptive tag to your recent rep in this thread")
    @app_commands.describe(tag="A short description of the interaction (e.g. 'Fast shipping')")
    async def add_tag(self, interaction: discord.Interaction, tag: str):
        # Ensure command is invoked within a thread
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return await interaction.response.send_message(
                "This command must be used within a marketplace thread.",
                ephemeral=True
            )
        # Determine the receiver (thread owner) and record the tag
        receiver_id = thread.owner_id
        db.add_rep_tag(interaction.user.id, receiver_id, thread.id, tag)
        db.add_log(thread_id=thread.id, user_id=interaction.user.id, action="TagAdded", details=tag)
        await interaction.response.send_message(
            f"🏷️ Added tag '{tag}' for <@{receiver_id}>.",
            ephemeral=True
        )

    # ------------------------------------------------------------------
    # Feedback Messages
    #
    # Users may provide additional textual feedback about their
    # transaction. This command records the feedback in the logs. Like
    # addtag, it must be invoked within the relevant thread.
    @app_commands.command(name="feedback", description="Leave optional feedback about this transaction")
    @app_commands.describe(message="Your feedback message (max 200 characters)")
    async def feedback(self, interaction: discord.Interaction, message: str):
        if len(message) > 200:
            return await interaction.response.send_message(
                "Feedback message must be 200 characters or fewer.",
                ephemeral=True
            )
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return await interaction.response.send_message(
                "This command must be used within a marketplace thread.",
                ephemeral=True
            )
        db.add_log(thread_id=thread.id, user_id=interaction.user.id, action="Feedback", details=message)
        await interaction.response.send_message(
            "💬 Thank you for your feedback!",
            ephemeral=True
        )

    # Future placeholders: rate limiting, reminder pings, rep tags, feedback prompts
    # Additional commands and listeners will be added here when these features are implemented.


async def setup(bot: commands.Bot):
    await bot.add_cog(BotEnhancements(bot))