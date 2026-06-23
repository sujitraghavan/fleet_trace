"""Geographic helper utilities for the synthetic telematics generator.

The current MVP works with an explicit bounding‑box supplied by the user.
Future versions may integrate a geocoder (e.g., Nominatim) to resolve city/state
names to a polygon.
"""

import argparse
from typing import Tuple

def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse a string of the form ``min_lat,min_lon,max_lat,max_lon``.
    Raises ``argparse.ArgumentTypeError`` on malformed input.
    """
    try:
        parts = [float(p) for p in bbox_str.split(',')]
        if len(parts) != 4:
            raise ValueError
        min_lat, min_lon, max_lat, max_lon = parts
        return min_lat, min_lon, max_lat, max_lon
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Invalid bbox '{bbox_str}'. Expected format: min_lat,min_lon,max_lat,max_lon"
        )

def random_point(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Return a uniformly random latitude/longitude inside ``bbox``.
    ``bbox`` is ``(min_lat, min_lon, max_lat, max_lon)``.
    """
    import random
    min_lat, min_lon, max_lat, max_lon = bbox
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_lon, max_lon)
    return lat, lon
