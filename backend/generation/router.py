# backend/generation/router.py
"""Routing module – real OSRM integration.

The OSRM service is started in Docker Compose with the service name ``osrm`` and
listens on port 5000.  Inside the Docker network the backend can reach it via
``http://osrm:5000``.  When running the backend locally (outside Docker) the
same endpoint can be accessed on ``http://localhost:5000``.

Both the CH (default) and MLD configurations expose the same HTTP API, so the
router implementation works for either algorithm.
"""

import os
from typing import List, Tuple, Optional
import httpx

from .gps import haversine

# Determine the base URL for OSRM depending on the execution environment.
# - Inside Docker (the default for the project) the service name ``osrm`` resolves
#   via Docker's internal DNS.
# - When the code is executed directly on the host (e.g. during local dev or
#   tests) we fall back to ``localhost``.
# If the env var OSRM_HOST is set, use it; otherwise:
#   - Inside Docker we expect the service name `osrm`
#   - When running locally (no Docker), fall back to localhost
_OSRM_HOST = os.getenv("OSRM_HOST") or ("osrm" if os.getenv("DOCKER_CONTAINER") else "localhost")
_OSRM_PORT = os.getenv("OSRM_PORT", "5000")
_BASE_URL = f"http://{_OSRM_HOST}:{_OSRM_PORT}"

async def snap_to_nearest(lat: float, lon: float) -> Optional[Tuple[float, float]]:
    """Snap a coordinate to the nearest drivable road using OSRM's /nearest service.
    Returns (lat, lon) of the snapped point, or None if the request fails or
    the point is far from any road.
    """
    url = f"{_BASE_URL}/nearest/v1/driving/{lon},{lat}?number=1"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "Ok" or not data.get("waypoints"):
                return None
            wp = data["waypoints"][0]
            snapped_lon, snapped_lat = wp["location"]  # OSRM returns [lon, lat]
            return (snapped_lat, snapped_lon)
    except Exception:
        return None

async def route(origin: Tuple[float, float], destination: Tuple[float, float]) -> List[Tuple[float, float]]:
    """Return a list of (lat, lon) points representing the shortest‑path route.

    Args:
        origin: ``(lat, lon)`` tuple for the start location.
        destination: ``(lat, lon)`` tuple for the end location.

    Returns:
        A list of ``(lat, lon)`` coordinates ordered from ``origin`` to
        ``destination``.  The points are taken directly from OSRM's GeoJSON
        geometry, which provides the most realistic road‑following trace.
    """
    print(f"OSRM host: {_OSRM_HOST}")
    print(f"OSRM port: {_OSRM_PORT}")

    # OSRM expects coordinates as ``lon,lat`` in the URL.
    url = f"{_BASE_URL}/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    print(f"OSRM URL: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"overview": "full", "geometries": "geojson"})
        response.raise_for_status()
        data = response.json()
        # OSRM returns a list of routes; we take the first one.
        geometry = data["routes"][0]["geometry"]["coordinates"]
        # Convert from [lon, lat] to (lat, lon).
        return [(lat, lon) for lon, lat in geometry]

async def route_with_timestamps(origin: Tuple[float, float], destination: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Return a list of (lat, lon, timestamp) points where timestamps are derived
    from OSRM route durations, giving a realistic speed profile.
    """
    print(f"OSRM host: {_OSRM_HOST}")
    print(f"OSRM port: {_OSRM_PORT}")

    url = f"{_BASE_URL}/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    print(f"OSRM URL: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"overview": "full", "geometries": "geojson"})
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "Ok":
            raise RuntimeError(f"OSRM error: {data}")
        route = data["routes"][0]
        geometry = route["geometry"]["coordinates"]  # list of [lon, lat]
        legs = route["legs"]
        total_duration = sum(leg["duration"] for leg in legs)  # seconds
        total_distance = sum(leg["distance"] for leg in legs)  # meters
        # If geometry is empty, return empty list
        if not geometry:
            return []
        points: List[Tuple[float, float, float]] = []
        time_acc = 0.0
        # Iterate over segments between consecutive points
        for i in range(len(geometry) - 1):
            lon1, lat1 = geometry[i]
            lon2, lat2 = geometry[i + 1]
            seg_dist = haversine((lat1, lon1), (lat2, lon2))
            # Avoid division by zero
            if total_distance > 0:
                fraction = seg_dist / total_distance
            else:
                fraction = 0.0
            seg_time = total_duration * fraction
            points.append((lat1, lon1, time_acc))
            time_acc += seg_time
        # Add final point
        lon_last, lat_last = geometry[-1]
        points.append((lat_last, lon_last, time_acc))
        # Ensure final time equals total_duration (may differ slightly due to rounding)
        return points