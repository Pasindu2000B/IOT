FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY services/ ./services/
COPY static/ ./static/
COPY .env .

# Create models directory
RUN mkdir -p models

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["python", "main.py"]
