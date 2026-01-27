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

## 5. Agent Workflow
- **Verify First**: Before writing new code, verify existing implementation to ensure no duplication.
- **Read Configs**: Respect `pyproject.toml` and `package.json` configurations.
- **Testing**: Ensure changes are clearer and robust. Run tests if applicable (`pytest` for backend, `vitest` for frontend).
