# Office Document Viewer/Editor Integration

This document describes how to integrate an existing OnlyOffice Document Server with the SimpleCMS project.

## Prerequisites

- An existing OnlyOffice Document Server instance running and accessible
- OnlyOffice Document Server URL and secret key

## Integration Steps

### 1. Backend Configuration

Edit the `backend/backend/settings.py` file and update the OnlyOffice configuration section:

```python
# OnlyOffice Document Server Configuration
ONLYOFFICE_DOCUMENT_SERVER_URL = 'http://your-onlyoffice-server:port'  # Replace with your OnlyOffice server URL
ONLYOFFICE_SECRET_KEY = 'your-secret-key-here'  # Replace with your OnlyOffice secret key
API_BASE_URL = 'http://your-backend-server:port'  # Your backend API URL
FRONTEND_URL = 'http://your-frontend-server:port'  # Your frontend URL
```

### 2. CORS Configuration

Ensure your OnlyOffice Document Server is included in the CORS allowed origins:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Vue.js development server
    "http://127.0.0.1:3000",
    "http://your-onlyoffice-server:port",  # Add your OnlyOffice server URL
    "http://your-frontend-server:port",  # Add your frontend URL
]
```

### 3. Configuration Example

For a typical setup with:
- OnlyOffice Document Server: `http://192.168.1.100:8080`
- Backend API: `http://192.168.1.100:8000`
- Frontend: `http://192.168.1.100:3000`
- Secret Key: `your-secret-key-123`

The configuration would be:

```python
# OnlyOffice Document Server Configuration
ONLYOFFICE_DOCUMENT_SERVER_URL = 'http://192.168.1.100:8080'
ONLYOFFICE_SECRET_KEY = 'your-secret-key-123'
API_BASE_URL = 'http://192.168.1.100:8000'
FRONTEND_URL = 'http://192.168.1.100:3000'
```

### 4. Verification

After updating the settings:

1. Restart your Django backend server
2. The frontend will automatically detect OnlyOffice availability
3. Office documents (Word, Excel, PowerPoint) will be viewable and editable in the browser
