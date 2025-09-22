# SimpleCMS Build Instructions

This project has been simplified to allow building directly from within each directory without needing to run scripts from the root.

## Frontend Build

To build the web application:

```bash
cd frontend
npm install
VITE_API_BASE_URL=<API_URL> npm run build
```

The built files will be in `frontend/dist/`.

## Electron Build

To build the desktop application:

```bash
cd electron
npm install
VITE_API_BASE_URL=<API_URL> npm run build
```

This will automatically build the frontend first, then build the Electron app.

### Available Electron Commands

- `npm run dev` - Run in development mode (with hot reload)
- `npm run build` - Build for production
- `npm run build:win` - Build for Windows
- `npm run build:mac` - Build for macOS  
- `npm run build:linux` - Build for Linux
- `npm run pack` - Package without installer
- `npm run dist` - Build and package for distribution

## Clean Build

To clean all build artifacts, you can manually remove the directories:

```bash
# Clean frontend
rm -rf frontend/dist frontend/node_modules

# Clean electron
rm -rf electron/node_modules electron/release

# Clean everything
rm -rf frontend/dist frontend/node_modules electron/node_modules electron/release
```
