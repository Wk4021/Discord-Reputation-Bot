"""
moderation.py

This cog lays the groundwork for moderation and trust-related
functionality. It currently contains placeholder implementations for
features such as strike appeals and trust score calculation. When
fully implemented, this cog will handle reputation decay, fraud
detection, and other moderation tools.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import db
import sqlite3


class Moderation(commands.Cog):
    """Cog implementing moderation & trust system features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Strike Appeals
    #
    # Users can submit an appeal for a strike they've received. The
    # appeal will be logged in the database with a pending status. Mods
    # can later review appeals and update their status via a separate
    # moderation interface or DB call.
    @app_commands.command(name="appealstrike", description="Submit an appeal for a strike you have received")
    @app_commands.describe(reason="Explain why you believe your strike should be removed")
    async def appeal_strike(self, interaction: discord.Interaction, reason: str):
        """
        Create a strike appeal. The user must provide a reason. The
        appeal is stored in the database with a pending status. A
        confirmation message with the appeal ID is returned.
        """
        appeal_id = db.submit_strike_appeal(interaction.user.id, reason)
        # log this action
        db.add_log(None, interaction.user.id, "strike_appeal_submitted", f"appeal_id={appeal_id}")
        await interaction.response.send_message(
            f"✅ Your strike appeal has been submitted (ID: {appeal_id}). A moderator will review it shortly.",
            ephemeral=True
        )

    # ------------------------------------------------------------------
    # Trust Score
    #
    # The trust score aggregates a user's rep, warning/strike counts,
    # and future metrics to give a snapshot of their reliability. For
    # now it simply computes positive minus negative rep and subtracts
    # points for each strike.
    @app_commands.command(name="trustscore", description="View a user's trust score")
    @app_commands.describe(user="The user whose trust score you want to view")
    async def trust_score(self, interaction: discord.Interaction, user: discord.Member):
        """
        Compute a simple trust score: (positive - negative) - (strikes * 5).
        This is a placeholder metric that will evolve over time. The
        command displays the breakdown and the resulting score.
        """
        pos, neg = db.get_user_rep(user.id)
        warnings, strikes = db.get_user_strikes(user.id)
        score = (pos - neg) - (strikes * 5)
        embed = discord.Embed(title=f"Trust Score for {user.display_name}", colour=discord.Colour.blue())
        embed.add_field(name="Positive Rep", value=str(pos), inline=True)
        embed.add_field(name="Negative Rep", value=str(neg), inline=True)
        embed.add_field(name="Warnings", value=str(warnings), inline=True)
        embed.add_field(name="Strikes", value=str(strikes), inline=True)
        embed.add_field(name="Score", value=str(score), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # Fraud Detection
    #
    # A simple fraud detection command that flags users who receive
    # multiple reps from the same giver in a short time or have large
    # positive deltas. This is a naive implementation to demonstrate
    # the concept; more sophisticated analysis should be performed
    # offline or in a separate service.
    @app_commands.command(name="fraudcheck", description="Flag suspicious rep patterns for a user")
    @app_commands.describe(user="Optional: specific user to check (defaults to all)")
    async def fraud_check(self, interaction: discord.Interaction, user: discord.Member | None = None):
        """
        Check for suspicious rep patterns. If a user is specified, only
        that user is analysed. Otherwise, the bot performs a simple
        scan across all users and reports those with potential fraud.
        """
        conn = sqlite3.connect(db.DB_PATH)
        c = conn.cursor()
        report_lines = []
        if user:
            # Count how many reps each giver has given this receiver
            c.execute(
                "SELECT giver_id, COUNT(*) FROM rep WHERE receiver_id = ? GROUP BY giver_id HAVING COUNT(*) > 1",
                (user.id,),
            )
            suspicious = c.fetchall()
            if suspicious:
                report_lines.append(f"User {user.display_name} has multiple reps from the same giver:")
                for giver_id, count in suspicious:
                    report_lines.append(f"- {giver_id} -> {count} reps")
            else:
                report_lines.append(f"No suspicious patterns found for {user.display_name}.")
        else:
            # Check all receivers for repeated givers
            c.execute(
                "SELECT receiver_id, giver_id, COUNT(*) FROM rep GROUP BY receiver_id, giver_id HAVING COUNT(*) > 2"
            )
            rows = c.fetchall()
            if rows:
                report_lines.append("Users with multiple reps from the same giver:")
                for receiver_id, giver_id, count in rows:
                    report_lines.append(f"- Receiver {receiver_id} from Giver {giver_id}: {count} reps")
            else:
                report_lines.append("No suspicious patterns found.")
        conn.close()
        await interaction.response.send_message("\n".join(report_lines), ephemeral=True)

    # ------------------------------------------------------------------
    # Strike & Warning Status
    #
    @app_commands.command(name="strikeinfo", description="View warnings and strikes for a user")
    @app_commands.describe(user="The user whose strike status you want to view")
    async def strike_info(self, interaction: discord.Interaction, user: discord.Member):
        """
        Display the number of warnings and strikes a user has accumulated.
        """
        warnings, strikes = db.get_user_strikes(user.id)
        await interaction.response.send_message(
            f"{user.display_name} has {warnings} warning(s) and {strikes} strike(s).",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))