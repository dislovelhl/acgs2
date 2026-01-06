FROM python:3.11-slim

WORKDIR /app

# Copy Python files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn faiss-cpu numpy requests

# Expose port
EXPOSE 8083

# Run client as service
CMD ["python", "client.py"]
