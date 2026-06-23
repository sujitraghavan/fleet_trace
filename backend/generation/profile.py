"""Speed profile utilities.

Future implementation will map OSM ``highway`` tags to base speeds and add
stochastic variation.
"""

def speed_for_highway(highway_type: str) -> float:
    """Return a base speed in meters per second for a given OSM highway tag.
    This stub uses a simple lookup; real implementation will be more nuanced.
    """
    mapping = {
        "motorway": 30.0,   # 108 km/h
        "trunk": 25.0,
        "primary": 20.0,
        "secondary": 15.0,
        "tertiary": 12.0,
        "residential": 8.0,
        "service": 5.0,
    }
    return mapping.get(highway_type, 10.0)  # default fallback
