# Implementation Guide

This document provides a concrete, step‑by‑step plan for turning the synthetic telematics data generation platform from the current MVP stub into a fully‑featured system.

---

## 1. Repository Restructuring

1. **Rename `synthetic_gen/` to `backend/`**
   - Move the existing CLI (`synthetic_gen.py`) into `backend/cli.py`.
   - Create a proper package layout:
   ```
   backend/
   ├─ __init__.py
   ├─ app.py          # FastAPI entry point
   ├─ cli.py          # Click‑based CLI wrapper around the generation engine
   ├─ generation/
   │   ├─ __init__.py
   │   ├─ area.py
   │   ├─ router.py    # OSRM/Valhalla wrapper (stub for now)
   │   ├─ profile.py
   │   ├─ gps.py
   │   └─ serializer.py
   ├─ tasks.py        # Celery worker definitions
   ├─ models.py       # Pydantic schemas (including SyntheticTrip)
   └─ db.py           # SQLite helper for job metadata
   ```
2. **Create a `frontend/` directory** with a fresh Vite + React project (see section 2).
3. **Add a `docker-compose.yml`** that orchestrates `api`, `redis`, and `osrm` services (section 3).

---

## 2. Backend – Core Features

### 2.1 FastAPI Endpoints
| Method | Path | Purpose | Implementation |
|-------|------|---------|----------------|
| `POST /jobs` | Accepts JSON `{area, trip_count, seed?}` and enqueues a Celery job. | `app.py` → validate request with `models.JobRequest`, store a row in `jobs` table, call `tasks.generate_trip_batch.delay(...)`. |
| `GET /jobs/{job_id}` | Returns job status (`queued`, `running`, `complete`, `failed`). | Query SQLite `jobs` table. |
| `GET /jobs/{job_id}/trips` | Lists generated trip IDs and metadata (no large payload). | Scan `data/trips/<date>/` or query an indexed SQLite view. |
| `GET /trips/{trip_id}` | Streams the full JSON file. | Use `FileResponse` with proper `application/json`. |
| `GET /metrics` | Prometheus metrics endpoint. | `prometheus_client` integration. |

### 2.2 Generation Engine
1. **Area handling (`area.py`)** – Resolve user‑provided strings via Nominatim (optional) or expect a bounding box. Return a `shapely.geometry.Polygon` for random point sampling.
2. **Routing (`router.py`)** – Wrap OSRM HTTP API:
   ```python
   def route(orig: Tuple[float,float], dest: Tuple[float,float]) -> List[Tuple[float,float]]:
       resp = httpx.get(f"http://osrm:5000/route/v1/driving/{orig[1]},{orig[0]};{dest[1]},{dest[0]}", params={"overview":"full","geometries":"geojson"})
       resp.raise_for_status()
       return [(pt[1], pt[0]) for pt in resp.json()["routes"][0]["geometry"]["coordinates"]]
   ```
   - Add exponential back‑off for transient network errors.
3. **Speed profile (`profile.py`)** – Map OSM `highway` tags to base speeds (e.g., `motorway` → 30 m/s). Add stochastic multiplicative factor (`lognormal(μ=1, σ=0.1)`).
4. **GPS trace (`gps.py`)** – Interpolate the routed geometry to 1 Hz, apply:
   - Gaussian GPS noise (σ = 3 m).
   - Turn‑penalty jitter (±0.2 s) at intersections.
   - Acceleration smoothing using a simple moving average window (3 s).
5. **Serialization (`serializer.py`)** – Validate against the JSON schema (`schema.json`) using `jsonschema.validate`. Write files to `data/trips/<YYYY-MM-DD>/<trip_id>.json`.

### 2.3 Celery Worker (`tasks.py`)
```python
@celery.task(bind=True)
def generate_trip_batch(self, job_id: str, area: dict, count: int, seed: Optional[int] = None):
    # Initialise RNG, create output folder, loop `count` times calling the generation engine
    # Update SQLite job row with progress percentage
    # On success: set status='complete', on exception: status='failed'
```
- Use the `prefetch_multiplier=1` to avoid flooding the broker.
- Store intermediate progress in the `jobs` table (e.g., `processed`, `total`).

