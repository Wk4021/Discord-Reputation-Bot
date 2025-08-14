# 📚 Discord Reputation Bot - Documentation Index

Welcome to the comprehensive documentation for Discord Reputation Bot V3.0-beta. This folder contains detailed guides for all aspects of the bot and web dashboard.

## 🚀 Getting Started

### **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)**
**Complete setup and launch guide**
- Interactive menu system (`RunMe.bat`)
- Installation and configuration
- Virtual environment setup
- Launch options and troubleshooting
- Best practices for deployment

*Start here if you're new to the bot!*

## 🌐 Web Dashboard

### **[WEB_DASHBOARD_GUIDE.md](WEB_DASHBOARD_GUIDE.md)**
**Complete web interface documentation**
- Installation and setup
- User directory and search
- Profile pages and review history
- Discord integration features
- Customization and deployment

### **[WEB_DASHBOARD_FEATURES.md](WEB_DASHBOARD_FEATURES.md)**
**Detailed feature overview**
- UI/UX components
- Technical architecture
- API endpoints
- Performance features
- Mobile responsiveness

## 👑 Administration

### **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)**
**Admin system management**
- Admin configuration in `config.yaml`
- Admin management commands
- Force close privileges
- Safety features and best practices
- User ID management

### **[CLOSE_POST_FLOW.md](CLOSE_POST_FLOW.md)**
**Post closing workflow**
- Owner vs admin closing
- Review requirements
- Confirmation modals
- Different closing scenarios
- Logging and tracking

## ⭐ Review System

### **[REVIEW_SYSTEM_MIGRATION.md](REVIEW_SYSTEM_MIGRATION.md)**
**Migration from old +/- rep system**
- New star rating features (1-10 scale)
- Review modal and notes system
- Database schema changes
- UI improvements and enhancements
- Backward compatibility

## 🔧 Technical Guides

### **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)**
**Modular logging system**
- Separated logging architecture
- Integration with other cogs
- Thread and event tracking
- API and usage examples
- Customization options

## 📋 Quick Reference

### **Essential Commands**
| Command | Description | Permission |
|---------|-------------|------------|
| `/reviews @user` | View user reviews | Everyone |
| `/leaderboard` | Top rated users | Everyone |
| `/admin_add @user` | Add admin | Admin only |
| `/admin_list` | View admins | Admin only |
| `/channel_set #forum` | Enable forum | Admin only |

### **File Structure Overview**
```
Discord-Reputation-Bot/
├── 🚀 RunMe.bat              # Interactive launcher
├── 🌐 start_dashboard.bat    # Web dashboard launcher
├── 🤖 bot.py                 # Discord bot
├── cogs/                     # Bot modules
├── web_dashboard/            # Web interface
├── guides/                   # Documentation (you are here)
├── data/                     # Config and database
└── utils/                    # Utilities
```

### **Key Configuration Files**
- **`.env`** - Discord bot token
- **`data/config.yaml`** - Forums, admins, messages
- **`data/rep.db`** - SQLite database (auto-created)

## 🎯 Common Use Cases

### **New Installation**
1. Read [STARTUP_GUIDE.md](STARTUP_GUIDE.md)
2. Configure `.env` and `config.yaml`
3. Use `RunMe.bat` → `[4]` to install requirements
4. Launch with `[3] Both` for full functionality

### **Adding Admins**
1. Get Discord user ID (Developer Mode → Right-click → Copy ID)
2. Add to `admin_ids` in `config.yaml`
3. Or use `/admin_add @user` command

### **Setting Up Web Dashboard**
1. Follow [WEB_DASHBOARD_GUIDE.md](WEB_DASHBOARD_GUIDE.md)
2. Launch with `RunMe.bat` → `[2]` or `start_dashboard.bat`
3. Access at http://localhost:5000

### **Migrating from Old System**
1. Read [REVIEW_SYSTEM_MIGRATION.md](REVIEW_SYSTEM_MIGRATION.md)
2. Existing data is preserved automatically
3. New features work alongside old data

## 🔍 Troubleshooting

### **Installation Issues**
- Use `RunMe.bat` → `[4]` for automatic installation
- Check Python version (3.9+ required)
- Verify virtual environment activation

### **Discord Bot Issues**
- Ensure bot token is correct in `.env`
- Check bot permissions in Discord server
- Use `!sync` to register slash commands

### **Web Dashboard Issues**
- Verify port 5000 is available
- Check that bot has created database first
- Review browser console for JavaScript errors

### **Permission Issues**
- Verify admin IDs in `config.yaml`
- Check Discord permissions for bot
- Ensure users have required roles

## 📖 Additional Resources

### **Development**
- All guides include technical implementation details
- Database schema documented in migration guide
- API endpoints covered in web dashboard guide

### **Community**
- [GitHub Issues](https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues) for bug reports
- [Discord Server](https://discord.com/servers/marketplace-and-student-stores-765205625524584458) for community support
- Pull requests welcome for contributions

### **Updates**
- Check README.md for version information
- Review migration guides before updating
- Backup database before major updates

---

<p align="center">
  <strong>Need help?</strong> Start with <a href="STARTUP_GUIDE.md">STARTUP_GUIDE.md</a> or check the specific guide for your needs!
</p>

<p align="center">
  <sub>📚 Documentation maintained for Discord Reputation Bot V3.0-beta</sub>
</p>