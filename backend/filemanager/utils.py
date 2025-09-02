import os
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
import mimetypes


class FilePathManager:
    """Manages secure file paths within the FILE_MANAGER_ROOT directory with UUID-based naming"""
    
    def __init__(self):
        self.root_dir = Path(settings.FILE_MANAGER_ROOT)
        self.thumbnails_dir = self.root_dir / 'thumbnails'
        self.ensure_thumbnails_directory()
    
    def ensure_thumbnails_directory(self):
        """Ensure thumbnails directory exists"""
        self.thumbnails_dir.mkdir(exist_ok=True)
    
    def sanitize_path(self, path):
        """Sanitize a path to prevent directory traversal attacks"""
        if not path:
            return ""
        
        # Remove any .. or . components
        clean_path = os.path.normpath(path)
        
        # Remove leading slashes
        clean_path = clean_path.lstrip('/')
        
        # Ensure path doesn't start with ../
        if clean_path.startswith('..'):
            raise ValidationError("Path contains invalid components")
        
        return clean_path
    
    def get_safe_path(self, relative_path=""):
        """Convert relative path to safe absolute path within FILE_MANAGER_ROOT"""
        if not relative_path:
            return str(self.root_dir)
        
        sanitized = self.sanitize_path(relative_path)
        safe_path = self.root_dir / sanitized
        
        # Ensure the final path is within the root directory
        try:
            real_safe_path = Path(os.path.realpath(safe_path))
            real_root = Path(os.path.realpath(self.root_dir))
            
            if not real_safe_path.is_relative_to(real_root):
                raise ValidationError("Path is outside allowed directory")
        except (OSError, ValueError):
            raise ValidationError("Invalid path")
        
        return str(safe_path)
    
    def ensure_directory_exists(self, path):
        """Ensure the directory exists, create if it doesn't"""
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
    
    def generate_uuid_filename(self, original_filename, extension=None):
        """Generate a UUID-based filename for secure storage"""
        if not extension:
            extension = Path(original_filename).suffix.lower()
        
        # Generate UUID and create filename
        file_uuid = str(uuid.uuid4())
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        
        return f"{file_uuid}{extension}"
    
    def get_upload_path(self, original_filename, relative_path=""):
        """Get safe path for file uploads with UUID-based naming"""
        # Generate UUID filename
        uuid_filename = self.generate_uuid_filename(original_filename)
        
        # In the new UUID-based system, we store all files in a flat structure
        # The relative_path is only used for database organization, not filesystem structure
        # All files go directly to the root upload directory with UUID names
        
        # Always use root directory for physical storage
        full_path = os.path.join(str(self.root_dir), uuid_filename)
        
        # For database storage, we can still use the relative path for logical organization
        relative_path_for_db = os.path.join(relative_path, uuid_filename) if relative_path else uuid_filename
        
        return full_path, relative_path_for_db
    
    def get_thumbnail_path(self, original_file_uuid, thumbnail_size, extension):
        """Get path for thumbnail storage"""
        # Ensure extension starts with dot
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        
        # Generate thumbnail UUID
        thumbnail_uuid = str(uuid.uuid4())
        thumbnail_filename = f"{thumbnail_uuid}{extension}"
        
        # Create thumbnail path
        thumbnail_path = self.thumbnails_dir / thumbnail_filename
        
        # Return both full path and relative path for database
        full_path = str(thumbnail_path)
        relative_path_for_db = f"thumbnails/{thumbnail_filename}"
        
        return full_path, relative_path_for_db
    
    def get_create_path(self, filename, relative_path=""):
        """Get safe path for created files"""
        # In the new UUID-based system, we don't create physical directory structures
        # All files are stored in the root upload directory
        return os.path.join(str(self.root_dir), filename)
    
    def get_relative_path(self, absolute_path):
        """Get relative path from FILE_MANAGER_ROOT"""
        try:
            abs_path = Path(absolute_path)
            if abs_path.is_relative_to(self.root_dir):
                return str(abs_path.relative_to(self.root_dir))
            return abs_path.name
        except ValueError:
            return Path(absolute_path).name
    
    def get_file_info(self, file_path):
        """Get file information including size and mime type"""
        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                mime_type, _ = mimetypes.guess_type(file_path)
                return {
                    'size': stat.st_size,
                    'mime_type': mime_type or 'application/octet-stream',
                    'extension': Path(file_path).suffix.lower(),
                }
        except (OSError, FileNotFoundError):
            pass
        return None


# Global instance
file_path_manager = FilePathManager()
