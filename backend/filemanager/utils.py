import os
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError


class FilePathManager:
    """Manages secure file paths within the FILE_MANAGER_ROOT directory"""
    
    def __init__(self):
        self.root_dir = Path(settings.FILE_MANAGER_ROOT)
    
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
    
    def get_upload_path(self, filename, relative_path=""):
        """Get safe path for file uploads"""
        safe_path = self.get_safe_path(relative_path)
        self.ensure_directory_exists(safe_path)
        return os.path.join(safe_path, filename)
    
    def get_create_path(self, filename, relative_path=""):
        """Get safe path for created files"""
        safe_path = self.get_safe_path(relative_path)
        self.ensure_directory_exists(safe_path)
        return os.path.join(safe_path, filename)
    
    def get_relative_path(self, absolute_path):
        """Get relative path from FILE_MANAGER_ROOT"""
        try:
            abs_path = Path(absolute_path)
            if abs_path.is_relative_to(self.root_dir):
                return str(abs_path.relative_to(self.root_dir))
            return abs_path.name
        except ValueError:
            return Path(absolute_path).name


# Global instance
file_path_manager = FilePathManager()
