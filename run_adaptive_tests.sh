#!/bin/bash
export PYTHONPATH=/home/dislove/document/acgs2/src/core:/home/dislove/document/acgs2
cd src/adaptive-learning/adaptive-learning-engine
python3 -m pytest tests/ -v --tb=short --ignore=tests/unit/monitoring/drift_detector/
