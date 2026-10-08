"""Interactive /settings panel and the modals behind each button."""
import discord

from utils.checks import is_admin
from utils.config import load_config, save_config
from utils.formatting import capped_lines
from utils.interactions import reply_ephemeral, report_error
from utils.presence import ACTIVITY_TYPES, STATUS_TYPES, apply_bot_status, clear_bot_status
from utils.threads import send_log

NOT_ADMIN = "❌ Only admins can modify settings."

# Discord limits for modal text inputs and what the values are used for
TOS_MESSAGE_MAX = 4000      # shown in an embed description (4096, minus the countdown)
DECLINE_MESSAGE_MAX = 2000  # sent as message content
STATUS_MESSAGE_MAX = 100


def _fit(value, max_length: int) -> str:
    """Modal defaults longer than max_length make Discord reject the whole modal."""
    return str(value)[:max_length]


class AdminModal(discord.ui.Modal):
    """
    Base for settings modals: re-checks admin rights on submit (they may have
    been revoked while the modal was open) and reports errors to the user.
    """

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            await reply_ephemeral(interaction, NOT_ADMIN)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await report_error(interaction, error, f"{type(self).__name__}")


class SettingsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 minute timeout
        self.interaction = interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Covers every button, so none can be reached without admin rights
        if not is_admin(interaction.user):
            await reply_ephemeral(interaction, NOT_ADMIN)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await report_error(interaction, error, "Settings panel")

    async def on_timeout(self) -> None:
        # Grey out the buttons so they don't just fail when clicked
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="🔧 Auto-Close Settings", style=discord.ButtonStyle.primary, row=0)
    async def auto_close_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutoCloseSettingsModal())

    @discord.ui.button(label="📋 TOS Settings", style=discord.ButtonStyle.secondary, row=0)
    async def tos_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TOSSettingsModal())

    @discord.ui.button(label="👑 Admin Settings", style=discord.ButtonStyle.success, row=1)
    async def admin_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_admin_settings_embed(interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🤖 Bot Status", style=discord.ButtonStyle.secondary, row=1)
    async def bot_status_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BotStatusSettingsModal())

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray, row=2)
    async def refresh_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_main_settings_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_main_settings_embed(self, interaction: discord.Interaction):
        config = load_config()

        embed = discord.Embed(
            title="⚙️ Bot Settings",
            description="Click the buttons below to view or modify specific settings",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🔧 Auto-Close Settings",
            value=(
                f"**Status:** {'✅ Enabled' if config['auto_close_enabled'] else '❌ Disabled'}\n"
                f"**Timer:** {config['auto_close_hours']} hours\n"
                f"**Admin Confirm:** {'✅ Yes' if config['admin_close_confirmation'] else '❌ No'}"
            ),
            inline=True
        )

        forum_count = len(config["forums"])
        embed.add_field(
            name="📁 Forum Channels",
            value=f"**Tracking:** {forum_count} forum{'s' if forum_count != 1 else ''}",
            inline=True
        )

        log_channel = config["log_channel"]
        embed.add_field(
            name="📝 Log Channel",
            value=f"**Channel:** {f'<#{log_channel}>' if log_channel else 'Not set'}",
            inline=True
        )

        embed.add_field(
            name="👑 Admin Settings",
            value=f"**Users:** {len(config['admin_ids'])}\n**Roles:** {len(config['admin_role_ids'])}",
            inline=True
        )

        embed.add_field(
            name="📋 TOS Settings",
            value=f"**Timeout:** {config['tos_timeout_seconds']} seconds",
            inline=True
        )

        bot_status = config["bot_status"]
        status_display = f"**Status:** {'✅ Enabled' if bot_status['enabled'] else '❌ Disabled'}"
        if bot_status["enabled"]:
            status_display += (
                f"\n**Activity:** {bot_status['activity_type'].title()} {bot_status['message']}"
                f"\n**Type:** {bot_status['status_type'].title()}"
            )
        embed.add_field(name="🤖 Bot Status", value=status_display[:1024], inline=True)

        embed.set_footer(text="Use buttons to modify settings • Admin permissions required")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def create_admin_settings_embed(self, interaction: discord.Interaction):
        config = load_config()
        admin_ids = config["admin_ids"]
        admin_role_ids = config["admin_role_ids"]

        embed = discord.Embed(
            title="👑 Admin Settings",
            description=(
                "Server administrators are always admins. Also configured:"
                if config["guild_id"] else "Configured admins:"
            ),
            color=discord.Color.purple()
        )

        if admin_ids:
            lines = []
            for admin_id in admin_ids:
                member = interaction.guild.get_member(admin_id)
                lines.append(f"• {member.mention}" if member else f"• <@{admin_id}> (Not found)")
            embed.add_field(name=f"Admin Users ({len(admin_ids)})", value=capped_lines(lines), inline=False)

        if admin_role_ids:
            lines = []
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(role_id)
                lines.append(f"• {role.mention}" if role else f"• <@&{role_id}> (Role deleted)")
            embed.add_field(name=f"Admin Roles ({len(admin_role_ids)})", value=capped_lines(lines), inline=False)

        if not admin_ids and not admin_role_ids:
            embed.description = (
                "Only server administrators are admins; no other users or roles are configured."
                if config["guild_id"] else
                "⚠️ No admins configured, and guild_id isn't set. Add admin_ids or guild_id to data/config.yaml."
            )

        return embed


