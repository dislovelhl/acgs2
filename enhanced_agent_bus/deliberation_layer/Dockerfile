FROM python:3.11-slim

WORKDIR /app

# Copy Python files
COPY . .

# Install dependencies (minimal for now)
RUN pip install --no-cache-dir fastapi uvicorn redis

# Expose port
EXPOSE 8081

# Run the dashboard as main service
CMD ["python", "dashboard.py"]