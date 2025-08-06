"""
web_integration.py

This cog is a placeholder for features that bridge the Discord bot
with an external web application. Planned capabilities include
OAuth-based account linking, item sales management, analytics
dashboards, and custom profile pages. Implementation of these
features will require a backend service and is outside the scope of
this demo.
"""

from __future__ import annotations

import discord
from discord.ext import commands


class WebIntegration(commands.Cog):
    """Cog scaffolding for web integration features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # No commands are currently implemented. All functionality lives on
    # the external website and will hook into this cog in the future.
    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WebIntegration(bot))