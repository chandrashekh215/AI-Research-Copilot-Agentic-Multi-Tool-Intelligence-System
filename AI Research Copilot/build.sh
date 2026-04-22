#!/bin/bash
set -e

echo "=== Building AI Research Copilot ==="

# Install backend dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "=== Build complete ==="
