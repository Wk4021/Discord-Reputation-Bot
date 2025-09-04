// Discord Review Dashboard JavaScript

// Global utility functions
window.DashboardUtils = {
    // Format dates consistently
    formatDate: function(dateString) {
        if (!dateString) return 'Unknown';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                return 'Yesterday';
            } else if (diffDays < 7) {
                return `${diffDays} days ago`;
            } else {
                return date.toLocaleDateString();
            }
        } catch (e) {
            return dateString;
        }
    },
    
    // Generate star rating display
    generateStarRating: function(rating) {
        if (rating === 0) return 'No rating';
        
        const starRating = rating / 2;
        const fullStars = Math.floor(starRating);
        const halfStar = (starRating - fullStars) >= 0.5 ? 1 : 0;
        const emptyStars = 5 - fullStars - halfStar;
        
        let stars = '⭐'.repeat(fullStars);
        if (halfStar) stars += '✨';
        stars += '☆'.repeat(emptyStars);
        
        return `${stars} (${rating.toFixed(1)}/10)`;
    },
    
    // Debounce function for search
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Show loading spinner
    showLoading: function(element) {
        if (element) {
            element.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>';
        }
    },
    
    // Show error message
    showError: function(element, message) {
        if (element) {
            element.innerHTML = `<div class="alert alert-warning">${message}</div>`;
        }
    }
};

// Cache for user data to avoid repeated API calls
window.UserCache = {
    users: new Map(),
    threads: new Map(),
    
    getUser: async function(userId) {
        if (this.users.has(userId)) {
            return this.users.get(userId);
        }
        
        try {
            const response = await fetch(`/api/discord_user/${userId}`);
            if (response.ok) {
                const userData = await response.json();
                this.users.set(userId, userData);
                return userData;
            }
        } catch (error) {
            console.error('Error fetching user data:', error);
        }
        
        return null;
    },
    
    getThread: async function(threadId) {
        if (this.threads.has(threadId)) {
            return this.threads.get(threadId);
        }
        
        try {
            const response = await fetch(`/api/thread_info/${threadId}`);
            if (response.ok) {
                const threadData = await response.json();
                this.threads.set(threadId, threadData);
                return threadData;
            }
        } catch (error) {
            console.error('Error fetching thread data:', error);
        }
        
        return null;
    }
};

// Enhanced search functionality
window.SearchManager = {
    init: function() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;
        
        const debouncedSearch = DashboardUtils.debounce(this.performSearch, 300);
        searchInput.addEventListener('input', debouncedSearch);
        
        // Add search suggestions
        this.setupSearchSuggestions();
    },
    
    performSearch: function() {
        const searchInput = document.getElementById('searchInput');
        const searchTerm = searchInput.value.toLowerCase().trim();
        const userCards = document.querySelectorAll('.user-card');
        let visibleCount = 0;
        
        userCards.forEach(card => {
            const searchTerms = card.getAttribute('data-search-terms').toLowerCase();
            const username = card.querySelector('.discord-username')?.textContent?.toLowerCase() || '';
            const userId = card.querySelector('[data-user-id]')?.getAttribute('data-user-id') || '';
            
            const isVisible = searchTerm === '' || 
                             searchTerms.includes(searchTerm) || 
                             username.includes(searchTerm) ||
                             userId.includes(searchTerm);
            
            card.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCount++;
        });
        
        // Update results counter
        SearchManager.updateResultsCounter(visibleCount);
    },
    
    updateResultsCounter: function(count) {
        let counter = document.getElementById('searchResults');
        if (!counter) {
            const searchInput = document.getElementById('searchInput');
            if (searchInput && searchInput.parentNode) {
                counter = document.createElement('small');
                counter.id = 'searchResults';
                counter.className = 'text-muted mt-1';
                searchInput.parentNode.insertBefore(counter, searchInput.nextSibling);
            }
        }
        
        if (counter) {
            counter.textContent = `${count} result${count !== 1 ? 's' : ''}`;
        }
    },
    
    setupSearchSuggestions: function() {
        // Future enhancement: Add search suggestions dropdown
        console.log('Search suggestions can be implemented here');
    }
};

