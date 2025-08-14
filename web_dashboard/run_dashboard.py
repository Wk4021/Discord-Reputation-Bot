#!/usr/bin/env python3
"""
Discord Review Dashboard Launcher
Run this script to start the web dashboard server.
"""

import os
import sys
import asyncio
from app import app

def main():
    print("=" * 60)
    print("🌐 Discord Review Dashboard")
    print("=" * 60)
    print()
    print("📋 Features:")
    print("  • User profiles with Discord avatars and banners")
    print("  • Review ratings and star displays")
    print("  • Active post tracking with Discord links")
    print("  • Responsive design for mobile and desktop")
    print("  • Real-time search and filtering")
    print()
    print("🔧 Setup:")
    print("  1. Make sure your Discord bot is running")
    print("  2. Update config.yaml with your Discord settings")
    print("  3. Install requirements: pip install -r requirements.txt")
    print()
    print("🚀 Starting dashboard server...")
    print("📊 Dashboard will be available at:")
    print("   • Local: http://localhost:5000")
    print("   • Network: http://0.0.0.0:5000")
    print()
    print("💡 Tips:")
    print("  • Use Ctrl+C to stop the server")
    print("  • Check the console for any errors")
    print("  • Make sure port 5000 is available")
    print()
    print("-" * 60)
    
    try:
        # Check if requirements are installed
        try:
            import flask
            import discord
            import yaml
        except ImportError as e:
            print(f"❌ Missing requirement: {e}")
            print("Please install requirements: pip install -r requirements.txt")
            return 1
        
        # Check if database exists
        db_path = os.path.join('..', 'data', 'rep.db')
        if not os.path.exists(db_path):
            print("⚠️  Database not found. Make sure the Discord bot has been run at least once.")
            print("   The dashboard will still work but may not have data to display.")
            print()
        
        # Check if config exists
        config_path = os.path.join('..', 'data', 'config.yaml')
        if not os.path.exists(config_path):
            print("❌ Config file not found. Please make sure config.yaml exists in the data folder.")
            return 1
        
        print("✅ All checks passed! Starting server...")
        print()
        
        # Start Flask app
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n")
        print("👋 Dashboard server stopped by user.")
        return 0
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())