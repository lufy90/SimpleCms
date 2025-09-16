#!/bin/bash

echo "Building SimpleCMS Electron Application..."

# First build the web application
echo "Building web application first..."
cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing web dependencies..."
    npm install
fi

# Build the web application
echo "Building web application..."
npm run build

# Navigate to electron directory
cd ../electron

# Install electron dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing electron dependencies..."
    npm install
fi

# Build the electron application
echo "Building electron application..."
electron-builder

echo "Electron application built successfully!"
echo "Output directory: electron/release/"
