#!/bin/bash
# Startup script for KCB API server

# Activate virtual environment
source .venv/bin/activate

# Start server
echo "Starting KCB API server..."
python main.py
