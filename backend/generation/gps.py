"""Geometric and GPS utilities used by the generation engine.

The MVP interpolates a straight line and then adds realistic GPS noise.
Future versions will operate on OSRM/Valhalla routes and incorporate traffic.
"""

import math
from typing import List, Tuple

def haversine(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Return the great‑circle distance between two lat/lon points in metres.
    Uses the haversine formula.
    """
    R = 6371000  # Earth radius in metres
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def interpolate_line(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float, int]]:
    """Generate 1 Hz points between ``start`` and ``end``.
    Returns a list of ``(lat, lon, timestamp)`` where timestamp starts at 0.
    """
    distance = haversine(start, end)
    speed_mps = 15.0  # constant 34 mph for the stub
    total_seconds = int(math.ceil(distance / speed_mps)) if distance else 0
    pts: List[Tuple[float, float, int]] = []
    for t in range(total_seconds + 1):
        f = t / total_seconds if total_seconds else 0.0
        lat = start[0] + (end[0] - start[0]) * f
        lon = start[1] + (end[1] - start[1]) * f
        pts.append((lat, lon, t))
    return pts

def add_gps_noise(lat: float, lon: float, sigma_m: float = 3.0) -> Tuple[float, float]:
    """Add Gaussian noise (meters) to a lat/lon coordinate.
    ``sigma_m`` defaults to 3 m, typical consumer GPS error.
    """
    import random
    # Approximate conversion from metres to degrees
    lat_deg_per_m = 1.0 / 111_000.0
    lon_deg_per_m = 1.0 / (111_000.0 * math.cos(math.radians(lat)))
    dlat = random.gauss(0, sigma_m) * lat_deg_per_m
    dlon = random.gauss(0, sigma_m) * lon_deg_per_m
    return lat + dlat, lon + dlon

def bearing(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Return compass bearing from ``p1`` to ``p2`` in degrees (0‑360).
    """
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360
