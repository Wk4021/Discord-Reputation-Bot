from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
import sys
import asyncio
import discord
from discord.ext import commands
import yaml
from datetime import datetime
from dotenv import load_dotenv
import threading
import time
import requests
import hmac
import hashlib
import json
from urllib.parse import urlencode
import secrets

# Load environment variables
load_dotenv()

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import db

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Configuration
CONFIG_PATH = '../data/config.yaml'
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0)) if os.getenv('GUILD_ID', '').replace('YOUR_GUILD_ID_HERE', '').strip() else None

# Discord OAuth2 Configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5000/auth/discord/callback')
DISCORD_API_BASE_URL = 'https://discord.com/api/v10'

# Global Discord client
discord_client = None
guild = None

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Discord OAuth2 Helper Functions
def get_discord_login_url():
    """Generate Discord OAuth2 login URL"""
    if not DISCORD_CLIENT_ID:
        return None
    
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify'
    }
    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return None
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': 'identify'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(f'{DISCORD_API_BASE_URL}/oauth2/token', data=data, headers=headers)
        print(f"DEBUG: Token exchange response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"DEBUG: Token response keys: {list(token_data.keys())}")
            return token_data
        else:
            print(f"DEBUG: Token exchange error response: {response.text}")
    except Exception as e:
        print(f"Error exchanging code for token: {e}")
    
    return None

def get_discord_user_info(access_token):
    """Get Discord user information using access token"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        print(f"DEBUG: Making request to Discord API with token: {access_token[:20]}...")  # Only show first 20 chars
        response = requests.get(f'{DISCORD_API_BASE_URL}/users/@me', headers=headers)
        print(f"DEBUG: Discord API response status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"DEBUG: Discord user data: {user_data}")
            return user_data
        else:
            print(f"DEBUG: Discord API error response: {response.text}")
    except Exception as e:
        print(f"Error getting Discord user info: {e}")
    
    return None

def is_user_in_guild(access_token, user_id):
    """Check if user is a member of the configured guild"""
    if not GUILD_ID:
        return True  # Skip check if no guild configured
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(f'{DISCORD_API_BASE_URL}/users/@me/guilds/{GUILD_ID}/member', headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking guild membership: {e}")
        return False

def sync_members_via_api():
    """Sync Discord members using REST API calls"""
    if not DISCORD_TOKEN or not GUILD_ID:
        return {'success': False, 'error': 'Discord token or guild ID not configured'}
    
    headers = {
        'Authorization': f'Bot {DISCORD_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        print("🔄 Fetching Discord server members via API...")
        
        # Get guild info
        guild_response = requests.get(f'https://discord.com/api/v10/guilds/{GUILD_ID}', headers=headers)
        if guild_response.status_code != 200:
            return {'success': False, 'error': f'Failed to fetch guild info: {guild_response.status_code}'}
        
        guild_data = guild_response.json()
        
        # Get all members (this might require pagination for large servers)
        members_response = requests.get(f'https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000', headers=headers)
        if members_response.status_code != 200:
            return {'success': False, 'error': f'Failed to fetch members: {members_response.status_code}'}
        
        members = members_response.json()
        current_member_ids = set()
        synced_count = 0
        
        for member_data in members:
            user = member_data['user']
            current_member_ids.add(int(user['id']))
            
            # Build avatar URL
            avatar_url = None
            if user.get('avatar'):
                avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
            
            # Get display name (nickname or global_name or username)
            display_name = member_data.get('nick') or user.get('global_name') or user['username']
            
            # Update user in database
            db.upsert_user(
                user_id=int(user['id']),
                username=user['username'],
                display_name=display_name,
                avatar_url=avatar_url,
                joined_at=member_data.get('joined_at'),
                is_in_server=True
            )
            synced_count += 1
        
        # Mark users who left the server
        all_db_users = db.get_all_users()
        left_count = 0
        for user in all_db_users:
            if user['is_in_server'] and user['user_id'] not in current_member_ids:
                db.mark_user_left(user['user_id'])
                left_count += 1
        
        print(f"✅ Synced {synced_count} members, marked {left_count} as left")
        return {
            'success': True, 
            'synced': synced_count, 
            'left': left_count,
            'guild_name': guild_data.get('name', 'Unknown'),
            'total_members': len(members)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request error: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return {'success': False, 'error': str(e)}

def get_user_stats(user_id):
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
        SELECT giver_id, rating, notes, created_at, thread_id
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
            'created_at': row[3],
            'thread_id': row[4]
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

def get_all_users_with_activity():
    """Get all users from the database with their review stats"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get all users from the users table with their stats
    c.execute("""
        SELECT 
            u.user_id,
            u.username,
            u.display_name,
            u.avatar_url,
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
        GROUP BY u.user_id, u.username, u.display_name, u.avatar_url, u.is_in_server, u.left_at, u.roles, u.badges
        ORDER BY u.is_in_server DESC, COALESCE(AVG(r_received.rating), 0) DESC, u.username ASC
    """)
    
    users_data = []
    for row in c.fetchall():
        # Parse JSON fields safely
        roles = []
        badges = []
        try:
            if row[6]:  # roles
                roles = json.loads(row[6])
        except (json.JSONDecodeError, TypeError):
            roles = []
            
        try:
            if row[7]:  # badges
                badges = json.loads(row[7])
        except (json.JSONDecodeError, TypeError):
            badges = []
        
        users_data.append({
            'user_id': row[0],
            'username': row[1],
            'display_name': row[2],
            'avatar_url': row[3],
            'is_in_server': bool(row[4]),
            'left_at': row[5],
            'roles': roles,
            'badges': badges,
            'avg_rating': float(row[8]),
            'total_reviews': row[9],
            'reviews_given': row[10]
        })
    
    conn.close()
    return users_data

def get_homepage_stats():
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

def get_guild_info():
    """Get Discord guild information via API and Widget API"""
    guild_info = None
    
    # Try to get guild info from Discord API first
    if DISCORD_TOKEN and GUILD_ID:
        headers = {
            'Authorization': f'Bot {DISCORD_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f'https://discord.com/api/v10/guilds/{GUILD_ID}', headers=headers)
            if response.status_code == 200:
                guild_data = response.json()
                icon_url = None
                if guild_data.get('icon'):
                    icon_url = f"https://cdn.discordapp.com/icons/{GUILD_ID}/{guild_data['icon']}.png"
                
                guild_info = {
                    'name': guild_data.get('name'),
                    'member_count': guild_data.get('approximate_member_count', 0),
                    'icon_url': icon_url,
                    'description': guild_data.get('description')
                }
        except Exception as e:
            print(f"Failed to fetch guild info from Bot API: {e}")
    
    # Fallback to Discord Widget API for public information
    if not guild_info and GUILD_ID:
        try:
            widget_response = requests.get(f'https://discord.com/api/guilds/{GUILD_ID}/widget.json')
            if widget_response.status_code == 200:
                widget_data = widget_response.json()
                
                # Extract member count from widget (count online members + estimate)
                online_members = len(widget_data.get('members', []))
                estimated_total = online_members * 3 if online_members > 0 else 0  # Rough estimate
                
                guild_info = {
                    'name': widget_data.get('name', 'Discord Server'),
                    'member_count': widget_data.get('presence_count', estimated_total),
                    'icon_url': None,  # Widget doesn't provide icon URL
                    'description': None,
                    'online_members': online_members,
                    'widget_available': True
                }
        except Exception as e:
            print(f"Failed to fetch widget info: {e}")
    
    return guild_info

def get_user_presence_from_widget(user_id):
    """Try to get user online status from Discord widget"""
    if not GUILD_ID:
        return None
    
    try:
        widget_response = requests.get(f'https://discord.com/api/guilds/{GUILD_ID}/widget.json')
        if widget_response.status_code == 200:
            widget_data = widget_response.json()
            members = widget_data.get('members', [])
            
            # Look for the user in online members
            for member in members:
                if str(member.get('id')) == str(user_id):
                    return member.get('status', 'online')  # online, idle, dnd, etc.
            
            # If not in online members but we have their data, they're probably offline
            return 'offline'
    except Exception as e:
        print(f"Failed to check user presence: {e}")
    
    return None

def get_recent_reviews(limit=6):
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
            'giver_name': row[2] or f'User {row[0]}',
            'giver_avatar': row[4],
            'receiver_name': row[5] or f'User {row[0]}',
            'receiver_avatar': row[7]
        })
    
    conn.close()
    return recent_reviews