// User data loading manager
window.UserDataManager = {
    loadedUsers: new Set(),
    
    loadUserData: async function(userId) {
        if (this.loadedUsers.has(userId)) return;
        
        try {
            const userData = await UserCache.getUser(userId);
            if (userData) {
                this.updateUserElements(userId, userData);
                this.loadedUsers.add(userId);
            }
        } catch (error) {
            console.error(`Error loading user ${userId}:`, error);
        }
    },
    
    updateUserElements: function(userId, userData) {
        // Update avatars
        document.querySelectorAll(`.discord-avatar[data-user-id="${userId}"]`).forEach(img => {
            img.src = userData.avatar_url;
            img.alt = userData.username;
        });
        
        // Update usernames
        document.querySelectorAll(`.discord-username[data-user-id="${userId}"]`).forEach(element => {
            element.textContent = userData.display_name || userData.username;
        });
        
        // Update discriminators
        document.querySelectorAll(`.discord-discriminator[data-user-id="${userId}"]`).forEach(element => {
            element.textContent = `@${userData.username}`;
        });
        
        // Update search terms
        document.querySelectorAll(`.user-card[data-search-terms*="${userId}"]`).forEach(card => {
            const currentTerms = card.getAttribute('data-search-terms');
            const newTerms = `${currentTerms} ${userData.username} ${userData.display_name || ''}`;
            card.setAttribute('data-search-terms', newTerms);
        });
    },
    
    loadAllVisibleUsers: function() {
        const userElements = document.querySelectorAll('[data-user-id]');
        const userIds = new Set();
        
        userElements.forEach(element => {
            const userId = element.getAttribute('data-user-id');
            if (userId && !this.loadedUsers.has(userId)) {
                userIds.add(userId);
            }
        });
        
        // Load users in batches to avoid overwhelming the API
        const userArray = Array.from(userIds);
        this.loadUsersBatch(userArray, 0, 5);
    },
    
    loadUsersBatch: function(userIds, startIndex, batchSize) {
        const batch = userIds.slice(startIndex, startIndex + batchSize);
        
        Promise.all(batch.map(userId => this.loadUserData(userId)))
            .then(() => {
                if (startIndex + batchSize < userIds.length) {
                    // Load next batch after a short delay
                    setTimeout(() => {
                        this.loadUsersBatch(userIds, startIndex + batchSize, batchSize);
                    }, 100);
                }
            })
            .catch(error => {
                console.error('Error loading user batch:', error);
            });
    }
};

// Thread data loading manager
window.ThreadDataManager = {
    loadThreadData: async function(threadId) {
        try {
            const threadData = await UserCache.getThread(threadId);
            if (threadData) {
                this.updateThreadElements(threadId, threadData);
            }
        } catch (error) {
            console.error(`Error loading thread ${threadId}:`, error);
        }
    },
    
    updateThreadElements: function(threadId, threadData) {
        // Update thread names
        document.querySelectorAll(`.thread-name[data-thread-id="${threadId}"], .thread-card[data-thread-id="${threadId}"] .thread-name`).forEach(element => {
            element.textContent = threadData.name || `Thread ${threadId}`;
        });
        
        // Update thread dates
        document.querySelectorAll(`.thread-date[data-thread-id="${threadId}"], .thread-card[data-thread-id="${threadId}"] .thread-date`).forEach(element => {
            element.textContent = `Created ${DashboardUtils.formatDate(threadData.created_at)}`;
        });
        
        // Update thread links
        document.querySelectorAll(`.thread-link[data-thread-id="${threadId}"]`).forEach(link => {
            link.href = threadData.url;
            link.target = '_blank';
        });
    },
    
    loadAllVisibleThreads: function() {
        const threadElements = document.querySelectorAll('[data-thread-id]');
        const threadIds = new Set();
        
        threadElements.forEach(element => {
            const threadId = element.getAttribute('data-thread-id');
            if (threadId) {
                threadIds.add(threadId);
            }
        });
        
        threadIds.forEach(threadId => {
            this.loadThreadData(threadId);
        });
    }
};

// Tooltip manager for better UX
window.TooltipManager = {
    init: function() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Add dynamic tooltips
        this.addDynamicTooltips();
    },
    
    addDynamicTooltips: function() {
        // Add tooltips to rating displays
        document.querySelectorAll('.rating-display .stars').forEach(element => {
            element.setAttribute('data-bs-toggle', 'tooltip');
            element.setAttribute('title', 'User rating based on reviews');
        });
        
        // Add tooltips to stat items
        document.querySelectorAll('.stat-item').forEach(element => {
            const label = element.querySelector('.stat-label')?.textContent;
            if (label) {
                element.setAttribute('data-bs-toggle', 'tooltip');
                element.setAttribute('title', `Total ${label.toLowerCase()}`);
            }
        });
    }
};

// Theme manager
window.ThemeManager = {
    init: function() {
        this.detectSystemTheme();
        this.addThemeToggle();
    },
    
    detectSystemTheme: function() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.add('dark-theme');
        }
        
        // Listen for theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                if (e.matches) {
                    document.body.classList.add('dark-theme');
                } else {
                    document.body.classList.remove('dark-theme');
                }
            });
        }
    },
    
    addThemeToggle: function() {
        // Future enhancement: Add manual theme toggle button
        console.log('Theme toggle can be implemented here');
    }
};

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Discord Review Dashboard...');
    
    // Initialize managers
    SearchManager.init();
    TooltipManager.init();
    ThemeManager.init();
    
    // Load user and thread data
    UserDataManager.loadAllVisibleUsers();
    ThreadDataManager.loadAllVisibleThreads();
    
    console.log('Dashboard initialized successfully!');
});

// Error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});