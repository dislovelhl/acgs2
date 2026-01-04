FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY docs/ docs/

# Create output directory for reports
RUN mkdir -p /tmp/compliance-reports && chmod 777 /tmp/compliance-reports

ENV PYTHONPATH=/app
ENV PORT=8100

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8100"]
