# Discord Review Dashboard V3.0-beta

A comprehensive web interface for viewing Discord user profiles, reviews, and forum activity with **live Discord integration** and **theme-aware design**.

## ✨ New Features in V3.0-beta

### 🎯 **Live Discord Widget Integration**
- **Real-time Server Activity**: Live Discord widget showing online members
- **Theme-Aware Widget**: Automatically switches between light/dark based on user preference
- **Server Statistics**: Live member count and activity metrics
- **Direct Server Access**: Join server button with invite integration

### 🎨 **Dark/Light Mode System**
- **Theme Toggle**: Manual light/dark mode switching
- **System Theme Detection**: Automatic theme based on browser preference
- **Discord Widget Sync**: Widget theme changes with dashboard theme
- **CSS Variables**: Complete theming system with smooth transitions

### 🔗 **Thread Tracking & Post Links**
- **"View Post" Buttons**: Direct links from reviews to Discord posts
- **Persistent Thread Storage**: Database tracks all Discord thread information
- **Real Discord URLs**: No more mock links - real Discord jump URLs
- **Post History**: Renamed from "Active Posts" for better clarity

## 🚀 Enhanced Features

### 🏠 **User Directory**
- **Complete User List**: View all users who have participated in the review system
- **Advanced Search**: Search by username, display name, or user ID with real-time filtering
- **Multiple Views**: All Users, Top Rated, and Most Active tabs
- **Real-time Stats**: Rating, review count, and activity metrics with live updates

### 👤 **User Profiles** 
- **Enhanced Discord Integration**: Shows real avatars, banners, roles, and badges
- **Comprehensive Stats**: Average rating, reviews given/received, post history
- **Review History**: Latest reviews received and given with "View Post" buttons
- **Post History**: Direct links to Discord threads with persistent URLs

### ⭐ **Review Display**
- **Star Rating System**: Visual 5-star display based on 1-10 ratings
- **Review Notes**: Full text reviews with timestamps and Discord links
- **Reviewer Information**: See who left each review with their complete profile
- **Thread Integration**: Direct access to original Discord conversations via database

### 📱 **Responsive Design**
- **Mobile Friendly**: Optimized for phones and tablets with adaptive layouts
- **Modern UI**: Bootstrap-based design with Discord theming and CSS variables
- **Theme System**: Complete dark/light mode with Discord widget synchronization
- **Fast Loading**: Cached data, optimized API calls, and efficient JavaScript

## 🚀 Quick Start

### 1. **Installation**
```bash
cd web_dashboard
pip install -r requirements.txt
```

### 2. **Configuration**
Make sure your main bot configuration (`../data/config.yaml`) includes:
```yaml
# Essential Configuration
forums:
  - YOUR_FORUM_CHANNEL_ID
log_channel: YOUR_LOG_CHANNEL_ID
admin_ids:
  - YOUR_ADMIN_USER_ID

# Web Dashboard Integration (NEW)
server_name: "Your Server Name"           # Displayed on homepage
server_invite: "https://discord.gg/xyz"   # Join server button

# Environment Variables (.env)
DISCORD_TOKEN=YOUR_BOT_TOKEN
GUILD_ID=YOUR_SERVER_ID                   # For Discord widget
```

### 3. **Start Dashboard**
```bash
python run_dashboard.py
```

### 4. **Access Dashboard**
Open your browser to:
- **Local**: http://localhost:5000
- **Network**: http://0.0.0.0:5000

## 📂 Project Structure

```
web_dashboard/
├── app.py                  # Main Flask application
├── run_dashboard.py        # Startup script
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── templates/             # HTML templates
│   ├── base.html          # Base layout with theme system
│   ├── homepage.html      # Homepage with Discord widget
│   ├── index.html         # User list page
│   └── user_profile.html  # User profile with post links
├── static/                # Static assets
│   ├── css/
│   │   └── style.css      # Custom styles
│   ├── js/
│   │   └── main.js        # Dashboard JavaScript
│   └── images/            # Image assets
└── utils/                 # Utility modules
    └── discord_integration.py # Discord API integration
```

