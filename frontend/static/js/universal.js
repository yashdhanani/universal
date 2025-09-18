// Initialize Progress Manager IMMEDIATELY
  window.progressManager = {
    progressBars: new Map(),
    
    createProgressBar(id, title, type = 'default') {
      const container = document.getElementById('progress-container');
      if (!container) {
        console.error('Progress container not found!');
        return id;
      }
      
      const element = document.createElement('div');
      element.className = 'bg-white dark:bg-gray-800 rounded-xl p-5 mb-4 border border-gray-200 dark:border-gray-600 shadow-lg transition-all duration-300 animate-fade-in';
      element.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <span class="font-bold text-gray-900 dark:text-white text-lg">${title}</span>
          <span class="progress-percentage text-blue-500 dark:text-blue-400 font-mono text-lg font-bold">0%</span>
        </div>
        <div class="bg-gray-200 dark:bg-gray-700 rounded-full h-4 mb-3 overflow-hidden shadow-inner">
          <div class="progress-fill bg-gradient-to-r from-blue-500 to-blue-600 h-4 rounded-full transition-all duration-500 ease-out shadow-sm" style="width: 0%"></div>
        </div>
        <div class="progress-status text-sm text-gray-600 dark:text-gray-400 font-medium">Starting...</div>
      `;
      
      container.appendChild(element);
      this.progressBars.set(id, { element, type, title });
      return id;
    },
    
    updateProgress(id, percentage, status = '') {
      const progressData = this.progressBars.get(id);
      if (!progressData) return;

      const element = progressData.element;
      const fill = element.querySelector('.progress-fill');
      const percentageEl = element.querySelector('.progress-percentage');
      const statusEl = element.querySelector('.progress-status');

      fill.style.width = Math.min(100, Math.max(0, percentage)) + '%';
      percentageEl.textContent = Math.round(percentage) + '%';
      if (status) statusEl.textContent = status;
      
      // Update colors based on progress
      if (percentage >= 100) {
        fill.className = fill.className.replace('from-blue-500 to-blue-600', 'from-green-500 to-green-600');
      }
    },
    
    startAnalysisProgress(url, platform = 'youtube') {
      const id = 'analysis-' + Date.now();
      
      // Dynamic title based on platform
      const platformTitles = {
        'youtube': 'ðŸ” Analyzing Video',
        'instagram': 'ðŸ” Analyzing Media',
        'tiktok': 'ðŸ” Analyzing Content',
        'twitter': 'ðŸ” Analyzing Tweet',
        'facebook': 'ðŸ” Analyzing Post',
        'snapchat': 'ðŸ” Analyzing Snap',
        'pinterest': 'ðŸ” Analyzing Pin',
        'linkedin': 'ðŸ” Analyzing Post',
        'reddit': 'ðŸ” Analyzing Post'
      };
      
      const title = platformTitles[platform.toLowerCase()] || 'ðŸ” Analyzing Media';
      this.createProgressBar(id, title, 'analyzing');
      
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 12 + 3;
        if (progress > 95) progress = 95;
        
        // Dynamic stages based on platform
        const platformStages = {
          'instagram': ['Connecting to Instagram...', 'Fetching post information...', 'Processing images and videos...', 'Finalizing analysis...'],
          'tiktok': ['Connecting to TikTok...', 'Fetching video information...', 'Processing available formats...', 'Finalizing analysis...'],
          'twitter': ['Connecting to Twitter...', 'Fetching tweet media...', 'Processing available formats...', 'Finalizing analysis...'],
          'default': ['Connecting to server...', 'Fetching media information...', 'Processing available formats...', 'Finalizing analysis...']
        };
        
        const stages = platformStages[platform.toLowerCase()] || platformStages['default'];
        const currentStage = Math.floor((progress / 100) * stages.length);
        const status = stages[currentStage] || stages[stages.length - 1];
        
        this.updateProgress(id, progress, status);
      }, 400);
      
      this.progressBars.get(id).interval = interval;
      return id;
    },
    
    completeAnalysisProgress(id, formatCount, mediaType = null) {
      const progressData = this.progressBars.get(id);
      if (progressData && progressData.interval) {
        clearInterval(progressData.interval);
      }
      
      // Dynamic completion message based on media type
      let message = `âœ… Analysis completed! Found ${formatCount} formats`;
      if (mediaType === 'image') {
        const imageWord = formatCount === 1 ? 'image' : 'images';
        message = `âœ… Analysis completed! Found ${formatCount} ${imageWord}`;
      } else if (mediaType === 'video') {
        const videoWord = formatCount === 1 ? 'video format' : 'video formats';
        message = `âœ… Analysis completed! Found ${formatCount} ${videoWord}`;
      }
      
      this.updateProgress(id, 100, message);
      
      setTimeout(() => {
        const element = progressData?.element;
        if (element && element.parentNode) {
          element.style.opacity = '0';
          element.style.transform = 'translateY(-10px)';
          setTimeout(() => element.remove(), 300);
        }
        this.progressBars.delete(id);
      }, 3000);
    },
    
    startDownloadProgress(filename) {
      const id = 'download-' + Date.now();
      this.createProgressBar(id, `ðŸ“¥ Downloading: ${filename}`, 'downloading');
      const element = this.progressBars.get(id).element;
      const fill = element.querySelector('.progress-fill');
      const percentage = element.querySelector('.progress-percentage');
      fill.className = fill.className.replace('from-blue-500 to-blue-600', 'from-green-500 to-green-600');
      percentage.className = percentage.className.replace('text-blue-500 dark:text-blue-400', 'text-green-500 dark:text-green-400');
      return id;
    },
    
    updateDownloadProgress(id, percentage, speed = '', eta = '', details = '') {
      const speedText = speed ? ` â€¢ ${speed}` : '';
      const etaText = eta ? ` â€¢ ETA: ${eta}` : '';
      const status = percentage < 100 ? `Downloading...${speedText}${etaText}` : 'Download completed!';
      this.updateProgress(id, percentage, status);
      
      if (percentage >= 100) {
        setTimeout(() => {
          const progressData = this.progressBars.get(id);
          const element = progressData?.element;
          if (element && element.parentNode) {
            element.style.opacity = '0';
            setTimeout(() => element.remove(), 300);
          }
          this.progressBars.delete(id);
        }, 2000);
      }
    },
    
    errorProgress(id, message) {
      const progressData = this.progressBars.get(id);
      if (!progressData) return;
      
      const element = progressData.element;
      const fill = element.querySelector('.progress-fill');
      const statusEl = element.querySelector('.progress-status');
      const percentageEl = element.querySelector('.progress-percentage');
      
      fill.className = fill.className.replace(/from-\w+-500 to-\w+-600/, 'from-red-500 to-red-600');
      statusEl.textContent = 'âŒ ' + message;
      statusEl.className = statusEl.className.replace('text-gray-600 dark:text-gray-400', 'text-red-500 dark:text-red-400');
      percentageEl.className = percentageEl.className.replace('text-blue-500 dark:text-blue-400', 'text-red-500 dark:text-red-400');
      
      setTimeout(() => {
        if (element && element.parentNode) {
          element.style.opacity = '0';
          setTimeout(() => element.remove(), 300);
        }
        this.progressBars.delete(id);
      }, 5000);
    }
  };
  
  console.log('âœ… Progress Manager initialized and ready!');

  document.addEventListener('DOMContentLoaded', () => {
    // Entrance: header + form
    document.querySelectorAll('.enter-fade-up').forEach((el, idx) => {
      setTimeout(() => el.classList.add('in'), idx * 40);
    });
    const API_BASE = (window.__CONFIG && window.__CONFIG.API_BASE) ? window.__CONFIG.API_BASE : ''; // runtime-configurable for Hostinger

    // Platform config
    const platformDetails = {
      youtube: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/64px-YouTube_full-color_icon_%282017%29.svg.png', name: 'YouTube', colorVar: '--color-youtube', placeholder: 'https://www.youtube.com/watch?v=...' },
      instagram: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png', name: 'Instagram', colorVar: '--color-instagram', placeholder: 'https://www.instagram.com/p/...' },
      facebook: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg', name: 'Facebook', colorVar: '--color-facebook', placeholder: 'https://www.facebook.com/.../videos/...' },
      tiktok: { iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8ZGVmcz4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ3JhZGllbnQxIiB4MT0iMCUiIHkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj4KICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3R5bGU9InN0b3AtY29sb3I6I0ZGMDA0NEIyO3N0b3Atb3BhY2l0eToxIiAvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiNGRjAwNDQ7c3RvcC1vcGFjaXR5OjEiIC8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogICAgPGxpbmVhckdyYWRpZW50IGlkPSJncmFkaWVudDIiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMTAwJSIgeTI9IjEwMCUiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdHlsZT0ic3RvcC1jb2xvcjojMDBGMkVBO3N0b3Atb3BhY2l0eToxIiAvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiMwMEY1RkY7c3RvcC1vcGFjaXR5OjEiIC8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogIDwvZGVmcz4KICA8cGF0aCBkPSJNMTkuNTkgNi42OWMtMS4zNi0uOTYtMi4yNy0yLjUyLTIuMzYtNC4zMUgxNS4ydjEyLjEyYzAgMi4yNy0xLjg0IDQuMTEtNC4xMSA0LjExcy00LjExLTEuODQtNC4xMS00LjExIDEuODQtNC4xMSA0LjExLTQuMTFjLjQyIDAgLjgzLjA3IDEuMjEuMlY3LjY5Yy0uMzktLjA1LS43OS0uMDgtMS4yMS0uMDgtMy4zNSAwLTYuMDcgMi43Mi02LjA3IDYuMDdzMi43MiA2LjA3IDYuMDcgNi4wNyA2LjA3LTIuNzIgNi4wNy02LjA3VjguNDJjMS4zMi45NCAyLjk2IDEuNSA0Ljc0IDEuNVY3Ljk2Yy0uODkgMC0xLjc0LS4yNy0yLjQ0LS43NnoiIGZpbGw9InVybCgjZ3JhZGllbnQxKSIvPgogIDxwYXRoIGQ9Ik0xNy4yMyA2LjY5Yy43LS40OSAxLjU1LS43NyAyLjQ0LS43N3YtMS45NmMtMS43OCAwLTMuNDItLjU2LTQuNzQtMS41djkuMDRjMCAzLjM1LTIuNzIgNi4wNy02LjA3IDYuMDdzLTYuMDctMi43Mi02LjA3LTYuMDcgMi43Mi02LjA3IDYuMDctNi4wN2MuNDIgMCAuODIuMDMgMS4yMS4wOHYtMS45NmMtLjM4LS4xMy0uNzktLjItMS4yMS0uMi0yLjI3IDAtNC4xMSAxLjg0LTQuMTEgNC4xMXMxLjg0IDQuMTEgNC4xMSA0LjExIDQuMTEtMS44NCA0LjExLTQuMTFWNi42OWMxLjMyLjk0IDIuOTYgMS41IDQuNzQgMS41VjYuMjNjLS44OSAwLTEuNzQuMjctMi40NC43N3oiIGZpbGw9InVybCgjZ3JhZGllbnQyKSIvPgo8L3N2Zz4K', name: 'TikTok', colorVar: '--color-tiktok', placeholder: 'https://www.tiktok.com/@user/video/...' },
      twitter: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/5/53/X_logo_2023_original.svg', name: 'Twitter', colorVar: '--color-twitter', placeholder: 'https://twitter.com/.../status/...' },
      pinterest: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/0/08/Pinterest-logo.png', name: 'Pinterest', colorVar: '--color-pinterest', placeholder: 'https://www.pinterest.com/pin/...' },
      snapchat: { iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cGF0aCBkPSJNMTIgMkM2LjQ4IDIgMiA2LjQ4IDIgMTJzNC40OCAxMCAxMCAxMCAxMC00LjQ4IDEwLTEwUzE3LjUyIDIgMTIgMnptMCAxOGMtNC40MSAwLTgtMy41OS04LThzMy41OS04IDgtOCA4IDMuNTkgOCA4LTMuNTkgOC04IDh6IiBmaWxsPSIjRkZGQzAwIi8+CiAgPHBhdGggZD0iTTEyIDZjLTMuMzEgMC02IDIuNjktNiA2czIuNjkgNiA2IDYgNi0yLjY5IDYtNi0yLjY5LTYtNi02em0wIDEwYy0yLjIxIDAtNC0xLjc5LTQtNHMxLjc5LTQgNC00IDQgMS43OSA0IDQtMS43OSA0LTQgNHoiIGZpbGw9IiNGRkZDMDAiLz4KPC9zdmc+', name: 'Snapchat', colorVar: '--color-snapchat', placeholder: 'https://www.snapchat.com/...' },
      linkedin: { iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg', name: 'LinkedIn', colorVar: '--color-linkedin', placeholder: 'https://www.linkedin.com/feed/update/urn:li:activity:...' },
      reddit: { iconUrl: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><circle cx='12' cy='12' r='12' fill='%23FF4500'/><circle cx='9' cy='12' r='1.5' fill='%23FFFFFF'/><circle cx='15' cy='12' r='1.5' fill='%23FFFFFF'/><path d='M8 15c1.2 1 2.6 1.5 4 1.5s2.8-.5 4-1.5' stroke='%23FFFFFF' stroke-width='1.5' fill='none' stroke-linecap='round'/><circle cx='18' cy='6' r='1.2' fill='%23FFFFFF'/><path d='M13.5 9l3-2' stroke='%23FFFFFF' stroke-width='1.2' stroke-linecap='round'/></svg>", name: 'Reddit', colorVar: '--color-reddit', placeholder: 'https://www.reddit.com/r/.../comments/...' },
    };

    let currentPlatform = 'youtube';

    // Elements
    const urlInput = document.getElementById('url-input');
    const statusContainer = document.getElementById('status-container');
    const resultContainer = document.getElementById('result-container');
    const submitBtn = document.getElementById('submit-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const clearBtn = document.getElementById('clear-url-btn');
    const platformSelector = document.getElementById('platform-selector');
    const inputIcon = document.getElementById('input-icon-container');

    // UI helpers
    function setPlatformColor(key){ document.documentElement.style.setProperty('--platform-color', getComputedStyle(document.documentElement).getPropertyValue(platformDetails[key].colorVar)); }
    function setPlatformPlaceholder(key){ urlInput.placeholder = platformDetails[key].placeholder; }
    function setInputIcon(key){ inputIcon.innerHTML = `<img alt="${key}" src="${platformDetails[key].iconUrl}"/>`; }

    // Build platform buttons
    function renderPlatforms(){
      platformSelector.innerHTML = '';
      Object.entries(platformDetails).forEach(([key, v]) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.dataset.key = key;
        btn.className = 'platform-button flex items-center gap-2 px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors';
        btn.innerHTML = `<img src="${v.iconUrl}" alt="${v.name}"><span class="font-medium">${v.name}</span>`;
        if (key === currentPlatform) btn.classList.add('active');
        btn.addEventListener('click', () => {
          currentPlatform = key;
          document.querySelectorAll('.platform-button').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          setPlatformColor(key); setPlatformPlaceholder(key); setInputIcon(key);
          submitBtn.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue('--platform-color');
        });
        platformSelector.appendChild(btn);
      });
      setPlatformColor(currentPlatform); setPlatformPlaceholder(currentPlatform); setInputIcon(currentPlatform);
    }

    renderPlatforms();

    // Helpers
    function showStatus(message, type='info'){
      const color = type==='error' ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800' : (type==='success' ? 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800' : 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800');
      const toast = document.createElement('div');
      toast.className = `${color} rounded-xl p-3 toast`;
      toast.innerHTML = `${message}`;
      statusContainer.appendChild(toast);
      requestAnimationFrame(()=> toast.classList.add('show'));
      setTimeout(()=>{ toast.classList.add('hide'); setTimeout(()=> toast.remove(), 250); }, 3500);
    }

    function humanSizeMB(mb){ return mb ? `${mb.toFixed ? mb.toFixed(1) : mb} MB` : ''; }

    // Strip ANSI escape codes (e.g., from yt-dlp progress)
    function stripAnsi(s){
      return typeof s === 'string' ? s.replace(/\x1B\[[0-9;]*[A-Za-z]/g, '') : s;
    }

    // Proxy media through backend to avoid hotlink/CORS blocks (e.g., Instagram)
    // --- Robust YouTube URL parser & canonicalizer (YouTube only) ---
    function parseTimeToSeconds(t) {
      if (!t) return null;
      if (/^\d+$/.test(t)) return parseInt(t, 10);
      // support mm:ss or hh:mm:ss
      if (/^\d{1,2}:\d{1,2}(:\d{1,2})?$/.test(t)) {
        const parts = t.split(':').map(n => parseInt(n, 10));
        if (parts.length === 2) return parts[0] * 60 + parts[1];
        if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
      const m = t.match(/(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?/);
      if (!m) return null;
      const h = parseInt(m[1] || 0, 10);
      const mn = parseInt(m[2] || 0, 10);
      const s = parseInt(m[3] || 0, 10);
      return h * 3600 + mn * 60 + s;
    }

    // parseYouTubeUrl(url) -> { type, videoId, playlistId, startSeconds, raw }
    function parseYouTubeUrl(rawUrl) {
      if (!rawUrl || typeof rawUrl !== 'string') return { type: 'unknown', raw: rawUrl };
      const url = rawUrl.trim();
      // raw ID
      if (/^[A-Za-z0-9_-]{11}$/.test(url)) {
        return { type: 'video', videoId: url, raw: rawUrl };
      }
      let u;
      try { u = new URL(url.startsWith('http') ? url : 'https://' + url); } catch (_) { u = null; }
      const normalized = u ? (u.hostname + u.pathname + (u.search || '')) : url;
      const listMatch = normalized.match(/[?&]list=([A-Za-z0-9_-]+)/);
      const playlistId = listMatch ? listMatch[1] : null;

      if (u && (u.hostname.includes('youtube.com') || u.hostname.includes('youtube-nocookie.com') || u.hostname.includes('music.youtube.com'))) {
        if (u.pathname.startsWith('/watch')) {
          const v = u.searchParams.get('v');
          const t = u.searchParams.get('t') || u.searchParams.get('start') || u.searchParams.get('time_continue');
          return {
            type: v ? 'video' : (playlistId ? 'playlist' : 'unknown'),
            videoId: v || null,
            playlistId,
            startSeconds: t ? parseTimeToSeconds(t) : null,
            raw: rawUrl
          };
        }
        const embedMatch = normalized.match(/\/embed\/([A-Za-z0-9_-]{11})/);
        if (embedMatch) {
          return { type: 'embed', videoId: embedMatch[1], playlistId, raw: rawUrl };
        }
        const shortsMatch = normalized.match(/\/shorts\/([A-Za-z0-9_-]{11})/);
        if (shortsMatch) {
          return { type: 'shorts', videoId: shortsMatch[1], playlistId, raw: rawUrl };
        }
        const vMatch = normalized.match(/\/v\/([A-Za-z0-9_-]{11})/);
        if (vMatch) {
          return { type: 'video', videoId: vMatch[1], playlistId, raw: rawUrl };
        }
      }
      const yb = normalized.match(/youtu\.be\/([A-Za-z0-9_-]{11})/);
      if (yb) {
        const tparam = normalized.match(/[?&](?:t|start)=([0-9hms:]+)/);
        return {
          type: 'short',
          videoId: yb[1],
          playlistId,
          startSeconds: tparam ? parseTimeToSeconds(tparam[1]) : null,
          raw: rawUrl
        };
      }
      if (playlistId && (!normalized.includes('v='))) {
        return { type: 'playlist', playlistId, raw: rawUrl };
      }
      if (u && (u.pathname.startsWith('/channel/') || u.pathname.startsWith('/c/') || u.pathname.startsWith('/@'))) {
        return { type: 'channel', raw: rawUrl };
      }
      const catchId = normalized.match(/([A-Za-z0-9_-]{11})/);
      if (catchId) return { type: 'video', videoId: catchId[1], playlistId, raw: rawUrl };
      return { type: 'unknown', raw: rawUrl };
    }

    function canonicalizePlatformUrl(platform, rawUrl) {
      try {
        if (String(platform).toLowerCase() !== 'youtube') return rawUrl;
        const parsed = parseYouTubeUrl(rawUrl);
        if ([ 'video', 'shorts', 'short', 'embed' ].includes(parsed.type) && parsed.videoId) {
          const t = parsed.startSeconds ? `&t=${parsed.startSeconds}s` : '';
          return `https://www.youtube.com/watch?v=${parsed.videoId}${t}`;
        }
        return rawUrl;
      } catch { return rawUrl; }
    }

    function proxyUrl(u){
      try {
        if (!u || typeof u !== 'string') return u;
        if (!/^https?:/i.test(u)) return u; // keep local or data URLs as-is
        return `${API_BASE}/api/passthrough?url=${encodeURIComponent(u)}`;
      } catch { return u; }
    }

    // Enhanced thumbnail URL extraction with multiple fallbacks
    function getThumbnailUrl(info) {
      // Prefer photos[] from v2 mapping
      if (info.photos && Array.isArray(info.photos) && info.photos.length > 0) {
        const p = info.photos[0];
        if (p && p.url && p.url.startsWith('http')) {
          return p.url;
        }
      }

      // Try jpg[] array (backend may also synthesize from thumbnail)
      if (info.jpg && Array.isArray(info.jpg) && info.jpg.length > 0) {
        const firstJpg = info.jpg[0];
        if (firstJpg && firstJpg.url && firstJpg.url.startsWith('http')) {
          return firstJpg.url;
        }
      }

      // Primary fields first
      if (typeof info.thumbnail === 'string' && info.thumbnail.startsWith('http')) {
        return info.thumbnail;
      }
      if (typeof info.thumbnail_url === 'string' && info.thumbnail_url.startsWith('http')) {
        return info.thumbnail_url;
      }
      
      // Try thumbnails array
      if (info.thumbnails && Array.isArray(info.thumbnails) && info.thumbnails.length > 0) {
        for (const thumb of info.thumbnails) {
          const url = (thumb && (thumb.url || thumb.src)) || null;
          if (typeof url === 'string' && url.startsWith('http')) {
            return url;
          }
        }
      }

      // Try items[0] (backend normalized item or raw platform structure)
      if (info.items && Array.isArray(info.items) && info.items.length > 0) {
        const it = info.items[0] || {};
        if (typeof it.thumbnail === 'string' && it.thumbnail.startsWith('http')) return it.thumbnail;
        if (typeof it.thumbnail_url === 'string' && it.thumbnail_url.startsWith('http')) return it.thumbnail_url;
        if (Array.isArray(it.thumbnails)) {
          for (const th of it.thumbnails) {
            const u = (th && (th.url || th.src)) || null;
            if (typeof u === 'string' && u.startsWith('http')) return u;
          }
        }
        // Instagram raw structure if passed through
        const candidatesArr = it.image_versions2 && Array.isArray(it.image_versions2.candidates) ? it.image_versions2.candidates : null;
        if (candidatesArr) {
          for (const c of candidatesArr) {
            if (c && typeof c.url === 'string' && c.url.startsWith('http')) return c.url;
          }
        }
      }
      
      // For Instagram: try to get from first image format
      if (info.images && Array.isArray(info.images) && info.images.length > 0) {
        const firstImage = info.images[0];
        if (firstImage && firstImage.url && firstImage.url.startsWith('http')) {
          return firstImage.url;
        }
      }
      
      // Fallback to default image (SVG placeholder)
      return '/static/og-default.svg';
    }

    // Render formats/results with modern card design and direct downloads
    function renderResult(info){
      const title = info.title || 'Unknown';
      const thumb = getThumbnailUrl(info);
      const views = info.views || (info.view_count ? `${(info.view_count / 1000000).toFixed(1)}M views` : '');

      const mediaType = info.media_type || (Array.isArray(info.videos) && info.videos.length ? 'video' : (Array.isArray(info.images) && info.images.length ? 'image' : 'unknown'));

      // Use the new MP4/MP3 structure from backend and filter to MP4 only for video
      let videoFormats = (info.mp4 || info.videos || []);
      videoFormats = Array.isArray(videoFormats) ? videoFormats.filter(f => (f.ext || '').toLowerCase() === 'mp4') : [];
      const audioFormats = info.mp3 || [];

      // Restrict Instagram, Facebook, Twitter to Instant-only progressive (video+audio)
      const INSTANT_ONLY_PLATFORMS = ['instagram','facebook','twitter'];
      const isInstantOnly = INSTANT_ONLY_PLATFORMS.includes(currentPlatform);
      if (isInstantOnly) {
        videoFormats = videoFormats.filter(f => !!f.is_progressive);
      }
      const bestInstantFormat = (videoFormats.find(f => f.is_progressive) || videoFormats[0] || null);
      const bestInstantFormatId = bestInstantFormat ? bestInstantFormat.format_id : 'best';

      // Image formats support (single or multiple images)
      const imageItems = info.images || [];
      
      // For Instagram and similar: group image variants and pick highest resolution per asset
      function normalizeVariantKey(u){
        try {
          const url = new URL(u, location.origin);
          // Remove size hint segments like /s1080x1350/ commonly used by CDNs
          const cleanedPath = url.pathname.replace(/\/s\d+x\d+\//g, '/');
          url.pathname = cleanedPath;
          url.search = ''; // ignore query differences
          return url.origin + url.pathname;
        } catch { return (u || '').replace(/\/s\d+x\d+\//g, '/').split('?')[0]; }
      }
      const grouped = {};
      (Array.isArray(imageItems) ? imageItems : []).forEach(img => {
        if (!img || !img.url) return;
        const key = normalizeVariantKey(img.url);
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(img);
      });
      const processedImages = Object.values(grouped).map(list => {
        try { list.sort((a,b)=>((a.width||0)*(a.height||0)) - ((b.width||0)*(b.height||0))); } catch {}
        return list[list.length-1]; // pick largest
      });
      
      const html = `
        <div class="animate-fade-in">
          <!-- Media Info Header -->
          <div class="bg-white dark:bg-gray-800 rounded-xl p-6 mb-6 shadow-lg">
            <div class="flex flex-col md:flex-row gap-6">
              <img src="${proxyUrl(thumb)}" alt="thumbnail" class="w-full md:w-80 h-48 object-cover rounded-lg shadow-md" 
                   onerror="this.src='/static/og-default.svg'; this.onerror=null;" 
                   onload="console.log('Thumbnail loaded successfully:', this.src)"/>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h2 class="text-2xl font-bold text-gray-900 dark:text-white">${title}</h2>
                  ${mediaType === 'short' ? `<span class="bg-red-500 text-white text-xs px-2 py-1 rounded-full">Shorts</span>` : ''}
                </div>
                ${views ? `<p class="text-gray-600 dark:text-gray-400 mb-2">${views}</p>` : ''}
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  Choose your preferred format and quality below
                </div>
              </div>
            </div>
          </div>

          <!-- Dynamic Content by Media Type -->
          ${mediaType === 'image' ? `
            <!-- Photo UI -->
            <div id="image-content" class="format-content">
              ${(processedImages.length) ? `
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-3">
                  <div class="text-sm text-gray-600 dark:text-gray-300">Select images to download as ZIP</div>
                  <button id="select-all" class="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 text-xs">Select all</button>
                  <button id="clear-all" class="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 text-xs">Clear all</button>
                  <button id="download-all" class="px-3 py-2 rounded bg-green-600 hover:bg-green-700 text-white font-semibold text-xs">ðŸ“¦ Download All</button>
                </div>
                <button id="zip-download" class="px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold disabled:opacity-50" disabled>Download selected (.zip)</button>
              </div>` : ''}
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${(processedImages.length) ? processedImages.map((img, i) => `
                  <div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow border border-gray-200 dark:border-gray-700">
                    <label class="flex items-center gap-2 mb-2 cursor-pointer select-none">
                      <input type="checkbox" class="img-select" value="${i}" />
                      <span class="text-sm text-gray-600 dark:text-gray-300">Select</span>
                    </label>
                    <img src="${proxyUrl(img.url || thumb)}" alt="image ${i+1}" class="w-full h-48 object-cover rounded mb-3 cursor-pointer hover:opacity-80 transition-opacity previewable" onclick="openImagePreview('${img.url || thumb}', '${title} - Image ${i+1}')"/>
                    <div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-300 mb-2">
                      <div>${(() => { const w = img.width||0, h = img.height||0; const gcd = (a,b)=>b?gcd(b,a%b):a; const g = gcd(w,h)||1; const ar = (w&&h)? `${Math.round(w/g)}:${Math.round(h/g)}` : ''; return `${w||''}x${h||''} ${ar ? '('+ar+') ' : ''}${(img.ext||'').toUpperCase()}`; })()}</div>
                      ${img.url ? `<div class="flex items-center gap-2">
                        <button class="smart-image-button px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs" data-image-url="${img.url}" data-default-name="${(title || 'image').replace(/[^\w\s.-]+/g,' ').trim()}-${i+1}.${(img.ext||'jpg').toLowerCase()}">â¬‡ï¸ Download</button>
                      </div>` : ''}
                    </div>
                    <input type="text" class="img-filename w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm" placeholder="${(title || 'image').replace(/[^\w\s.-]+/g,' ').trim()}-${i+1}.${(img.ext||'jpg').toLowerCase()}" value="${(title || 'image').replace(/[^\w\s.-]+/g,' ').trim()}-${i+1}.${(img.ext||'jpg').toLowerCase()}" />
                  </div>
                `).join('') : `
                  <div class="text-gray-500 dark:text-gray-400">No images detected.</div>
                `}
              </div>
            </div>
          ` : `
            <!-- Video/Short UI with tabs -->
            <div class="mb-6">
              <div class="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-fit">
                <button id="mp4-tab" class="tab-button active px-6 py-3 rounded-md font-semibold transition-all duration-200">ðŸŽ¬ MP4 Video</button>
                ${Array.isArray(audioFormats) && audioFormats.length ? '<button id="mp3-tab" class="tab-button px-6 py-3 rounded-md font-semibold transition-all duration-200">ðŸŽµ Audio</button>' : ''}
              </div>
              <div class="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div class="flex items-start gap-3">
                  <div class="text-blue-500 mt-0.5">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  </div>
                  <div class="text-sm text-blue-800 dark:text-blue-200">
                    <strong>ðŸš€ Instant Downloads:</strong> Green buttons download immediately (0-2 seconds).${(['twitter','instagram','facebook'].includes(currentPlatform)) ? '' : ' Orange buttons use server processing (1-3 minutes).'}
                  </div>
                </div>
              </div>
              <div class="flex justify-end mt-3 gap-2">
                <button class="instant-download-button bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg"
                        data-instant-url="${API_BASE}/api/v2/${currentPlatform}/instant?url=${encodeURIComponent(urlInput.value.trim())}&format_id=${encodeURIComponent(bestInstantFormatId)}&filename=${encodeURIComponent(((title || 'video').replace(/[\/:*?\"<>|]+/g,' ').replace(/[^\w\s.-]+/g,' ').trim().replace(/\s+/g,' ')) + '-best.mp4')}">âš¡ Instant Best</button>
                ${isInstantOnly ? '' : '<button class="smart-item-button bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg" data-format="best">ðŸ–¥ Server Best</button>'}
              </div>
            </div>
            <div id="mp4-content" class="format-content">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                ${videoFormats.map(f => {
                  const avBadge = '';
                  const withAudioEmoji = f.is_progressive ? 'ðŸ”Š' : 'ðŸ”‡';
                  const safeTitle = (title || 'video').replace(/[\/:*?"<>|]+/g,' ').replace(/[^\w\s.-]+/g,' ').trim().replace(/\s+/g,' ');
                  const desiredName = `${safeTitle}-${(f.quality || f.resolution || 'video')}.${(f.ext || 'mp4').toLowerCase()}`;
                  const instantHref = `${API_BASE}/api/v2/sign?url=${encodeURIComponent(urlInput.value.trim())}&format_id=${encodeURIComponent(f.format_id)}&filename=${encodeURIComponent(desiredName)}`;
                  return `
                  <div class="quality-card bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border border-gray-200 dark:border-gray-700">
                    <div class="flex items-center justify-between">
                      <div class="flex-1">
                        <div class="text-xl font-bold text-gray-900 dark:text-white mb-1">${withAudioEmoji} ${f.quality}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-3">${f.ext} â€¢ ${f.filesize_mb ? humanSizeMB(f.filesize_mb) : (f.estimated_size_mb ? ('â‰ˆ ' + humanSizeMB(f.estimated_size_mb)) : 'Unknown size')}</div>
                        <div class="text-xs text-gray-400 dark:text-gray-500">${f.fps ? f.fps + ' fps â€¢ ' : ''}${f.resolution || 'Video'}</div>
                      </div>
                      <div class="flex flex-col gap-2">
                        <button class="instant-download-button bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg"
                                data-instant-url="${API_BASE}/api/v2/${currentPlatform}/instant?url=${encodeURIComponent(urlInput.value.trim())}&format_id=${encodeURIComponent(f.format_id)}&filename=${encodeURIComponent(desiredName)}"
                                data-direct-url="${(f && f.is_progressive && f.url) ? String(f.url).replace(/\"/g,'&quot;') : ''}">âš¡ ${withAudioEmoji} Instant</button>
                        ${isInstantOnly ? '' : `<button class="smart-item-button bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg" data-format="${f.format_id}" data-progressive="${f.is_progressive ? 'true' : 'false'}">ðŸ–¥ ${withAudioEmoji} Server</button>`}
                      </div>
                    </div>
                  </div>`;
                }).join('')}
              </div>
            </div>
            <div id="mp3-content" class="format-content hidden">
              <div class="flex items-center justify-between mb-2">
                <div class="text-xs text-gray-600 dark:text-gray-300">ðŸ’¡ Instant = no server processing, faster.</div>
                <label class="text-xs flex items-center gap-2">
                  <input id="show-all-audio-toggle" type="checkbox" class="w-4 h-4">
                  <span class="text-gray-600 dark:text-gray-300">Show all audio (WEBM/M4A)</span>
                </label>
              </div>
              <div id="audio-list-container" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
            </div>
          `}
        </div>`;
      
      resultContainer.innerHTML = html;
      
      // Render audio list: MP3 first by default, toggle to reveal all audio
      (function renderAudioSection(){
        const audioBox = document.getElementById('mp3-content');
        if (!audioBox) return;
        const listEl = document.getElementById('audio-list-container');
        const toggle = document.getElementById('show-all-audio-toggle');
        const mp3Only = (arr) => (arr || []).filter(f => String(f.ext || '').toUpperCase() === 'MP3');
        const renderList = (arr) => {
          listEl.innerHTML = (arr || []).map(f => {
            const safeTitle = (title || 'audio').replace(/[\/:*?"<>|]+/g,' ').replace(/[^\w\s.-]+/g,' ').trim().replace(/\s+/g,' ');
            const desiredName = `${safeTitle}-${(f.quality || 'audio')}.${(f.ext || 'm4a').toLowerCase()}`;
            return `
              <div class="quality-card bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <div class="text-xl font-bold text-gray-900 dark:text-white mb-1">${f.quality}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-3">${f.ext} â€¢ ${f.size || (f.filesize_mb ? humanSizeMB(f.filesize_mb) : 'Unknown size')}</div>
                  </div>
                  <div class="flex flex-col gap-2">
                    ${
                      String(f.ext || '').toUpperCase() === 'MP3'
                        ? `<button class="instant-download-button bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg" data-instant-url="${API_BASE}/api/v2/${currentPlatform}/instant?url=${encodeURIComponent(urlInput.value.trim())}&format_id=${encodeURIComponent(f.format_id)}&filename=${encodeURIComponent(desiredName)}">âš¡ Instant MP3</button>`
                        : `<button class="instant-download-button bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg" data-instant-url="${API_BASE}/api/v2/${currentPlatform}/instant?url=${encodeURIComponent(urlInput.value.trim())}&format_id=${encodeURIComponent(f.format_id)}&filename=${encodeURIComponent(desiredName)}">âš¡ Instant Audio</button>`
                    }
                  </div>
                </div>
              </div>`;
          }).join('');
          // Rebind buttons inside audio list
          bindInstantButtons();
          // Rebind smart-item buttons created by re-render
          listEl.querySelectorAll('.smart-item-button').forEach(btn => {
            if (btn.dataset.boundSmart === '1') return;
            btn.dataset.boundSmart = '1';
            btn.addEventListener('click', async (e) => {
              e.preventDefault();
              const formatId = btn.getAttribute('data-format') || 'audio';
              const url = urlInput.value.trim();
              if (!url) return;
              await startDownloadWithProgress(btn, url, formatId);
            });
          });
        };
        // Initial render: prefer MP3 tab and sort MP3 by bitrate (320 kbps first)
        const byBitrate = (arr) => {
          const getRate = (q) => {
            try { const m = String(q || '').match(/(\d{2,3})/); return m ? parseInt(m[1], 10) : 0; } catch { return 0; }
          };
          try { return (arr || []).slice().sort((a,b) => getRate(b.quality) - getRate(a.quality)); } catch { return arr || []; }
        };
        const mp3List = byBitrate(mp3Only(audioFormats));
        const nonMp3 = (audioFormats || []).filter(f => String(f.ext || '').toUpperCase() !== 'MP3');
        const allSorted = [...mp3List, ...byBitrate(nonMp3)];

        // Default to MP3-only list if present, else show all sorted
        const initial = (mp3List.length ? mp3List : allSorted);
        renderList(initial);

        // Activate the MP3 tab by default when audio exists
        try {
          if ((audioFormats || []).length) {
            const mp3Tab = document.getElementById('mp3-tab');
            const mp4Tab = document.getElementById('mp4-tab');
            const mp3Content = document.getElementById('mp3-content');
            const mp4Content = document.getElementById('mp4-content');
            if (mp3Tab && mp3Content && mp4Tab && mp4Content) {
              mp3Tab.classList.add('active');
              mp4Tab.classList.remove('active');
              mp3Content.classList.remove('hidden');
              mp4Content.classList.add('hidden');
            }
          }
        } catch {}

        if (toggle) {
          // Persist preference
          const saved = localStorage.getItem('showAllAudio') === '1';
          toggle.checked = saved;
          if (saved) renderList(allSorted);
          toggle.addEventListener('change', () => {
            const showAll = !!toggle.checked;
            try { localStorage.setItem('showAllAudio', showAll ? '1' : '0'); } catch{}
            renderList(showAll ? allSorted : (mp3List.length ? mp3List : allSorted));
          });
        }
      })();

      // Setup tab switching (only for video/audio)
      if (mediaType !== 'image') setupTabs();

      // ZIP selection handling for images
      if (mediaType === 'image') {
        const zipBtn = document.getElementById('zip-download');
        const checkboxes = Array.from(resultContainer.querySelectorAll('.img-select'));
        const filenameInputs = Array.from(resultContainer.querySelectorAll('.img-filename'));
        const btnSelectAll = document.getElementById('select-all');
        const btnClearAll = document.getElementById('clear-all');
        const btnDownloadAll = document.getElementById('download-all');
        const updateBtn = () => {
          const any = checkboxes.some(c => c.checked);
          if (zipBtn) zipBtn.disabled = !any;
        };
        checkboxes.forEach(c => c.addEventListener('change', updateBtn));
        if (btnSelectAll) btnSelectAll.addEventListener('click', () => { checkboxes.forEach(c => c.checked = true); updateBtn(); });
        if (btnClearAll) btnClearAll.addEventListener('click', () => { checkboxes.forEach(c => c.checked = false); updateBtn(); });
        
        // Download All button - auto-select all and trigger ZIP download
        if (btnDownloadAll) {
          btnDownloadAll.addEventListener('click', async () => {
            // Select all images
            checkboxes.forEach(c => c.checked = true);
            updateBtn();
            
            // Trigger ZIP download with all images
            const selected = checkboxes.map((c, idx) => ({ idx: parseInt(c.value, 10), checked: true, name: filenameInputs[idx]?.value?.trim() || '' }));
            const idxs = selected.map(x => x.idx);
            const names = selected.map(x => x.name);
            
            try {
              btnDownloadAll.disabled = true;
              btnDownloadAll.innerHTML = 'â³ Preparing ZIP...';
              
              const r = await fetch(`${API_BASE}/api/${currentPlatform}/download_images_zip`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: urlInput.value.trim(), indices: idxs, filenames: names })
              });
              if (!r.ok) throw new Error('ZIP failed');
              const blob = await r.blob();
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = (info.title ? info.title.replace(/[^\w\s.-]+/g,' ').trim() : 'images') + '-all-images.zip';
              document.body.appendChild(a); a.click(); a.remove();
              setTimeout(() => URL.revokeObjectURL(a.href), 2000);
              
              btnDownloadAll.innerHTML = 'âœ… Downloaded!';
              setTimeout(() => {
                btnDownloadAll.disabled = false;
                btnDownloadAll.innerHTML = 'ðŸ“¦ Download All';
              }, 2000);
            } catch (e) {
              btnDownloadAll.disabled = false;
              btnDownloadAll.innerHTML = 'âŒ Failed';
              setTimeout(() => btnDownloadAll.innerHTML = 'ðŸ“¦ Download All', 2000);
              alert('Download All failed: ' + e.message);
            }
          });
        }
        updateBtn();
        if (zipBtn) {
          zipBtn.addEventListener('click', async () => {
            const selected = checkboxes.map((c, idx) => ({ idx: parseInt(c.value, 10), checked: c.checked, name: filenameInputs[idx]?.value?.trim() || '' }))
                                       .filter(x => x.checked);
            if (!selected.length) return;
            const idxs = selected.map(x => x.idx);
            const names = selected.map(x => x.name);
            try {
              const r = await fetch(`${API_BASE}/api/${currentPlatform}/download_images_zip`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: urlInput.value.trim(), indices: idxs, filenames: names })
              });
              if (!r.ok) throw new Error('ZIP failed');
              const blob = await r.blob();
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = (info.title ? info.title.replace(/[^\w\s.-]+/g,' ').trim() : 'images') + '-images.zip';
              document.body.appendChild(a); a.click(); a.remove();
              setTimeout(() => URL.revokeObjectURL(a.href), 2000);
            } catch (e) {
              alert('ZIP download failed');
            }
          });
        }
      }
      
      // Setup download buttons for non-direct URLs (fallback to server processing)
      resultContainer.querySelectorAll('.download-button[data-format]').forEach(btn => {
        btn.addEventListener('click', () => {
          const url = btn.getAttribute('data-url');
          const formatId = btn.getAttribute('data-format');
          startDownloadWithProgress(btn, url, formatId);
        });
      });

      // Setup per-item Smart buttons (video/audio cards)
      resultContainer.querySelectorAll('.smart-item-button').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.preventDefault();
          const url = urlInput.value.trim();
          if (!url) return;
          const formatId = btn.getAttribute('data-format') || 'best';
          // Always use inline progress UI for downloads
          await startDownloadWithProgress(btn, url, formatId);
        });
      });

      // Setup Instant Download buttons (prefer true direct URL when available; fallback to proxy endpoint)
      function bindInstantButtons() {
        resultContainer.querySelectorAll('.instant-download-button').forEach(btn => {
          // Avoid double-binding when re-rendering lists
          if (btn.dataset.boundInstant === '1') return;
          btn.dataset.boundInstant = '1';
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            const proxyInstant = btn.getAttribute('data-instant-url');
            const directMedia = btn.getAttribute('data-direct-url');
            const href = (directMedia && directMedia.length > 0) ? directMedia : proxyInstant;
            if (!href) return;

            // Show quick starting feedback on the button
            const originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = 'â³ Starting...';

            // If our instant URL points to our API, canonicalize embedded url for YouTube and control ?fast
            let finalHref = href;
            try {
              const u = new URL(href, location.origin);
              const isInstant = /\/api\/v2\/.*\/instant$/.test(u.pathname) || /\/(youtube|instagram|twitter|tiktok|pinterest|facebook)\/instant$/.test(u.pathname);
              if (isInstant) {
                const rawParam = u.searchParams.get('url');
                if (rawParam) {
                  const canon = canonicalizePlatformUrl(currentPlatform, rawParam);
                  if (canon && canon !== rawParam) u.searchParams.set('url', canon);
                }
                const fastPrefOn = (localStorage.getItem('fastRedirect') ?? '1') === '1';
                if (fastPrefOn) u.searchParams.set('fast', '1'); else u.searchParams.delete('fast');
                finalHref = u.toString();
              }
            } catch {}

            // Analytics: fire Instant click event
            try {
              if (typeof gtag === 'function') {
                gtag('event', 'instant_click', {
                  event_category: 'download',
                  event_label: currentPlatform || 'unknown',
                  fast: (localStorage.getItem('fastRedirect') ?? '1') === '1' ? 'on' : 'off'
                });
              }
            } catch {}

            // Trigger browser download via a temporary anchor
            const a = document.createElement('a');
            a.href = finalHref;
            a.rel = 'noopener noreferrer';
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            a.remove();

            // Restore button state shortly after triggering
            setTimeout(() => {
              btn.disabled = false;
              btn.innerHTML = originalHtml;
            }, 1500);
          });
        });
      }
      // Initial bind for the first render
      bindInstantButtons();

      // Setup Smart buttons for image items
      resultContainer.querySelectorAll('.smart-image-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const raw = btn.getAttribute('data-image-url');
          const defaultName = btn.getAttribute('data-default-name') || 'photo.jpg';
          if (!raw) return;

          const originalHtml = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = 'â³ Preparing...';

          const href = `${API_BASE}/api/passthrough?url=${encodeURIComponent(raw)}&filename=${encodeURIComponent(defaultName)}`;
          const a = document.createElement('a'); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; document.body.appendChild(a); a.click(); a.remove();

          setTimeout(() => { btn.disabled = false; btn.innerHTML = originalHtml; }, 1500);
        });
      });
    }

    // Enhanced download with real-time progress bar
    async function startDownloadWithProgress(button, url, formatId) {
      try {
        // Replace button with progress bar
        const originalButton = button.cloneNode(true);
        const progressContainer = document.createElement('div');
        progressContainer.className = 'bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-600 shadow-lg transition-all duration-300';
        progressContainer.innerHTML = `
          <div class="flex items-center justify-between mb-2">
            <span class="font-bold text-gray-900 dark:text-white">ðŸ“¥ Downloading...</span>
            <span class="download-percentage text-green-500 dark:text-green-400 font-mono font-bold">0%</span>
          </div>
          <div class="bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2 overflow-hidden shadow-inner">
            <div class="download-progress-fill bg-gradient-to-r from-green-500 to-green-600 h-3 rounded-full transition-all duration-300 ease-out" style="width: 0%"></div>
          </div>
          <div class="download-status text-sm text-gray-600 dark:text-gray-400">Starting download...</div>
          <button class="cancel-download-btn mt-2 px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-xs rounded font-bold">Cancel</button>
        `;
        
        button.parentNode.replaceChild(progressContainer, button);
        
        // Get progress elements
        const progressFill = progressContainer.querySelector('.download-progress-fill');
        const progressPercentage = progressContainer.querySelector('.download-percentage');
        const progressStatus = progressContainer.querySelector('.download-status');
        const cancelBtn = progressContainer.querySelector('.cancel-download-btn');
        
        // Start download
        const normUrl = canonicalizePlatformUrl(currentPlatform, url);
        let body = { url: normUrl };
        // Preserve exact format id to keep selected MP3 bitrate (mp3_128/192/320)
        body.format_id = String(formatId);
        
        const response = await fetch(`${API_BASE}/api/v2/${currentPlatform}/download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        
        if (!response.ok) {
          throw new Error(`Download failed: ${response.status}`);
        }
        
        const result = await response.json();
        const taskId = result.task_id;
        
        // Setup cancel functionality
        let cancelled = false;
        cancelBtn.addEventListener('click', async () => {
          cancelled = true;
          try {
            await fetch(`${API_BASE}/api/v2/task/${encodeURIComponent(taskId)}`, { method: 'DELETE' });
          } catch {}
          
          // Restore original button
          progressContainer.parentNode.replaceChild(originalButton, progressContainer);
          // Re-attach event listener
          originalButton.addEventListener('click', () => startDownloadWithProgress(originalButton, url, formatId));
        });
        
        // Poll for progress
        await pollDownloadProgress(taskId, progressFill, progressPercentage, progressStatus, progressContainer, originalButton, url, formatId);
        
      } catch (error) {
        console.error('Download failed:', error);
        
        // Show error and restore button
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-100 dark:bg-red-900 border border-red-400 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-2';
        errorDiv.innerHTML = `âŒ Download failed: ${error.message}`;
        
        button.parentNode.insertBefore(errorDiv, button);
        
        setTimeout(() => {
          if (errorDiv.parentNode) {
            errorDiv.remove();
          }
        }, 5000);
      }
    }
    
    // Poll download progress with real-time updates (Celery/Redis-backed)
    async function pollDownloadProgress(taskId, progressFill, progressPercentage, progressStatus, progressContainer, originalButton, url, formatId) {
      try {
        while (true) {
          const response = await fetch(`${API_BASE}/api/v2/task/${encodeURIComponent(taskId)}`);
          if (!response.ok) {
            throw new Error(`Progress request failed: ${response.status}`);
          }
          const data = await response.json();

          // Prefer Celery payload: state, status, percent, eta, detail, result
          const state = (data.state || '').toUpperCase();
          const statusText = data.detail || data.status || 'processing';
          let percentage = typeof data.percent === 'number' ? data.percent : 0;
          let etaSeconds = typeof data.eta === 'number' ? data.eta : null;

          if (state === 'SUCCESS') {
            // Task finished, show download link
            const path = data.result && data.result.path;
            const filename = path ? String(path).split(/[\\\/]/).pop() : null;
            if (filename) {
              const downloadLink = document.createElement('a');
              downloadLink.href = `/download/${encodeURIComponent(filename)}`;
              downloadLink.download = filename;
              downloadLink.className = 'inline-block mt-3 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-bold transition-all duration-200 hover:scale-105 shadow-lg text-decoration-none';
              downloadLink.innerHTML = 'ðŸ’¾ Download File';
              progressContainer.appendChild(downloadLink);
            }
            // Update progress bar to completion
            progressFill.style.width = '100%';
            progressPercentage.textContent = '100%';
            progressStatus.textContent = 'âœ… Download completed!';
            const cancelBtn = progressContainer.querySelector('.cancel-download-btn');
            if (cancelBtn) cancelBtn.remove();
            break;
          }

          if (state === 'FAILURE') {
            throw new Error((data && data.detail) || 'Download failed');
          }

          // Ongoing: use provided percent; if missing, try to parse from detail
          if (!percentage && typeof statusText === 'string') {
            const m = statusText.match(/(\d+(?:\.\d+)?)%/);
            if (m) percentage = parseFloat(m[1]);
          }

          // Build status with optional ETA if present
          let status = statusText || 'Downloading...';
          if (etaSeconds != null) {
            const mins = Math.floor(etaSeconds / 60);
            const secs = Math.floor(etaSeconds % 60).toString().padStart(2, '0');
            status += ` â€¢ ETA: ${mins}:${secs}`;
          }

          // Update UI
          progressFill.style.width = Math.min(100, Math.max(0, percentage || 0)) + '%';
          progressPercentage.textContent = String(Math.round(percentage || 0)) + '%';
          progressStatus.textContent = status;

          // Wait before next poll
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      } catch (error) {
        console.error('Progress polling failed:', error);
        // Show error in progress bar
        progressFill.className = progressFill.className.replace('from-green-500 to-green-600', 'from-red-500 to-red-600');
        progressPercentage.className = progressPercentage.className.replace('text-green-500 dark:text-green-400', 'text-red-500 dark:text-red-400');
        progressStatus.textContent = 'âŒ ' + error.message;
        progressStatus.className = progressStatus.className.replace('text-gray-600 dark:text-gray-400', 'text-red-500 dark:text-red-400');

        // Add retry button
        const retryBtn = document.createElement('button');
        retryBtn.className = 'mt-2 px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-xs rounded font-bold mr-2';
        retryBtn.textContent = 'ðŸ”„ Retry';
        retryBtn.addEventListener('click', () => {
          progressContainer.parentNode.replaceChild(originalButton, progressContainer);
          originalButton.addEventListener('click', () => startDownloadWithProgress(originalButton, url, formatId));
        });
        const cancelBtn = progressContainer.querySelector('.cancel-download-btn');
        if (cancelBtn) {
          cancelBtn.parentNode.insertBefore(retryBtn, cancelBtn);
        }
      }
    }

    // Tab switching functionality
    function setupTabs() {
      const mp4Tab = document.getElementById('mp4-tab');
      const mp3Tab = document.getElementById('mp3-tab');
      const mp4Content = document.getElementById('mp4-content');
      const mp3Content = document.getElementById('mp3-content');

      mp4Tab.addEventListener('click', () => {
        mp4Tab.classList.add('active');
        mp3Tab.classList.remove('active');
        mp4Content.classList.remove('hidden');
        mp3Content.classList.add('hidden');
      });

      mp3Tab.addEventListener('click', () => {
        mp3Tab.classList.add('active');
        mp4Tab.classList.remove('active');
        mp3Content.classList.remove('hidden');
        mp4Content.classList.add('hidden');
      });
    }

    // API calls
    async function analyze(url, platform){
      // Start colorful progress bar for analysis with platform-specific messaging
      const progressId = window.progressManager.startAnalysisProgress(url, platform);
      
      try {
        const normUrl = PlatformUtils.canonicalizePlatformUrl(platform, url);
        const r = await fetch(`${API_BASE}/api/v2/${platform}/info?url=${encodeURIComponent(normUrl)}`);
        if (!r.ok) {
          const errorData = await r.json().catch(() => ({}));
          throw new Error(errorData.error || 'Analyze failed');
        }
        
        const result = await r.json();
        
        // Complete analysis progress with format count and media type
        const formatCount = (result.mp4?.length || 0) + (result.mp3?.length || 0) + (result.images?.length || 0);
        const mediaType = result.media_type || (result.images?.length > 0 && !result.mp4?.length ? 'image' : 'video');
        window.progressManager.completeAnalysisProgress(progressId, formatCount, mediaType);
        
        return result;
      } catch (error) {
        // Show error in progress bar
        window.progressManager.errorProgress(progressId, error.message);
        throw error;
      }
    }

    let currentTaskId = null;
    let currentDownloadProgressId = null;
    
    // opts: { preferredExt?: 'mkv'|'mp4'|'mp3', desiredFilename?: string }
    async function startDownload(url, format_id, opts = {}){
      try {
        // Start colorful progress bar for download (use desired filename if provided)
        const progressLabel = opts.desiredFilename || `${format_id}_download`;
        currentDownloadProgressId = window.progressManager.startDownloadProgress(progressLabel);
        
        // Start server-side task via v2 API
        const normUrl = PlatformUtils.canonicalizePlatformUrl(currentPlatform, url);
        let body = { url: normUrl };
        if (String(format_id).startsWith('mp3_')) {
          // Use universal mp3 workflow (fixed 192k)
          body.format_id = 'audio';
        } else {
          body.format_id = String(format_id);
        }
        const r = await fetch(`${API_BASE}/api/v2/${currentPlatform}/download`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        let data = null;
        try { data = await r.json(); } catch {}
        if (!r.ok) throw new Error((data && (data.detail || data.error)) || `Start failed (${r.status})`);
        currentTaskId = data.task_id;
        showProcessing(true);
        pollProgress(currentTaskId);
      } catch (err) {
        console.error('Server Download start failed:', err);
        if (currentDownloadProgressId) {
          window.progressManager.errorProgress(currentDownloadProgressId, err?.message || 'Start failed');
        }
        showProcessing(false);
        showStatus(err?.message || 'Start failed', 'error');
      }
    }

    // Progress modal
    const modal = document.getElementById('processing-modal');
    const progressText = document.getElementById('progress-text');
    const etaText = document.getElementById('eta-text');
    const bar = document.getElementById('modal-progress-bar');
    const spinner = document.getElementById('progress-spinner');

    function showProcessing(show){
      if (show){
        // Reset modal visual state
        progressText.classList.add('invisible');
        etaText.classList.add('hidden');
        bar.style.width = '0%';
        spinner.style.display = 'block';
        modal.classList.remove('hidden');
        requestAnimationFrame(()=> modal.style.opacity = '1');
      } else {
        modal.style.opacity = '0';
        setTimeout(()=> modal.classList.add('hidden'), 300);
      }
    }

    // Cancel handling
    const cancelBtn = document.getElementById('cancel-merge');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', async () => {
        try {
          if (currentTaskId) {
            await fetch(`${API_BASE}/api/v2/task/${currentTaskId}`, { method: 'DELETE' });
          }
        } catch {}
        showProcessing(false);
        showStatus('Cancelled by user.', 'error');
      });
    }

    async function pollProgress(taskId){
      try {
        while (true){
          const r = await fetch(`${API_BASE}/api/v2/task/${taskId}`);
          if (!r.ok) {
            const txt = await r.text();
            throw new Error(`Progress request failed (${r.status}) ${txt || ''}`);
          }
          let data = null;
          try { data = await r.json(); } catch (e) {
            console.warn('Progress JSON parse failed:', e);
            throw new Error('Invalid progress response');
          }
          const status = data.status || data.state || 'initializing';
          // Progress may contain ANSI codes like "\u001b[0;94m 38.5%\u001b[0m"; clean it
          const raw = (data.progress ?? '0').toString();
          const cleaned = stripAnsi(raw).trim();
          const match = cleaned.match(/([0-9]+(?:\.[0-9]+)?)%/);
          const pct = match ? parseFloat(match[1]) : (parseFloat(cleaned) || 0);
          
          // Update original modal
          progressText.textContent = `${isNaN(pct) ? 0 : pct}%`;
          bar.style.width = Math.max(0, Math.min(100, isNaN(pct) ? 0 : pct)) + '%';
          
          // Update colorful progress bar
          if (currentDownloadProgressId) {
            const speed = data.speed || '';
            const etaFormatted = data.eta != null ? `${Math.floor(data.eta / 60)}:${Math.floor(data.eta % 60).toString().padStart(2,'0')}` : '';
            const details = `Status: ${status} | Task: ${taskId}`;
            window.progressManager.updateDownloadProgress(currentDownloadProgressId, isNaN(pct) ? 0 : pct, speed, etaFormatted, details);
          }
          
          if (data.eta != null){
            const mins = Math.floor(data.eta / 60), secs = Math.floor(data.eta % 60);
            etaText.textContent = `ETA: ${mins}:${secs.toString().padStart(2,'0')}`;
          }
          if (status === 'cancelled'){
            if (currentDownloadProgressId) {
              window.progressManager.errorProgress(currentDownloadProgressId, 'Cancelled by user');
            }
            showProcessing(false);
            showStatus('Cancelled by user.', 'error');
            break;
          }
          if (status === 'finished' && data.filename){
            if (currentDownloadProgressId) {
              window.progressManager.updateDownloadProgress(currentDownloadProgressId, 100, '', '', `File: ${data.filename}`);
            }
            showProcessing(false);
            window.location.href = `/download/${encodeURIComponent(data.filename)}`;
            break;
          }
          if (status === 'error'){
            if (currentDownloadProgressId) {
              window.progressManager.errorProgress(currentDownloadProgressId, data.error || 'Download error');
            }
            showProcessing(false);
            
            // Check if it's a cookies-related error
            const errorMsg = data.error || 'Download error';
            const needsCookies = data.cookies_required || 
              /login|private|forbidden|403|unauthorized|401|consent|age.restricted/i.test(errorMsg);
            
            if (needsCookies) {
              showCookiesError(errorMsg);
            } else {
              showStatus(errorMsg, 'error');
            }
            break;
          }
          await new Promise(res => setTimeout(res, 800));
        }
      } catch(e){
        console.error('Progress polling failed:', e);
        if (currentDownloadProgressId) {
          window.progressManager.errorProgress(currentDownloadProgressId, e.message || 'Progress error');
        }
        showProcessing(false);
        showStatus(e.message || 'Progress error', 'error');
      }
    }

    // Show cookies error with helpful message
    function showCookiesError(errorMsg) {
      const statusContainer = document.getElementById('status-container');
      statusContainer.innerHTML = `
        <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4 animate-fade-in">
          <div class="flex items-start gap-3">
            <span class="text-2xl">ðŸª</span>
            <div class="flex-1">
              <h3 class="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Login Required</h3>
              <p class="text-sm text-yellow-700 dark:text-yellow-300 mb-3">${errorMsg}</p>
              <p class="text-sm text-yellow-600 dark:text-yellow-400 mb-3">
                This content requires login cookies. Upload your browser cookies to access private posts.
              </p>
              <div class="flex gap-2">
                <a href="/cookies" class="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-semibold transition-colors">
                  <span>ðŸª</span> Manage Cookies
                </a>
                <button onclick="this.parentElement.parentElement.parentElement.parentElement.remove()" 
                        class="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    // Copy to clipboard function
    async function copyToClipboard(url) {
      try {
        await navigator.clipboard.writeText(url);
        showStatus('Link copied to clipboard! ðŸ“‹', 'success');
      } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showStatus('Link copied to clipboard! ðŸ“‹', 'success');
      }
    }

    // Form actions
    document.getElementById('download-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = urlInput.value.trim();
      if (!url){ urlInput.classList.add('animate-shake'); setTimeout(()=>urlInput.classList.remove('animate-shake'), 500); return; }
      showStatus('ðŸ” Starting analysis with colorful progress...', 'info');
      submitBtn.disabled = true;
      try {
        const info = await analyze(url, currentPlatform);
        renderResult(info);
        // Remember last analyzed for nicer filenames with Instant Best
        window.lastAnalyzed = { url, title: (info && info.title) ? String(info.title) : null };
        showStatus('âœ… Analysis completed successfully!', 'success');
      } catch(err){ 
        showStatus(`âŒ ${err.message || 'Analyze failed'}`, 'error'); 
      }
      finally { submitBtn.disabled = false; }
    });

    pasteBtn.addEventListener('click', async () => {
      try { const txt = await navigator.clipboard.readText(); urlInput.value = txt || urlInput.value; } catch{}
      clearBtn.classList.toggle('hidden', !urlInput.value);
    });
    clearBtn.addEventListener('click', () => { urlInput.value=''; clearBtn.classList.add('hidden'); });
    urlInput.addEventListener('input', () => clearBtn.classList.toggle('hidden', !urlInput.value));

    // Quick Test Links: render and enable one-click analyze
    function selectPlatform(key){
      const btn = document.querySelector(`.platform-button[data-key="${key}"]`);
      if (btn) {
        btn.click();
      } else {
        currentPlatform = key;
        setPlatformColor(key); setPlatformPlaceholder(key); setInputIcon(key);
        submitBtn.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue('--platform-color');
        document.querySelectorAll('.platform-button').forEach(b => b.dataset.key && b.classList.toggle('active', b.dataset.key === key));
      }
    }

    async function analyzeLink(url, platform){
      try {
        selectPlatform(platform);
        urlInput.value = url;
        clearBtn.classList.toggle('hidden', !urlInput.value);
        showStatus('ðŸ” Starting analysis...', 'info');
        const info = await analyze(url, platform);
        renderResult(info);
        window.lastAnalyzed = { url, title: (info && info.title) ? String(info.title) : null };
        showStatus('âœ… Analysis completed successfully!', 'success');
      } catch (err) {
        showStatus(`âŒ ${err && err.message ? err.message : 'Analyze failed'}`, 'error');
      }
    }

    function renderTestLinks(){
      const container = document.getElementById('test-links-container');
      if (!container) return;

      // Ordered by common usage
      const platformOrder = ['youtube','instagram','tiktok','facebook','twitter','pinterest','snapchat','linkedin','reddit'];

      // Grouped by content type with badges
      const testLinks = {
        youtube: {
          'ðŸŽ¥ Video': [
            { label: 'Normal Video', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', badge: 'ðŸŽ¥ Long Video' }
          ],
          'ðŸŽ¬ Shorts / ðŸ“‘ Playlist / ðŸ‘¤ Channel': [
            { label: 'Shorts', url: 'https://www.youtube.com/shorts/aqz-KE-bpKQ', badge: 'ðŸŽ¬ Short' },
            { label: 'Playlist', url: 'https://www.youtube.com/playlist?list=PLMC9KNkIncKtsacKpgMb0CVqT5pXrWpKf', badge: 'ðŸ“‘ Playlist' },
            { label: 'Channel', url: 'https://www.youtube.com/@NASA', badge: 'ðŸ”— Page' }
          ]
        },
        instagram: {
          'ðŸ–¼ Photo / ðŸ“‘ Carousel': [
            { label: 'Photo', url: 'https://www.instagram.com/p/C8QltYbIh2P/', badge: 'Photo' },
            { label: 'Carousel', url: 'https://www.instagram.com/p/CWg8ZBxD5cf/', badge: 'Carousel' }
          ],
          'ðŸŽ¥ Video / ðŸŽ¬ Reels / IGTV': [
            { label: 'Video', url: 'https://www.instagram.com/p/CFkFyr0HT5G/', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Reel', url: 'https://www.instagram.com/reel/C9cP8s1yR3R/', badge: 'ðŸŽ¬ Reel' },
            { label: 'IGTV', url: 'https://www.instagram.com/tv/CFnU1OcJk5L/', badge: 'ðŸŽ¬ IGTV' }
          ],
          'ðŸ‘¤ Profile / # Hashtag / ðŸ“ Location': [
            { label: 'Profile', url: 'https://www.instagram.com/nasa/', badge: 'ðŸ”— Page' },
            { label: 'Location', url: 'https://www.instagram.com/explore/locations/213385402/new-york-new-york/', badge: 'ðŸ”— Page' },
            { label: 'Hashtag', url: 'https://www.instagram.com/explore/tags/sunset/', badge: 'ðŸ”— Page' }
          ]
        },
        tiktok: {
          'ðŸŽ¥ Video / ðŸ‘¤ Profile / # Hashtag': [
            { label: 'Video', url: 'https://www.tiktok.com/@scout2015/video/6718335390845095173', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Profile', url: 'https://www.tiktok.com/@charlidamelio', badge: 'ðŸ”— Page' },
            { label: 'Hashtag', url: 'https://www.tiktok.com/tag/fyp', badge: 'ðŸ”— Page' }
          ]
        },
        facebook: {
          'ðŸŽ¥ Video / ðŸ–¼ Post / ðŸ“‘ Album / ðŸ‘¤ Page': [
            { label: 'Public Video', url: 'https://www.facebook.com/watch/?v=10153231379946729', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Image Post', url: 'https://www.facebook.com/20531316728/posts/10154009990506729/', badge: 'ðŸ–¼ Photo' },
            { label: 'Album', url: 'https://www.facebook.com/media/set/?set=a.10100480647661891&type=3', badge: 'ðŸ“‘ Album' },
            { label: 'Page', url: 'https://www.facebook.com/nasa', badge: 'ðŸ”— Page' }
          ]
        },
        twitter: {
          'ðŸ–¼ Image / ðŸŽ¥ Video / ðŸ§µ Thread / ðŸ‘¤ Profile / # Hashtag': [
            { label: 'Image Tweet', url: 'https://twitter.com/nasa/status/1410624005669169154', badge: 'ðŸ–¼ Photo' },
            { label: 'Video Tweet', url: 'https://twitter.com/jack/status/20', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Thread', url: 'https://twitter.com/naval/status/1002103360646823936', badge: 'ðŸ”— Page' },
            { label: 'Profile', url: 'https://twitter.com/nasa', badge: 'ðŸ”— Page' },
            { label: 'Hashtag', url: 'https://twitter.com/hashtag/AI', badge: 'ðŸ”— Page' }
          ]
        },
        pinterest: {
          'ðŸ–¼ Pin / ðŸ“‘ Board / ðŸ‘¤ Profile': [
            { label: 'Pin', url: 'https://www.pinterest.com/pin/99360735500167749/', badge: 'ðŸ–¼ Photo' },
            { label: 'Board', url: 'https://www.pinterest.com/nasa/space/', badge: 'ðŸ“‘ Board' },
            { label: 'Profile', url: 'https://www.pinterest.com/nasa/', badge: 'ðŸ”— Page' }
          ]
        },
        snapchat: {
          'ðŸŽ¥ Spotlight / ðŸ‘¤ Profile': [
            { label: 'Spotlight', url: 'https://www.snapchat.com/spotlight/WxPZ7VUrW3n', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Profile', url: 'https://www.snapchat.com/add/team.snapchat', badge: 'ðŸ”— Page' }
          ]
        },
        linkedin: {
          'ðŸ–¼ Post (Image) / ðŸŽ¥ Post (Video) / ðŸ‘¤ Company / ðŸ“„ Article': [
            { label: 'Post (Image)', url: 'https://www.linkedin.com/posts/linkedin_what-are-your-goals-activity-7010844765029011456-XYZ/', badge: 'ðŸ–¼ Photo' },
            { label: 'Post (Video)', url: 'https://www.linkedin.com/posts/ericschmidt_ai-and-society-activity-7048730381558749184-YsJK/', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Profile', url: 'https://www.linkedin.com/company/nasa/', badge: 'ðŸ”— Page' },
            { label: 'Article', url: 'https://www.linkedin.com/pulse/future-work-jeff-weiner/', badge: 'ðŸ”— Page' }
          ]
        },
        reddit: {
          'ðŸŽ¥ Video / ðŸ–¼ Image / ðŸ“ Text / ðŸ§© Subreddit': [
            { label: 'Video Post', url: 'https://www.reddit.com/r/videos/comments/1c7dqk/sample_video_post/', badge: 'ðŸŽ¥ Long Video' },
            { label: 'Image Post', url: 'https://www.reddit.com/r/pics/comments/3g1jfi/cute_cat_picture/', badge: 'ðŸ–¼ Photo' },
            { label: 'Text Post', url: 'https://www.reddit.com/r/AskReddit/comments/1ajk3f/what_is_your_favorite_book/', badge: 'ðŸ”— Page' },
            { label: 'Subreddit', url: 'https://www.reddit.com/r/space/', badge: 'ðŸ”— Page' }
          ]
        }
      };

      // PDF tests (separate at bottom)
      const pdfTests = [
        { label: 'Sample PDF 1', url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf', badge: 'PDF' },
        { label: 'Sample PDF 2', url: 'https://www.africau.edu/images/default/sample.pdf', badge: 'PDF' }
      ];

      container.innerHTML = '';

      // Render per platform with collapsible sections
      platformOrder.forEach(platform => {
        const groups = testLinks[platform];
        if (!groups) return;
        const section = document.createElement('div');
        section.className = 'rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden';
        const OPEN_PANELS_STATE = (loadOpenPanels ? loadOpenPanels() : ['youtube','instagram']);
        const shouldOpen = OPEN_PANELS_STATE.includes(platform);
        section.innerHTML = `
          <details class="group" data-platform="${platform}" ${shouldOpen ? 'open' : ''}>
            <summary class="flex items-center justify-between px-3 py-2 cursor-pointer bg-gray-50 dark:bg-gray-900/40">
              <span class="font-semibold flex items-center gap-2">
                <img src="${platformDetails[platform]?.iconUrl || ''}" class="w-5 h-5" alt="${platform}">
                <span class="capitalize">${platform}</span>
              </span>
              <div class="flex items-center gap-2">
                <button class="copy-all-btn px-2 py-0.5 text-[11px] rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600" data-platform="${platform}">Copy All</button>
                <button class="run-all-btn px-2 py-0.5 text-[11px] rounded bg-red-500 hover:bg-red-600 text-white" data-platform="${platform}">Run All</button>
                <span class="text-xs text-gray-500 group-open:hidden">Expand</span>
                <span class="text-xs text-gray-500 hidden group-open:inline">Collapse</span>
              </div>
            </summary>
            <div class="p-3 space-y-3">
            </div>
          </details>`;

        const body = section.querySelector('.p-3.space-y-3');
        Object.entries(groups).forEach(([groupTitle, items]) => {
          const block = document.createElement('div');
          block.className = 'bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700';
          const inner = document.createElement('div');
          inner.className = 'p-3 space-y-2';
          const heading = document.createElement('div');
          heading.className = 'text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1';
          heading.textContent = groupTitle;
          inner.appendChild(heading);

          items.forEach(item => {
            const analyzable = (() => {
              const b = item.badge || '';
              const lbl = (item.label || '').toLowerCase();
              switch (platform) {
                case 'youtube':
                  if (b.includes('Playlist')) return true; // ðŸ“‘ Playlist
                  if (lbl.includes('channel')) return true; // Channel
                  break;
                case 'twitter':
                  if (lbl.includes('thread')) return true; // Thread
                  break;
                case 'facebook':
                  if (b.includes('Album') || lbl.includes('album')) return true; // ðŸ“‘ Album
                  break;
              }
              if (b === 'ðŸ”— Page' || b === 'ðŸ“‘ Board') return false; // disable for generic Page and Board
              return true; // photos/videos/reels/etc.
            })();

            const badgeClasses = !analyzable
              ? 'ml-2 px-2 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              : 'ml-2 px-2 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700';

            const row = document.createElement('div');
            row.className = 'flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white dark:bg-gray-800 rounded border border-gray-100 dark:border-gray-700 p-2';
            row.innerHTML = `
              <div class="min-w-0 ${!analyzable ? 'opacity-80' : ''}">
                <div class="text-sm font-medium flex items-center gap-2">${item.label}
                  ${item.badge ? `<span class=\"${badgeClasses}\">${item.badge}</span>` : ''}
                </div>
                <a href="${item.url}" target="_blank" class="text-xs text-blue-600 break-all">${item.url}</a>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                ${analyzable ? `<button class=\"analyze-btn px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-xs rounded\" data-platform=\"${platform}\" data-url=\"${item.url}\">Analyze</button>` : ''}
                <button class="copy-btn px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-xs rounded" data-url="${item.url}">Copy</button>
              </div>`;
            inner.appendChild(row);
          });
          block.appendChild(inner);
          body.appendChild(block);
        });

        container.appendChild(section);

        // Persist toggle state
        const detailsEl = section.querySelector('details');
        if (detailsEl) {
          detailsEl.addEventListener('toggle', () => {
            if (typeof loadOpenPanels === 'function' && typeof saveOpenPanels === 'function') {
              const list = loadOpenPanels();
              const key = detailsEl.dataset.platform;
              const idx = list.indexOf(key);
              if (detailsEl.open && idx === -1) list.push(key);
              if (!detailsEl.open && idx !== -1) list.splice(idx, 1);
              saveOpenPanels(list);
            }
          });
        }
      });

      // PDF section at the bottom
      const pdfSection = document.createElement('div');
      pdfSection.className = 'rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden';
      pdfSection.innerHTML = `
        <details class="group">
          <summary class="flex items-center justify-between px-3 py-2 cursor-pointer bg-gray-50 dark:bg-gray-900/40">
            <span class="font-semibold flex items-center gap-2">ðŸ“„ <span>Generic PDF Tests</span></span>
            <span class="text-xs text-gray-500 group-open:hidden">Expand</span>
            <span class="text-xs text-gray-500 hidden group-open:inline">Collapse</span>
          </summary>
          <div class="p-3 space-y-2"></div>
        </details>`;
      const pdfBody = pdfSection.querySelector('.p-3.space-y-2');
      pdfTests.forEach(item => {
        const row = document.createElement('div');
        row.className = 'flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white dark:bg-gray-800 rounded-md p-2 border border-gray-200 dark:border-gray-700';
        row.innerHTML = `
          <div class="min-w-0">
            <div class="text-sm font-medium flex items-center gap-2">${item.label}
              <span class="ml-2 px-2 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700">${item.badge}</span>
            </div>
            <a href="${item.url}" target="_blank" class="text-xs text-blue-600 break-all">${item.url}</a>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button class="copy-btn px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-xs rounded" data-url="${item.url}">Copy</button>
          </div>`;
        pdfBody.appendChild(row);
      });
      container.appendChild(pdfSection);

      // Wire events
      container.querySelectorAll('.analyze-btn').forEach(btn => {
        btn.addEventListener('click', () => analyzeLink(btn.dataset.url, btn.dataset.platform));
      });
      container.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => copyToClipboard(btn.dataset.url));
      });

      // Copy All / Run All per platform
      container.querySelectorAll('.copy-all-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const platform = btn.dataset.platform;
          const urls = Array.from(btn.closest('details').querySelectorAll('[data-url]')).map(b => b.dataset.url);
          const text = urls.join('\n');
          navigator.clipboard.writeText(text).then(() => showStatus(`Copied ${urls.length} links for ${platform}`, 'success')).catch(() => showStatus('Copy failed', 'error'));
        });
      });
      container.querySelectorAll('.run-all-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const platform = btn.dataset.platform;
          const urls = Array.from(btn.closest('details').querySelectorAll('[data-url]')).map(b => b.dataset.url);
          if (!urls.length) return;
          selectPlatform(platform);
          showStatus(`Queuing ${urls.length} analyses for ${platform}...`, 'info');
          for (const u of urls) {
            try {
              await analyzeLink(u, platform);
            } catch (e) {
              console.warn('Batch analyze failed for', u, e);
            }
            await new Promise(r => setTimeout(r, 400));
          }
          showStatus(`Finished batch analyze for ${platform}`, 'success');
        });
      });

      // Expand/Collapse all
      const expandAll = document.getElementById('expand-all-tests');
      const collapseAll = document.getElementById('collapse-all-tests');
      if (expandAll) expandAll.addEventListener('click', () => {
        container.querySelectorAll('details').forEach(d => d.open = true);
        if (typeof persistOpenPanelsFromDOM === 'function') persistOpenPanelsFromDOM();
      });
      if (collapseAll) collapseAll.addEventListener('click', () => {
        container.querySelectorAll('details').forEach(d => d.open = false);
        if (typeof persistOpenPanelsFromDOM === 'function') persistOpenPanelsFromDOM();
      });
    }

    // Render once on load
    try { renderTestLinks(); } catch (e) { console.warn('Test links render failed:', e); }

    // Global Run All Tests with adjustable delays and optional concurrency
    const RUN_ALL_CONFIG_DEFAULTS = {
      intraDelayMs: 600,   // delay between links in same platform
      interDelayMs: 1800,  // delay when switching platforms
      concurrency: 1       // optional concurrency per platform (1 = sequential)
    };

    // Persist expanded/collapsed platform sections
    const DEFAULT_OPEN_PLATFORMS = ['youtube','instagram']; // configurable default
    const OPEN_PANELS_KEY = 'testLinksOpenPanels';
    function loadOpenPanels() {
      try {
        const raw = localStorage.getItem(OPEN_PANELS_KEY);
        if (!raw) return [...DEFAULT_OPEN_PLATFORMS];
        const arr = JSON.parse(raw);
        return Array.isArray(arr) ? arr : [...DEFAULT_OPEN_PLATFORMS];
      } catch { return [...DEFAULT_OPEN_PLATFORMS]; }
    }
    function saveOpenPanels(arr) {
      try { localStorage.setItem(OPEN_PANELS_KEY, JSON.stringify(arr)); } catch {}
    }
    function persistOpenPanelsFromDOM() {
      const open = Array.from(document.querySelectorAll('#test-links-container details[data-platform]'))
        .filter(d => d.open)
        .map(d => d.dataset.platform);
      saveOpenPanels(open);
    }

    // Global config persistence
    function loadRunAllConfig(){
      try {
        const raw = localStorage.getItem('runAllConfig');
        if (!raw) return { ...RUN_ALL_CONFIG_DEFAULTS };
        const parsed = JSON.parse(raw);
        return {
          intraDelayMs: Math.max(200, parsed.intraDelayMs ?? RUN_ALL_CONFIG_DEFAULTS.intraDelayMs),
          interDelayMs: Math.max(800, parsed.interDelayMs ?? RUN_ALL_CONFIG_DEFAULTS.interDelayMs),
          concurrency: Math.max(1, Math.min(3, parsed.concurrency ?? RUN_ALL_CONFIG_DEFAULTS.concurrency))
        };
      } catch { return { ...RUN_ALL_CONFIG_DEFAULTS }; }
    }
    function saveRunAllConfig(cfg){
      try { localStorage.setItem('runAllConfig', JSON.stringify(cfg)); } catch {}
    }

    // Test Mode persistence + UI
    const TEST_MODE_KEY = 'runAllTestMode';
    function isTestMode() { return localStorage.getItem(TEST_MODE_KEY) === '1'; }
    function setTestMode(on) { try { localStorage.setItem(TEST_MODE_KEY, on ? '1' : '0'); } catch {}; applyTestModeUI(); }
    function applyTestModeUI() {
      const on = isTestMode();
      const cb = document.getElementById('as-testmode'); if (cb) cb.checked = on;
      const badge = document.getElementById('testmode-banner'); if (badge) badge.classList.toggle('hidden', !on);
      const intra = document.getElementById('as-intra');
      const inter = document.getElementById('as-inter');
      const conc = document.getElementById('as-concurrency');
      [intra, inter, conc].forEach(el => el && (el.disabled = on));
    }
    function getEffectiveRunAllConfig() {
      if (isTestMode()) { return { intraDelayMs: 1000, interDelayMs: 2500, concurrency: 1 }; }
      return { ...RUN_ALL_CONFIG };
    }

    let RUN_ALL_CONFIG = loadRunAllConfig();
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // Global run state
    let GLOBAL_RUN_ACTIVE = false;
    let GLOBAL_RUN_STOP = false;

    async function runAllGlobal(tasks, config = RUN_ALL_CONFIG) {
      const counterEl = document.getElementById('global-run-counter');
      const stopBtn = document.getElementById('stop-global-run');
      const runBtn = document.getElementById('run-all-global');

      // Setup UI state
      GLOBAL_RUN_ACTIVE = true;
      GLOBAL_RUN_STOP = false;
      let done = 0;
      const total = tasks.length;
      const updateCounter = () => {
        if (!counterEl) return;
        counterEl.textContent = `Running ${done}/${total} testsâ€¦`;
      };
      if (counterEl) { counterEl.classList.remove('hidden'); counterEl.textContent = `Running 0/${total} testsâ€¦`; }
      if (stopBtn) { stopBtn.classList.remove('hidden'); stopBtn.disabled = false; stopBtn.onclick = () => { GLOBAL_RUN_STOP = true; stopBtn.disabled = true; }; }
      if (runBtn) { runBtn.disabled = true; }

      // Group tasks by platform to respect inter-platform delay and optional concurrency
      const byPlatform = tasks.reduce((acc, t) => { (acc[t.platform] ||= []).push(t); return acc; }, {});
      const platforms = Object.keys(byPlatform);

      try {
        for (const platform of platforms) {
          if (GLOBAL_RUN_STOP) break;
          selectPlatform(platform);
          await sleep(config.interDelayMs);
          const items = byPlatform[platform];

          if ((config.concurrency || 1) <= 1) {
            // Sequential
            for (const { url } of items) {
              if (GLOBAL_RUN_STOP) break;
              try { await analyzeLink(url, platform); } catch (e) { console.warn('Analyze failed', platform, url, e); }
              done++; updateCounter();
              await sleep(config.intraDelayMs);
            }
          } else {
            // Limited concurrency with progress updates
            const pool = Math.max(1, Math.min(3, config.concurrency));
            let idx = 0;
            async function worker() {
              while (idx < items.length && !GLOBAL_RUN_STOP) {
                const i = idx++;
                const { url } = items[i];
                try { await analyzeLink(url, platform); } catch (e) { console.warn('Analyze failed', platform, url, e); }
                done++; updateCounter();
                await sleep(config.intraDelayMs);
              }
            }
            await Promise.all(Array.from({ length: pool }, worker));
          }
        }
      } finally {
        GLOBAL_RUN_ACTIVE = false;
        GLOBAL_RUN_STOP = false;
        if (counterEl) counterEl.classList.add('hidden');
        if (stopBtn) { stopBtn.classList.add('hidden'); stopBtn.disabled = false; stopBtn.onclick = null; }
        if (runBtn) runBtn.disabled = false;
      }
    }

    // Wire Advanced Settings Apply
    function seedAdvancedDefaults(){
      const intra = document.getElementById('as-intra');
      const inter = document.getElementById('as-inter');
      const conc = document.getElementById('as-concurrency');
      if (intra) intra.value = RUN_ALL_CONFIG.intraDelayMs;
      if (inter) inter.value = RUN_ALL_CONFIG.interDelayMs;
      if (conc) conc.value = String(Math.max(1, Math.min(3, RUN_ALL_CONFIG.concurrency || 1)));
    }
    seedAdvancedDefaults();

    const applyBtn = document.getElementById('as-apply');
    if (applyBtn) {
      applyBtn.addEventListener('click', () => {
        const intra = parseInt(document.getElementById('as-intra')?.value || '600', 10);
        const inter = parseInt(document.getElementById('as-inter')?.value || '1800', 10);
        let conc = parseInt(document.getElementById('as-concurrency')?.value || '1', 10);
        const tmode = !!document.getElementById('as-testmode')?.checked;
        if (isNaN(intra) || intra < 200) return showStatus('Intra delay must be â‰¥ 200ms', 'error');
        if (isNaN(inter) || inter < 800) return showStatus('Inter delay must be â‰¥ 800ms', 'error');
        if (isNaN(conc)) conc = 1;
        conc = Math.max(1, Math.min(3, conc));
        RUN_ALL_CONFIG.intraDelayMs = intra;
        RUN_ALL_CONFIG.interDelayMs = inter;
        RUN_ALL_CONFIG.concurrency = conc;
        saveRunAllConfig(RUN_ALL_CONFIG);
        setTestMode(tmode);
        if (tmode) showStatus('ðŸ§ª Test Mode overrides are active (concurrency=1, delays 1000/2500ms).', 'info');
        showStatus('âœ… Settings applied', 'success');
      });
    }

    const resetBtn = document.getElementById('as-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        RUN_ALL_CONFIG = { ...RUN_ALL_CONFIG_DEFAULTS };
        saveRunAllConfig(RUN_ALL_CONFIG);
        try { localStorage.removeItem('runAllTestMode'); } catch {}
        applyTestModeUI();
        seedAdvancedDefaults();
        showStatus('âœ… Settings reset to defaults', 'success');
      });
    }

    const globalRunAllBtn = document.getElementById('run-all-global');
    if (globalRunAllBtn) {
      // Rebind to ensure we always use effective config (respects Test Mode)
      const clone = globalRunAllBtn.cloneNode(true);
      globalRunAllBtn.parentNode.replaceChild(clone, globalRunAllBtn);
      clone.addEventListener('click', async () => {
        if (GLOBAL_RUN_ACTIVE) return; // prevent double start
        const allDetails = Array.from(document.querySelectorAll('#test-links-container details'));
        const tasks = [];
        allDetails.forEach(d => {
          const platform = d.querySelector('.run-all-btn')?.dataset.platform;
          if (!platform) return;
          d.querySelectorAll('.analyze-btn').forEach(btn => tasks.push({ platform, url: btn.dataset.url }));
        });
        if (!tasks.length) { showStatus('No analyzable links found.', 'error'); return; }
        const confirmMsg = `This will queue ${tasks.length} analyses across all platforms. Continue?`;
        if (!confirm(confirmMsg)) return;
        showStatus(`Starting global run of ${tasks.length} analyses...`, 'info');
        try {
          await runAllGlobal(tasks, getEffectiveRunAllConfig());
          showStatus('Global run finished.', 'success');
        } catch (e) {
          console.warn('Global run error', e);
          showStatus('Global run encountered errors. See console.', 'error');
        }
      });
    }


    // Theme + Fast Redirect toggles
    const themeBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');
    const fastBtn = document.getElementById('fast-toggle-btn');

    function setTheme(mode){
      document.documentElement.classList.toggle('dark', mode==='dark');
      themeIcon.textContent = mode==='dark' ? 'ðŸŒž' : 'ðŸŒ™';
      localStorage.setItem('theme', mode);
    }
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    themeBtn.addEventListener('click', () => setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark'));

    // Fast Redirect preference (default ON)
    function setFastPref(on){
      try { localStorage.setItem('fastRedirect', on ? '1' : '0'); } catch {}
      fastBtn.classList.toggle('bg-green-500', !!on);
      fastBtn.classList.toggle('text-white', !!on);
      fastBtn.classList.toggle('bg-gray-200', !on);
      fastBtn.classList.toggle('dark:bg-gray-700', !on);
      fastBtn.title = on ? 'Fast Redirect ON (302 to CDN)' : 'Fast Redirect OFF (server proxy)';
    }
    let fastPref = (localStorage.getItem('fastRedirect') ?? '1') === '1';
    setFastPref(fastPref);
    fastBtn.addEventListener('click', () => { fastPref = !fastPref; setFastPref(fastPref); });
  });

  // Image Preview Modal Functions
  function openImagePreview(imageUrl, title) {
    const modal = document.getElementById('image-preview-modal');
    const previewImage = document.getElementById('preview-image');
    const previewTitle = document.getElementById('preview-title');
    
    // Use passthrough proxy to avoid hotlink/CORS blocks
    const proxied = proxyUrl(imageUrl);
    previewImage.onerror = () => { previewImage.src = '/static/og-default.svg'; previewImage.onerror = null; };
    previewImage.src = proxied;
    previewTitle.textContent = title || 'Image Preview';
    modal.classList.remove('hidden');
    
    // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeImagePreview();
    });
    
    // Close on Escape key
    document.addEventListener('keydown', function escapeHandler(e) {
      if (e.key === 'Escape') {
        closeImagePreview();
        document.removeEventListener('keydown', escapeHandler);
      }
    });
  }

  function closeImagePreview() {
    const modal = document.getElementById('image-preview-modal');
    modal.classList.add('hidden');
  }

  // Single Image Download Function
  function downloadSingleImage(imageUrl, filename) {
    try {
      const safeName = (filename || 'image.jpg').replace(/[\/:*?"<>|]+/g,' ').replace(/[^\w\s.-]+/g,' ').trim().replace(/\s+/g,' ');
      const passthroughUrl = `/api/passthrough?url=${encodeURIComponent(imageUrl)}&filename=${encodeURIComponent(safeName)}`;
      // Create temporary anchor for forced download via server (sets Content-Disposition)
      const a = document.createElement('a');
      a.href = passthroughUrl;
      a.rel = 'noopener noreferrer';
      a.target = '_blank';
      document.body.appendChild(a);
      a.click();
      a.remove();
      showStatus(`âš¡ Downloading ${safeName}...`, 'success');
    } catch (error) {
      console.error('Single image download failed:', error);
      showStatus('âŒ Download failed', 'error');
    }
  }
