FROM python:3.9-alpine

WORKDIR /app

# Install system dependencies (required for some Python packages)
RUN apk add --no-cache gcc musl-dev

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data

# Set entrypoint
CMD ["python", "main.py"]
