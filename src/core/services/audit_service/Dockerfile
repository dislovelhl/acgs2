FROM python:3.11-slim

WORKDIR /app

# Copy all service files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn web3 eth-account cryptography

# Expose port
EXPOSE 8084

# Run audit ledger as service
CMD ["python", "-m", "core.audit_ledger"]
