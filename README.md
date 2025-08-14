<!-- PROJECT BADGES -->
<p align="center">
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/actions"><img src="https://img.shields.io/github/actions/workflow/status/Wk4021/Marketplace-Discord-Rep-Bot/ci.yml?style=for-the-badge" alt="CI Status"/></a>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/stargazers"><img src="https://img.shields.io/github/stars/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="GitHub Stars"/></a>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues"><img src="https://img.shields.io/github/issues/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="GitHub Issues"/></a>
  <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458"><img src="https://img.shields.io/discord/765205625524584458?style=for-the-badge" alt="Discord Server"/></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge" alt="Python Version"/>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="License"/></a>
</p>

# 🌟 Discord Reputation Bot V3.0-beta

A **complete reputation system** for Discord marketplace communities featuring **star ratings**, **detailed reviews**, **integrated web dashboard**, and **professional moderation tools**. Transform your Discord server into a trusted marketplace with TOS gating, review management, comprehensive user analytics, and live Discord integration.

## 🆕 **What's New in V3.0-beta**
- ⭐ **Star Rating System** (1-10 ratings with visual stars)
- 📝 **Detailed Reviews** (text reviews with rating modal)
- 🌐 **Integrated Web Dashboard** (real-time Discord widget integration)
- 🎨 **Dark/Light Mode** (theme-aware interface with automatic Discord widget switching)
- 🔗 **Thread Tracking** (direct links to Discord posts from reviews)
- 👑 **Admin System** (force close posts, manage admins)
- 📊 **Enhanced UI** (improved embeds and user experience)
- 🔧 **Modular Architecture** (separated logging system)

---

## 🚀 Features

### 🔒 **TOS Gating & Thread Management**
- **Smart TOS Prompts**: New threads require Terms of Service acceptance
- **Live Countdown**: Discord timestamps show exact timeout
- **Message Protection**: Auto-delete messages before TOS acceptance
- **Auto-Close**: Threads close automatically if unattended
- **Admin Override**: Admins can force close any post

### ⭐ **Advanced Review System**
- **1-10 Star Ratings**: Detailed rating system with visual stars
- **Review Modal**: Professional popup for collecting ratings and notes
- **Review Notes**: Detailed text feedback (up to 500 characters)
- **Latest Reviews**: Display recent reviews with full context
- **Average Ratings**: Smart calculation with star visualization
- **Review History**: Complete review timeline for users

### 🌐 **Integrated Web Dashboard**
- **Live Discord Widget**: Real-time server activity and member status
- **User Directory**: Complete list with search and filtering
- **User Profiles**: Discord avatars, banners, roles, and badges
- **Review Analytics**: Average ratings, review counts, activity metrics
- **Post History**: Direct links to Discord threads with real URLs
- **Dark/Light Mode**: Theme toggle with Discord widget synchronization
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Real-time Data**: Live updates from Discord API and database
- **Thread Integration**: Persistent Discord post links stored in database

### 👑 **Admin System**
- **Configurable Admins**: Add/remove admins via commands
- **Force Close**: Override close restrictions for moderation
- **Admin Commands**: `/admin_add`, `/admin_remove`, `/admin_list`
- **Enhanced Logging**: Track admin actions and user activity
- **Permission Checking**: Smart role-based permissions

### 📊 **Analytics & Reporting**
- **User Statistics**: Comprehensive user activity tracking
- **Leaderboards**: Top rated users and most active reviewers
- **Review Insights**: Detailed review analysis with direct post links
- **Thread Tracking**: Persistent Discord thread data storage
- **Live Server Stats**: Real-time member count and online activity
- **Export Ready**: Database designed for analytics with thread URLs

### 🛠️ **Modern Architecture**
- **Modular Design**: Separated logging, review, and web systems
- **Enhanced Database**: Thread tracking with Discord URLs
- **API Integration**: RESTful endpoints for web dashboard and Discord
- **Theme System**: CSS variables for light/dark mode switching
- **Error Handling**: Comprehensive error management and logging
- **Scalable**: Designed for high-volume communities with real-time updates

---

## 📁 Project Structure

