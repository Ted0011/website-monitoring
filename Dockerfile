FROM python:3.9-alpine

WORKDIR /app

# Install requirements
RUN pip install requests schedule

# Copy application code
COPY ./app /app

# Create data directory
RUN mkdir -p /data

# Set entrypoint
CMD ["python", "main.py"]
