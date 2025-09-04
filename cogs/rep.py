import discord
from discord.ext import commands
from discord import app_commands
import yaml
import random
import asyncio
import sqlite3
import time
import re
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

async def setup(bot: commands.Bot):
    await bot.add_cog(Rep(bot))
