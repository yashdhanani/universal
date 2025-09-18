# Universal Media Downloader

A web application for downloading videos, photos, reels, and stories from various social media platforms.

## Project Structure

This is a mono-repository containing two main components:

### Frontend (`frontend/`)
- **Deployment**: Hostinger
- **Technology**: Static HTML/CSS/JS with Tailwind CSS
- **Purpose**: Client-side interface for media downloads
- **Build**: Static files ready for hosting

### Backend (`backend/`)
- **Deployment**: Render
- **Technology**: FastAPI (Python)
- **Purpose**: Server-side API for processing downloads
- **Features**: Platform-specific downloaders, progress tracking, authentication

## Development

### Prerequisites
- Python 3.8+
- Node.js (for frontend dependencies, if any)
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd downloader
   ```

2. Setup backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Setup frontend (if needed):
   ```bash
   cd frontend
   npm install
   ```

### Running Locally

1. Start backend:
   ```bash
   cd backend
   python main_api.py
   ```

2. Open frontend:
   - Open `frontend/index.html` in your browser
   - Or serve static files from `frontend/` directory

## Deployment

### Frontend (Hostinger)
- Upload contents of `frontend/` folder to Hostinger
- Ensure all static assets are uploaded
- Configure domain routing

### Backend (Render)
- Deploy contents of `backend/` folder to Render
- Use `uvicorn main_api:app --host 0.0.0.0 --port $PORT` as start command
- Configure environment variables

## Contributing

1. Make changes in respective folders
2. Test both frontend and backend
3. Commit and push

## License

[Add your license here]