```bash
Discord-Reputation-Bot/
├── 🚀 RunMe.bat                    # Interactive launcher (Discord + Web)
├── 🌐 start_dashboard.bat          # Quick web dashboard launcher
├── 🤖 bot.py                       # Discord bot entry point
├── 📋 requirements.txt             # All dependencies (bot + web)
├── cogs/                           # Discord bot modules
│   ├── rep.py                      # Review system (star ratings + modals)
│   └── logging.py                  # Modular logging system
├── utils/                          # Database and utilities
│   └── db.py                       # Enhanced database (reviews + thread tracking)
├── data/                           # Configuration and database
│   ├── config.yaml                 # Settings (forums, admins, messages)
│   └── rep.db                      # SQLite database (auto-created)
├── assets/                         # Static content
│   └── rep_messages.txt            # Review response messages
├── web_dashboard/                  # Web interface
│   ├── app.py                      # Flask web application
│   ├── run_dashboard.py            # Dashboard launcher
│   ├── templates/                  # HTML templates
│   │   ├── base.html               # Base layout with theme system
│   │   ├── homepage.html           # Homepage with Discord widget
│   │   ├── index.html              # User directory
│   │   └── user_profile.html       # User profile with post links
│   ├── static/                     # Static web assets
│   │   ├── css/style.css           # Discord-themed styling + dark mode
│   │   ├── js/main.js              # Interactive JavaScript
│   │   └── images/                 # Image assets
│   └── utils/                      # Web utilities
│       └── discord_integration.py  # Discord API integration
├── guides/                         # Documentation
│   ├── ADMIN_GUIDE.md              # Admin system guide
│   ├── STARTUP_GUIDE.md            # Complete startup guide
│   ├── WEB_DASHBOARD_GUIDE.md      # Web dashboard documentation
│   ├── LOGGING_GUIDE.md            # Logging system guide
│   ├── REVIEW_SYSTEM_MIGRATION.md  # Migration from old system
│   ├── CLOSE_POST_FLOW.md          # Post closing workflow
│   └── WEB_DASHBOARD_FEATURES.md   # Web features overview
├── unused/                         # Deprecated files
│   ├── example_cog.py              # Example integration code
│   └── web_dashboard_requirements.txt # Old requirements file
└── .env                            # Discord bot token (create this)
```

---

## 🚀 Quick Start

### **Option 1: Easy Setup (Windows)**
1. **Download and extract** the bot files
2. **Double-click `RunMe.bat`** to open the interactive menu
3. **Select `[4] Install/Update Requirements`** to install all dependencies
4. **Create `.env` file** with your Discord bot token (see step 3 below)
5. **Configure `data/config.yaml`** with your server settings (see step 4 below)
6. **Select `[3] Both`** from the menu to start Discord bot + Web dashboard

### **Option 2: Manual Setup**

1. **Clone & install dependencies**
   ```bash
   git clone https://github.com/Wk4021/Marketplace-Discord-Rep-Bot.git
   cd Marketplace-Discord-Rep-Bot
   pip install -r requirements.txt
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Create `.env` file**
   ```env
   DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
   ```

4. **Configure `data/config.yaml`**
   ```yaml
   # Basic Configuration
   forums:
     - 123456789012345678   # Your forum channel IDs
   log_channel: 987654321098765432  # Log channel ID
   admin_ids:              # Admin user IDs
     - 111222333444555666  # Your admin user ID
     - 777888999000111222  # Additional admin IDs
   
   # Web Dashboard Settings (Optional)
   server_name: "Your Server Name"
   server_invite: "https://discord.gg/yourinvite"
   
   # TOS Messages
   tos_message: |
     Please review our Terms of Service in <#123456789012345678>
     and then click ✅ to agree or ❌ to decline.
     If you do not respond within {timeout}, this post will be automatically closed.
   tos_decline_response: |
     Marketplace terms not accepted. Thread will now be closed.
   
   # Rep Messages
   no_rep_messages:
     - "Damn, get your rep up! 📈"
     - "Zero rep? 🚨 Proceed with caution!"
     - "No rep? Bold move. 🚀"
     - "Are you new here? 🤔"
     # Add more creative messages!
   ```

5. **Launch Services**
   
   **Discord Bot Only:**
   ```bash
   python bot.py
   ```
   
   **Web Dashboard Only:**
   ```bash
   python start_dashboard.bat
   # or manually:
   cd web_dashboard
   python run_dashboard.py
   ```
   
   **Both Services:**
   - Use `RunMe.bat` menu option `[3]`
   - Or run both commands in separate terminals

6. **Access Web Dashboard**
   - Open browser to: **http://localhost:5000**
   - View user profiles, reviews, and analytics

7. **Invite Bot & Sync Commands**
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=8
   ```
   - Use `!sync` in Discord to register slash commands (may take up to 1 hour)

---

## ⭐ New Review System

### **How It Works**
1. **User clicks "⭐ Leave a Review"** button in Discord thread
2. **Modal popup appears** requesting rating (1-10) and optional notes
3. **Review is saved** to database with timestamp
4. **UI updates** showing new average rating and latest reviews
5. **Web dashboard** displays comprehensive review history

