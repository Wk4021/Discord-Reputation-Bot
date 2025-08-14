# Discord Reputation Bot - Startup Guide

## 🚀 Quick Start Options

The Discord Reputation Bot now includes multiple components that can be run individually or together:

### **Option 1: Interactive Menu (Recommended)**
Double-click `RunMe.bat` to open the interactive menu:

```
═══════════════════════════════════════════════════════════
             Discord Reputation Bot V3.0-beta
═══════════════════════════════════════════════════════════

Choose what to run:
  [1] Discord Bot (Main bot functionality)
  [2] Web Dashboard (User interface at http://localhost:5000)
  [3] Both (Bot + Dashboard in separate windows)
  [4] Install/Update Requirements
  [0] Exit
```

### **Option 2: Quick Dashboard Launch**
Double-click `start_dashboard.bat` to launch only the web dashboard.

### **Option 3: Manual Launch**
Run components manually:
```bash
# Discord Bot
python bot.py

# Web Dashboard
cd web_dashboard
python run_dashboard.py
```

## 📋 Menu Options Explained

### **[1] Discord Bot**
- Starts the main Discord bot
- Handles reviews, forums, and user interactions
- Required for Discord functionality
- Runs in the current window

### **[2] Web Dashboard**
- Starts the web interface at http://localhost:5000
- View user profiles, reviews, and ratings
- Browse community activity
- Runs in the current window

### **[3] Both Services**
- Starts Discord bot in one window
- Starts web dashboard in another window
- Both services run simultaneously
- Original window can be closed

### **[4] Install/Update Requirements**
- Installs Python dependencies
- Updates existing packages
- Works with virtual environments
- Returns to main menu when complete

## 🔧 Requirements & Dependencies

### **Updated requirements.txt includes:**

**Discord Bot Requirements:**
- discord.py>=2.3.2
- PyYAML
- python-dotenv

**Web Dashboard Requirements:**
- Flask==2.3.3
- Werkzeug==2.3.7
- Jinja2==3.1.2
- MarkupSafe==2.1.3
- click==8.1.7
- itsdangerous==2.1.2

**Shared Dependencies:**
- aiohttp, aiosignal, async-timeout
- attrs, charset-normalizer
- frozenlist, multidict, yarl

### **Installation Methods:**

**Using the Menu:**
1. Run `RunMe.bat`
2. Select option `[4] Install/Update Requirements`
3. Wait for installation to complete

**Manual Installation:**
```bash
pip install -r requirements.txt
```

**With Virtual Environment:**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 🌐 Web Dashboard Access

### **URLs:**
- **Local Access**: http://localhost:5000
- **Network Access**: http://0.0.0.0:5000 (if firewall allows)

### **Features:**
- User directory with search
- Individual user profiles
- Review history and ratings
- Active post tracking
- Discord profile integration
- Responsive mobile design

## 🗂️ File Structure

```
Discord-Reputation-Bot/
├── RunMe.bat                 # Main interactive launcher
├── start_dashboard.bat       # Quick dashboard launcher
├── bot.py                    # Discord bot main file
├── requirements.txt          # All dependencies (bot + web)
├── data/
│   ├── config.yaml          # Bot configuration
│   └── rep.db              # Review database
├── cogs/                    # Bot modules
│   ├── rep.py              # Review system
│   └── logging.py          # Logging system
├── utils/
│   └── db.py              # Database functions
└── web_dashboard/          # Web interface
    ├── app.py             # Flask application
    ├── run_dashboard.py   # Dashboard launcher
    ├── templates/         # HTML templates
    ├── static/           # CSS, JS, images
    └── utils/            # Web utilities
```

## ⚙️ Configuration

### **Discord Bot Setup:**
1. Create Discord application at https://discord.com/developers/applications
2. Copy bot token to `.env` file:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```
3. Configure `data/config.yaml` with your server settings

### **Web Dashboard Setup:**
- No additional configuration required
- Uses same database and config as Discord bot
- Automatically starts on port 5000

## 🔧 Troubleshooting

### **Common Issues:**

**"No module named 'flask'":**
- Run option `[4]` from the menu to install requirements
- Or manually: `pip install -r requirements.txt`

**"Port 5000 already in use":**
- Close other applications using port 5000
- Or edit `web_dashboard/app.py` to use different port

**"Database not found":**
- Run the Discord bot first to create the database
- Make sure `data/rep.db` exists

**Virtual environment not working:**
- Create new venv: `python -m venv .venv`
- Activate: `.venv\Scripts\activate`
- Install requirements: `pip install -r requirements.txt`

### **Getting Help:**
- Check console output for error messages
- Verify all requirements are installed
- Ensure Discord bot token is configured
- Make sure port 5000 is available

## 🎯 Best Practices

### **For Development:**
- Use virtual environment
- Run both bot and dashboard for full functionality
- Check web dashboard for user activity monitoring

### **For Production:**
- Keep bot running 24/7 for Discord functionality
- Run dashboard as needed for administration
- Use process manager (PM2, supervisord) for auto-restart

### **For Testing:**
- Install requirements first
- Test bot functionality before web dashboard
- Check both components work independently

## 📊 Usage Statistics

### **Typical Startup Process:**
1. **First Time**: Run `[4]` to install requirements
2. **Daily Use**: Run `[3]` for both services
3. **Administration**: Run `[2]` for web dashboard only
4. **Discord Only**: Run `[1]` for bot functionality

### **Performance Notes:**
- Discord bot: ~50MB RAM usage
- Web dashboard: ~30MB RAM additional
- Combined: Suitable for VPS with 1GB+ RAM
- Database grows ~1MB per 1000 reviews

This comprehensive startup system makes it easy to run and manage your Discord Reputation Bot with its new web dashboard interface!