## 🔧 API Endpoints

### **Web Pages**
- `GET /` - Homepage with Discord widget and server stats
- `GET /users` - User directory and search
- `GET /user/<user_id>` - User profile page

### **API Endpoints**
- `GET /api/discord_user/<user_id>` - Get Discord user information (enhanced with roles/badges)
- `GET /api/thread_info/<thread_id>` - Get Discord thread information (real URLs from database)
- `POST /api/sync_members` - Sync Discord members with database

## 🎨 Customization

### **Styling**
Edit `static/css/style.css` to customize:
- Color schemes and branding
- Layout and spacing
- Discord theme elements
- Responsive breakpoints

### **Templates**
Modify HTML templates in `templates/`:
- `base.html` - Overall layout and navigation
- `index.html` - User list and search functionality  
- `user_profile.html` - Individual user pages

### **JavaScript**
Enhance functionality in `static/js/main.js`:
- Search and filtering
- Data loading and caching
- User interaction features
- Theme management

## 📊 Data Sources

### **Enhanced Database Integration**
- Reads from the same SQLite database as the Discord bot
- Queries `reviews`, `users`, and `threads` tables for comprehensive data
- Thread URLs stored persistently in database for "View Post" functionality
- Real-time user synchronization with Discord API

### **Discord API Integration**
- Fetches user avatars, banners, roles, and badges
- Live Discord widget showing server activity
- Real-time member count and online status
- Discord thread information with persistent URL storage

## 🔒 Security Notes

### **Important Considerations**
- Dashboard shows public profile information only
- No authentication system (add if needed for private servers)
- Read-only access to bot database
- No sensitive data exposed in web interface

### **Recommended Setup**
- Run on internal network for private communities
- Use reverse proxy (nginx) for public deployment
- Add HTTPS in production environments
- Implement rate limiting for API endpoints

## 🛠 Development

### **Adding Features**
1. **New API Endpoints**: Add routes in `app.py`
2. **Database Queries**: Use existing database functions in `../utils/db.py`
3. **Frontend Features**: Extend JavaScript in `main.js`
4. **UI Components**: Create new templates or modify existing ones

### **Testing**
```bash
# Run in development mode
python app.py

# Check for JavaScript errors in browser console
# Test responsive design with browser dev tools
# Verify database queries with sample data
```

## 📝 Troubleshooting

### **Common Issues**

**Dashboard won't start:**
- Check that port 5000 is available
- Verify all requirements are installed
- Ensure config.yaml exists and is valid

**No user data showing:**
- Make sure the Discord bot has run and created the database
- Check that reviews exist in the database
- Verify file paths are correct

**Discord widget not loading:**
- Check that server has Discord widget enabled in Server Settings
- Verify GUILD_ID is correctly set in environment variables
- Ensure Discord widget URL is accessible (not blocked by firewall)

**"View Post" buttons not working:**
- Make sure Discord bot has been running to populate thread database
- Check that reviews have associated thread_id in database
- Verify thread_info API endpoint is returning real URLs

**Dark mode theme issues:**
- Clear browser cache and reload page
- Check browser console for JavaScript errors
- Verify CSS variables are loading correctly

**Discord data not loading:**
- User avatars and names will show as placeholders initially
- Check Discord bot token and permissions
- Verify API endpoints in browser console

**Styling issues:**
- Clear browser cache
- Check that CSS files are loading correctly
- Verify Bootstrap CDN is accessible
- Test theme toggle functionality

### **Performance Tips**
- Dashboard caches user data to reduce API calls
- Search is optimized with debouncing
- Images lazy-load for better performance
- Consider adding database indexing for large datasets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project follows the same license as the main Discord bot project.

---

**Enjoy your new Discord Review Dashboard! 🎉**

For support or questions, check the main bot documentation or create an issue in the repository.