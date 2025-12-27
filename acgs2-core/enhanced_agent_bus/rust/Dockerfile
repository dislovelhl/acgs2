# Use Rust base image for building
FROM rust:1.70-slim as builder

WORKDIR /app

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

# Copy source code
COPY src/ ./src/

# Build the library
RUN cargo build --release

# Python runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy built Rust library
COPY --from=builder /app/target/release/libenhanced_agent_bus.so /app/

# Copy Python files
COPY ../*.py ./

# Install Python dependencies (minimal for now)
RUN pip install --no-cache-dir pyo3

# Expose port for message bus service
EXPOSE 8080

# Default command (to be overridden)
CMD ["python", "-c", "print('Rust Message Bus Ready')"]