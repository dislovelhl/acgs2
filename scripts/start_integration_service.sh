#!/bin/bash

cd integration-service

# Start integration service
exec python3 -m uvicorn src.main:app --port 8100 --reload
