(function(window){
  'use strict';

  // Convert various time formats to seconds (e.g., "90", "1:30", "1h2m3s")
  function parseTimeToSeconds(t) {
    if (!t) return null;
    if (/^\d+$/.test(t)) return parseInt(t, 10);
    // support mm:ss or hh:mm:ss
    if (/^\d{1,2}:\d{1,2}(:\d{1,2})?$/.test(t)) {
      const parts = t.split(':').map(n => parseInt(n, 10));
      if (parts.length === 2) return parts[0] * 60 + parts[1];
      if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    const m = (t + '').match(/(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?/);
    if (!m) return null;
    const h = parseInt(m[1] || 0, 10);
    const mn = parseInt(m[2] || 0, 10);
    const s = parseInt(m[3] || 0, 10);
    return h * 3600 + mn * 60 + s;
  }

  // Robust YouTube URL parser → { type, videoId, playlistId, startSeconds, raw }
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

  // Canonicalize platform URLs to a standard form used by the backend
  function canonicalizePlatformUrl(platform, inputUrl) {
    if (!inputUrl) return inputUrl;
    const p = (platform || '').toLowerCase();
    switch (p) {
      case 'youtube': {
        const parsed = parseYouTubeUrl(inputUrl);
        if (['video','shorts','short','embed'].includes(parsed.type) && parsed.videoId) {
          const t = parsed.startSeconds ? `&t=${parsed.startSeconds}s` : '';
          return `https://www.youtube.com/watch?v=${parsed.videoId}${t}`;
        }
        return inputUrl;
      }
      // Add more platforms here when canonicalization rules are defined
      default:
        return inputUrl;
    }
  }

  window.PlatformUtils = {
    parseTimeToSeconds,
    parseYouTubeUrl,
    canonicalizePlatformUrl
  };
})(window);