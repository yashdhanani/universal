// Platform utilities for Universal Media Downloader
// This file contains helper functions for handling different social media platforms

// Placeholder for platform-specific utilities
const PlatformUtils = {
    // Add platform detection and utility functions here
    detectPlatform: function(url) {
        // Simple platform detection based on URL
        if (url.includes('youtube.com') || url.includes('youtu.be')) return 'youtube';
        if (url.includes('instagram.com')) return 'instagram';
        if (url.includes('facebook.com') || url.includes('fb.com')) return 'facebook';
        if (url.includes('tiktok.com')) return 'tiktok';
        if (url.includes('twitter.com') || url.includes('x.com')) return 'twitter';
        if (url.includes('pinterest.com')) return 'pinterest';
        if (url.includes('snapchat.com')) return 'snapchat';
        if (url.includes('linkedin.com')) return 'linkedin';
        if (url.includes('reddit.com')) return 'reddit';
        return null;
    },

    // Add more utilities as needed
    getPlatformColor: function(platform) {
        const colors = {
            youtube: '#FF0000',
            instagram: '#C13584',
            facebook: '#1877F2',
            tiktok: '#00f2ea',
            twitter: '#1DA1F2',
            pinterest: '#E60023',
            snapchat: '#FFFC00',
            linkedin: '#0A66C2',
            reddit: '#FF4500'
        };
        return colors[platform] || '#6b7280';
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PlatformUtils;
}