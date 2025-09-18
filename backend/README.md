# Backend - Universal Media Downloader API

FastAPI-based backend service for downloading media from social platforms.

## Features

- Multi-platform support (YouTube, Instagram, TikTok, etc.)
- Asynchronous download processing
- Progress tracking
- Authentication and rate limiting
- Celery for background tasks

## API Endpoints

- `POST /download` - Start download task
- `GET /progress/{task_id}` - Get download progress
- `GET /result/{task_id}` - Get download result

## Environment Variables

Create a `.env` file based on `.env.example`:

```
SECRET_KEY=your-secret-key
API_KEYS=key1,key2
COOKIES_FILE=path/to/cookies.txt
FFMPEG_LOCATION=path/to/ffmpeg
```

## Running

```bash
python main_api.py
```

Or with uvicorn:
```bash
uvicorn main_api:app --reload
```

## Deployment

Deploy this folder to Render with the following start command:
```bash
uvicorn main_api:app --host 0.0.0.0 --port $PORT
```