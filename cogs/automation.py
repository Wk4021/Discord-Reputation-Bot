"""
automation.py

This cog serves as a placeholder for intelligence and automation
features. Planned capabilities include advanced inactivity detection
that ignores low-quality bump messages, suggesting top sellers to
buyers, and validating thread titles. Currently, only a stub
command is provided.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import db


# Words or phrases that are not allowed in thread titles. These
# patterns are matched case-insensitively. Administrators can
# customise this list to suit their community's rules.
BANNED_TITLE_PATTERNS = [
    "scam",
    "fraud",
    "illegal",
    "stolen",
]


class IntelligenceAutomation(commands.Cog):
    """Cog implementing intelligence/automation features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Seller Suggestions
    #
    # This command returns a list of top sellers based on positive rep.
    # It leverages the rep_totals table to find the highest-rated
    # sellers and presents them as suggestions. This is a simple
    # heuristic; more advanced recommendations could factor in
    # category matching or recent activity.
    @app_commands.command(name="suggestsellers", description="Suggest top sellers based on rep history")
    async def suggest_sellers(self, interaction: discord.Interaction):
        top = db.get_top_positive_rep(limit=5)
        if not top:
            return await interaction.response.send_message(
                "No seller data available yet.",
                ephemeral=True
            )
        lines = ["Here are some top sellers based on positive rep:"]
        for rank, (user_id, pos) in enumerate(top, start=1):
            lines.append(f"{rank}. <@{user_id}> — {pos} positive rep")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    # ------------------------------------------------------------------
    # Thread Title Validation
    #
    # Listen for new thread creation and automatically close threads
    # whose titles contain banned patterns. This helps prevent
    # obviously fraudulent or prohibited listings.
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        # Skip if this is not a forum listed in config; the Rep cog
        # already filters for tracked forums. We'll perform a quick
        # banned-word check regardless.
        name_lower = thread.name.lower()
        for pattern in BANNED_TITLE_PATTERNS:
            if pattern in name_lower:
                try:
                    await thread.send(
                        f"🚫 Thread title contains a prohibited word ('{pattern}'). This thread has been closed.",
                    )
                    # Archive and lock the thread
                    await thread.edit(archived=True, locked=True)
                    # Log the rejection
                    db.add_log(
                        thread_id=thread.id,
                        user_id=thread.owner_id,
                        action="TitleRejected",
                        details=f"banned_word={pattern}"
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to close thread with banned title: {e}")
                break


async def setup(bot: commands.Bot):
    await bot.add_cog(IntelligenceAutomation(bot))