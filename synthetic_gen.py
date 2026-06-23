#!/usr/bin/env python3
"""synthetic_gen.py – Minimal CLI for generating synthetic GPS trips.

Usage examples:
  python synthetic_gen.py generate --area "Austin, TX" --trips 5
  python synthetic_gen.py generate --bbox "30.0,-98.0,30.5,-97.5" --trips 1

The implementation is deliberately lightweight for the MVP:
* It does **not** call an external routing engine – it creates a straight‑line
  interpolation between a random origin and destination inside the supplied
  bounding box.
* A 1 Hz trace is generated, with simple Gaussian GPS noise (σ≈3 m).
* The output conforms to the *SyntheticTrip* JSON schema described in the
  accompanying PRD; see `schema.json` for the full definition.

Future work should replace ``_straight_line_route`` with a real OSRM/Valhalla
call, add realistic speed profiles, stops, and traffic‑light modelling.
"""

import argparse
import json
import math
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse a ``min_lat,min_lon,max_lat,max_lon`` string into a tuple.
    Raises ``argparse.ArgumentTypeError`` on failure.
    """
    try:
        parts = [float(p) for p in bbox_str.split(',')]
        if len(parts) != 4:
            raise ValueError
        min_lat, min_lon, max_lat, max_lon = parts
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90 and
                -180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError
        return min_lat, min_lon, max_lat, max_lon
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Invalid bbox '{bbox_str}'. Expected format: min_lat,min_lon,max_lat,max_lon"
        )


def random_point(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Return a random (lat, lon) inside the given bounding box.
    The function is deterministic when ``random.seed`` has been set.
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_lon, max_lon)
    return lat, lon


def haversine(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Return distance between two lat/lon points in meters (Haversine).
    Used for speed calculation in the simple stub implementation.
    """
    R = 6371000  # Earth radius in meters
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def interpolate_line(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float, int]]:
    """Generate a 1 Hz list of (lat, lon, timestamp_offset) points.
    Returns a list where the timestamp offset starts at 0.
    """
    distance = haversine(start, end)
    # Choose a modest constant speed (m/s) for the straight line; 15 m/s ≈ 34 mph.
    speed_mps = 15.0
    total_seconds = int(math.ceil(distance / speed_mps)) if distance > 0 else 0
    points: List[Tuple[float, float, int]] = []
    for t in range(total_seconds + 1):
        fraction = t / total_seconds if total_seconds else 0.0
        lat = start[0] + (end[0] - start[0]) * fraction
        lon = start[1] + (end[1] - start[1]) * fraction
        points.append((lat, lon, t))
    return points


def add_gps_noise(lat: float, lon: float, sigma_m: float = 3.0) -> Tuple[float, float]:
    """Add Gaussian noise (meters) to a lat/lon point.
    ``sigma_m`` defaults to 3 m, a typical consumer‑grade GPS error.
    """
    # Approx conversion: 1° latitude ≈ 111 km.
    lat_deg_per_m = 1.0 / 111_000.0
    lon_deg_per_m = 1.0 / (111_000.0 * math.cos(math.radians(lat)))
    dlat = random.gauss(0, sigma_m) * lat_deg_per_m
    dlon = random.gauss(0, sigma_m) * lon_deg_per_m
    return lat + dlat, lon + dlon


def bearing(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate compass bearing from p1 to p2 in degrees (0‑360)."""
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )
    bearing_rad = math.atan2(x, y)
    return (math.degrees(bearing_rad) + 360) % 360


def build_trip_json(trip_id: str,
                    origin: Tuple[float, float],
                    destination: Tuple[float, float],
                    start_time: datetime,
                    points: List[Tuple[float, float, int]]) -> dict:
    """Assemble the final JSON structure for a single trip.
    ``points`` is a list of (lat, lon, offset_seconds).
    """
    trace = []
    for idx, (lat, lon, offset) in enumerate(points):
        noisy_lat, noisy_lon = add_gps_noise(lat, lon)
        # Heading – compute to next point when possible.
        if idx < len(points) - 1:
            heading = bearing((lat, lon), (points[idx + 1][0], points[idx + 1][1]))
        else:
            heading = 0.0
        # Speed – distance to next point (m/s) or 0 at the end.
        if idx < len(points) - 1:
            spd = haversine((lat, lon), (points[idx + 1][0], points[idx + 1][1]))
        else:
            spd = 0.0
        trace.append({
            "timestamp": offset,
            "lat": noisy_lat,
            "lon": noisy_lon,
            "heading": heading,
            "speed": spd,
        })
    duration = points[-1][2] if points else 0
    return {
        "trip_id": trip_id,
        "metadata": {
            "origin": {"lat": origin[0], "lon": origin[1]},
            "destination": {"lat": destination[0], "lon": destination[1]},
            "start_time": start_time.isoformat(),
            "duration_seconds": duration,
            "profile": "stub",
        },
        "trace": trace,
    }

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic GPS‑trace generator (MVP).")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    gen = subparsers.add_parser("generate", help="Generate one or more synthetic trips.")
    gen.add_argument("--area", type=str, help="Place name (e.g., 'Austin, TX'). Not used in stub.")
    gen.add_argument("--bbox", type=parse_bbox, required=True,
                     help="Bounding box: min_lat,min_lon,max_lat,max_lon")
    gen.add_argument("--trips", type=int, default=1, help="Number of trips to generate.")
    gen.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    gen.add_argument("--output", type=str, default="output", help="Directory for JSON files.")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    os.makedirs(args.output, exist_ok=True)

    for i in range(args.trips):
        origin = random_point(args.bbox)
        destination = random_point(args.bbox)
        points = interpolate_line(origin, destination)
        trip_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        json_obj = build_trip_json(trip_id, origin, destination, start_time, points)
        out_path = os.path.join(args.output, f"{trip_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, indent=2)
        print(f"Generated trip {i+1}/{args.trips}: {out_path}")

if __name__ == "__main__":
    main()
