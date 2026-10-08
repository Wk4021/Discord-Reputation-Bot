"""Admin cog: configuration and admin-management slash commands."""
import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only, is_admin
from utils.config import list_append, list_remove, load_config, save_config
from utils.formatting import capped_lines
from utils.threads import send_log
from views.settings import SettingsView


ADMIN_LIST_INTRO = "Server administrators are always admins. Also configured:"


async def log_admin_action(interaction: discord.Interaction, title: str, description: str,
                           color: discord.Color = discord.Color.blue()) -> None:
    """Record a configuration change in the log channel."""
    await send_log(interaction.client, discord.Embed(
        title=title,
        description=f"{interaction.user.mention} {description}",
        color=color
    ))


class Admin(commands.Cog):
    """Configuration and admin-management slash commands."""

    @app_commands.command(name="channel_set", description="Add a forum channel for tracking reps (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(channel="Forum channel to activate rep tracking on.")
    async def channel_set(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        config = load_config()
        if channel.id in config["forums"]:
            return await interaction.response.send_message("This channel is already tracked.", ephemeral=True)

        list_append(config, "forums", channel.id)
        save_config(config)
        await interaction.response.send_message(f"✅ Channel {channel.mention} added to rep tracking.", ephemeral=True)
        await log_admin_action(interaction, "📁 Forum Added", f"added {channel.mention} to rep tracking")

    @app_commands.command(name="log", description="Set a channel for review logs (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(channel="The channel to send review logs to.")
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        old_channel = config["log_channel"]
        config["log_channel"] = channel.id
        save_config(config)

        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Review logs will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Announce in both channels so a redirect can't go unnoticed
        description = f"moved the log channel from {f'<#{old_channel}>' if old_channel else 'nowhere'} to {channel.mention}"
        await log_admin_action(interaction, "📝 Log Channel Changed", description)
        if old_channel and old_channel != channel.id:
            old = interaction.client.get_channel(old_channel)
            if old:
                try:
                    await old.send(embed=discord.Embed(
                        title="📝 Log Channel Changed",
                        description=f"{interaction.user.mention} {description}",
                        color=discord.Color.blue()
                    ))
                except discord.HTTPException:
                    pass

    @app_commands.command(name="admin_add", description="Add a user as admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(user="The user to add as admin.")
    async def admin_add(self, interaction: discord.Interaction, user: discord.Member):
        if user.bot:
            return await interaction.response.send_message("❌ Bots can't be admins.", ephemeral=True)

        config = load_config()
        if user.id in config["admin_ids"]:
            return await interaction.response.send_message(
                f"{user.mention} is already in the admin list.", ephemeral=True
            )

        list_append(config, "admin_ids", user.id)
        save_config(config)

        embed = discord.Embed(
            title="✅ Admin Added",
            description=f"{user.mention} has been added as an admin.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_admin_action(interaction, "👑 Admin Added", f"made {user.mention} an admin", discord.Color.green())

    @app_commands.command(name="admin_remove", description="Remove a user from admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(user="The user to remove from admin (works for people who left the server).")
    async def admin_remove(self, interaction: discord.Interaction, user: discord.User):
        config = load_config()
        admin_ids = config["admin_ids"]

        if user.id not in admin_ids:
            return await interaction.response.send_message(
                f"{user.mention} isn't in the admin list. Admin rights from a role or the "
                "server Administrator permission can't be removed here.",
                ephemeral=True
            )

        # Don't allow self-removal if only admin
        if user.id == interaction.user.id and len(admin_ids) == 1:
            return await interaction.response.send_message(
                "❌ Cannot remove yourself as the last admin.", ephemeral=True
            )

        list_remove(config, "admin_ids", user.id)
        save_config(config)

        description = f"{user.mention} has been removed from the admin list."
        # They may still be an admin through a role or the Administrator permission
        member = interaction.guild.get_member(user.id)
        if member and is_admin(member):
            description += "\n⚠️ They are still an admin through a role or the Administrator permission."

        embed = discord.Embed(title="✅ Admin Removed", description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_admin_action(interaction, "👑 Admin Removed", f"removed {user.mention} from the admin list",
                               discord.Color.orange())

    @app_commands.command(name="admin_list", description="List all admins (admin only).")
    @app_commands.guild_only()
    @admin_only()
    async def admin_list(self, interaction: discord.Interaction):
        config = load_config()
        admin_ids = config["admin_ids"]
        admin_role_ids = config["admin_role_ids"]

        embed = discord.Embed(
            title="👑 Admin List",
            description=ADMIN_LIST_INTRO if config["guild_id"] else "Configured admins:",
            color=discord.Color.purple()
        )

        if not admin_ids and not admin_role_ids:
            embed.description = (
                "Only server administrators are admins; no other users or roles are configured."
                if config["guild_id"] else
                "⚠️ No admins configured, and guild_id isn't set. Add admin_ids or guild_id to data/config.yaml."
            )

        if admin_ids:
            lines = []
            for admin_id in admin_ids:
                member = interaction.guild.get_member(admin_id)
                lines.append(f"• {member.mention} ({member.display_name})" if member else f"• <@{admin_id}> (ID: {admin_id})")
            embed.add_field(name=f"Admin Users ({len(admin_ids)})", value=capped_lines(lines), inline=False)

        if admin_role_ids:
            lines = []
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(role_id)
                lines.append(f"• {role.mention} ({role.name})" if role else f"• <@&{role_id}> (ID: {role_id})")
            embed.add_field(name=f"Admin Roles ({len(admin_role_ids)})", value=capped_lines(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_role_add", description="Add a role as admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(role="The role to add as admin.")
    async def admin_role_add(self, interaction: discord.Interaction, role: discord.Role):
        # @everyone would make every member an admin; bot/integration roles are
        # managed by Discord and not meant for people
        if role.is_default() or role.managed:
            return await interaction.response.send_message(
                "❌ That role can't be an admin role.", ephemeral=True
            )

        config = load_config()
        if role.id in config["admin_role_ids"]:
            return await interaction.response.send_message(
                f"{role.mention} is already an admin role.", ephemeral=True
            )

        list_append(config, "admin_role_ids", role.id)
        save_config(config)

        embed = discord.Embed(
            title="✅ Admin Role Added",
            description=f"{role.mention} has been added as an admin role.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_admin_action(interaction, "👑 Admin Role Added", f"made {role.mention} an admin role",
                               discord.Color.green())

    @app_commands.command(name="admin_role_remove", description="Remove a role from admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(role="The role to remove from admin.")
    async def admin_role_remove(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        if role.id not in config["admin_role_ids"]:
            return await interaction.response.send_message(
                f"{role.mention} is not an admin role.", ephemeral=True
            )

        list_remove(config, "admin_role_ids", role.id)
        save_config(config)

        embed = discord.Embed(
            title="✅ Admin Role Removed",
            description=f"{role.mention} has been removed from admin roles.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_admin_action(interaction, "👑 Admin Role Removed", f"removed {role.mention} from admin roles",
                               discord.Color.orange())

    @app_commands.command(name="auto_close_toggle", description="Toggle the auto-close feature on/off (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(enabled="Enable or disable auto-close feature")
    async def auto_close_toggle(self, interaction: discord.Interaction, enabled: bool | None = None):
        config = load_config()

        # If no parameter provided, show current status
        if enabled is None:
            embed = discord.Embed(
                title="⚙️ Auto-Close Settings",
                description=f"**Status:** {'✅ Enabled' if config['auto_close_enabled'] else '❌ Disabled'}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Auto-Close Timer", value=f"{config['auto_close_hours']} hours", inline=True)
            embed.add_field(name="Usage", value="Use `/auto_close_toggle true/false` to change", inline=False)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        old_status = config["auto_close_enabled"]
        config["auto_close_enabled"] = enabled
        save_config(config)

        status_text = "✅ Enabled" if enabled else "❌ Disabled"
        color = discord.Color.green() if enabled else discord.Color.red()

        embed = discord.Embed(
            title="⚙️ Auto-Close Setting Updated",
            description=f"Auto-close feature is now **{status_text}**",
            color=color
        )
        if enabled:
            embed.add_field(
                name="Timer",
                value=f"Threads will auto-close {config['auto_close_hours']} hours after first review",
                inline=False
            )
        else:
            embed.add_field(
                name="Note",
                value="Existing scheduled auto-closes will still occur unless manually cancelled",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(
            title="🔧 Auto-Close Setting Changed",
            description=f"{interaction.user.mention} **{'enabled' if enabled else 'disabled'}** the auto-close feature",
            color=color
        )
        log_embed.add_field(name="Previous Status", value="✅ Enabled" if old_status else "❌ Disabled", inline=True)
        log_embed.add_field(name="New Status", value=status_text, inline=True)
        await send_log(interaction.client, log_embed)

        print(f"[AUTO-CLOSE] {interaction.user} ({'enabled' if enabled else 'disabled'}) auto-close feature")

    @app_commands.command(name="auto_close_hours", description="Set the number of hours before auto-close (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(hours="Number of hours to wait before auto-closing threads (1-168)")
    async def auto_close_hours(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168]):
        config = load_config()
        old_hours = config["auto_close_hours"]
        config["auto_close_hours"] = hours
        save_config(config)

        embed = discord.Embed(
            title="⏰ Auto-Close Timer Updated",
            description=f"Auto-close timer set to **{hours} hours**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Previous", value=f"{old_hours} hours", inline=True)
        embed.add_field(name="New", value=f"{hours} hours", inline=True)
        embed.add_field(
            name="Note",
            value="This only affects new auto-close schedules. Existing ones keep their original timing.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_admin_action(interaction, "⏰ Auto-Close Timer Changed",
                               f"changed auto-close timer from **{old_hours}h** to **{hours}h**")

        print(f"[AUTO-CLOSE] {interaction.user} changed auto-close timer to {hours} hours")

    @app_commands.command(name="settings", description="View and modify bot settings (admin only).")
    @app_commands.guild_only()
    @admin_only()
    async def settings_command(self, interaction: discord.Interaction):
        view = SettingsView(interaction)
        embed = await view.create_main_settings_embed(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await log_admin_action(interaction, "⚙️ Settings Panel Accessed", "opened the settings panel")
        print(f"[SETTINGS] {interaction.user} opened the settings panel")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
