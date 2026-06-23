# Fleet Trace

Synthetic Telematics data generation platform using FastAPI and OSRM.

## Overview

Generates synthetic GPS traces by routing origin‑destination pairs through a local OSRM service, providing a CLI for batch generation and a REST API for testing routes and retrieving trips.

## Features

* Realistic road‑following traces via OSRM.
* Mitigations: snapping to nearest road, distance filtering, timestamp derivation from route durations.
* FastAPI endpoints:
  * `POST /test-route` – test OSRM routing.
  * `GET /jobs/{job_id}/trips` – list generated trips.
  * Static serving of trip JSONs under `/trips/<trip_id>.json`.
* CLI (`backend/cli.py`) with `--use-osrm`, `--min-distance`, `--max-distance` flags.

## Quick Start

```bash
# Clone repo
git clone https://github.com/sujitraghavan/fleet_trace.git
cd fleet_trace

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Unix

# Install dependencies
pip install -r requirements.txt

# Start OSRM and services (Docker)
docker compose up -d

# Start API
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# Generate trips (example)
python -m backend.cli generate --bbox "-25.30,-57.70,-25.20,-57.60" --trips 5 --use-osrm

# List trips
curl http://localhost:8000/jobs/dummy/trips
```
