"""Celery task definitions for batch trip generation.

The MVP uses the CLI logic to generate trips; the Celery worker simply
executes the same code in a subprocess so we don't duplicate the generation
logic here.
"""

from celery import Celery
from .db import get_conn
import subprocess, shlex, os

celery = Celery(
    "backend.tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

@celery.task(bind=True)
def generate_trip_batch(self, job_id: str, area: str, count: int, seed: int = None):
    """Run the CLI with the same arguments to generate *count* trips.
    ``area`` is expected to be a bbox string because the stub CLI requires it.
    """
    cmd = ["python", "-m", "backend.cli", "generate", "--bbox", area, "--trips", str(count)]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    # Run inside the container's working directory
    subprocess.run(cmd, check=True)
    # Update job status in SQLite
    conn = get_conn()
    conn.execute("UPDATE jobs SET status='complete', processed=? WHERE job_id=?", (count, job_id))
    conn.commit()
    conn.close()