class AutoCloseSettingsModal(AdminModal):
    def __init__(self):
        super().__init__(title="Auto-Close Settings")
        config = load_config()

        self.enabled = discord.ui.TextInput(
            label="Enable Auto-Close (true/false)",
            placeholder="true or false",
            default=str(config["auto_close_enabled"]).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.enabled)

        self.hours = discord.ui.TextInput(
            label="Auto-Close Hours (1-168)",
            placeholder="Number of hours before auto-close",
            default=_fit(config["auto_close_hours"], 3),
            max_length=3,
            required=True
        )
        self.add_item(self.hours)

        self.admin_confirmation = discord.ui.TextInput(
            label="Admin Close Confirmation (true/false)",
            placeholder="true or false",
            default=str(config["admin_close_confirmation"]).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.admin_confirmation)

    async def on_submit(self, interaction: discord.Interaction):
        enabled_value = self.enabled.value.lower().strip()
        if enabled_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Enabled must be 'true' or 'false'", ephemeral=True)
        enabled = enabled_value == "true"

        try:
            hours = int(self.hours.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Hours must be a valid number", ephemeral=True)
        if not (1 <= hours <= 168):
            return await interaction.response.send_message("❌ Hours must be between 1 and 168", ephemeral=True)

        admin_confirmation_value = self.admin_confirmation.value.lower().strip()
        if admin_confirmation_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Admin confirmation must be 'true' or 'false'", ephemeral=True)
        admin_confirmation = admin_confirmation_value == "true"

        config = load_config()
        old_enabled = config["auto_close_enabled"]
        old_hours = config["auto_close_hours"]
        old_admin_confirmation = config["admin_close_confirmation"]

        config["auto_close_enabled"] = enabled
        config["auto_close_hours"] = hours
        config["admin_close_confirmation"] = admin_confirmation
        save_config(config)

        embed = discord.Embed(title="✅ Auto-Close Settings Updated", color=discord.Color.green())
        embed.add_field(name="Enabled", value=f"{old_enabled} → **{enabled}**", inline=True)
        embed.add_field(name="Hours", value=f"{old_hours} → **{hours}**", inline=True)
        embed.add_field(name="Admin Confirmation", value=f"{old_admin_confirmation} → **{admin_confirmation}**", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(
            title="⚙️ Auto-Close Settings Modified",
            description=f"{interaction.user.mention} updated auto-close settings",
            color=discord.Color.blue()
        )
        log_embed.add_field(name="Enabled", value=f"{old_enabled} → {enabled}", inline=True)
        log_embed.add_field(name="Hours", value=f"{old_hours} → {hours}", inline=True)
        log_embed.add_field(name="Admin Confirmation", value=f"{old_admin_confirmation} → {admin_confirmation}", inline=True)
        await send_log(interaction.client, log_embed)


class TOSSettingsModal(AdminModal):
    def __init__(self):
        super().__init__(title="TOS Settings")
        config = load_config()

        self.tos_message = discord.ui.TextInput(
            label="TOS Message ({timeout} = countdown)",
            placeholder="Message shown when threads are created...",
            default=_fit(config["tos_message"], TOS_MESSAGE_MAX),
            style=discord.TextStyle.paragraph,
            max_length=TOS_MESSAGE_MAX,
            required=True
        )
        self.add_item(self.tos_message)

        self.decline_response = discord.ui.TextInput(
            label="TOS Decline Response",
            placeholder="Message when TOS is declined...",
            default=_fit(config["tos_decline_response"], DECLINE_MESSAGE_MAX),
            style=discord.TextStyle.paragraph,
            max_length=DECLINE_MESSAGE_MAX,
            required=True
        )
        self.add_item(self.decline_response)

    async def on_submit(self, interaction: discord.Interaction):
        tos_message = self.tos_message.value.strip()
        decline_response = self.decline_response.value.strip()
        if not tos_message or not decline_response:
            return await interaction.response.send_message("❌ Messages can't be empty.", ephemeral=True)

        config = load_config()
        config["tos_message"] = tos_message
        config["tos_decline_response"] = decline_response
        save_config(config)

        embed = discord.Embed(
            title="✅ TOS Settings Updated",
            description="Terms of Service messages have been updated",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(
            title="📋 TOS Settings Modified",
            description=f"{interaction.user.mention} updated TOS messages",
            color=discord.Color.blue()
        )
        await send_log(interaction.client, log_embed)


class BotStatusSettingsModal(AdminModal):
    def __init__(self):
        super().__init__(title="Bot Status Settings")
        bot_status = load_config()["bot_status"]

        self.enabled = discord.ui.TextInput(
            label="Enable Custom Status (true/false)",
            placeholder="true or false",
            default=str(bot_status["enabled"]).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.enabled)

        self.activity_type = discord.ui.TextInput(
            label="Activity Type",
            placeholder="playing, listening, watching, competing, streaming",
            default=_fit(bot_status["activity_type"], 15),
            max_length=15,
            required=True
        )
        self.add_item(self.activity_type)

        self.message = discord.ui.TextInput(
            label="Status Message",
            placeholder="What the bot is doing (e.g. marketplace reviews)",
            default=_fit(bot_status["message"], STATUS_MESSAGE_MAX),
            max_length=STATUS_MESSAGE_MAX,
            required=True
        )
        self.add_item(self.message)

        self.status_type = discord.ui.TextInput(
            label="Status Type",
            placeholder="online, idle, dnd, invisible",
            default=_fit(bot_status["status_type"], 10),
            max_length=10,
            required=True
        )
        self.add_item(self.status_type)

    async def on_submit(self, interaction: discord.Interaction):
        enabled_value = self.enabled.value.lower().strip()
        if enabled_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Enabled must be 'true' or 'false'", ephemeral=True)
        enabled = enabled_value == "true"

        activity_type = self.activity_type.value.lower().strip()
        if activity_type not in ACTIVITY_TYPES:
            return await interaction.response.send_message(
                f"❌ Activity type must be one of: {', '.join(ACTIVITY_TYPES)}", ephemeral=True
            )

        status_type = self.status_type.value.lower().strip()
        if status_type not in STATUS_TYPES:
            return await interaction.response.send_message(
                f"❌ Status type must be one of: {', '.join(STATUS_TYPES)}", ephemeral=True
            )

        message = self.message.value.strip()
        if not message:
            return await interaction.response.send_message("❌ Status message cannot be empty", ephemeral=True)

        config = load_config()
        config["bot_status"].update({
            "enabled": enabled,
            "activity_type": activity_type,
            "message": message,
            "status_type": status_type
        })
        save_config(config)

        # Apply immediately, including switching the custom status off
        if enabled:
            await apply_bot_status(interaction.client, activity_type, message, status_type)
        else:
            await clear_bot_status(interaction.client)

        embed = discord.Embed(title="✅ Bot Status Settings Updated", color=discord.Color.green())
        embed.add_field(name="Enabled", value=f"**{enabled}**", inline=True)
        embed.add_field(name="Activity", value=f"**{activity_type.title()}**", inline=True)
        embed.add_field(name="Message", value=f"**{message}**", inline=True)
        embed.add_field(name="Status", value=f"**{status_type.title()}**", inline=True)
        if enabled:
            embed.add_field(name="Result", value=f"{activity_type.title()} {message}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(
            title="🤖 Bot Status Settings Modified",
            description=f"{interaction.user.mention} updated bot status settings",
            color=discord.Color.blue()
        )
        log_embed.add_field(name="Enabled", value=str(enabled), inline=True)
        log_embed.add_field(name="Activity", value=activity_type, inline=True)
        log_embed.add_field(name="Message", value=message, inline=True)
        log_embed.add_field(name="Status Type", value=status_type, inline=True)
        await send_log(interaction.client, log_embed)

        print(f"[BOT-STATUS] {interaction.user} updated bot status: {activity_type} {message} ({status_type})")