### **Star Display Examples**

| Rating | Stars Display | Description |
|--------|---------------|-------------|
| 10/10  | ⭐⭐⭐⭐⭐ | Perfect rating |
| 9/10   | ⭐⭐⭐⭐✨ | Excellent with half star |
| 8/10   | ⭐⭐⭐⭐☆ | Very good |
| 6/10   | ⭐⭐⭐☆☆ | Average |
| 3/10   | ⭐✨☆☆☆ | Below average |
| 1/10   | ✨☆☆☆☆ | Poor rating |

### **Available Commands**

| Command | Description |
|---------|-------------|
| `/reviews @user` | View user's rating and recent reviews |
| `/leaderboard` | Top 10 highest rated users |
| `/admin_add @user` | Add user as admin (admin only) |
| `/admin_remove @user` | Remove admin privileges (admin only) |
| `/admin_list` | View all current admins (admin only) |
| `/channel_set #forum` | Enable reviews for forum channel |
| `/log #channel` | Set log channel for review notifications |

---

## 🌐 Web Dashboard

### **Features**
- **Live Discord Widget**: Real-time server activity with online members
- **User Directory**: Browse all community members with advanced search
- **Dark/Light Mode**: Toggle themes with automatic Discord widget switching
- **User Profiles**: Discord avatars, banners, roles, badges, and comprehensive stats
- **Post History**: Direct "View Post" buttons linking to Discord threads
- **Review Analytics**: Complete review timeline with Discord post integration
- **Mobile Responsive**: Adaptive layouts for all devices

### **Access**
- **Local**: http://localhost:5000
- **Features**: Real-time Discord integration with persistent thread tracking
- **No Setup Required**: Automatically uses Discord bot config and guild settings

---

## 📚 Documentation

Comprehensive guides are available in the `guides/` folder:

- **[STARTUP_GUIDE.md](guides/STARTUP_GUIDE.md)** - Complete setup instructions
- **[WEB_DASHBOARD_GUIDE.md](guides/WEB_DASHBOARD_GUIDE.md)** - Web interface documentation  
- **[ADMIN_GUIDE.md](guides/ADMIN_GUIDE.md)** - Admin system management
- **[REVIEW_SYSTEM_MIGRATION.md](guides/REVIEW_SYSTEM_MIGRATION.md)** - Migration from v2.x
- **[LOGGING_GUIDE.md](guides/LOGGING_GUIDE.md)** - Logging system documentation
- **[CLOSE_POST_FLOW.md](guides/CLOSE_POST_FLOW.md)** - Post closing workflow

---

## ❓ Troubleshooting & FAQ

### **Common Issues**

**Q: "No module named 'flask'" error?**
A: Run the requirements installer: `RunMe.bat` → `[4] Install/Update Requirements`

**Q: Web dashboard shows no users?**
A: Make sure Discord bot has run first to create database with review data

**Q: Discord widget not loading?**
A: Verify your server has widget enabled in Discord Server Settings → Widget

**Q: "View Post" buttons not working?**
A: Ensure Discord bot has been running to save thread information to database

**Q: Port 5000 already in use?**
A: Close other applications or edit `web_dashboard/app.py` to use different port

**Q: Dark mode not switching Discord widget theme?**
A: Check browser console for JavaScript errors and ensure widget iframe loads properly

**Q: Slash commands not appearing?**
A: Use `!sync` command and wait up to 1 hour for global registration

**Q: How do I get Discord user IDs for admin config?**
A: Enable Developer Mode in Discord, right-click user → Copy User ID

### **Support**

**🐛 Bug Reports**: [Open an issue](https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues)
**💡 Feature Requests**: Fork the repo and submit a pull request
**💬 Community**: Join our [Discord server](https://discord.com/servers/marketplace-and-student-stores-765205625524584458)

### **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

**Don't forget to ⭐ the project if you find it helpful!**

---

<p align="center">
  <strong>🌟 Discord Reputation Bot V3.0-beta 🌟</strong><br/>
  <em>Transform your Discord server into a trusted marketplace</em>
</p>

<p align="center">
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-web-dashboard">🌐 Web Dashboard</a> •
  <a href="#-documentation">📚 Docs</a> •
  <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458">💬 Discord</a>
</p>

<p align="center">
  <strong>⭐ If you find this bot useful, please give it a star! ⭐</strong><br/>
  <em>Join our community:</em> <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458">Marketplace & Student Stores</a>
</p>

---

<p align="center">
  <sub>Built with ❤️ for Discord marketplace communities</sub>
</p>
