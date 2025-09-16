# SimpleCMS File Manager - Desktop Application

This directory contains the Electron desktop application for SimpleCMS File Manager.

## Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Run in development mode**:
   ```bash
   npm run electron:dev
   ```

3. **Build for production**:
   ```bash
   npm run electron:build
   ```

## Available Scripts

- `npm run electron` - Run Electron app (requires web app to be built)
- `npm run electron:dev` - Run in development mode with hot reload
- `npm run electron:build` - Build for current platform
- `npm run electron:build:win` - Build for Windows
- `npm run electron:build:mac` - Build for macOS
- `npm run electron:build:linux` - Build for Linux
- `npm run electron:dist` - Build without publishing
- `npm run electron:pack` - Package without installer

## Dependencies

This package only includes Electron-specific dependencies:
- `electron` - Electron framework
- `electron-builder` - Build and packaging
- `concurrently` - Run multiple commands
- `wait-on` - Wait for services to be ready

## Web Application

The web application is built separately in the `../frontend/` directory and is automatically included in the Electron build.

For more detailed information, see [ELECTRON.md](./ELECTRON.md).
