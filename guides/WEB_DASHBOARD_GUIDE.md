# Discord Review Dashboard

A comprehensive web interface for viewing Discord user profiles, reviews, and forum activity from your Discord reputation bot.

## ✨ Features

### 🏠 **User Directory**
- **Complete User List**: View all users who have participated in the review system
- **Smart Search**: Search by username, display name, or user ID
- **Multiple Views**: All Users, Top Rated, and Most Active tabs
- **Real-time Stats**: Rating, review count, and activity metrics

### 👤 **User Profiles** 
- **Discord Integration**: Shows real avatars, banners, and user status
- **Comprehensive Stats**: Average rating, reviews given/received, active posts
- **Review History**: Latest reviews received and given with full details
- **Active Posts**: Direct links to Discord threads with activity tracking

### ⭐ **Review Display**
- **Star Rating System**: Visual 5-star display based on 1-10 ratings
- **Review Notes**: Full text reviews with timestamps
- **Reviewer Information**: See who left each review with their profile
- **Thread Links**: Direct access to original Discord conversations

### 📱 **Responsive Design**
- **Mobile Friendly**: Optimized for phones and tablets
- **Modern UI**: Bootstrap-based design with Discord theming
- **Dark Mode Support**: Automatically adapts to system theme
- **Fast Loading**: Cached data and optimized API calls

## 🚀 Quick Start

### 1. **Installation**
```bash
cd web_dashboard
pip install -r requirements.txt
```

### 2. **Configuration**
Make sure your main bot configuration (`../data/config.yaml`) includes:
```yaml
forums:
  - YOUR_FORUM_CHANNEL_ID
log_channel: YOUR_LOG_CHANNEL_ID
admin_ids:
  - YOUR_ADMIN_USER_ID
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
│   ├── base.html          # Base layout
│   ├── index.html         # User list page
│   └── user_profile.html  # User profile page
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
- `GET /` - Main user directory
- `GET /user/<user_id>` - User profile page

### **API Endpoints**
- `GET /api/discord_user/<user_id>` - Get Discord user information
- `GET /api/thread_info/<thread_id>` - Get Discord thread information

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

### **Database Integration**
- Reads from the same SQLite database as the Discord bot
- Queries `reviews` table for rating and review data
- No database writes - read-only dashboard

### **Discord API**
- Fetches user avatars, banners, and profile information
- Retrieves thread names and Discord links
- Real-time status information (when bot is connected)

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

**Discord data not loading:**
- User avatars and names will show as placeholders initially
- Discord integration requires additional setup for real data
- Check browser console for API errors

**Styling issues:**
- Clear browser cache
- Check that CSS files are loading correctly
- Verify Bootstrap CDN is accessible

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