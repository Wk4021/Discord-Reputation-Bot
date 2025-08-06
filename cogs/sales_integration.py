"""
sales_integration.py

This cog adds commands for simple sales confirmation and logging. It
introduces a `/confirm_sale` slash command that sellers can use to
record a completed transaction with a buyer. Transactions are stored
in the `transactions` table via utils.db.log_transaction. Future
enhancements could include escrow management and multi-item threads.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import db


class SalesIntegration(commands.Cog):
    """Cog implementing basic sales confirmation features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="confirm_sale", description="Confirm a sale with a buyer and log it in the database")
    @app_commands.describe(buyer="The user who purchased your item", item="Optional description of the item sold")
    async def confirm_sale(self, interaction: discord.Interaction, buyer: discord.Member, item: str | None = None):
        """
        Confirm a sale. This command must be invoked by the seller within
        the marketplace thread where the transaction occurred. It records
        the sale in the `transactions` table and logs the event. A
        confirmation message is sent to both parties.
        """
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            return await interaction.response.send_message(
                "This command must be used inside the relevant thread.",
                ephemeral=True
            )
        seller_id = interaction.user.id
        buyer_id = buyer.id
        trans_id = db.log_transaction(
            thread_id=thread.id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            item_name=item,
            status="confirmed",
        )
        db.add_log(
            thread_id=thread.id,
            user_id=seller_id,
            action="SaleConfirmed",
            details=f"transaction_id={trans_id}, buyer={buyer_id}, item={item or ''}"
        )
        # Notify both seller and buyer privately
        await interaction.response.send_message(
            f"💼 Sale confirmed with {buyer.mention}! Transaction ID: {trans_id}.",
            ephemeral=True
        )
        try:
            await buyer.send(
                f"🧾 {interaction.user.display_name} has confirmed a sale with you in thread '{thread.name}'. Transaction ID: {trans_id}."
            )
        except Exception:
            # ignore if DM fails
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(SalesIntegration(bot))