# Authentication Routes
@app.route('/auth/discord')
def discord_login():
    """Redirect to Discord OAuth2 login"""
    login_url = get_discord_login_url()
    if not login_url:
        return render_template('error.html',
                             error_title="Discord Login Not Configured",
                             error_message="Discord OAuth2 authentication is not set up. Please configure DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET in your .env file.")
    return redirect(login_url)

@app.route('/auth/discord/callback')
def discord_callback():
    """Handle Discord OAuth2 callback"""
    try:
        code = request.args.get('code')
        if not code:
            return "Authorization failed", 400
        
        # Exchange code for token
        token_data = exchange_code_for_token(code)
        if not token_data:
            return "Failed to get access token", 400
        
        access_token = token_data.get('access_token')
        if not access_token:
            return "Invalid token response", 400
        
        # Get user information
        user_info = get_discord_user_info(access_token)
        if not user_info:
            return "Failed to get user information", 400
        
        print(f"DEBUG: User info from Discord: {user_info}")  # Debug log
        
        user_id = user_info.get('id')
        if not user_id:
            return "Invalid user data - no user ID", 400
        
        # Validate that user_id is numeric (Discord user IDs are numeric strings)
        try:
            int(user_id)  # Test if it's a valid integer
        except (ValueError, TypeError):
            print(f"ERROR: Invalid user_id received: {user_id}")
            return f"Invalid user ID format: {user_id}", 400
        
        user_id = str(user_id)  # Ensure it's a string
        
        # Skip guild membership check for now to avoid issues
        # TODO: Re-enable guild membership check once OAuth is working
        # if GUILD_ID and not is_user_in_guild(access_token, user_id):
        #     return render_template('error.html', 
        #                          error_title="Access Denied",
        #                          error_message="You must be a member of our Discord server to access this dashboard.")
        
        # Store user data in session
        session['user'] = {
            'id': user_id,
            'username': user_info.get('username', 'Unknown'),
            'discriminator': user_info.get('discriminator', ''),
            'avatar': user_info.get('avatar', ''),
            'global_name': user_info.get('global_name', ''),
            'access_token': access_token
        }
        
        # Sync user data to database
        try:
            avatar_url = None
            if user_info.get('avatar'):
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_info['avatar']}.png"
            
            db.upsert_user(
                user_id=int(user_id),
                username=user_info.get('username', 'Unknown'),
                display_name=user_info.get('global_name') or user_info.get('username', 'Unknown'),
                avatar_url=avatar_url,
                is_in_server=True
            )
        except Exception as e:
            print(f"Error syncing user to database: {e}")
        
        # Redirect to their profile or originally requested page
        next_page = session.get('next_page')
        if next_page:
            session.pop('next_page', None)
            return redirect(next_page)
        
        return redirect(url_for('user_profile', user_id=int(user_id)))
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return render_template('error.html',
                             error_title="Authentication Error", 
                             error_message=f"An error occurred during authentication: {str(e)}")

