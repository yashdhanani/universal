# Frontend - Universal Media Downloader

Static frontend interface for the Universal Media Downloader.

## Features

- Clean, responsive UI
- Platform-specific download forms
- Real-time progress updates
- Dark mode support
- Mobile-friendly design

## Technologies

- HTML5
- CSS3 with Tailwind CSS
- Vanilla JavaScript
- Service Worker for caching

## Structure

- `index.html` - Main download interface
- `static/` - CSS, JS, and assets
- `templates/` - Additional HTML templates
- Platform-specific subdirectories for SEO

## Deployment

Upload all files to Hostinger. The backend API should be configured in `static/config.js`.

## Configuration

Update `static/config.js` with your backend API URL:

```javascript
const CONFIG = {
  API_BASE: 'https://your-backend.onrender.com'
};
```