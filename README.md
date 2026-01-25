# 🎾 Tennis Elbow Hub

A modern web application for tracking live Tennis Elbow 4 scores and analyzing match logs.

## Features

- **Live Scores** - Real-time score updates via WebSocket
- **Match Analysis** - Upload HTML match logs and view detailed statistics
- **Dark/Light Theme** - Toggle between themes with persistence
- **Responsive Design** - Works on desktop and mobile

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Vue 3 / Vite |
| State | Pinia |
| Charts | Chart.js |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example ../.env

# Run development server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
TE4-PROJECT/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API endpoints
│   │   ├── core/      # Config, security
│   │   ├── models/    # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── utils/     # Helpers
│   └── tests/         # pytest tests
│
└── frontend/          # Vue 3 frontend
    └── src/
        ├── components/
        ├── views/
        ├── stores/
        └── composables/
```

## Configuration

See `.env.example` for available configuration options.

## License

MIT
