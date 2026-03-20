FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pyahocorasick and sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model (avoids downloading at runtime)

# Copy backend source code
COPY . .

EXPOSE 8000

# Run from the parent directory context so "backend.main" module path works
# We'll handle this via docker-compose working_dir instead
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
