"""Pydantic models that describe the JSON schema for a generated trip.

The schema matches the example in the PRD and is used by FastAPI for response
data validation.
"""

from pydantic import BaseModel
from typing import List

class Position(BaseModel):
    lat: float
    lon: float

class Metadata(BaseModel):
    origin: Position
    destination: Position
    start_time: str
    duration_seconds: int
    profile: str = "stub"

class TracePoint(BaseModel):
    timestamp: int
    lat: float
    lon: float
    heading: float
    speed: float

class SyntheticTrip(BaseModel):
    trip_id: str
    metadata: Metadata
    trace: List[TracePoint]
