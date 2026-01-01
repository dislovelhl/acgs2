#!/bin/bash
# ACGS-2 NVIDIA GPU Integration - Kilo Code Session Starter

set -e

echo "🚀 Starting Kilo Code for NVIDIA GPU Integration..."
echo ""
echo "Project: ACGS-2 (AI Constitutional Governance System)"
echo "Task: GPU Acceleration Profiling & Integration"
echo ""

# Change to project directory
cd /home/dislove/document/acgs2

# Check context files exist
if [[ ! -f ".kilocode-context/nvidia-gpu-acceleration.md" ]]; then
    echo "❌ Context file missing. Run setup first."
    exit 1
fi

echo "📋 Context loaded from .kilocode-context/"
echo ""
echo "Starting Kilo Code in Architect mode..."
echo "Use /mode code to switch to coding when ready."
echo ""

# Start Kilo Code with architect mode for planning
kilocode --mode architect --workspace /home/dislove/document/acgs2

# Alternative commands:
# kilocode --mode code    # Direct coding mode
# kilocode --continue     # Resume last session
# kilocode --auto "..."   # Autonomous mode
