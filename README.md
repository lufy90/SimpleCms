# SimpleCMS - File Management System

A comprehensive Content Management System built with Django and Vue.js that can manage any kind of file on your disk.

## Features

- **File System Management**: Browse, upload, download, and manage files and directories
- **Advanced Search**: Search through files by name, path, type, and content
- **File Tagging**: Organize files with custom tags and colors
- **Access Control**: Public/private file visibility and user ownership
- **File Operations**: Copy, move, delete, and rename files
- **Directory Scanning**: Automatically scan and index your filesystem
- **Access Logging**: Track file access, downloads, and modifications
- **RESTful API**: Full API for frontend integration
- **Admin Interface**: Django admin for system management

## Project Structure

```
SimpleCms/
├── backend/                 # Django backend
│   ├── backend/            # Django project settings
│   ├── filemanager/        # File management app
│   │   ├── models.py       # Database models
│   ├── manage.py           # Django management script
│   └── requirements.txt    # Python dependencies
└── README.md               # This file
```

## Backend API Endpoints

### File Management
- `GET /api/files/` - List all files and directories
- `POST /api/files/` - Create new file/directory entry
- `GET /api/files/{id}/` - Get file/directory details
- `PUT /api/files/{id}/` - Update file/directory
- `DELETE /api/files/{id}/` - Delete file/directory
- `GET /api/files/{id}/download/` - Download file
- `GET /api/files/{id}/preview/` - Get file preview info

### Directory Operations
- `GET /api/files/tree/` - Get directory tree structure
- `POST /api/files/scan_directory/` - Scan directory and add to database

### File Operations
- `POST /api/upload/` - Upload new files
- `POST /api/operations/` - Copy, move, or delete files

### Search and Filtering
- `GET /api/files/search/?q=query` - Search files
- `GET /api/files/?type=file` - Filter by type
- `GET /api/files/?parent=id` - Filter by parent directory
- `GET /api/files/?extension=.txt` - Filter by file extension

### Tags and Categories
- `GET /api/tags/` - List all tags
- `POST /api/tags/` - Create new tag
- `GET /api/tag-relations/` - List file-tag relationships

### Access Logs
- `GET /api/access-logs/` - View file access history

## Installation

### Prerequisites
- Python 3.8+
- Virtual environment
- Django 5.2+

### Backend Setup

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Scan filesystem** (optional):
   ```bash
   # Scan from root directory
   python manage.py scan_filesystem --path / --user admin
   
   # Dry run to see what would be scanned
   python manage.py scan_filesystem --path /home/user --dry-run
   
   # Scan with custom depth limit
   python manage.py scan_filesystem --path /home/user --max-depth 5
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

## Usage Examples

### Scan Your Home Directory
```bash
python manage.py scan_filesystem --path /home/username --user admin --max-depth 3
```

### API Usage

#### List all files
```bash
curl -X GET "http://localhost:8000/api/files/" \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)"
```

#### Search for files
```bash
curl -X GET "http://localhost:8000/api/files/search/?q=document" \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)"
```

#### Get directory tree
```bash
curl -X GET "http://localhost:8000/api/files/tree/?root=/home/username" \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)"
```

#### Upload a file
```bash
curl -X POST "http://localhost:8000/api/upload/" \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)" \
  -F "file=@/path/to/local/file.txt" \
  -F "destination_path=/home/username/uploads" \
  -F "tags=work,important" \
  -F "is_public=false"
```

## Configuration

### Django Settings
The main settings are in `backend/backend/settings.py`:

- **CORS**: Configured for Vue.js frontend
- **File Upload**: 100MB maximum file size
- **Media Files**: Served from `/media/` directory
- **REST Framework**: Pagination, authentication, and permissions

### Security Considerations
- Files are validated before processing
- User authentication required for most operations
- File paths are validated for security
- Access logging for audit trails

## Database Models

### FileSystemItem
- Stores file and directory information
- Tracks metadata (size, type, permissions)
- Hierarchical structure with parent-child relationships
- User ownership and public/private visibility

### FileTag
- Custom tags for file organization
- Color coding support
- Many-to-many relationship with files

### FileAccessLog
- Tracks all file operations
- User activity monitoring
- IP address and user agent logging

## Management Commands

### scan_filesystem
Scans the filesystem and populates the database:

```bash
python manage.py scan_filesystem --help
```

Options:
- `--path`: Root directory to scan
- `--user`: Username to assign as owner
- `--max-depth`: Maximum directory depth
- `--dry-run`: Preview without making changes

## Development

### Adding New Features
1. Create models in `filemanager/models.py`
2. Add serializers in `filemanager/serializers.py`
3. Implement views in `filemanager/views.py`
4. Update URLs in `filemanager/urls.py`
5. Add admin interface in `filemanager/admin.py`

### Testing
```bash
python manage.py test filemanager
```

### Code Style
- Follow PEP 8 guidelines
- Use Django best practices
- Document complex functions and classes

## API Documentation

The API includes a browsable interface at `http://localhost:8000/api/` when using the Django REST framework's browsable API renderer.

## Frontend Integration

This backend is designed to work with a Vue.js frontend. The API provides:

- RESTful endpoints for all operations
- JSON responses for easy frontend consumption
- CORS configuration for cross-origin requests
- Authentication support for secure operations

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the Django process has read access to scanned directories
2. **Large Directory Scans**: Use `--max-depth` to limit scan depth
3. **Memory Issues**: Process directories in smaller batches
4. **File Locking**: Some files may be locked by other processes

### Logs
Check Django logs for detailed error information:
```bash
python manage.py runserver --verbosity 2
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Django and DRF documentation
3. Create an issue in the repository
