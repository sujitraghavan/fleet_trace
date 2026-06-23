# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Common Development Commands

| Task | Command | Notes |
|------|---------|-------|
| **Create a virtual environment (backend)** | `python -m venv .venv && source .venv/bin/activate` | Run from the project root before installing any Python dependencies. |
| **Install backend dependencies** | `pip install -r requirements.txt` | After activating the virtual environment. |
| **Run the backend API** | `uvicorn app:app --reload` | Starts the FastAPI server on `http://localhost:8000`. |
| **Run tests (backend)** | `pytest` | Looks for tests under a `tests/` directory. |
| **Lint backend** | `ruff check .` | Uses **ruff**; apply fixes with `ruff check . --fix`. |
| **Format backend** | `black .` | Enforces consistent formatting. |
| **Run the CLI tool** | `python synthetic_gen.py --help` | Shows available commands for generating trips. |
| **Run a single generation job** | `python synthetic_gen.py generate --area "Austin, TX" --trips 10` | Writes a few example JSON files under `output/`. |

*Tip*: When the repository grows, you can add npm scripts, Makefile targets, or Docker Compose definitions and update this table accordingly.

---

## 2. High‑Level Architecture Overview

The repository is intended to be split into two logical layers:

### 2.1 Backend (Python)
- **FastAPI** provides a thin HTTP layer for submitting generation jobs, polling their status, and retrieving generated JSON files.
- **Trip Generation Core** lives under `synthetic_gen/` and contains the following high‑level responsibilities:
  - **Area handling** – resolve user‑provided geography (city, state, etc.) to a bounding box.
  - **Routing** – (future) integration with a local OSRM/Valhalla instance to obtain road‑network routes.
  - **Speed & movement modelling** – apply realistic speed profiles, stops, and GPS noise.
  - **Serialization** – emit the final JSON payload that conforms to the `SyntheticTrip` schema (see `schema.json`).
- **Celery** (optional) can be used to parallelise large batch jobs; the MVP can start with a simple synchronous implementation.

### 2.2 Frontend (Future)
- A React‑based UI (e.g., using **MapLibre GL**) will consume the generated JSON files and provide playback, heat‑maps, and multi‑trip overlays.
- The UI will talk to the FastAPI backend via a REST endpoint (`/trips`) to fetch trip metadata and the full trace on demand.

---

## 3. Project Layout (Suggested)

```
project-root/
├─ CLAUDE.md                # ← this file
├─ README.md                # High‑level description and quick‑start
├─ requirements.txt          # Python dependencies (FastAPI, pydantic, etc.)
├─ synthetic_gen.py          # CLI entry point (implementation file)
├─ synthetic_gen/            # Core generation package
│   ├─ __init__.py
│   ├─ area.py               # Geometry utilities
│   ├─ router.py            # Stub for OSRM wrapper (future)
│   ├─ profile.py           # Speed‑profile logic (stub)
│   ├─ gps.py               # GPS trace sampling logic (stub)
│   └─ serializer.py        # JSON output handling
├─ tests/                   # Unit / integration tests
│   └─ test_synthetic_gen.py
└─ output/                  # Generated trip JSON files (git‑ignored)
```

Feel free to adjust the layout as the codebase evolves. The most important thing for Claude Code is to keep this high‑level map in mind when navigating the repository.

---

## 4. Updating This File

When new scripts, Docker configurations, or cursor/Copilot rules are added, extend the relevant sections above:
- Add new entries to **Common Development Commands**.
- Refine the **Architecture Overview** to reflect added services (e.g., a Redis broker).
- Mention any `.cursor/` or `.github/copilot‑instructions.md` constraints.

---

## 5. Full Project Implementation Guidance

The repository is intended to host **all** components required for a synthetic telematics data platform.  When fleshing out the MVP, follow these high‑level steps:

1. **Scaffold the backend package** – create a `backend/` directory (or rename the existing `synthetic_gen/` to `backend/`) with a proper Python package layout (`__init__.py`, `app.py` for FastAPI, `router.py` for OSRM integration, `generation/` for the core logic).  Keep the public API minimal: a `POST /jobs` endpoint that accepts a JSON payload describing `area`, `trip_count`, and optional `seed`.
2. **Add a Celery worker** – define a `tasks.py` that receives the job request, calls the generation functions, writes JSON files to a date‑partitioned folder, and updates a lightweight SQLite status table.
3. **Introduce Docker compose** – include services for `api`, `redis` (broker), and `osrm`.  The `docker-compose.yml` should mount a persistent `data/graph-cache/` volume for OSRM tiles and a `data/trips/` volume for generated output.
4. **Develop the frontend** – create a `frontend/` React app with a `TripPlayer` component (MapLibre GL) and a `TripList` view that calls `GET /jobs/:id/trips` to fetch metadata.  Use **Vite** for fast hot‑module reloading.  The UI should support pagination/lazy‑loading of large trip collections.
5. **Implement proper logging & metrics** – `structlog` for JSON logs, and expose Prometheus metrics (`/metrics`) for job throughput, average generation time, and queue depth.
6. **Write tests** – backend unit tests for each generation function, integration tests for the API (via `httpx`), and frontend Jest tests for UI components.  Aim for at least 80 % coverage before merging.
7. **Continuous Integration** – GitHub Actions workflow that runs lint, tests, and builds the Docker images on every push.  Use a matrix strategy to test on Linux and Windows runners if OS‑specific code exists.
8. **Documentation** – keep `README.md` updated with quick‑start commands, architecture diagram, and contribution guidelines.

When additional modules (e.g., analytics, data‑export) are added, extend the package hierarchy accordingly and update this CLAUDE.md file to reflect the new high‑level structure.

## 6. Periodic GitHub Commit Practices

* **Commit Frequency** – commit at logical checkpoints (e.g., after adding a new package, completing a test suite, or finalising a Docker service).  Aim for commits every 30‑60 minutes during active development to keep history granular.
* **Conventional Commits** – use the format `type(scope): description`
  - `feat(<module>)`: new feature or substantial addition
  - `fix(<module>)`: bug fix
  - `refactor(<module>)`: internal refactor without observable change
  - `docs`: documentation updates
  - `chore`: tooling, CI, or build changes
* **Co‑Authored‑By** – when a change originates from an AI‑assisted implementation, append the line:
  ```
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
  to the commit message body.
* **Atomic Commits** – keep each commit focused on a single concern (e.g., “Add Celery task for batch generation” separate from “Add Docker compose service for Redis”).
* **Branch Strategy** – work on short‑lived feature branches (`feature/<name>`) and open a pull request when the implementation and tests are complete.  Merge with a **squash** to keep a clean history, unless the commit series provides valuable context.
* **Tagging Releases** – after the MVP is stable, create a git tag `v0.1.0` and push to GitHub; the CI workflow can then publish Docker images with the same version tag.
* **Verification Before Push** – run `make lint && make test && docker compose build` locally; the CI will double‑check, but local verification reduces CI failures.

Following these practices ensures a clean, traceable history and makes it easy for future Claude Code instances to understand why a change was made.

*End of CLAUDE.md*