---
trigger: always_on
---

# Project Rules & Guidelines

These guidelines are critical for maintaining the quality and architecture of the Tennis Elbow 4 Hub project. All agents and developers must adhere to these rules.

---

## 1. Deployment & Environment
- **Platform**: [Render](https://render.com)
- **Frontend Framework**: Vue 3.x with Vite 5.x
- **Backend Runtime**: Python 3.11+ / FastAPI
- **State Management**: Pinia
- **Charts**: Chart.js
- **Version Control**: Git

---

## 2. Python Coding Standards
- **Standard**: Strictly follow [PEP 8](https://peps.python.org/pep-0008/) style guide.
- **Tooling**: Use `ruff` (configured in `pyproject.toml`) for linting and formatting.
- **Best Practices**:
  - Write clear, self-documenting code.
  - Use type hints (`mypy` strict mode is enabled).
  - Docstrings are encouraged for complex logic.

---

## 3. Architecture & Design Principles
- **Separation of Concerns**: Maintain a strict separation between the Frontend (`frontend/`) and Backend (`backend/`).
  - **Backend**: Handles API endpoints, data parsing (logs), business logic, and storage.
  - **Frontend**: Handles UI, user interaction, and state management (Pinia).
- **No Duplication**:
  - **DRY (Don't Repeat Yourself)**: Extract common logic into services or utility functions.
  - **No Bloated Code**: Keep functions and components focused and concise. Remove unused code immediately.
- **Modularity**: Code should be modular. Avoid giant files; break them down into logical components or services.

---

## 4. Project Context: Tennis Elbow 4 Hub
- **Goal**: A website/webapp hub for the "Tennis Elbow 4" game.
- **Core Tabs/Features**:
  1. **Live Scores**: Real-time display of game scores with WebSocket updates.
  2. **Match Analysis**: Upload HTML match logs for detailed statistics, radar charts, and head-to-head analysis.
  3. **WTSL Tour Logs**: Analyze WTSL tour CSV files with player rankings, stats leaders, and match history.

---

## 5. Project Structure

```
TE4-PROJECT/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── live_scores.py      # Live scores REST & WebSocket
│   │   │   │   ├── match_analysis.py   # Match log upload/analysis
│   │   │   │   └── tour_logs.py        # WTSL tour log processing
│   │   │   ├── deps.py                 # Dependency injection
│   │   │   └── router.py               # API router aggregation
│   │   ├── core/                       # Configuration & settings
│   │   ├── models/
│   │   │   ├── game_server.py          # Live match data models
│   │   │   ├── match_stats.py          # Match statistics models
│   │   │   └── daily_stats.py          # Daily statistics models
│   │   ├── services/
│   │   │   ├── scraper.py              # HTTP fetching for live scores
│   │   │   ├── parser.py               # Live score data parsing
│   │   │   ├── analyzer.py             # Match log analysis logic
│   │   │   └── stats_service.py        # Finished match tracking & DB
│   │   └── utils/                      # Helper utilities
│   └── tests/                          # pytest tests
│
└── frontend/                   # Vue 3 Frontend
    └── src/
        ├── components/
        │   ├── analysis/               # Match Analysis components
        │   │   ├── FileUploader.vue    # HTML file upload
        │   │   ├── StatsChart.vue      # Radar chart visualization
        │   │   └── StatsTable.vue      # Statistics table display
        │   ├── scores/                 # Live Scores components
        │   │   ├── MatchCard.vue       # Individual match display
        │   │   └── FilterBar.vue       # Filter controls
        │   ├── tourlogs/               # WTSL Tour Logs components
        │   │   ├── TourLogsTable.vue   # Match history table
        │   │   ├── PlayerRankings.vue  # ELO rankings display
        │   │   └── StatsLeaders.vue    # Statistical leaders
        │   └── common/                 # Shared components
        │       ├── ThemeToggle.vue     # Dark/light theme toggle
        │       ├── LoadingSpinner.vue  # Loading indicator
        │       ├── ErrorAlert.vue      # Error display
        │       └── PlayerSelectionModal.vue  # Player identity modal
        ├── views/
        │   ├── LiveScoresView.vue      # Live Scores page
        │   ├── MatchAnalysisView.vue   # Match Analysis page
        │   └── WTSLTourLogsView.vue    # WTSL Tour Logs page
        ├── stores/                     # Pinia state management
        │   ├── scores.js               # Live scores state
        │   ├── analysis.js             # Match analysis state
        │   └── tourLogs.js             # Tour logs state
        ├── composables/                # Vue composables
        ├── config/                     # App configuration
        ├── data/
        │   └── tournaments.json        # Tournament-to-surface mapping
        └── router/                     # Vue Router configuration
```

---

## 6. API Architecture

### 6.1 Live Scores API
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
- `backend/app/services/parser.py` — Data parsing with WTSL mod detection
- `backend/app/services/stats_service.py` — Finished match tracking (SQLite)
- `backend/app/models/game_server.py` — Data models (GameServer, MatchInfo)

**Features:**
- WTSL mod detection from match names (e.g., "XKT(WTSL)")
- Match duration display ("Started 15 min ago")
- ELO difference indicator with color-coding
- Tournament-to-surface mapping with icons

**Protocol Specification:**

The server list is a string containing multiple space-separated entries. Each entry represents a game server.

**Format per Server:**
```
Ip Port "Name" GameInfo MaxPing Elo NbGame "TagLine" "Score" OtherElo GiveUpRate Reputation "SurfaceName" CreationTimeInMs
```

- **Ip**: Hex string (e.g., `4A3B2C1D`) or `0` if the match is started.
- **Port**: Hex number.
- **Name**: Quoted string.
- **GameInfo**: Hex bitfield (see below).
- **MaxPing, Elo, NbGame**: Hex numbers.
- **TagLine, Score**: Quoted strings.
- **OtherElo, GiveUpRate, Reputation**: Hex numbers.
- **SurfaceName**: Quoted string.
- **CreationTimeInMs**: Hex number.

**GameInfo Bitfield (28 bits):**
- **Trial**: 2 bits
- **PlayerCfg**: 3 bits (0=Singles, 2=Competitive Doubles, 3=Cooperative Doubles)
- **NbSet**: 2 bits
- **SkillMode**: 2 bits
- **(Empty/Court)**: 9 bits
- **GamePerSet**: 3 bits
- **(Unused)**: 1 bit
- **ControlMode**: 2 bits
- **Preview**: 3 bits
- **Tiredness**: 1 bit


---

### 6.2 Match Log Analysis API
Parses HTML match log files uploaded by users.

```
[User Uploads HTML] → [Backend Parser] → [Analysis Response] → [Frontend Charts]
```

**Flow:**
1. User uploads `.html` match log file
2. `POST /api/analysis/parse` receives and validates file
3. `analyzer.py` extracts match data (players, scores, stats)
4. Returns structured JSON with match statistics
5. Frontend displays radar charts and detailed analysis

**Key Files:**
- `backend/app/api/endpoints/match_analysis.py` — Upload endpoint
- `backend/app/services/analyzer.py` — HTML parsing & statistics logic
- `backend/app/models/match_stats.py` — Parsed data models

**Features:**
- Multi-match parsing from single log file
- Player identity management (associates unknown players with user)
- Radar chart with 6 metrics: Power, Serve Accuracy, Net Game, Consistency, Pressure Points, Stamina
- Head-to-head filtering by opponent
- Surface, tournament, and match format filters
- Aggregate statistics (average/median toggle)
- Win rate calculations (match/set/game)

---

### 6.3 WTSL Tour Logs API
Processes WTSL tour CSV files for rankings and statistics.

```
[User Uploads CSV] → [Backend Parser] → [Processed Data] → [Frontend Tables]
```

**Flow:**
1. User uploads WTSL tour log `.csv` file
2. `POST /api/tourlogs/parse` receives and validates file (handles encoding)
3. Backend processes CSV data: player rankings, match history, stat leaders
4. Returns structured JSON with processed data
5. Frontend displays rankings, leaders, and match history

**Key Files:**
- `backend/app/api/endpoints/tour_logs.py` — CSV upload & processing
- `frontend/src/views/WTSLTourLogsView.vue` — Tour logs page
- `frontend/src/stores/tourLogs.js` — State management

**Features:**
- ELO-based player rankings
- Statistical leaders (aces, winners, etc.)
- Match history table with filtering
- Score-based winner determination (not ELO delta)

---

## 7. Key Data Models

### GameServer (Live Scores)
- `match_id`: Unique hash identifier
- `server_name`, `server_port`
- `player1_name`, `player2_name`
- `score`: Current match score
- `match_info`: Tournament, surface, mod version
- `started_at`: Match start timestamp
- `elo_player1`, `elo_player2`: Player ELO ratings

### MatchStats (Analysis)
- `match_id`: Unique identifier
- `players`: Player info with stats
- `score`: Match score breakdown
- `statistics`: Comprehensive stat blocks (aces, winners, errors, etc.)
- `surface`, `tournament`, `match_format`

---

## 8. Frontend State Management (Pinia)

| Store | Purpose |
|-------|---------|
| `scores.js` | Live match data, WebSocket connection, filters |
| `analysis.js` | Match log data, selected player, filters, aggregation mode |
| `tourLogs.js` | Tour log data, rankings, stats leaders, match history |

---

## 9. Agent Workflow
- **Verify First**: Before writing new code, verify existing implementation to ensure no duplication.
- **Read Configs**: Respect `pyproject.toml` and `package.json` configurations.
- **Testing**: Ensure changes are clear and robust. Run tests if applicable (`pytest` for backend, `vitest` for frontend).
- **File Organization**: Place new components in appropriate subdirectories (`analysis/`, `scores/`, `tourlogs/`, `common/`).