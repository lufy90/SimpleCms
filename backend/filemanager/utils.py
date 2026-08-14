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
                mime_type_result = mimetypes.guess_type(file_path)
                mime_type = mime_type_result[0] if mime_type_result else None
                return {
                    'size': stat.st_size,
                    'mime_type': mime_type or 'application/octet-stream',
                    'extension': Path(file_path).suffix.lower(),
                }
        except (OSError, FileNotFoundError):
            pass
        return None


def determine_file_sharing(parent_directory, requested_visibility, requested_shared_users, requested_shared_groups, user):
    """
    Determine file sharing based on parent directory and user preferences.
    
    Logic:
    1. If user explicitly sets sharing (not 'private'), use their choice
    2. If parent directory is shared, inherit its sharing permissions
    3. Otherwise, default to 'private'
    """
    # If user explicitly requested sharing, use their choice
    if requested_visibility != 'private':
        return requested_visibility, requested_shared_users, requested_shared_groups
    
    # Check if parent directory is shared
    if parent_directory and parent_directory.owner != user:
        # User is creating file in someone else's directory
        # Inherit the parent directory's sharing permissions
        parent_visibility = parent_directory.visibility
        
        if parent_visibility == 'user':
            # Inherit shared users from parent
            shared_user_ids = list(parent_directory.shared_users.values_list('id', flat=True))
            return 'user', shared_user_ids, []
        
        elif parent_visibility == 'group':
            # Inherit shared groups from parent
            shared_group_ids = list(parent_directory.shared_groups.values_list('id', flat=True))
            return 'group', [], shared_group_ids
        
        elif parent_visibility == 'public':
            # Make file public
            return 'public', [], []
    
    # Check if parent directory has explicit permissions that include the user
    if parent_directory:
        # Check if user has access to parent through explicit permissions
        user_permissions = parent_directory.access_permissions.filter(
            user=user, is_active=True
        ).exclude(permission_type='read')  # Exclude read-only permissions
        
        if user_permissions.exists():
            # User has write/delete/share/admin permissions
            # Inherit parent's sharing structure
            parent_visibility = parent_directory.visibility
            
            if parent_visibility == 'user':
                shared_user_ids = list(parent_directory.shared_users.values_list('id', flat=True))
                return 'user', shared_user_ids, []
            
            elif parent_visibility == 'group':
                shared_group_ids = list(parent_directory.shared_groups.values_list('id', flat=True))
                return 'group', [], shared_group_ids
            
            elif parent_visibility == 'public':
                return 'public', [], []
    
    # Default to private
    return 'private', [], []


# Global instance
file_path_manager = FilePathManager()


def _gps_coordinate_to_degrees(values):
    """Convert GPS EXIF DMS tuple to decimal degrees."""
    if not values or len(values) < 3:
        return None
    try:
        degrees = float(values[0])
        minutes = float(values[1])
        seconds = float(values[2])
        return degrees + (minutes / 60.0) + (seconds / 3600.0)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract_image_gps(file_path):
    """
    Extract GPS coordinates from an image file's EXIF data.

    Returns (latitude, longitude) as Decimals, or None if unavailable.
    Never raises — callers can safely ignore a missing location.
    """
    try:
        from decimal import Decimal, ROUND_HALF_UP
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, IFD

        with Image.open(file_path) as img:
            exif = img.getexif()
            if not exif:
                return None

            gps_ifd = exif.get_ifd(IFD.GPSInfo)
            if not gps_ifd:
                return None

            gps_data = {GPSTAGS.get(tag, tag): value for tag, value in gps_ifd.items()}
            lat_values = gps_data.get('GPSLatitude')
            lon_values = gps_data.get('GPSLongitude')
            lat_ref = gps_data.get('GPSLatitudeRef')
            lon_ref = gps_data.get('GPSLongitudeRef')

            if not lat_values or not lon_values or not lat_ref or not lon_ref:
                return None

            latitude = _gps_coordinate_to_degrees(lat_values)
            longitude = _gps_coordinate_to_degrees(lon_values)
            if latitude is None or longitude is None:
                return None

            if str(lat_ref).upper() == 'S':
                latitude = -latitude
            if str(lon_ref).upper() == 'W':
                longitude = -longitude

            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return None

            quantize = Decimal('0.000001')
            return (
                Decimal(str(latitude)).quantize(quantize, rounding=ROUND_HALF_UP),
                Decimal(str(longitude)).quantize(quantize, rounding=ROUND_HALF_UP),
            )
    except Exception:
        return None


def apply_image_gps_to_storage(file_storage):
    """Extract GPS from storage file and persist on FileStorage when present."""
    try:
        if not file_storage.mime_type or not file_storage.mime_type.startswith('image/'):
            if file_storage.latitude is not None or file_storage.longitude is not None:
                file_storage.latitude = None
                file_storage.longitude = None
                file_storage.save(update_fields=['latitude', 'longitude'])
            return False
        coords = extract_image_gps(file_storage.get_file_path())
        if not coords:
            file_storage.latitude = None
            file_storage.longitude = None
            file_storage.save(update_fields=['latitude', 'longitude'])
            return False
        file_storage.latitude, file_storage.longitude = coords
        file_storage.save(update_fields=['latitude', 'longitude'])
        return True
    except Exception:
        return False


def _run_ffmpeg_extract_frame(video_path, output_jpg_path, seek_seconds):
    """Run ffmpeg to extract a single frame. Returns True on success."""
    import subprocess

    cmd = [
        'ffmpeg',
        '-y',
        '-ss', str(seek_seconds),
        '-i', video_path,
        '-frames:v', '1',
        '-q:v', '2',
        output_jpg_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0 and os.path.exists(output_jpg_path) and os.path.getsize(output_jpg_path) > 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def extract_video_frame(video_path, output_jpg_path):
    """
    Extract a single frame from a video into a JPEG file using system ffmpeg.

    Tries seek at 1s first, then 0s. Returns True on success.
    Never raises — callers can safely ignore failure.
    """
    try:
        if not video_path or not os.path.exists(video_path):
            return False
        output_dir = os.path.dirname(output_jpg_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        if _run_ffmpeg_extract_frame(video_path, output_jpg_path, 1):
            return True
        # Short videos may have no frame at 1s
        if os.path.exists(output_jpg_path):
            try:
                os.remove(output_jpg_path)
            except OSError:
                pass
        return _run_ffmpeg_extract_frame(video_path, output_jpg_path, 0)
    except Exception:
        return False
