# Fleet Trace – Project Guide

## 1. Project Overview
Fleet Trace is a synthetic telematics data generation platform that creates realistic GPS traces by routing via OSRM with GPS headings, and speed. It offers both a CLI for batch creation and a REST API for testing routes and listing generated trips.

## 2. Architecture & Workflow
1. **Input** – Bounding box and number of trips (CLI or API).
2. **Origin/Destination** – Destination** – Uniform Inside the points are **Snap to\|nearest drivable road via OSRM  `% nearest` service, via service, G comes from OSRM `/route/v1/driving` and the legs for each leg segment distance and duration.
 All via OSRM
5. Derive timestamps per leg from OSRM durations.
6. Apply Gaussian GPS noise, compute heading/instantaneous speed.
7. Write JSON file to `data/trips/<UUID>.json`.
8. API Endpoints:  
   - POST `/test-route` – quick OSRM sanity check.  
   - GET `/jobs/{job_id}/trips` – list metadata of all trips.  
   - Static mount `/trips/<trip_id>.json` – serve individual trip files.
   
9. Optional: Rabbit off‑loaded batch work via Celery + Redis broker.

## 3. How to Run Locally
```bash
# 1. Clone repo & cd
git clone https://github.com/sujitraghavan/fleet_trace.git
cd fleet_trace

# 2. Create & activate virtualenv
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Unix

# 3. Install deps
pip install -r requirements.txt

# 4. Start services (Docker)
docker compose up -d   # starts osrm, redis, api, worker

# 5. Start FastAPI server
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# 6. Generate trips (example)
python -m backend.cli generate --bbox "-25.30,-57.70,-25.20,-57.60" --trips 5 --use-osrm

# 7. List trips via API
curl http://localhost:8000/jobs/dummy/trips
```

## 4. Generating Trips – CLI Options
| Flag | Description | Example |
|------|-------------|---------|
| `--bbox` | Bounding box: `min_lat,min_lon,max_lat,max_lon` | `-25.30,-57.70,-25.20,-57.60` |
| `--trips` | Number of trips to generate | `5` |
| `--use-osrm` | Use real OSRM routing (default: stub) | |
| `--min-distance` | Minimum trip distance in meters (default: 20) | `500` |
| `--max-distance` | Maximum trip distance in meters (default: 50000) | `5000` |
| `--output` | Directory for JSON files (default: `data/trips`) | `data/trips` |
| `--seed` | Random seed for reproducibility | `42` |

Example:
```bash
python -m backend.cli generate \
    --bbox "-25.30,-57.70,-25.20,-57.60" \
    --trips 10 \
    --use-osrm \
    --min-distance 500 \
    --max-distance 5000
```

## 5. API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/test-route` | Accepts `{origin:{lat,lon},destination:{lat,lon}}` and returns the OSRM route as a list of `[lat,lon]` pairs. |
| GET | `/jobs/{job_id}/trips` | Ignores `job_id` in MVP; returns JSON array with objects containing `trip_id`, `start_time`, `duration_seconds`. |
| GET | `/trips/<trip_id>.json` | Serves the full trip JSON file (static mount). |

OpenAPI docs: `http://localhost:8000/docs`

## 6. Extending the Project
- **Persistence** – Add a SQLite/Postgres job store in `backend/db.py` and expose `/jobs/{id}` endpoints.
- **Alternative Router** – Swap OSRM for Valhalla by replacing calls in `router.py`.
- **Speed Profile** – Replace constant‑speed timestamp derivation with a speed‑by‑highway‑type lookup.
- **Front‑end** – Build a React/MapLibre‑GL UI that consumes `/jobs/{id}/trips` and `/trips/<id>.json`.

## 7. Repository Hygiene
- `.gitignore` excludes `venv/`, `__pycache__/`, `data/`, IDE folders, and build outputs.
- CI workflow runs `ruff` and `pytest` on each push.
- Documentation lives in `README.md` and this `GUIDE.md`.

---  
*Prepared for internal reference and onboarding.*  
