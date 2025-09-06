import discord
from discord.ext import commands, tasks
from discord import app_commands
import yaml
import random
import asyncio
import sqlite3
import time
import re
from datetime import datetime, timedelta
from utils import db

CONFIG_PATH = 'data/config.yaml'

# Tracks threads waiting on TOS acceptance
# new — maps thread.id → timestamp when TOS prompt was sent
pending_tos_timestamps: dict[int, float] = {}

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def is_admin(user: discord.Member) -> bool:
    """Check if a user is an admin (either by user ID or role ID)"""
    config = load_config()
    admin_ids = config.get("admin_ids", [])
    admin_role_ids = config.get("admin_role_ids", [])
    
    # Check user ID
    if user.id in admin_ids:
        return True
    
    # Check role IDs
    user_role_ids = [role.id for role in user.roles]
    if any(role_id in admin_role_ids for role_id in user_role_ids):
        return True
    
    return False


def load_funny_messages():
    try:
        with open("assets/rep_messages.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return ["Damn, get your rep up!"]


class RepTOSView(discord.ui.View):
    def __init__(
        self,
        thread: discord.Thread,
        op_id: int,
        timeout: float = 30.0
    ):
        # timeout is in seconds
        super().__init__(timeout=timeout)
        self.thread = thread
        self.op_id = op_id

    @discord.ui.button(label='✅ I Agree', style=discord.ButtonStyle.success)
    async def agree(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can accept the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        # ─── Update the Thread Log with ✅ Accepted ───
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"TOS Status": f"✅ Accepted at <t:{int(time.time())}:T>"}
            )

        # Remove the TOS prompt and proceed to the review UI
        await interaction.message.delete()
        await post_review_ui(self.thread, self.op_id)

    @discord.ui.button(label='❌ I Do Not Agree', style=discord.ButtonStyle.danger)
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can decline the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        
        # ─── Update the Thread Log with ❌ Declined ───
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"TOS Status": f"❌ Declined at <t:{int(time.time())}:T>"}
            )

        config = load_config()
        # Edit the prompt to the decline response
        await interaction.message.edit(
            content=config['tos_decline_response'],
            view=None
        )

        # Archive & lock the thread
        await self.thread.edit(archived=True, locked=True)
        
        # Update thread status in database
        db.upsert_thread(
            thread_id=self.thread.id,
            channel_id=self.thread.parent_id,
            guild_id=self.thread.guild.id,
            name=self.thread.name,
            owner_id=self.thread.owner_id,
            jump_url=self.thread.jump_url,
            archived=True,
            locked=True
        )

    async def on_timeout(self):
        # Called if neither button is pressed within timeout
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        try:
            print(f"[TOS] Thread {self.thread.id} timed out. Auto-closing.")

            # ─── Update the Thread Log to show ❌ Timed Out ───
            bot = self.thread._state._get_client()
            logging_cog = bot.get_cog("LoggingSystem")
            if logging_cog:
                await logging_cog.update_thread_log(
                    self.thread,
                    field_updates={
                        "TOS Status": f"⌛ Timed out at <t:{int(time.time())}:T>",
                        "Thread Status": f"❌ Closed (timeout)"
                    }
                )

            # Notify in-thread
            await self.thread.send(
                "⏱️ No response to TOS in time. This post has been auto-closed."
            )

            # Archive & lock
            await self.thread.edit(archived=True, locked=True)
            
            # Update thread status in database
            db.upsert_thread(
                thread_id=self.thread.id,
                channel_id=self.thread.parent_id,
                guild_id=self.thread.guild.id,
                name=self.thread.name,
                owner_id=self.thread.owner_id,
                jump_url=self.thread.jump_url,
                archived=True,
                locked=True
            )

        except Exception as e:
            print(f"[ERROR] Auto-close on timeout failed: {e}")


