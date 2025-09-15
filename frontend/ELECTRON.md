# Electron Setup for SimpleCMS

This document explains how to build and run the SimpleCMS File Manager as a desktop application using Electron.

## Prerequisites

- Node.js (version 20.19.0 or higher)
- npm or yarn package manager

## Installation

1. Install dependencies:
```bash
npm install
```

2. Install additional Electron dependencies:
```bash
npm install --save-dev concurrently wait-on
```

## Development

### Run in Development Mode

To run the application in development mode with hot reload:

```bash
npm run electron:dev
```

This command will:
- Start the Vite development server on port 3001
- Wait for the server to be ready
- Launch the Electron application

### Run Electron Only

If the Vite server is already running, you can launch just the Electron app:

```bash
npm run electron
```

## Building for Production

### Build for Current Platform

```bash
npm run electron:build
```

### Build for Specific Platforms

```bash
# Windows
npm run electron:build:win

# macOS
npm run electron:build:mac

# Linux
npm run electron:build:linux
```

### Build Without Publishing

```bash
npm run electron:dist
```

### Package Only (No Installer)

```bash
npm run electron:pack
```

## Output

- **Development**: The app runs directly from source
- **Production**: Built files are output to the `release/` directory
- **Packages**: Platform-specific installers and packages are created

## Platform-Specific Notes

### Windows
- Creates NSIS installer and portable executable
- Requires Windows 10 or later
- Icons: `public/icon.ico`
- **Note**: Building Windows packages on Linux requires Wine to be installed

### macOS
- Creates DMG and ZIP packages
- Supports both Intel and Apple Silicon
- Icons: `public/icon.icns`
- Requires code signing for distribution
- **Note**: Building macOS packages on Linux is not supported

### Linux
- Creates AppImage, DEB, and RPM packages
- Supports x64 architecture
- Icons: `public/icon.png`
- **Note**: This is the recommended platform for building on Linux

## Configuration

### Package Metadata
- **Author**: SimpleCMS Team (test@lufy.org)
- **Homepage**: https://github.com/simplecms/filemanager
- **Description**: SimpleCMS File Manager - A modern file management application
- **Maintainer**: test@lufy.org (for .deb packages)

### Electron Main Process
- **File**: `electron/main.cjs`
- **Purpose**: Controls application lifecycle, window management, and native features
- **Note**: Uses CommonJS syntax (.cjs extension) to avoid ES module conflicts

### Preload Script
- **File**: `electron/preload.cjs`
- **Purpose**: Secure communication bridge between main and renderer processes
- **Note**: Uses CommonJS syntax (.cjs extension) to avoid ES module conflicts

### Build Configuration
- **File**: `electron-builder.json`
- **Purpose**: Defines build targets, packaging options, and platform-specific settings

## Security Features

- Context isolation enabled
- Node integration disabled in renderer
- Remote module disabled
- External link handling
- Navigation protection

## Storage System

The application uses a hybrid storage system that automatically detects the environment:

### Web Environment
- Uses `js-cookie` library for token storage
- Tokens are stored as HTTP-only cookies
- Automatic expiration handling

### Electron Environment
- Uses `localStorage` for token storage
- Tokens are stored as key-value pairs
- Same expiration logic as web environment

### Storage Interface
- **File**: `src/utils/storage.ts`
- **Purpose**: Provides unified storage interface for both environments
- **Detection**: Automatically detects Electron vs web context
- **API**: `tokenStorage.getAccessToken()`, `tokenStorage.setAccessToken()`, etc.

## Troubleshooting

### Common Issues

1. **ES Module Error: "require is not defined"**
   - **Cause**: Electron main process using CommonJS in ES module context
   - **Solution**: Use `.cjs` extension for Electron files (main.cjs, preload.cjs)
   - **Note**: This is already configured in the current setup

2. **Authentication Issues in Electron**
   - **Cause**: Cookies not working properly in Electron context
   - **Solution**: Use the hybrid storage system (already implemented)
   - **Note**: Tokens are automatically stored in localStorage in Electron

3. **Port Already in Use**
   - Change the port in `vite.config.ts` and `electron/main.cjs`

4. **Build Failures**
   - Ensure all dependencies are installed
   - Check Node.js version compatibility
   - Clear `node_modules` and reinstall

5. **Icon Issues**
   - Ensure icon files exist in `public/` directory
   - Use correct formats: `.ico` (Windows), `.icns` (macOS), `.png` (Linux)

6. **Permission Issues (macOS)**
   - Check entitlements in `build/entitlements.mac.plist`
   - Ensure proper code signing setup

### Development Tips

- Use `Ctrl+Shift+I` (or `Cmd+Option+I` on macOS) to open DevTools
- Check the console for error messages
- Use the Vue DevTools extension for debugging
- Monitor the terminal for build output

## File Structure

```
frontend/
├── electron/
│   ├── main.js          # Main Electron process
│   └── preload.js       # Preload script
├── build/
│   └── entitlements.mac.plist  # macOS entitlements
├── public/
│   ├── icon.png         # Linux icon
│   ├── icon.ico         # Windows icon
│   └── icon.icns        # macOS icon
├── electron-builder.json # Build configuration
└── package.json         # Scripts and dependencies
```

## Next Steps

1. Add proper application icons
2. Configure code signing for distribution
3. Set up auto-updater if needed
4. Customize application menu
5. Add platform-specific features
