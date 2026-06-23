#!/usr/bin/env python3
"""CLI entry point for the synthetic telematics generator.

Usage examples:
  python -m backend.cli generate --bbox "30.0,-98.0,30.5,-97.5" --trips 10

The CLI reuses the generation helpers under ``backend.generation``.
"""

import argparse
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Tuple, Optional

from backend.generation.area import parse_bbox, random_point
from backend.generation.gps import interpolate_line, haversine
from backend.generation.router import route, snap_to_nearest, route_with_timestamps
from backend.generation.serializer import build_trip_json

def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic GPS‑trace generator (backend CLI)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Generate synthetic trips")
    gen.add_argument("--bbox", type=parse_bbox, required=True,
                     help="Bounding box: min_lat,min_lon,max_lat,max_lon")
    gen.add_argument("--trips", type=int, default=1, help="Number of trips to generate")
    gen.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    gen.add_argument("--output", type=str, default="data/trips", help="Directory for JSON files")
    gen.add_argument("--use-osrm", action="store_true", help="Use OSRM routing instead of straight‑line interpolation")
    gen.add_argument("--min-distance", type=int, default=20, help="Minimum trip distance in meters (default: 20)")
    gen.add_argument("--max-distance", type=int, default=50000, help="Maximum trip distance in meters (default: 50000)")

    args = parser.parse_args()

    if args.seed is not None:
        import random
        random.seed(args.seed)

    os.makedirs(args.output, exist_ok=True)

    for i in range(args.trips):
        attempts = 0
        max_attempts = 10
        while attempts < max_attempts:
            origin_raw = random_point(args.bbox)
            destination_raw = random_point(args.bbox)
            # Snap to nearest road
            origin = asyncio.run(snap_to_nearest(origin_raw[0], origin_raw[1]))
            destination = asyncio.run(snap_to_nearest(destination_raw[0], destination_raw[1]))
            if origin is None or destination is None:
                attempts += 1
                continue
            # Compute distance
            dist = haversine(origin, destination)
            if dist < args.min_distance or dist > args.max_distance:
                attempts += 1
                continue
            break
        else:
            # Failed to find suitable points after max_attempts; use raw unsnapped points
            origin = origin_raw
            destination = destination_raw

        if args.use_osrm:
            # Use OSRM with timestamps derived from route durations
            routed = asyncio.run(route_with_timestamps(origin, destination))
            points = routed  # each is (lat, lon, timestamp)
        else:
            points = interpolate_line(origin, destination)

        trip_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        trip_json = build_trip_json(trip_id, origin, destination, start_time, points)
        out_path = os.path.join(args.output, f"{trip_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            import json
            json.dump(trip_json, f, indent=2)
        print(f"Generated {i+1}/{args.trips}: {out_path}")

if __name__ == "__main__":
    main()