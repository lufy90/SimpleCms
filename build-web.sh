#!/bin/bash

echo "Building SimpleCMS Web Application..."

# Navigate to frontend directory
cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing web dependencies..."
    npm install
fi

# Build the web application
echo "Building web application..."
npm run build

echo "Web application built successfully!"
echo "Output directory: frontend/dist/"
