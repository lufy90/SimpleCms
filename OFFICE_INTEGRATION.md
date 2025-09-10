# Office Document Viewer/Editor Integration

This document explains how to use the OnlyOffice document server integration that has been added to the SimpleCMS system.

## Features

- **Office Document Support**: View and edit Word (.docx, .doc), Excel (.xlsx, .xls), PowerPoint (.pptx, .ppt), and OpenDocument formats (.odt, .ods, .odp)
- **Real-time Collaboration**: Multiple users can edit documents simultaneously
- **Auto-save**: Documents are automatically saved as you edit
- **Pluggable Architecture**: Easy to enable/disable or configure
- **Permission-based Access**: Respects file permissions for editing vs viewing

## Configuration

### Backend Configuration

1. Add the OnlyOffice settings to your `backend/backend/settings.py`:

```python
# OnlyOffice Document Server Configuration
ONLYOFFICE_DOCUMENT_SERVER_URL = 'http://10.0.1.6'
ONLYOFFICE_SECRET_KEY = 'oyLbTv339qrQgW8uRUJ2N0lXuRtFh7qd'
API_BASE_URL = 'http://localhost:8002'  # Update to match your frontend URL
```

2. The office integration is already added to the URL patterns in `backend/filemanager/urls.py`

### Frontend Configuration

The frontend configuration is handled automatically through the `officeConfig` service. The document server URL and secret key are configured in `/frontend/src/services/officeConfig.ts`.

## Supported File Types

### Word Documents
- .docx (Microsoft Word 2007+)
- .doc (Microsoft Word 97-2003)
- .odt (OpenDocument Text)
- .rtf (Rich Text Format)
- .txt (Plain Text)

### Excel Spreadsheets
- .xlsx (Microsoft Excel 2007+)
- .xls (Microsoft Excel 97-2003)
- .ods (OpenDocument Spreadsheet)
- .csv (Comma Separated Values)

### PowerPoint Presentations
- .pptx (Microsoft PowerPoint 2007+)
- .ppt (Microsoft PowerPoint 97-2003)
- .odp (OpenDocument Presentation)

## Usage

### Viewing Office Documents

1. Navigate to any office document in the file browser
2. Click on the document to open it
3. The document will open in the OnlyOffice editor/viewer
4. For read-only access, users will see the document in view mode
5. For users with write permissions, the document will open in edit mode

### Editing Office Documents

1. Open an office document (requires write permissions)
2. The document opens in edit mode with full OnlyOffice functionality
3. Make your changes - they are auto-saved
4. Close the editor when done
5. Changes are automatically saved back to the file system

### File Operations

- **Download**: Click the download button to save the current version
- **Refresh**: Click refresh to reload the document
- **New Tab**: Open the document in a new browser tab

## API Endpoints

The integration adds several new API endpoints:

- `GET /api/office/config/{file_id}/` - Get OnlyOffice configuration for a file
- `POST /api/office/callback/` - Handle OnlyOffice server callbacks
- `GET /api/office/info/` - Get document server status
- `POST /api/office/convert/{file_id}/` - Convert document to different format

## Architecture

### Frontend Components

- **OfficeDocumentViewer**: Main component that integrates with OnlyOffice
- **officeConfig**: Service for managing OnlyOffice configuration and file type detection
- **FileReader**: Updated to include office document support
- **FileIcon**: Updated to show appropriate icons for office documents

### Backend Integration

- **office_views.py**: Contains all OnlyOffice-related API endpoints
- **Document Server Communication**: Handles configuration, callbacks, and file operations
- **Permission Integration**: Respects existing file permissions for edit/view access

## Security

- **Authentication**: All API endpoints require user authentication
- **Permission Checks**: File access is controlled by existing permission system
- **Signature Verification**: OnlyOffice callbacks are verified using HMAC signatures
- **Secure Communication**: All communication with the document server is over HTTP/HTTPS

## Troubleshooting

### Common Issues

1. **Document Server Not Responding**
   - Check if the OnlyOffice server is running at `http://10.0.1.6`
   - Verify the server URL in the configuration

2. **Documents Not Loading**
   - Check browser console for JavaScript errors
   - Verify the document server is accessible from the frontend
   - Check file permissions

3. **Changes Not Saving**
   - Verify the callback URL is accessible from the document server
   - Check the API_BASE_URL configuration
   - Review server logs for callback errors

### Debug Mode

Enable debug logging by checking the browser console and Django logs when working with office documents.

## Customization

### Adding New File Types

To add support for additional file types, update the `officeDocumentTypes` object in `/frontend/src/services/officeConfig.ts`.

### Styling

The office document viewer uses standard CSS classes that can be customized:
- `.office-document-viewer` - Main container
- `.document-editor` - OnlyOffice editor container
- `.document-header` - Header with file info and actions

### Configuration Options

The OnlyOffice editor can be customized by modifying the `config` object in the `OfficeDocumentViewer` component.

## Performance Considerations

- **Large Documents**: Very large documents may take longer to load
- **Concurrent Users**: Multiple users editing the same document simultaneously
- **Network Latency**: Document server should be on a fast network connection
- **Browser Compatibility**: OnlyOffice requires modern browsers with JavaScript enabled

## Future Enhancements

Potential future improvements:
- Document versioning and history
- Advanced collaboration features
- Document templates
- Batch document operations
- Mobile app support
- Offline editing capabilities
