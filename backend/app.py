# backend/app.py
"""FastAPI entry point for the synthetic telematics platform.

Provides job creation, status polling, and a test endpoint that exercises the
OSRM router implementation (backend.generation.router.route).
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
from fastapi.staticfiles import StaticFiles

# ------------------------------------------------------------------
# Existing imports for DB, jobs, etc. (keep them if present)
# ------------------------------------------------------------------
# from .db import get_conn   # placeholder – keep any DB imports you need
# from .models import JobRequest, JobStatus  # placeholder – keep if you have them

app = FastAPI(title="Synthetic Telematics API")
# Serve generated trip JSON files under /trips/<trip_id>.json
app.mount("/trips", StaticFiles(directory="data/trips"), name="trips")

# ------------------------------------------------------------------
# ==== TEST ROUTER ENDPOINT =========================================
# ------------------------------------------------------------------

class LatLon(BaseModel):
    """Simple latitude/longitude point used by the test endpoint."""
    lat: float
    lon: float

class RouteRequest(BaseModel):
    """Payload schema for the /test-route endpoint.

    The client sends an ``origin`` and ``destination`` point, each expressed as
    ``{"lat": <float>, "lon": <float>}``.  FastAPI validates the JSON and
    passes the values directly to the OSRM router helper.
    """
    origin: LatLon
    destination: LatLon

# Import the async OSRM router we built earlier
from backend.generation.router import route

@app.post("/test-route")
async def test_route(req: RouteRequest):
    """Call the OSRM service via the async ``route`` helper.

    Returns a JSON payload with a ``route`` key containing an ordered list of
    ``[lat, lon]`` coordinate pairs that trace the computed road‑following
    path.
    """
    try:
        # ``route`` expects (lat, lon) tuples
        path: List[Tuple[float, float]] = await route(
            (req.origin.lat, req.origin.lon),
            (req.destination.lat, req.destination.lon),
        )
        return {"route": path}
    except Exception as exc:
        # Any failure (e.g., no route found) is reported as a 400 Bad Request.
        raise HTTPException(status_code=400, detail=str(exc))

# ------------------------------------------------------------------
# ==== LIST TRIPS ENDPOINT =========================================
# ------------------------------------------------------------------
from pathlib import Path
import json
from fastapi.responses import JSONResponse

TRIPS_DIR = Path(__file__).parent.parent / "data" / "trips"

@app.get("/jobs/{job_id}/trips")
def list_trips(job_id: str):
    """Return metadata for all generated trip JSON files.

    In this MVP we ignore the job_id (all trips are stored in the same folder).
    """
    print(f"TRIPS_DIR: {TRIPS_DIR}, exists: {TRIPS_DIR.exists()}")
    if not TRIPS_DIR.exists():
        raise HTTPException(status_code=404, detail="No trips generated yet")
    trips = []
    for file in TRIPS_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            trips.append({
                "trip_id": payload["trip_id"],
                "start_time": payload["metadata"]["start_time"],
                "duration_seconds": payload["metadata"]["duration_seconds"]
            })
        except Exception:
            # Skip malformed files
            continue
    print(f"Found {len(trips)} trips")
    return JSONResponse(content=trips)

# ------------------------------------------------------------------
# (Leave any other existing endpoints – e.g., /jobs – unchanged below)
# ------------------------------------------------------------------
# @app.post("/jobs")
# async def create_job(...):
#     ...
