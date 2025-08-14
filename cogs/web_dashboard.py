import discord
from discord.ext import commands, tasks
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import sys
import threading
import time
import asyncio
import json
from datetime import datetime
import yaml
from typing import List, Dict, Any

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import db

class WebDashboard(commands.Cog):
    """Web dashboard integration cog for the Discord bot"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app = None
        self.flask_thread = None
        self.config = None
        self.load_config()
        self.enhanced_sync_task.start()  # Start background task
        
    def load_config(self):
        """Load configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            print("❌ Config file not found")
            self.config = {}
    
    def setup_flask_app(self):
        """Setup Flask application"""
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_dashboard', 'templates')
        static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_dashboard', 'static')
        
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        self.app.secret_key = 'discord-rep-bot-dashboard'
        
        # Template context processor
        @self.app.context_processor
        def inject_config():
            return {'config': self.config}
        
        # Template filters
        @self.app.template_filter('star_display')
        def star_display_filter(rating):
            return self.generate_star_display(rating)
        
        @self.app.template_filter('format_date')
        def format_date_filter(date_str):
            if not date_str:
                return "Unknown"
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            except:
                return date_str
        
        # Routes
        @self.app.route('/')
        def index():
            """Homepage with server information and stats"""
            stats = self.get_homepage_stats()
            guild_info = self.get_guild_info()
            recent_reviews = self.get_recent_reviews(6)
            
            return render_template('homepage.html', 
                                 server_name=self.config.get('server_name'),
                                 server_invite=self.config.get('server_invite'),
                                 guild_info=guild_info,
                                 stats=stats,
                                 recent_reviews=recent_reviews)
        
        @self.app.route('/users')
        def users():
            """Users page showing all community members with pagination"""
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 25, type=int)
            
            # Validate per_page values
            if per_page not in [10, 25, 50, 100]:
                per_page = 25
            
            all_users = self.get_all_users_with_activity()
            
            # Calculate pagination
            total_users = len(all_users)
            start = (page - 1) * per_page
            end = start + per_page
            users_page = all_users[start:end]
            
            # Calculate pagination info
            total_pages = (total_users + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            pagination_info = {
                'page': page,
                'per_page': per_page,
                'total': total_users,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_num': page - 1 if has_prev else None,
                'next_num': page + 1 if has_next else None,
                'start_index': start + 1,
                'end_index': min(end, total_users)
            }
            
            return render_template('index.html', users=users_page, pagination=pagination_info)
        
        @self.app.route('/user/<int:user_id>')
        def user_profile(user_id):
            """User profile page"""
            stats = self.get_user_stats(user_id)
            return render_template('user_profile.html', user_id=user_id, stats=stats)
        
        @self.app.route('/api/discord_user/<int:user_id>')
        def get_discord_user_info(user_id):
            """API endpoint to get Discord user information"""
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                SELECT username, display_name, avatar_url, banner_url, accent_color, 
                       public_flags, is_in_server, roles, badges
                FROM users WHERE user_id = ?
            """, (user_id,))
            result = c.fetchone()
            conn.close()
            
            if result:
                # Parse JSON data
                roles = json.loads(result[7]) if result[7] else []
                badges = json.loads(result[8]) if result[8] else []
                
                return jsonify({
                    'id': user_id,
                    'username': result[0],
                    'display_name': result[1] or result[0],
                    'avatar_url': result[2] or f'https://cdn.discordapp.com/embed/avatars/{user_id % 5}.png',
                    'banner_url': result[3],
                    'accent_color': result[4],
                    'public_flags': result[5],
                    'status': 'Online' if result[6] else 'Offline',
                    'roles': roles,
                    'badges': badges
                })
            else:
                return jsonify({
                    'id': user_id,
                    'username': f'User{user_id}',
                    'display_name': f'User {user_id}',
                    'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{user_id % 5}.png',
                    'banner_url': None,
                    'accent_color': None,
                    'public_flags': None,
                    'status': 'Unknown',
                    'roles': [],
                    'badges': []
                })
        
        @self.app.route('/api/thread_info/<int:thread_id>')
        def get_thread_info(thread_id):
            """API endpoint to get Discord thread information"""
            guild_id = getattr(self.bot.guilds[0], 'id', 'GUILD_ID') if self.bot.guilds else 'GUILD_ID'
            return jsonify({
                'id': thread_id,
                'name': f'Thread {thread_id}',
                'url': f'https://discord.com/channels/{guild_id}/CHANNEL_ID/{thread_id}',
                'created_at': '2024-01-01T00:00:00Z',
                'archived': False,
                'owner_id': 123456789
            })
        
        @self.app.route('/api/search_users')
        def search_users():
            """API endpoint to search users in the database"""
            query = request.args.get('q', '').strip()
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 25, type=int)
            
            # Validate per_page values
            if per_page not in [10, 25, 50, 100]:
                per_page = 25
            
            if not query:
                return jsonify({'users': [], 'pagination': None})
            
            # Search users in database
            search_results = self.search_users_in_database(query)
            
            # Apply pagination to search results
            total_results = len(search_results)
            start = (page - 1) * per_page
            end = start + per_page
            users_page = search_results[start:end]
            
            # Calculate pagination info
            total_pages = (total_results + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            pagination_info = {
                'page': page,
                'per_page': per_page,
                'total': total_results,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_num': page - 1 if has_prev else None,
                'next_num': page + 1 if has_next else None,
                'start_index': start + 1,
                'end_index': min(end, total_results),
                'query': query
            }
            
            return jsonify({
                'users': users_page,
                'pagination': pagination_info
            })

        @self.app.route('/api/sync_members', methods=['POST'])
        def sync_members():
            """API endpoint to manually sync Discord members"""
            if not self.bot.is_ready():
                return jsonify({'status': 'error', 'message': 'Bot not ready'}), 400
            
            try:
                # Check if enhanced sync is requested
                data = request.get_json() or {}
                enhanced = data.get('enhanced', False)
                
                # Create a task to run the async sync function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.sync_guild_members(enhanced=enhanced))
                loop.close()
                
                if result['success']:
                    if enhanced:
                        return jsonify({'status': 'success', 'message': f'Enhanced sync completed! {result["count"]} members, {result["enhanced"]} with enhanced data'})
                    else:
                        return jsonify({'status': 'success', 'message': f'Basic sync completed! {result["count"]} members synced'})
                else:
                    return jsonify({'status': 'error', 'message': result['error']}), 400
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400
    
    def generate_star_display(self, rating):
        """Convert numeric rating to star display"""
        if rating == 0:
            return "No rating"
        
        star_rating = rating / 2
        full_stars = int(star_rating)
        half_star = 1 if (star_rating - full_stars) >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        
        stars = "⭐" * full_stars
        if half_star:
            stars += "✨"
        stars += "☆" * empty_stars
        
        return f"{stars} ({rating:.1f}/10)"
    
    def parse_discord_badges(self, public_flags):
        """Parse Discord badges from public flags"""
        if not public_flags:
            return []
        
        badge_map = {
            1 << 0: {"name": "Discord Staff", "emoji": "🛡️", "color": "#5865F2"},
            1 << 1: {"name": "Discord Partner", "emoji": "🤝", "color": "#4FC3F7"},
            1 << 2: {"name": "HypeSquad Events", "emoji": "⚡", "color": "#F47FFF"},
            1 << 3: {"name": "Bug Hunter Level 1", "emoji": "🐛", "color": "#2ECC71"},
            1 << 6: {"name": "House Bravery", "emoji": "💜", "color": "#9C84EF"},
            1 << 7: {"name": "House Brilliance", "emoji": "🧡", "color": "#F47FFF"},
            1 << 8: {"name": "House Balance", "emoji": "💚", "color": "#45DDC0"},
            1 << 9: {"name": "Early Supporter", "emoji": "⭐", "color": "#F47FFF"},
            1 << 14: {"name": "Bug Hunter Level 2", "emoji": "🐞", "color": "#2ECC71"},
            1 << 16: {"name": "Verified Bot Developer", "emoji": "🔧", "color": "#5865F2"},
            1 << 17: {"name": "Certified Moderator", "emoji": "🛡️", "color": "#5865F2"},
            1 << 18: {"name": "Bot HTTP Interactions", "emoji": "🤖", "color": "#5865F2"},
            1 << 22: {"name": "Active Developer", "emoji": "💻", "color": "#5865F2"},
        }
        
        badges = []
        for flag, badge_info in badge_map.items():
            if public_flags & flag:
                badges.append(badge_info)
        
        return badges
    
    def get_role_data(self, member):
        """Get role information for a member"""
        if not member:
            return []
        
        roles = []
        for role in member.roles:
            if role.name != "@everyone":  # Skip @everyone role
                role_data = {
                    "id": role.id,
                    "name": role.name,
                    "color": str(role.color) if role.color.value != 0 else None,
                    "position": role.position,
                    "hoisted": role.hoist,
                    "mentionable": role.mentionable
                }
                roles.append(role_data)
        
        # Sort by position (highest first)
        roles.sort(key=lambda x: x["position"], reverse=True)
        return roles
    
    @tasks.loop(hours=6)  # Run every 6 hours
    async def enhanced_sync_task(self):
        """Background task to periodically sync enhanced profile data"""
        if not self.bot.is_ready():
            return
            
        try:
            await self.sync_enhanced_profiles()
        except Exception as e:
            print(f"⚠️  Background enhanced sync error: {e}")
    
    @enhanced_sync_task.before_loop
    async def before_enhanced_sync(self):
        """Wait for bot to be ready before starting background task"""
        await self.bot.wait_until_ready()
        await asyncio.sleep(600)  # Wait 10 minutes after startup before first enhanced sync
    
    async def sync_enhanced_profiles(self):
        """Sync enhanced profile data for users who don't have it yet"""
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Find users without enhanced data (no banner_url and no badges)
            c.execute("""
                SELECT user_id, username FROM users 
                WHERE is_in_server = TRUE 
                AND (banner_url IS NULL AND badges IS NULL)
                ORDER BY last_updated ASC
                LIMIT 50
            """)
            
            users_to_update = c.fetchall()
            conn.close()
            
            if not users_to_update:
                print("🎯 All users have enhanced profile data")
                return
            
            print(f"🔄 Background sync: updating enhanced data for {len(users_to_update)} users...")
            
            for i, (user_id, username) in enumerate(users_to_update):
                try:
                    # Rate limiting
                    if i > 0 and i % 5 == 0:
                        await asyncio.sleep(3)
                    
                    # Fetch enhanced data
                    full_user = await self.bot.fetch_user(user_id)
                    if full_user:
                        banner_url = full_user.banner.url if full_user.banner else None
                        accent_color = full_user.accent_color.value if full_user.accent_color else None
                        public_flags = full_user.public_flags.value if hasattr(full_user, 'public_flags') and full_user.public_flags else None
                        badges_json = None
                        
                        if public_flags:
                            badges = self.parse_discord_badges(public_flags)
                            badges_json = json.dumps(badges) if badges else None
                        
                        # Update only enhanced fields
                        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("""
                            UPDATE users 
                            SET banner_url = ?, accent_color = ?, public_flags = ?, badges = ?, 
                                last_updated = CURRENT_TIMESTAMP
                            WHERE user_id = ?
                        """, (banner_url, accent_color, public_flags, badges_json, user_id))
                        conn.commit()
                        conn.close()
                        
                except Exception as e:
                    # Skip individual errors
                    continue
            
            print(f"✅ Background sync completed for {len(users_to_update)} users")
            
        except Exception as e:
            print(f"❌ Background enhanced sync error: {e}")

    def get_user_stats(self, user_id):
        """Get comprehensive user statistics"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get review stats
        c.execute("""
            SELECT AVG(rating), COUNT(*) 
            FROM reviews 
            WHERE receiver_id = ?
        """, (user_id,))
        result = c.fetchone()
        avg_rating = result[0] if result[0] else 0.0
        total_reviews = result[1]
        
        # Get reviews given by this user
        c.execute("""
            SELECT COUNT(*) 
            FROM reviews 
            WHERE giver_id = ?
        """, (user_id,))
        reviews_given = c.fetchone()[0]
        
        # Get active threads (not archived)
        c.execute("""
            SELECT DISTINCT thread_id 
            FROM reviews 
            WHERE receiver_id = ?
        """, (user_id,))
        thread_ids = [row[0] for row in c.fetchall()]
        
        # Get latest reviews received
        c.execute("""
            SELECT giver_id, rating, notes, created_at 
            FROM reviews 
            WHERE receiver_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user_id,))
        
        latest_reviews = []
        for row in c.fetchall():
            latest_reviews.append({
                'giver_id': row[0],
                'rating': row[1],
                'notes': row[2],
                'created_at': row[3]
            })
        
        # Get latest reviews given
        c.execute("""
            SELECT receiver_id, rating, notes, created_at, thread_id
            FROM reviews 
            WHERE giver_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user_id,))
        
        reviews_given_data = []
        for row in c.fetchall():
            reviews_given_data.append({
                'receiver_id': row[0],
                'rating': row[1],
                'notes': row[2],
                'created_at': row[3],
                'thread_id': row[4]
            })
        
        conn.close()
        
        return {
            'avg_rating': avg_rating,
            'total_reviews': total_reviews,
            'reviews_given': reviews_given,
            'thread_ids': thread_ids,
            'latest_reviews': latest_reviews,
            'reviews_given_data': reviews_given_data
        }
    
    def get_all_users_with_activity(self):
        """Get all users from the database with their review stats"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.display_name,
                u.avatar_url,
                u.banner_url,
                u.accent_color,
                u.public_flags,
                u.is_in_server,
                u.left_at,
                u.roles,
                u.badges,
                COALESCE(AVG(r_received.rating), 0) as avg_rating,
                COALESCE(COUNT(r_received.id), 0) as total_reviews,
                COALESCE(COUNT(r_given.id), 0) as reviews_given
            FROM users u
            LEFT JOIN reviews r_received ON u.user_id = r_received.receiver_id
            LEFT JOIN reviews r_given ON u.user_id = r_given.giver_id
            GROUP BY u.user_id, u.username, u.display_name, u.avatar_url, u.banner_url, 
                     u.accent_color, u.public_flags, u.is_in_server, u.left_at, u.roles, u.badges
            ORDER BY u.is_in_server DESC, COALESCE(AVG(r_received.rating), 0) DESC, u.username ASC
        """)
        
        users_data = []
        for row in c.fetchall():
            # Parse JSON data
            roles = json.loads(row[9]) if row[9] else []
            badges = json.loads(row[10]) if row[10] else []
            
            users_data.append({
                'user_id': row[0],
                'username': row[1],
                'display_name': row[2],
                'avatar_url': row[3],
                'banner_url': row[4],
                'accent_color': row[5],
                'public_flags': row[6],
                'is_in_server': bool(row[7]),
                'left_at': row[8],
                'roles': roles,
                'badges': badges,
                'avg_rating': float(row[11]),
                'total_reviews': row[12],
                'reviews_given': row[13]
            })
        
        conn.close()
        return users_data
    
    def get_homepage_stats(self):
        """Get overall statistics for the homepage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get total reviews and average rating
        c.execute("SELECT COUNT(*), AVG(rating) FROM reviews")
        total_reviews, avg_rating = c.fetchone()
        total_reviews = total_reviews or 0
        avg_rating = avg_rating or 0.0
        
        # Get active users (users who have given or received reviews)
        c.execute("""
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT giver_id as user_id FROM reviews
                UNION
                SELECT receiver_id as user_id FROM reviews
            )
        """)
        active_users = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_reviews': total_reviews,
            'avg_rating': avg_rating,
            'active_users': active_users
        }
    
    def get_guild_info(self):
        """Get Discord guild information"""
        if self.bot.guilds:
            guild = self.bot.guilds[0]  # Assuming first guild
            return {
                'name': guild.name,
                'member_count': guild.member_count,
                'icon_url': guild.icon.url if guild.icon else None,
                'description': guild.description
            }
        return None
    
    def get_recent_reviews(self, limit=6):
        """Get recent reviews for homepage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                r.rating,
                r.created_at,
                giver.username as giver_name,
                giver.display_name as giver_display,
                giver.avatar_url as giver_avatar,
                receiver.username as receiver_name,
                receiver.display_name as receiver_display,
                receiver.avatar_url as receiver_avatar
            FROM reviews r
            LEFT JOIN users giver ON r.giver_id = giver.user_id
            LEFT JOIN users receiver ON r.receiver_id = receiver.user_id
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (limit,))
        
        recent_reviews = []
        for row in c.fetchall():
            recent_reviews.append({
                'rating': row[0],
                'created_at': row[1],
                'giver_name': row[3] or row[2] or f'User',
                'giver_avatar': row[4],
                'receiver_name': row[6] or row[5] or f'User',
                'receiver_avatar': row[7]
            })
        
        conn.close()
        return recent_reviews

    def search_users_in_database(self, query):
        """Search users in database by username, display_name, or user_id"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Search by username, display_name, or user_id
        search_query = f"%{query}%"
        
        # Check if query is a number (user_id search)
        if query.isdigit():
            c.execute("""
                SELECT 
                    u.user_id,
                    u.username,
                    u.display_name,
                    u.avatar_url,
                    u.banner_url,
                    u.accent_color,
                    u.public_flags,
                    u.is_in_server,
                    u.left_at,
                    u.roles,
                    u.badges,
                    COALESCE(AVG(r_received.rating), 0) as avg_rating,
                    COALESCE(COUNT(r_received.id), 0) as total_reviews,
                    COALESCE(COUNT(r_given.id), 0) as reviews_given
                FROM users u
                LEFT JOIN reviews r_received ON u.user_id = r_received.receiver_id
                LEFT JOIN reviews r_given ON u.user_id = r_given.giver_id
                WHERE u.user_id = ? OR u.username LIKE ? OR u.display_name LIKE ?
                GROUP BY u.user_id, u.username, u.display_name, u.avatar_url, u.banner_url, 
                         u.accent_color, u.public_flags, u.is_in_server, u.left_at, u.roles, u.badges
                ORDER BY u.is_in_server DESC, COALESCE(AVG(r_received.rating), 0) DESC, u.username ASC
            """, (int(query), search_query, search_query))
        else:
            c.execute("""
                SELECT 
                    u.user_id,
                    u.username,
                    u.display_name,
                    u.avatar_url,
                    u.banner_url,
                    u.accent_color,
                    u.public_flags,
                    u.is_in_server,
                    u.left_at,
                    u.roles,
                    u.badges,
                    COALESCE(AVG(r_received.rating), 0) as avg_rating,
                    COALESCE(COUNT(r_received.id), 0) as total_reviews,
                    COALESCE(COUNT(r_given.id), 0) as reviews_given
                FROM users u
                LEFT JOIN reviews r_received ON u.user_id = r_received.receiver_id
                LEFT JOIN reviews r_given ON u.user_id = r_given.giver_id
                WHERE u.username LIKE ? OR u.display_name LIKE ?
                GROUP BY u.user_id, u.username, u.display_name, u.avatar_url, u.banner_url, 
                         u.accent_color, u.public_flags, u.is_in_server, u.left_at, u.roles, u.badges
                ORDER BY u.is_in_server DESC, COALESCE(AVG(r_received.rating), 0) DESC, u.username ASC
            """, (search_query, search_query))
        
        users_data = []
        for row in c.fetchall():
            # Parse JSON data
            roles = json.loads(row[9]) if row[9] else []
            badges = json.loads(row[10]) if row[10] else []
            
            users_data.append({
                'user_id': row[0],
                'username': row[1],
                'display_name': row[2],
                'avatar_url': row[3],
                'banner_url': row[4],
                'accent_color': row[5],
                'public_flags': row[6],
                'is_in_server': bool(row[7]),
                'left_at': row[8],
                'roles': roles,
                'badges': badges,
                'avg_rating': float(row[11]),
                'total_reviews': row[12],
                'reviews_given': row[13]
            })
        
        conn.close()
        return users_data
    
    async def sync_guild_members(self, enhanced=False):
        """Sync all guild members to database with optional enhanced profile data"""
        try:
            if not self.bot.guilds:
                return {'success': False, 'error': 'No guilds found'}
            
            guild = self.bot.guilds[0]  # Use first guild
            current_member_ids = set()
            
            if enhanced:
                print(f"🔄 Syncing {guild.member_count} members from {guild.name} with enhanced data...")
            else:
                print(f"🔄 Syncing {guild.member_count} members from {guild.name} (basic info)...")
            
            # Process all members
            enhanced_count = 0
            for i, member in enumerate(guild.members):
                current_member_ids.add(member.id)
                
                # Basic info (always available)
                avatar_url = member.display_avatar.url if member.display_avatar else None
                joined_at = member.joined_at.isoformat() if member.joined_at else None
                role_data = self.get_role_data(member)
                roles_json = json.dumps(role_data) if role_data else None
                
                # Enhanced profile data (optional)
                banner_url = None
                accent_color = None
                public_flags = None
                badges_json = None
                
                if enhanced:
                    try:
                        # Rate limiting
                        if i > 0 and i % 20 == 0:
                            print(f"⏳ Processed {i}/{len(guild.members)} members...")
                            await asyncio.sleep(3)
                        
                        # Fetch enhanced user data
                        full_user = await self.bot.fetch_user(member.id)
                        if full_user:
                            if full_user.banner:
                                banner_url = full_user.banner.url
                            if full_user.accent_color:
                                accent_color = full_user.accent_color.value
                            if hasattr(full_user, 'public_flags') and full_user.public_flags:
                                public_flags = full_user.public_flags.value
                                badges = self.parse_discord_badges(public_flags)
                                badges_json = json.dumps(badges) if badges else None
                                enhanced_count += 1
                            
                    except discord.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            print(f"⚠️  Rate limited, waiting...")
                            await asyncio.sleep(10)
                            continue
                    except Exception:
                        # Skip individual errors
                        pass
                
                # Update database
                db.upsert_user(
                    user_id=member.id,
                    username=member.name,
                    display_name=member.display_name,
                    avatar_url=avatar_url,
                    banner_url=banner_url,
                    accent_color=accent_color,
                    public_flags=public_flags,
                    joined_at=joined_at,
                    is_in_server=True,
                    roles=roles_json,
                    badges=badges_json
                )
            
            # Mark users who left the server
            all_db_users = db.get_all_users()
            left_count = 0
            for user in all_db_users:
                if user['is_in_server'] and user['user_id'] not in current_member_ids:
                    db.mark_user_left(user['user_id'])
                    left_count += 1
            
            if enhanced:
                print(f"✅ Synced {len(current_member_ids)} members ({enhanced_count} with enhanced data), marked {left_count} as left")
            else:
                print(f"✅ Synced {len(current_member_ids)} members (basic info), marked {left_count} as left")
            return {'success': True, 'count': len(current_member_ids), 'enhanced': enhanced_count}
            
        except Exception as e:
            print(f"❌ Sync error: {e}")
            return {'success': False, 'error': str(e)}
    
    def start_flask(self):
        """Start Flask server in a separate thread"""
        def run_flask():
            print("🌐 Starting integrated web dashboard...")
            print("📊 Dashboard available at http://localhost:5000")
            self.app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        if not self.app:
            self.setup_flask_app()
            self.start_flask()
            
            # Wait a moment then sync members
            await self.bot.wait_until_ready()
            await asyncio.sleep(3)  # Give Flask time to start
            
            print("🔄 Auto-syncing guild members (basic info)...")
            await self.sync_guild_members(enhanced=False)  # Only basic sync on startup
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Called when a member joins the guild"""
        avatar_url = member.display_avatar.url if member.display_avatar else None
        joined_at = member.joined_at.isoformat() if member.joined_at else None
        
        # Try to fetch enhanced profile data
        banner_url = None
        accent_color = None
        public_flags = None
        badges_json = None
        
        try:
            full_user = await self.bot.fetch_user(member.id)
            if full_user.banner:
                banner_url = full_user.banner.url
            if full_user.accent_color:
                accent_color = full_user.accent_color.value
            if hasattr(full_user, 'public_flags') and full_user.public_flags:
                public_flags = full_user.public_flags.value
                badges = self.parse_discord_badges(public_flags)
                badges_json = json.dumps(badges) if badges else None
        except:
            pass
        
        # Get role data
        role_data = self.get_role_data(member)
        roles_json = json.dumps(role_data) if role_data else None
        
        db.upsert_user(
            user_id=member.id,
            username=member.name,
            display_name=member.display_name,
            avatar_url=avatar_url,
            banner_url=banner_url,
            accent_color=accent_color,
            public_flags=public_flags,
            joined_at=joined_at,
            is_in_server=True,
            roles=roles_json,
            badges=badges_json
        )
        print(f"👋 Added new member: {member.display_name} ({member.id})")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Called when a member leaves the guild"""
        db.mark_user_left(member.id)
        print(f"👋 Marked member as left: {member.display_name} ({member.id})")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Called when a member's profile is updated"""
        # Check if roles changed or display info changed
        roles_changed = set(before.roles) != set(after.roles)
        profile_changed = (before.display_name != after.display_name or 
                          before.display_avatar != after.display_avatar)
        
        if roles_changed or profile_changed:
            avatar_url = after.display_avatar.url if after.display_avatar else None
            
            # Get updated role data
            role_data = self.get_role_data(after)
            roles_json = json.dumps(role_data) if role_data else None
            
            # Try to fetch updated profile data
            banner_url = None
            accent_color = None
            public_flags = None
            badges_json = None
            
            try:
                full_user = await self.bot.fetch_user(after.id)
                if full_user.banner:
                    banner_url = full_user.banner.url
                if full_user.accent_color:
                    accent_color = full_user.accent_color.value
                if hasattr(full_user, 'public_flags') and full_user.public_flags:
                    public_flags = full_user.public_flags.value
                    badges = self.parse_discord_badges(public_flags)
                    badges_json = json.dumps(badges) if badges else None
            except:
                pass
            
            db.upsert_user(
                user_id=after.id,
                username=after.name,
                display_name=after.display_name,
                avatar_url=avatar_url,
                banner_url=banner_url,
                accent_color=accent_color,
                public_flags=public_flags,
                is_in_server=True,
                roles=roles_json,
                badges=badges_json
            )
    
    @commands.command(name="sync_enhanced")
    @commands.has_permissions(administrator=True)
    async def sync_enhanced_command(self, ctx):
        """Manual command to sync enhanced profile data"""
        await ctx.send("🔄 Starting enhanced profile sync... This may take a while!")
        
        result = await self.sync_guild_members(enhanced=True)
        if result['success']:
            await ctx.send(f"✅ Enhanced sync completed! Processed {result['count']} members with {result['enhanced']} enhanced profiles.")
        else:
            await ctx.send(f"❌ Enhanced sync failed: {result['error']}")
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.enhanced_sync_task.cancel()

async def setup(bot):
    await bot.add_cog(WebDashboard(bot))