---

## 3. Docker Compose Setup
```yaml
version: "3.8"
services:
  api:
    build: ./backend
    command: uvicorn backend.app:app --host 0.0.0.0 --port 8000
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
      - osrm
    ports:
      - "8000:8000"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  osrm:
    image: osrm/osrm-backend:latest
    command: osrm-routed --algorithm mld data/graph-cache/usa.osrm
    volumes:
      - ./data/graph-cache:/data/graph-cache
    ports:
      - "5000:5000"

  worker:
    build: ./backend
    command: celery -A backend.tasks worker --loglevel=info
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
      - osrm
```
- The `backend` Dockerfile should copy the `requirements.txt`, install dependencies, and set `WORKDIR /app`.
- Add a healthcheck for the `osrm` service that curls `http://osrm:5000/health`.

---

## 4. Frontend – React Implementation
1. **Project bootstrap** – `npm create vite@latest frontend -- --template react-ts`.
2. **Install dependencies**:
   ```bash
   cd frontend
   npm i maplibre-gl @maplibre/maplibre-gl-react zustand axios
   ```
3. **Core components**:
   - `TripList.tsx` – fetches `/jobs/:id/trips`, paginates, and displays a selectable list.
   - `TripPlayer.tsx` – receives a trip JSON, creates a MapLibre `LineLayer`, and animates a marker using `requestAnimationFrame`. Implements play/pause, speed multiplier, and a timeline slider.
   - `HeatMap.tsx` – aggregates coordinates from multiple trips into a `HeatmapLayer`.
4. **State management** – a small `useStore` (Zustand) holds `selectedTripId`, `playbackState`, and UI preferences.
5. **API client** – a thin wrapper around `axios` that injects the base URL (`http://localhost:8000`).
6. **Testing** – write Jest + React Testing Library tests for component rendering and API error handling.

---

## 5. Logging, Metrics, and Observability
- **Backend** – configure `structlog` to output JSON lines to `stdout`.  Include fields: `event`, `job_id`, `trip_id`, `level`, `timestamp`.
- **Prometheus** – expose counters:
  - `trips_generated_total`
  - `jobs_running`
  - `generation_latency_seconds`
- **Grafana dashboard** (optional) can plot these metrics to monitor throughput.

---

## 6. CI / CD Pipeline (GitHub Actions)
```yaml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install backend deps
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install -r backend/requirements.txt
      - name: Lint backend
        run: ruff check backend/
      - name: Test backend
        run: pytest backend/tests/
      - name: Build Docker images
        run: docker compose build
      - name: Frontend lint & tests
        run: |
          cd frontend
          npm ci
          npm run lint
          npm test -- --watch=false
```
- Add a `release` workflow that tags `vX.Y.Z`, pushes Docker images to GitHub Container Registry, and creates a GitHub Release.

---

## 7. Documentation & Knowledge Transfer
- Keep the **README.md** minimal: quick‑start commands, architecture diagram (Mermaid), and contribution guidelines.
- Update **CLAUDE.md** whenever new services or scripts are added (the file already contains a “Full Project Implementation Guidance” section).
- Store the architecture diagram in `docs/architecture.mmd` and reference it from the README.

---

## 8. Periodic Commit Checklist (for developers)
1. **Run lint & tests locally** before committing.
2. **Stage only relevant files** (`git add backend/`, `frontend/`, `docker-compose.yml`).
3. **Write a Conventional Commit** message, e.g.:
   ```
   feat(generation): add speed‑profile mapping for highway types
   ```
4. **Append Co‑Authored‑By** line if AI assistance was used.
5. **Push** and open a PR; CI will automatically verify.
6. **Squash‑merge** after approval to keep history clean.

---

# End of implementation.md
