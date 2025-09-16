#!/bin/bash

echo "Running SimpleCMS Electron in Development Mode..."

# First ensure frontend dependencies are installed
echo "Checking frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Navigate to electron directory
cd ../electron

# Install electron dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing electron dependencies..."
    npm install
fi

# Run electron in development mode
echo "Starting electron development mode..."
npm run electron:dev