def generate_star_rating(avg_rating: float, total_reviews: int) -> str | None:
    if total_reviews == 0:
        return None
    
    # Convert 1-10 rating to 5-star display
    star_rating = avg_rating / 2
    full_stars = int(star_rating)
    half_star = 1 if (star_rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = "⭐" * full_stars
    if half_star:
        stars += "✨"
    stars += "☆" * empty_stars
    
    return f"Rating: {stars} ({avg_rating:.1f}/10 from {total_reviews} review{'s' if total_reviews != 1 else ''})"

class SettingsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 minute timeout
        self.interaction = interaction

    @discord.ui.button(label="🔧 Auto-Close Settings", style=discord.ButtonStyle.primary, row=0)
    async def auto_close_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = AutoCloseSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 TOS Settings", style=discord.ButtonStyle.secondary, row=0)
    async def tos_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = TOSSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👑 Admin Settings", style=discord.ButtonStyle.success, row=1)
    async def admin_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can view admin settings.", ephemeral=True)
        
        embed = await self.create_admin_settings_embed(interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🌐 Server Settings", style=discord.ButtonStyle.secondary, row=1)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = ServerSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray, row=2)
    async def refresh_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_main_settings_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_main_settings_embed(self, interaction: discord.Interaction):
        config = load_config()
        
        embed = discord.Embed(
            title="⚙️ Bot Settings Dashboard",
            description="Click the buttons below to view or modify specific settings",
            color=discord.Color.blue()
        )

        # Auto-Close Settings
        auto_close_enabled = config.get("auto_close_enabled", True)
        auto_close_hours = config.get("auto_close_hours", 24)
        embed.add_field(
            name="🔧 Auto-Close Settings",
            value=f"**Status:** {'✅ Enabled' if auto_close_enabled else '❌ Disabled'}\n**Timer:** {auto_close_hours} hours",
            inline=True
        )

        # Forum Settings
        forums = config.get("forums", [])
        forum_count = len(forums)
        embed.add_field(
            name="📁 Forum Channels",
            value=f"**Tracking:** {forum_count} forum{'s' if forum_count != 1 else ''}",
            inline=True
        )

        # Log Channel
        log_channel = config.get("log_channel")
        log_status = f"<#{log_channel}>" if log_channel else "Not set"
        embed.add_field(
            name="📝 Log Channel",
            value=f"**Channel:** {log_status}",
            inline=True
        )

        # Admin Settings
        admin_ids = len(config.get("admin_ids", []))
        admin_roles = len(config.get("admin_role_ids", []))
        embed.add_field(
            name="👑 Admin Settings",
            value=f"**Users:** {admin_ids}\n**Roles:** {admin_roles}",
            inline=True
        )

        # Server Settings
        server_name = config.get("server_name", "Not set")
        embed.add_field(
            name="🌐 Server Info",
            value=f"**Name:** {server_name[:20]}{'...' if len(server_name) > 20 else ''}",
            inline=True
        )

        # TOS Settings
        embed.add_field(
            name="📋 TOS Settings",
            value="**Message:** Configured\n**Decline:** Configured",
            inline=True
        )

        embed.set_footer(text="Use buttons to modify settings • Admin permissions required")
        embed.timestamp = datetime.now()

        return embed

    async def create_admin_settings_embed(self, interaction: discord.Interaction):
        config = load_config()
        
        embed = discord.Embed(
            title="👑 Admin Settings",
            description="Current administrative users and roles",
            color=discord.Color.purple()
        )

        # Admin Users
        admin_ids = config.get("admin_ids", [])
        if admin_ids:
            admin_mentions = []
            for admin_id in admin_ids[:10]:  # Limit to first 10
                member = interaction.guild.get_member(admin_id)
                if member:
                    admin_mentions.append(f"• {member.mention}")
                else:
                    admin_mentions.append(f"• <@{admin_id}> (Not found)")
            
            if len(admin_ids) > 10:
                admin_mentions.append(f"• ... and {len(admin_ids) - 10} more")
                
            embed.add_field(
                name=f"Admin Users ({len(admin_ids)})",
                value="\n".join(admin_mentions) if admin_mentions else "None",
                inline=False
            )

        # Admin Roles
        admin_role_ids = config.get("admin_role_ids", [])
        if admin_role_ids:
            role_mentions = []
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(f"• {role.mention}")
                else:
                    role_mentions.append(f"• <@&{role_id}> (Role deleted)")
                    
            embed.add_field(
                name=f"Admin Roles ({len(admin_role_ids)})",
                value="\n".join(role_mentions) if role_mentions else "None",
                inline=False
            )

        if not admin_ids and not admin_role_ids:
            embed.description = "⚠️ No admins configured!"

        return embed

class AutoCloseSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Auto-Close Settings")
        
        config = load_config()
        
        self.enabled = discord.ui.TextInput(
            label="Enable Auto-Close (true/false)",
            placeholder="true or false",
            default=str(config.get("auto_close_enabled", True)).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.enabled)
        
        self.hours = discord.ui.TextInput(
            label="Auto-Close Hours (1-168)",
            placeholder="Number of hours before auto-close",
            default=str(config.get("auto_close_hours", 24)),
            max_length=3,
            required=True
        )
        self.add_item(self.hours)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Validate enabled setting
        enabled_value = self.enabled.value.lower().strip()
        if enabled_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Enabled must be 'true' or 'false'", ephemeral=True)
        
        enabled = enabled_value == "true"
        
        # Validate hours
        try:
            hours = int(self.hours.value.strip())
            if not (1 <= hours <= 168):
                return await interaction.response.send_message("❌ Hours must be between 1 and 168", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Hours must be a valid number", ephemeral=True)

        # Save changes
        old_enabled = config.get("auto_close_enabled", True)
        old_hours = config.get("auto_close_hours", 24)
        
        config["auto_close_enabled"] = enabled
        config["auto_close_hours"] = hours
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        # Create response
        embed = discord.Embed(
            title="✅ Auto-Close Settings Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Enabled", value=f"{old_enabled} → **{enabled}**", inline=True)
        embed.add_field(name="Hours", value=f"{old_hours} → **{hours}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⚙️ Auto-Close Settings Modified",
                    description=f"{interaction.user.mention} updated auto-close settings",
                    color=discord.Color.blue()
                )
                log_embed.add_field(name="Enabled", value=f"{old_enabled} → {enabled}", inline=True)
                log_embed.add_field(name="Hours", value=f"{old_hours} → {hours}", inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)

class TOSSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="TOS Settings")
        
        config = load_config()
        
        self.tos_message = discord.ui.TextInput(
            label="TOS Message",
            placeholder="Message shown when threads are created...",
            default=config.get("tos_message", ""),
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.tos_message)
        
        self.decline_response = discord.ui.TextInput(
            label="TOS Decline Response",
            placeholder="Message when TOS is declined...",
            default=config.get("tos_decline_response", ""),
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.decline_response)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Save changes
        config["tos_message"] = self.tos_message.value.strip()
        config["tos_decline_response"] = self.decline_response.value.strip()
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        embed = discord.Embed(
            title="✅ TOS Settings Updated",
            description="Terms of Service messages have been updated",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="📋 TOS Settings Modified",
                    description=f"{interaction.user.mention} updated TOS messages",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)

class ServerSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Server Settings")
        
        config = load_config()
        
        self.server_name = discord.ui.TextInput(
            label="Server Display Name",
            placeholder="Name shown on web dashboard",
            default=config.get("server_name", ""),
            max_length=100,
            required=True
        )
        self.add_item(self.server_name)
        
        self.server_invite = discord.ui.TextInput(
            label="Server Invite Link",
            placeholder="https://discord.gg/your-invite",
            default=config.get("server_invite", ""),
            max_length=200,
            required=False
        )
        self.add_item(self.server_invite)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Save changes
        config["server_name"] = self.server_name.value.strip()
        if self.server_invite.value.strip():
            config["server_invite"] = self.server_invite.value.strip()

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        embed = discord.Embed(
            title="✅ Server Settings Updated",
            description="Server information has been updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Server Name", value=self.server_name.value, inline=False)
        if self.server_invite.value.strip():
            embed.add_field(name="Invite Link", value=self.server_invite.value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🌐 Server Settings Modified",
                    description=f"{interaction.user.mention} updated server information",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)

class AutoCloseView(discord.ui.View):
    def __init__(self, thread: discord.Thread = None):
        super().__init__(timeout=None)
        self.thread = thread

    @discord.ui.button(custom_id="cancel_auto_close", label="I have multiple items - Keep thread open", style=discord.ButtonStyle.secondary)
    async def cancel_auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get thread from interaction if not provided during init (persistent view)
        thread = self.thread or interaction.channel
        
        # Only the thread owner can cancel auto-close
        if interaction.user.id != thread.owner_id:
            return await interaction.response.send_message(
                "Only the thread owner can cancel auto-close.", ephemeral=True
            )
        
        # Cancel the auto-close in database
        db.cancel_thread_auto_close(thread.id)
        
        # Update the message to show it's been cancelled
        embed = discord.Embed(
            title="🔓 Auto-close Cancelled",
            description="This thread will no longer be automatically closed. You can close it manually when ready.",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Log the cancellation
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔓 Auto-Close Cancelled",
                    description=f"{interaction.user.mention} cancelled auto-close for [{thread.name}]({thread.jump_url})",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
                log_embed.add_field(name="Reason", value="Multiple items in listing", inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
                
        print(f"[AUTO-CLOSE] {interaction.user} cancelled auto-close for thread {thread.id} ({thread.name})")

class ReviewModal(discord.ui.Modal):
    def __init__(self, thread: discord.Thread, receiver_id: int):
        super().__init__(title="Leave a Review")
        self.thread = thread
        self.receiver_id = receiver_id
        
        self.rating = discord.ui.TextInput(
            label="Rating (1-10)",
            placeholder="Enter a number between 1 and 10",
            required=True,
            max_length=2
        )
        self.add_item(self.rating)
        
        self.notes = discord.ui.TextInput(
            label="Review Notes (Optional)",
            placeholder="Share your experience... (optional)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.notes)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating_value = int(self.rating.value)
            if not (1 <= rating_value <= 10):
                raise ValueError("Rating must be between 1 and 10")
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid rating between 1 and 10.", 
                ephemeral=True
            )
            return
        
        notes_value = self.notes.value.strip() if self.notes.value else None
        
        # Record the review
        success = db.add_review(
            interaction.user.id,
            self.receiver_id,
            self.thread.id,
            rating_value,
            notes_value
        )
        
        if not success:
            await interaction.response.send_message(
                "❌ You've already reviewed this user in this thread.", 
                ephemeral=True
            )
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Review Submitted",
            description=(
                f"{interaction.user.mention} gave a **{rating_value}/10** rating "
                f"to <@{self.receiver_id}> in [this thread]({self.thread.jump_url})"
            ),
            color=discord.Color.green()
        )
        
        if notes_value:
            embed.add_field(name="Review Notes", value=notes_value[:100] + "..." if len(notes_value) > 100 else notes_value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Check if this is the first review in the thread
        is_first = db.is_first_review_in_thread(self.thread.id)
        
        # Send mention to thread owner with review notification
        mention_message = f"<@{self.receiver_id}> You received a **{rating_value}/10** review!"
        
        # Load config to check auto-close settings
        config = load_config()
        auto_close_enabled = config.get("auto_close_enabled", True)
        
        if is_first and auto_close_enabled:
            # Schedule auto-close based on configured hours
            auto_close_hours = config.get("auto_close_hours", 24)
            close_time = time.time() + (auto_close_hours * 60 * 60)  # Convert hours to seconds
            db.schedule_thread_auto_close(self.thread.id, close_time)
            
            # Create auto-close warning embed
            auto_close_embed = discord.Embed(
                title="⏰ Auto-Close Scheduled",
                description=f"This thread will automatically close <t:{int(close_time)}:R> unless you cancel it below.",
                color=discord.Color.orange()
            )
            auto_close_embed.add_field(
                name="Why?", 
                value="Threads auto-close after the first review to keep the marketplace clean. If you have multiple items in this listing, click the button below.",
                inline=False
            )
            
            view = AutoCloseView(self.thread)
            await self.thread.send(content=mention_message, embed=auto_close_embed, view=view)
            
            # Log auto-close scheduling
            log_ch_id = config.get("log_channel")
            if log_ch_id:
                log_ch = interaction.client.get_channel(log_ch_id)
                if log_ch:
                    log_embed = discord.Embed(
                        title="⏰ Auto-Close Scheduled",
                        description=f"Thread [{self.thread.name}]({self.thread.jump_url}) scheduled to auto-close <t:{int(close_time)}:R>",
                        color=discord.Color.orange()
                    )
                    log_embed.add_field(name="Thread Owner", value=f"<@{self.receiver_id}>", inline=True)
                    log_embed.add_field(name="Trigger", value="First review received", inline=True)
                    log_embed.add_field(name="Timer", value=f"{auto_close_hours} hours", inline=True)
                    log_embed.timestamp = datetime.now()
                    await log_ch.send(embed=log_embed)
                    
            print(f"[AUTO-CLOSE] Scheduled thread {self.thread.id} ({self.thread.name}) to close in {auto_close_hours} hours")
        else:
            # Just send the mention for subsequent reviews or when auto-close is disabled
            await self.thread.send(content=mention_message)
            
            # Log if auto-close is disabled but would have been triggered
            if is_first and not auto_close_enabled:
                print(f"[AUTO-CLOSE] First review in thread {self.thread.id} but auto-close is disabled")
        
        # Update thread log
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                event_additions={
                    "Review Events": f"{interaction.user.mention} gave {rating_value}/10 rating"
                }
            )
        
        # Send to log channel if configured
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                await log_ch.send(embed=embed)
        
        # Refresh the in-thread review UI
        await post_review_ui(self.thread, self.receiver_id)

class CloseConfirmationModal(discord.ui.Modal):
    def __init__(self, thread: discord.Thread):
        super().__init__(title="Close Post Confirmation")
        self.thread = thread
        
        self.confirmation = discord.ui.TextInput(
            label="Type 'Yes' to confirm closing without reviews",
            placeholder="Yes",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmation)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.lower() != "yes":
            await interaction.response.send_message(
                "❌ Post closure cancelled. You must type 'Yes' to confirm.",
                ephemeral=True
            )
            return
        
        # Proceed with closing the post
        await interaction.response.send_message(
            "🔒 This thread is now closed by its creator (no reviews received).", 
            ephemeral=False
        )
        
        # Update thread log
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"Thread Status": f"❌ Closed without reviews at <t:{int(time.time())}:T>"}
            )
        
        # Archive & lock
        await self.thread.edit(archived=True, locked=True)
        
        # Update thread status in database
        db.upsert_thread(
            thread_id=self.thread.id,
            channel_id=self.thread.parent_id,
            guild_id=self.thread.guild.id,
            name=self.thread.name,
            owner_id=self.thread.owner_id,
            jump_url=self.thread.jump_url,
            archived=True,
            locked=True
        )

# Load the category→messages mapping
def load_rep_messages():
    cats = {"good": [], "neutral": [], "bad": []}
    try:
        with open("assets/rep_messages.txt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    cat, msg = line.split("|", 1)
                    cat = cat.strip().lower()
                    msg = msg.strip()
                    if cat in cats:
                        cats[cat].append(msg)
    except FileNotFoundError:
        # fallback to a minimal set
        cats["neutral"].append("No rep data…")
    return cats

GIF_URL_RE = re.compile(
    r'(https?://\S+?\.(?:gif|mp4|webm))(?=[\s"\'<]|$)', 
    flags=re.IGNORECASE
)

async def post_review_ui(thread: discord.Thread, op_id: int):
    config = load_config()
    rep_msgs = load_rep_messages()
    no_rep_lines = config.get("no_rep_messages", [])

    # Get review data instead of old rep data
    avg_rating, total_reviews, latest_reviews = db.get_user_reviews(op_id)

    # 1) No reviews yet
    if total_reviews == 0:
        content = f"😶 {random.choice(no_rep_lines)}"
        gif_url = None

    # 2) Otherwise pick a line based on average rating
    else:
        if avg_rating >= 7.0:
            pool = rep_msgs["good"]
        elif avg_rating <= 4.0:
            pool = rep_msgs["bad"]
        else:
            pool = rep_msgs["neutral"]

        raw = random.choice(pool) if pool else ""
        # Split on last space
        parts = raw.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].lower().endswith((".gif", ".mp4", ".webm")):
            text, gif_url = parts[0], parts[1]
        else:
            text, gif_url = raw, None

        content = text

    # 3) Prepend star rating if any
    rating_display = generate_star_rating(avg_rating, total_reviews)
    if rating_display and total_reviews > 0:
        content = f"📊 {rating_display}\n\n{content}"

    # 4) Build the embed
    embed = discord.Embed(description=content, color=discord.Color.green())
    if gif_url:
        embed.set_image(url=gif_url)
        print(f"[DEBUG] Embedding GIF: {gif_url}")  # for your logs

    # 5) Add latest reviews if any
    if latest_reviews:
        reviews_text = ""
        for i, review in enumerate(latest_reviews[:3]):
            stars = "⭐" * (review['rating'] // 2) + ("✨" if review['rating'] % 2 else "")
            reviews_text += f"**{stars} {review['rating']}/10** by <@{review['giver_id']}>"
            if review['notes']:
                notes_preview = review['notes'][:50] + "..." if len(review['notes']) > 50 else review['notes']
                reviews_text += f"\n> {notes_preview}"
            reviews_text += "\n\n"
        
        embed.add_field(name="📝 Latest Reviews", value=reviews_text.strip(), inline=False)

    view = ReviewButtonView()
    await thread.send(embed=embed, view=view)


class ReviewButtonView(discord.ui.View):
    def __init__(self):
        # persistent across restarts
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="leave_review", label="⭐ Leave a Review", style=discord.ButtonStyle.primary)
    async def leave_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread: discord.Thread = interaction.channel
        op_id = thread.owner_id

        # 1) Prevent self-review
        if interaction.user.id == op_id:
            return await interaction.response.send_message(
                "You can't review yourself.", ephemeral=True
            )

        # 2) Check if already reviewed
        if db.has_user_reviewed(interaction.user.id, op_id, thread.id):
            return await interaction.response.send_message(
                "You've already reviewed this user in this thread.", ephemeral=True
            )

        # 3) Require the user to have spoken in the thread
        has_spoken = False
        async for msg in thread.history(limit=100):
            if msg.author.id == interaction.user.id:
                has_spoken = True
                break
        if not has_spoken:
            return await interaction.response.send_message(
                "You need to interact in the thread first before leaving a review.", ephemeral=True
            )

        # 4) Show the review modal
        modal = ReviewModal(thread, op_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(custom_id="close_post", label="Close Post", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = interaction.channel  # type: discord.Thread
        op_id = thread.owner_id
        
        # Check if user is OP or admin
        is_owner = interaction.user.id == op_id
        is_admin = is_admin(interaction.user)
        
        # 1) Only the OP or admins may close
        if not is_owner and not is_admin:
            return await interaction.response.send_message(
                "Only the thread creator or admins can close this post.", ephemeral=True
            )

        # 2) For non-admin users (OP), check if there's at least one review
        if not is_admin:
            conn = sqlite3.connect(db.DB_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM reviews WHERE thread_id = ? AND giver_id != ?",
                (thread.id, op_id)
            )
            count = c.fetchone()[0]
            conn.close()

            # If no reviews, show confirmation modal
            if count == 0:
                modal = CloseConfirmationModal(thread)
                await interaction.response.send_modal(modal)
                return

        # 3) Announce closure with different messages for different users
        if is_admin and not is_owner:
            closure_message = f"🔒 This thread has been closed by admin {interaction.user.mention}."
            log_status = f"❌ Force closed by admin {interaction.user.mention} at <t:{int(time.time())}:T>"
        else:
            # Post creator closing with reviews
            closure_message = "🔒 This thread is now closed by its creator."
            log_status = f"❌ Closed at <t:{int(time.time())}:T>"
        
        await interaction.response.send_message(closure_message, ephemeral=False)

        # 4) Update thread log to Closed
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                thread,
                field_updates={"Thread Status": log_status}
            )

        # 5) Archive & lock
        await thread.edit(archived=True, locked=True)
        
        # 6) Update thread status in database
        db.upsert_thread(
            thread_id=thread.id,
            channel_id=thread.parent_id,
            guild_id=thread.guild.id,
            name=thread.name,
            owner_id=thread.owner_id,
            jump_url=thread.jump_url,
            archived=True,
            locked=True
        )


class Rep(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("🔧 Rep cog loaded")
        
    async def cog_load(self):
        """Start background tasks when the cog loads"""
        self.auto_close_task.start()
    
    async def cog_unload(self):
        """Stop background tasks when the cog unloads"""
        self.auto_close_task.cancel()
    
    @tasks.loop(minutes=10)  # Check every 10 minutes
    async def auto_close_task(self):
        """Background task to auto-close threads that have passed their scheduled time"""
        try:
            threads_to_close = db.get_threads_to_auto_close()
            
            if threads_to_close:
                print(f"[AUTO-CLOSE] Found {len(threads_to_close)} thread(s) ready for auto-close")
            
            for thread_data in threads_to_close:
                try:
                    # Get the actual thread object
                    channel = self.bot.get_channel(thread_data['channel_id'])
                    if not channel:
                        continue
                        
                    thread = channel.get_thread(thread_data['thread_id'])
                    if not thread:
                        continue
                    
                    # Send auto-close notification
                    embed = discord.Embed(
                        title="🔒 Thread Auto-Closed",
                        description="This thread was automatically closed 24 hours after receiving its first review.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Why did this happen?",
                        value="To keep the marketplace clean, threads automatically close after receiving reviews. This helps prevent clutter from completed transactions.",
                        inline=False
                    )
                    
                    await thread.send(embed=embed)
                    
                    # Update thread log
                    logging_cog = self.bot.get_cog("LoggingSystem")
                    if logging_cog:
                        await logging_cog.update_thread_log(
                            thread,
                            field_updates={"Thread Status": f"🤖 Auto-closed at <t:{int(time.time())}:T>"}
                        )
                    
                    # Archive and lock the thread
                    await thread.edit(archived=True, locked=True)
                    
                    # Update thread status in database
                    db.upsert_thread(
                        thread_id=thread.id,
                        channel_id=thread.parent_id,
                        guild_id=thread.guild.id,
                        name=thread.name,
                        owner_id=thread.owner_id,
                        jump_url=thread.jump_url,
                        archived=True,
                        locked=True
                    )
                    
                    # Log to log channel
                    config = load_config()
                    log_ch_id = config.get("log_channel")
                    if log_ch_id:
                        log_ch = self.bot.get_channel(log_ch_id)
                        if log_ch:
                            log_embed = discord.Embed(
                                title="🤖 Thread Auto-Closed",
                                description=f"Thread [{thread.name}]({thread.jump_url}) was automatically closed",
                                color=discord.Color.red()
                            )
                            log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
                            log_embed.add_field(name="Reason", value="24-hour timer expired", inline=True)
                            log_embed.add_field(name="Action", value="Archived & Locked", inline=True)
                            log_embed.timestamp = datetime.now()
                            await log_ch.send(embed=log_embed)
                    
                    print(f"[AUTO-CLOSE] Successfully closed thread {thread.id} ({thread.name})")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to auto-close thread {thread_data['thread_id']}: {e}")
                    
        except Exception as e:
            print(f"[ERROR] Auto-close task failed: {e}")
    
    @auto_close_task.before_loop
    async def before_auto_close_task(self):
        """Wait until the bot is ready before starting the auto-close task"""
        await self.bot.wait_until_ready()


    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            forums = [int(f) for f in config.get("forums", []) if str(f).isdigit()]
            if thread.parent_id not in forums:
                return

            # Save thread information to database
            db.upsert_thread(
                thread_id=thread.id,
                channel_id=thread.parent_id,
                guild_id=thread.guild.id,
                name=thread.name,
                owner_id=thread.owner_id,
                jump_url=thread.jump_url,
                archived=thread.archived,
                locked=thread.locked
            )

            # Join so the bot can send
            try:
                await thread.join()
            except Exception:
                pass

            # Prepare TOS prompt
            timeout_secs = 30
            ts = int(time.time()) + timeout_secs
            countdown = f"<t:{ts}:R>"
            tos_message_text = config["tos_message"].replace("{timeout}", countdown)
            
            # Create embedded TOS message
            embed = discord.Embed(
                title="📋 Marketplace Terms of Service",
                description=tos_message_text,
                color=discord.Color.blue()
            )
            
            view = RepTOSView(thread=thread, op_id=thread.owner_id, timeout=timeout_secs)
            await asyncio.sleep(2)
            await thread.send(content=f"<@{thread.owner_id}>", embed=embed, view=view)
            pending_tos_timestamps[thread.id] = time.time()

            # Initialize log embed
            logging_cog = self.bot.get_cog("LoggingSystem")
            if logging_cog:
                await logging_cog.create_thread_log(
                    thread,
                    fields={
                        "TOS Status": "⏳ Pending",
                        "Review Events": "*No events yet*",
                        "Thread Status": "✅ Open"
                    }
                )

        except Exception as e:
            print(f"[ERROR] on_thread_create: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Delete user messages posted after TOS prompt until it's handled
        ts = pending_tos_timestamps.get(message.channel.id)
        if (
            ts
            and isinstance(message.channel, discord.Thread)
            and not message.author.bot
            and message.created_at.timestamp() > ts
        ):
            try:
                await message.delete()
            except discord.Forbidden:
                pass

    @app_commands.command(name="channel_set", description="Add a forum channel for tracking reps.")
    @app_commands.describe(channel="Forum channel to activate rep tracking on.")
    async def channel_set(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        config = load_config()
        config.setdefault("forums", [])
        if channel.id not in config["forums"]:
            config["forums"].append(channel.id)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)
            await interaction.response.send_message(
                f"✅ Channel {channel.mention} added to rep tracking.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "This channel is already tracked.", ephemeral=True
            )

    @app_commands.command(name="reviews", description="Check a user's reviews and rating.")
    @app_commands.describe(user="The user to check reviews for.")
    async def reviews_lookup(self, interaction: discord.Interaction, user: discord.Member):
        avg_rating, total_reviews, latest_reviews = db.get_user_reviews(user.id)
        
        embed = discord.Embed(
            title=f"⭐ Reviews for {user.display_name}",
            color=discord.Color.blue()
        )
        
        if total_reviews == 0:
            embed.description = "😶 No reviews yet. Time to build that reputation!"
            embed.add_field(name="Rating", value="No rating yet", inline=True)
            embed.add_field(name="Total Reviews", value="0", inline=True)
        else:
            rating_display = generate_star_rating(avg_rating, total_reviews)
            embed.description = rating_display
            embed.add_field(name="Average Rating", value=f"{avg_rating:.1f}/10", inline=True)
            embed.add_field(name="Total Reviews", value=str(total_reviews), inline=True)
            
            # Show latest reviews
            if latest_reviews:
                reviews_text = ""
                for i, review in enumerate(latest_reviews):
                    stars = "⭐" * (review['rating'] // 2) + ("✨" if review['rating'] % 2 else "")
                    reviews_text += f"**{stars} {review['rating']}/10** by <@{review['giver_id']}>"
                    if review['notes']:
                        notes_preview = review['notes'][:80] + "..." if len(review['notes']) > 80 else review['notes']
                        reviews_text += f"\n> {notes_preview}"
                    if i < len(latest_reviews) - 1:
                        reviews_text += "\n\n"
                
                embed.add_field(name="Latest Reviews", value=reviews_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 users by rating.")
    async def review_leaderboard(self, interaction: discord.Interaction):
        top = db.get_top_rated_users(limit=10)
        embed = discord.Embed(
            title="🏆 Top Rated Users",
            description="Here are the highest rated users:",
            color=discord.Color.gold()
        )
        if not top:
            embed.description = "No review data found."
        else:
            for i, (user_id, avg_rating, total_reviews) in enumerate(top, start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                
                # Convert to star display
                star_rating = avg_rating / 2
                full_stars = int(star_rating)
                half_star = 1 if (star_rating - full_stars) >= 0.5 else 0
                empty_stars = 5 - full_stars - half_star
                
                stars = "⭐" * full_stars
                if half_star:
                    stars += "✨"
                stars += "☆" * empty_stars
                
                embed.add_field(
                    name=f"{i}. {name}",
                    value=f"{stars} {avg_rating:.1f}/10 ({total_reviews} review{'s' if total_reviews != 1 else ''})",
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="log", description="Set a channel for review logs.")
    @app_commands.describe(channel="The channel to send review logs to.")
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        config["log_channel"] = channel.id
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Review logs will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_add", description="Add a user as admin (admin only).")
    @app_commands.describe(user="The user to add as admin.")
    async def admin_add(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user is already an admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can add other admins.", ephemeral=True
            )
            return
            
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        
        # Check if target is already admin
        if is_admin(user):
            await interaction.response.send_message(
                f"{user.mention} is already an admin.", ephemeral=True
            )
            return
            
        # Add the new admin (add to user IDs by default)
        admin_ids.append(user.id)
        config["admin_ids"] = admin_ids
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
            
        embed = discord.Embed(
            title="✅ Admin Added",
            description=f"{user.mention} has been added as an admin.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_remove", description="Remove a user from admin (admin only).")
    @app_commands.describe(user="The user to remove from admin.")
    async def admin_remove(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can remove other admins.", ephemeral=True
            )
            return
            
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        
        # Check if target is admin by user ID (only remove from user IDs, not roles)
        if user.id not in admin_ids:
            await interaction.response.send_message(
                f"{user.mention} is not an admin.", ephemeral=True
            )
            return
            
        # Don't allow self-removal if only admin
        if user.id == interaction.user.id and len(admin_ids) == 1:
            await interaction.response.send_message(
                "❌ Cannot remove yourself as the last admin.", ephemeral=True
            )
            return
            
        # Remove the admin
        admin_ids.remove(user.id)
        config["admin_ids"] = admin_ids
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
            
        embed = discord.Embed(
            title="✅ Admin Removed",
            description=f"{user.mention} has been removed from admin.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_list", description="List all admins (admin only).")
    async def admin_list(self, interaction: discord.Interaction):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can view the admin list.", ephemeral=True
            )
            return
        
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        admin_role_ids = config.get("admin_role_ids", [])
        
        embed = discord.Embed(
            title="👑 Admin List",
            description="Current bot administrators:",
            color=discord.Color.purple()
        )
        
        if not admin_ids and not admin_role_ids:
            embed.description = "No admins configured."
        else:
            # Show admin users
            if admin_ids:
                admin_mentions = []
                for admin_id in admin_ids:
                    member = interaction.guild.get_member(admin_id)
                    if member:
                        admin_mentions.append(f"• {member.mention} ({member.display_name})")
                    else:
                        admin_mentions.append(f"• <@{admin_id}> (ID: {admin_id})")
                
                embed.add_field(
                    name=f"Admin Users ({len(admin_ids)})",
                    value="\n".join(admin_mentions),
                    inline=False
                )
            
            # Show admin roles
            if admin_role_ids:
                role_mentions = []
                for role_id in admin_role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_mentions.append(f"• {role.mention} ({role.name})")
                    else:
                        role_mentions.append(f"• <@&{role_id}> (ID: {role_id})")
                
                embed.add_field(
                    name=f"Admin Roles ({len(admin_role_ids)})",
                    value="\n".join(role_mentions),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_role_add", description="Add a role as admin (admin only).")
    @app_commands.describe(role="The role to add as admin.")
    async def admin_role_add(self, interaction: discord.Interaction, role: discord.Role):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can add admin roles.", ephemeral=True
            )
            return
            
        config = load_config()
        admin_role_ids = config.get("admin_role_ids", [])
        
        # Check if role is already admin
        if role.id in admin_role_ids:
            await interaction.response.send_message(
                f"{role.mention} is already an admin role.", ephemeral=True
            )
            return
            
        # Add the new admin role
        admin_role_ids.append(role.id)
        config["admin_role_ids"] = admin_role_ids
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
            
        embed = discord.Embed(
            title="✅ Admin Role Added",
            description=f"{role.mention} has been added as an admin role.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_role_remove", description="Remove a role from admin (admin only).")
    @app_commands.describe(role="The role to remove from admin.")
    async def admin_role_remove(self, interaction: discord.Interaction, role: discord.Role):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can remove admin roles.", ephemeral=True
            )
            return
            
        config = load_config()
        admin_role_ids = config.get("admin_role_ids", [])
        
        # Check if role is admin
        if role.id not in admin_role_ids:
            await interaction.response.send_message(
                f"{role.mention} is not an admin role.", ephemeral=True
            )
            return
            
        # Remove the admin role
        admin_role_ids.remove(role.id)
        config["admin_role_ids"] = admin_role_ids
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
            
        embed = discord.Embed(
            title="✅ Admin Role Removed",
            description=f"{role.mention} has been removed from admin roles.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="send_review_ui", description="Send the rate/close interface to the current thread (admin only).")
    async def send_review_ui(self, interaction: discord.Interaction):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can use this command.", ephemeral=True
            )
            return
        
        # Check if command is used in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ This command can only be used in a thread.", ephemeral=True
            )
            return
        
        thread = interaction.channel
        op_id = thread.owner_id
        
        # Send the review UI
        await post_review_ui(thread, op_id)
        
        await interaction.response.send_message(
            "✅ Rate/close interface sent to this thread.", ephemeral=True
        )

    @app_commands.command(name="auto_close_toggle", description="Toggle the auto-close feature on/off (admin only).")
    @app_commands.describe(enabled="Enable or disable auto-close feature")
    async def auto_close_toggle(self, interaction: discord.Interaction, enabled: bool = None):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can toggle auto-close settings.", ephemeral=True
            )
            return
        
        config = load_config()
        
        # If no parameter provided, show current status
        if enabled is None:
            current_status = config.get("auto_close_enabled", True)
            current_hours = config.get("auto_close_hours", 24)
            
            embed = discord.Embed(
                title="⚙️ Auto-Close Settings",
                description=f"**Status:** {'✅ Enabled' if current_status else '❌ Disabled'}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Auto-Close Timer", value=f"{current_hours} hours", inline=True)
            embed.add_field(name="Usage", value="Use `/auto_close_toggle true/false` to change", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update the setting
        old_status = config.get("auto_close_enabled", True)
        config["auto_close_enabled"] = enabled
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        
        # Create response embed
        status_text = "✅ Enabled" if enabled else "❌ Disabled"
        color = discord.Color.green() if enabled else discord.Color.red()
        
        embed = discord.Embed(
            title="⚙️ Auto-Close Setting Updated",
            description=f"Auto-close feature is now **{status_text}**",
            color=color
        )
        
        if enabled:
            hours = config.get("auto_close_hours", 24)
            embed.add_field(
                name="Timer", 
                value=f"Threads will auto-close {hours} hours after first review", 
                inline=False
            )
        else:
            embed.add_field(
                name="Note", 
                value="Existing scheduled auto-closes will still occur unless manually cancelled", 
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the change to log channel
        config_log = load_config()
        log_ch_id = config_log.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔧 Auto-Close Setting Changed",
                    description=f"{interaction.user.mention} **{'enabled' if enabled else 'disabled'}** the auto-close feature",
                    color=color
                )
                log_embed.add_field(name="Previous Status", value="✅ Enabled" if old_status else "❌ Disabled", inline=True)
                log_embed.add_field(name="New Status", value=status_text, inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
        
        print(f"[AUTO-CLOSE] {interaction.user} ({'enabled' if enabled else 'disabled'}) auto-close feature")

    @app_commands.command(name="auto_close_hours", description="Set the number of hours before auto-close (admin only).")
    @app_commands.describe(hours="Number of hours to wait before auto-closing threads (1-168)")
    async def auto_close_hours(self, interaction: discord.Interaction, hours: int):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can modify auto-close settings.", ephemeral=True
            )
            return
        
        # Validate hours (1 hour to 1 week)
        if not (1 <= hours <= 168):
            await interaction.response.send_message(
                "❌ Hours must be between 1 and 168 (1 week).", ephemeral=True
            )
            return
        
        config = load_config()
        old_hours = config.get("auto_close_hours", 24)
        config["auto_close_hours"] = hours
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        
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
        
        # Log the change
        config_log = load_config()
        log_ch_id = config_log.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⏰ Auto-Close Timer Changed",
                    description=f"{interaction.user.mention} changed auto-close timer from **{old_hours}h** to **{hours}h**",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
        
        print(f"[AUTO-CLOSE] {interaction.user} changed auto-close timer to {hours} hours")

    @app_commands.command(name="settings", description="View and modify bot settings through an interactive interface (admin only).")
    async def settings_command(self, interaction: discord.Interaction):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can access bot settings.", ephemeral=True
            )
            return

        # Create the settings view and embed
        view = SettingsView(interaction)
        embed = await view.create_main_settings_embed(interaction)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Log settings access
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⚙️ Settings Panel Accessed",
                    description=f"{interaction.user.mention} opened the settings dashboard",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)

        print(f"[SETTINGS] {interaction.user} accessed settings dashboard")

async def setup(bot: commands.Bot):
    # Add persistent views
    bot.add_view(ReviewButtonView())
    bot.add_view(AutoCloseView(None))  # Template view for persistent handling
    await bot.add_cog(Rep(bot))
