from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import sys
import asyncio
import discord
from discord.ext import commands
import yaml
from datetime import datetime

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
CONFIG_PATH = '../data/config.yaml'
GUILD_ID = None  # Will be set from config

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_discord_client():
    """Initialize Discord client for API calls"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    return commands.Bot(command_prefix="!", intents=intents)

def get_user_stats(user_id):
    """Get comprehensive user statistics"""
    conn = sqlite3.connect('../' + db.DB_PATH)
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

def get_all_users_with_activity():
    """Get all users who have either given or received reviews"""
    conn = sqlite3.connect('../' + db.DB_PATH)
    c = conn.cursor()
    
    # Get all unique user IDs from reviews
    c.execute("""
        SELECT DISTINCT receiver_id as user_id FROM reviews
        UNION
        SELECT DISTINCT giver_id as user_id FROM reviews
        ORDER BY user_id
    """)
    
    user_ids = [row[0] for row in c.fetchall()]
    users_data = []
    
    for user_id in user_ids:
        stats = get_user_stats(user_id)
        users_data.append({
            'user_id': user_id,
            'avg_rating': stats['avg_rating'],
            'total_reviews': stats['total_reviews'],
            'reviews_given': stats['reviews_given']
        })
    
    conn.close()
    return sorted(users_data, key=lambda x: x['avg_rating'], reverse=True)

@app.route('/')
def index():
    """Main page showing all users"""
    users = get_all_users_with_activity()
    return render_template('index.html', users=users)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    """User profile page"""
    stats = get_user_stats(user_id)
    return render_template('user_profile.html', user_id=user_id, stats=stats)

@app.route('/api/discord_user/<int:user_id>')
def get_discord_user_info(user_id):
    """API endpoint to get Discord user information"""
    # This would require a running Discord bot instance
    # For now, return mock data structure
    return jsonify({
        'id': user_id,
        'username': f'User{user_id}',
        'display_name': f'Display User {user_id}',
        'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{user_id % 5}.png',
        'banner_url': None,
        'status': 'Unknown'
    })

@app.route('/api/thread_info/<int:thread_id>')
def get_thread_info(thread_id):
    """API endpoint to get Discord thread information"""
    # Mock thread data - would need Discord API integration
    return jsonify({
        'id': thread_id,
        'name': f'Thread {thread_id}',
        'url': f'https://discord.com/channels/GUILD_ID/CHANNEL_ID/{thread_id}',
        'created_at': '2024-01-01T00:00:00Z',
        'archived': False,
        'owner_id': 123456789
    })

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

if __name__ == '__main__':
    print("🌐 Starting Discord Review Dashboard...")
    print("📊 Dashboard will be available at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)