#!/bin/bash

echo "Setting up Electron for SimpleCMS..."

# Install additional dependencies
echo "Installing Electron development dependencies..."
npm install --save-dev concurrently wait-on

# Create necessary directories
echo "Creating build directories..."
mkdir -p build
mkdir -p public

# Check if icon files exist, if not create placeholders
if [ ! -f "public/icon.png" ]; then
    echo "Creating placeholder icon files..."
    # Create a simple 1x1 PNG as placeholder
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > public/icon.png
fi

echo "Electron setup complete!"
echo ""
echo "Available commands:"
echo "  npm run dev     - Run in development mode"
echo "  npm run build   - Build for production"
echo "  npm run pack    - Package without installer"
echo ""
echo "For more information, see ELECTRON.md"
