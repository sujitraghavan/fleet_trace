FROM python:3.11-slim

WORKDIR /app

# Install system packages needed for any compiled dependencies (none for now)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY backend/ ./backend/

EXPOSE 8000

# Default command runs the FastAPI server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]