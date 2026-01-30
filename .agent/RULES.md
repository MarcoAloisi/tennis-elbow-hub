# Project Rules & Guidelines

These guidelines are critical for maintaining the quality and architecture of the Tennis Elbow 4 Hub project. All agents and developers must adhere to these rules.

## 1. Deployment & Environment
- **Platform**: [Render](https://render.com)
- **Frontend Framework**: Vue 5.4.1 (Note: This refers to the Vite/Vue ecosystem versioning; `package.json` specifies Vue 3.x with Vite 5.x).
- **Backend Runtime**: Python 3.11+
- **Version Control**: Git

## 2. Python Coding Standards
- **Standard**: Strictly follow [PEP 8](https://peps.python.org/pep-0008/) style guide.
- **Tooling**: Use `ruff` (configured in `pyproject.toml`) for linting and formatting.
- **Best Practices**:
  - Write clear, self-documenting code.
  - Use type hints (`mypy` strict mode is enabled).
  - Docstrings are encouraged for complex logic.

## 3. Architecture & Design Principles
- **Separation of Concerns**: Maintain a strict separation between the Frontend (`frontend/`) and Backend (`backend/`).
  - **Backend**: Handles API endpoints, data parsing (logs), business logic, and storage.
  - **Frontend**: Handles UI, user interaction, and state management (Pinia).
- **No Duplication**:
  - **DRY (Don't Repeat Yourself)**: extracting common logic into services or utility functions.
  - **No Bloated Code**: Keep functions and components focused and concise. Remove unused code immediately.
- **Modularity**: Code should be modular. Avoid giant files; break them down into logical components or services.

## 4. Project Context: Tennis Elbow 4 Hub
- **Goal**: A website/webapp hub for the "Tennis Elbow 4" game.
- **Core Tabs/Features**:
  1.  **Live Scores**: Real-time display of game scores.
  2.  **Match Analysis**: A tool to upload/read match logs and provide detailed statistics and analysis for users.

## 5. API Architecture

### Live Scores API
Fetches real-time match data from Tennis Elbow 4 server list.

```
[External TE4 Server] → [Backend Scraper] → [WebSocket/REST] → [Frontend]
```

**Flow:**
1. `scraper.py` fetches raw data from `LIVE_SCORES_URL` every 5 seconds
2. `parser.py` parses the custom format into `GameServer` models
3. Each `GameServer` gets a unique `match_id` (hash of timestamp + names + port)
4. `stats_service.py` tracks matches: when a match disappears (5+ games) → counted as finished
5. Data served via:
   - `GET /api/scores` — Current live matches
   - `WS /api/scores/ws` — WebSocket for real-time updates
   - `GET /api/scores/stats/today` — Today's finished match counts
   - `GET /api/scores/stats/history` — Historical daily stats

**Key Files:**
- `backend/app/services/scraper.py` — HTTP fetching
- `backend/app/services/parser.py` — Data parsing
- `backend/app/services/stats_service.py` — Finished match tracking
- `backend/app/models/game_server.py` — Data models

### Match Log Analysis API
Parses HTML match log files uploaded by users.

```
[User Uploads HTML] → [Backend Parser] → [Analysis Response] → [Frontend Charts]
```

**Flow:**
1. User uploads `.html` match log file
2. `POST /api/matchlog/parse` receives and validates file
3. `log_parser.py` extracts match data (players, scores, stats)
4. Returns structured JSON with match statistics
5. Frontend displays charts and analysis

**Key Files:**
- `backend/app/api/endpoints/matchlog.py` — Upload endpoint
- `backend/app/services/log_parser.py` — HTML parsing logic
- `backend/app/models/match_log.py` — Parsed data models

## 6. Agent Workflow
- **Verify First**: Before writing new code, verify existing implementation to ensure no duplication.
- **Read Configs**: Respect `pyproject.toml` and `package.json` configurations.
- **Testing**: Ensure changes are clearer and robust. Run tests if applicable (`pytest` for backend, `vitest` for frontend).
