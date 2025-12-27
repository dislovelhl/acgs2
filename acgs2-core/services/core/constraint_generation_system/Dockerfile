FROM python:3.11-slim

WORKDIR /app

# Copy Python files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Expose port
EXPOSE 8082

# Run demo as service
CMD ["python", "demo.py"]