@app.route('/auth/logout')
def logout():
    """Log out the current user"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Homepage with server information and stats"""
    config = load_config()
    
    # Get overall stats
    stats = get_homepage_stats()
    
    # Get guild information
    guild_info = get_guild_info()
    
    # Get recent reviews
    recent_reviews = get_recent_reviews(6)
    
    return render_template('homepage.html', 
                         server_name=config.get('server_name'),
                         server_invite=config.get('server_invite'),
                         guild_info=guild_info,
                         guild_id=GUILD_ID,
                         stats=stats,
                         recent_reviews=recent_reviews,
                         discord_login_url=get_discord_login_url(),
                         current_user=session.get('user'))

@app.route('/users')
def users():
    """Users page showing all community members"""
    users = get_all_users_with_activity()
    return render_template('index.html', 
                         users=users,
                         discord_login_url=get_discord_login_url(),
                         current_user=session.get('user'))

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    """User profile page"""
    stats = get_user_stats(user_id)
    return render_template('user_profile.html', 
                         user_id=user_id, 
                         stats=stats,
                         discord_login_url=get_discord_login_url(),
                         current_user=session.get('user'))

@app.route('/profile')
def my_profile():
    """Redirect to current user's profile"""
    current_user = session.get('user')
    if not current_user:
        session['next_page'] = url_for('my_profile')
        return redirect(url_for('discord_login'))
    
    return redirect(url_for('user_profile', user_id=current_user['id']))

