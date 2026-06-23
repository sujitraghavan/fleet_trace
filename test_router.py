# test_router.py
"""
Quick sanity‑check for the OSRM router implementation.

It calls the async ``backend.generation.router.route`` function with two
coordinates that lie inside the Paraguay OSM extract and prints the
resulting list of (lat, lon) points.

Run it after you have installed the backend requirements and the OSRM
container is up (e.g. ``docker compose up``).

    python test_router.py
"""

import asyncio
from backend.generation.router import route


# ----------------------------------------------------------------------
# Example coordinates – a short segment inside Asunción, Paraguay.
# OSRM expects (lat, lon) tuples, but the router converts them to the
# lon,lat format required by the HTTP API.
# ----------------------------------------------------------------------
ORIGIN = (-25.2960, -57.6412)       # (lat, lon) – city centre
DESTINATION = (-25.2960, -57.6350)  # (lat, lon) – ~500 m east


async def main() -> None:
    try:
        path = await route(ORIGIN, DESTINATION)
        print(f"\n✅ Route computed: {len(path)} points returned")
        print("First few points (lat, lon):")
        for pt in path[:5]:
            print(f"  {pt}")
        print("\nLast few points:")
        for pt in path[-5:]:
            print(f"  {pt}")
    except Exception as exc:
        # Any HTTP error, connection issue, or OSRM error will land here.
        print(f"\n❌ Failed to compute route: {exc}")


if __name__ == "__main__":
    asyncio.run(main())