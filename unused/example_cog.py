import discord
from discord.ext import commands
from discord import app_commands

class ExampleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("📝 Example cog loaded")

    @app_commands.command(name="example_log", description="Demonstrates how to use the logging system")
    async def example_log(self, interaction: discord.Interaction):
        logging_cog = self.bot.get_cog("LoggingSystem")
        if not logging_cog:
            await interaction.response.send_message("Logging system not available", ephemeral=True)
            return

        # Example 1: Simple message log
        await logging_cog.log_simple_message(
            f"📝 Example command used by {interaction.user.mention}"
        )

        # Example 2: Create a custom tracked log
        log_msg = await logging_cog.create_custom_log(
            identifier=f"example_{interaction.user.id}_{interaction.id}",
            title="🎯 Example Activity Log",
            description=f"Activity started by {interaction.user.mention}",
            color=discord.Color.purple(),
            fields={
                "Status": "🟡 In Progress",
                "Actions": "*No actions yet*"
            }
        )

        if log_msg:
            # Example 3: Update the custom log
            await logging_cog.update_custom_log(
                identifier=f"example_{interaction.user.id}_{interaction.id}",
                field_updates={"Status": "🟢 Completed"},
                event_additions={"Actions": f"Command executed by {interaction.user.mention}"}
            )

        await interaction.response.send_message(
            "✅ Example logging operations completed! Check your log channel.",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Example of using logging system in event listeners"""
        logging_cog = self.bot.get_cog("LoggingSystem")
        if logging_cog:
            embed = discord.Embed(
                title="👋 New Member Joined",
                description=f"{member.mention} ({member.display_name}) joined the server",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await logging_cog.log_simple_message("", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ExampleCog(bot))