@app.route('/api/discord_user/<int:user_id>')
def get_discord_user_info(user_id):
    """API endpoint to get Discord user information"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db.DB_PATH)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT username, display_name, avatar_url, banner_url, accent_color, is_in_server, roles, badges
        FROM users WHERE user_id = ?
    """, (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        # Parse JSON fields safely
        roles = []
        badges = []
        try:
            if result[6]:  # roles
                roles = json.loads(result[6])
        except (json.JSONDecodeError, TypeError):
            roles = []
            
        try:
            if result[7]:  # badges
                badges = json.loads(result[7])
        except (json.JSONDecodeError, TypeError):
            badges = []
        
        # Try to get real-time status from Discord widget
        presence = get_user_presence_from_widget(user_id) if result[5] else None
        
        if presence == 'online':
            status = 'Online'
        elif presence == 'idle':
            status = 'Away'
        elif presence == 'dnd':
            status = 'Do Not Disturb'
        elif presence == 'offline':
            status = 'Offline'
        elif result[5]:  # is_in_server but no presence data
            status = 'Member'
        else:
            status = 'Left Server'
        
        return jsonify({
            'id': user_id,
            'username': result[0] or 'Unknown',
            'display_name': result[1] or result[0] or 'Unknown',
            'avatar_url': result[2] or f'https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png',
            'banner_url': result[3],
            'accent_color': result[4],
            'status': status,
            'roles': roles,
            'badges': badges
        })
    else:
        # Fallback for users not in database
        return jsonify({
            'id': user_id,
            'username': f'User{user_id}',
            'display_name': f'User {user_id}',
            'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png',
            'banner_url': None,
            'accent_color': None,
            'status': 'Not Found',
            'roles': [],
            'badges': []
        })

@app.route('/api/thread_info/<int:thread_id>')
def get_thread_info_api(thread_id):
    """API endpoint to get Discord thread information"""
    thread_info = db.get_thread_info(thread_id)
    
    if thread_info:
        return jsonify({
            'id': thread_info['thread_id'],
            'name': thread_info['name'],
            'url': thread_info['jump_url'],
            'created_at': thread_info['created_at'],
            'archived': thread_info['archived'],
            'locked': thread_info['locked'],
            'owner_id': thread_info['owner_id'],
            'channel_id': thread_info['channel_id'],
            'guild_id': thread_info['guild_id']
        })
    else:
        # Fallback for threads not in database yet
        return jsonify({
            'id': thread_id,
            'name': f'Thread {thread_id}',
            'url': f'https://discord.com/channels/{GUILD_ID or "GUILD_ID"}/CHANNEL_ID/{thread_id}',
            'created_at': '2024-01-01T00:00:00Z',
            'archived': False,
            'locked': False,
            'owner_id': None,
            'error': 'Thread not found in database'
        })

@app.route('/api/sync_members', methods=['POST'])
def sync_members():
    """API endpoint to manually sync Discord members"""
    try:
        result = sync_members_via_api()
        if result['success']:
            return jsonify({
                'status': 'success', 
                'message': f'Synced {result["synced"]} members',
                'data': result
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': result['error']
            }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def generate_star_display(rating):
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

# Template filters
@app.template_filter('star_display')
def star_display_filter(rating):
    return generate_star_display(rating)

@app.template_filter('format_date')
def format_date_filter(date_str):
    if not date_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return date_str

# Template context processor
@app.context_processor
def inject_config():
    return {'config': load_config()}

if __name__ == '__main__':
    print("🌐 Starting Discord Review Dashboard...")
    print("📊 Dashboard will be available at http://localhost:5000")
    
    # Initialize database
    db.init_db()
    
    # Check Discord configuration
    if DISCORD_TOKEN and GUILD_ID:
        print("🤖 Discord integration configured (using REST API)")
        print("   Use the 'Sync' button to fetch server members")
    else:
        print("⚠️  Discord integration disabled (missing token or guild ID)")
        print("   Add DISCORD_TOKEN and GUILD_ID to .env file to enable")
    
    app.run(debug=True, host='0.0.0.0', port=5000)