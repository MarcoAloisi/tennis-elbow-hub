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

### Quick Start (Windows)

We have provided a helper script to set up and run everything in one go.

```powershell
./start-dev.ps1
```

This will:
1. Create a Python virtual environment (`.venv`) if missing.
2. Install backend dependencies.
3. Launch the Backend Server in a new window.
4. Install frontend dependencies (if missing).
5. Launch the Frontend Server in the current window.

### Manual Setup (Optional)

If you prefer running things manually:

#### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
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
