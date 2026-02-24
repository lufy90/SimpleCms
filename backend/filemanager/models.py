from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
import os
import mimetypes
from pathlib import Path
from datetime import timezone as dt_timezone
import uuid
import hashlib


class FileItemManager(models.Manager):
    """Custom manager to filter out deleted items by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Include deleted items in the queryset"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Only deleted items"""
        return super().get_queryset().filter(is_deleted=True)


class FileStorage(models.Model):
    """Physical file storage with UUID naming"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)  # upload_directory/uuid.ext
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    extension = models.CharField(max_length=20)
    checksum = models.CharField(max_length=64)  # SHA256 for integrity
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['original_filename']),
            models.Index(fields=['mime_type']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.uuid})"
    
    def get_file_path(self):
        """Get the absolute file system path"""
        from django.conf import settings
        return os.path.join(settings.FILE_MANAGER_ROOT, self.file_path)
    
    def calculate_checksum(self):
        """Calculate SHA256 checksum of the file"""
        try:
            file_path = self.get_file_path()
            if os.path.exists(file_path):
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                return sha256_hash.hexdigest()
        except (OSError, FileNotFoundError):
            pass
        return None
    
    def verify_checksum(self):
        """Verify file integrity by comparing stored vs calculated checksum"""
        if not self.checksum:
            return False
        calculated = self.calculate_checksum()
        return calculated == self.checksum if calculated else False


class FileThumbnail(models.Model):
    """Thumbnail storage for files"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    original_file = models.ForeignKey(FileStorage, on_delete=models.CASCADE, related_name='thumbnails')
    thumbnail_path = models.CharField(max_length=500)  # upload_directory/thumbnails/uuid.ext
    thumbnail_size = models.CharField(max_length=20)  # e.g., "150x150", "300x300"
    width = models.IntegerField()
    height = models.IntegerField()
    file_size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['original_file']),
            models.Index(fields=['thumbnail_size']),
        ]
    
    def __str__(self):
        return f"{self.thumbnail_size} thumbnail for {self.original_file.original_filename}"
    
    def get_thumbnail_path(self):
        """Get the absolute thumbnail file path"""
        from django.conf import settings
        return os.path.join(settings.FILE_MANAGER_ROOT, self.thumbnail_path)


class FileItem(models.Model):
    """Logical file system structure (separated from physical storage)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ITEM_TYPES = [
        ('file', 'File'),
        ('directory', 'Directory'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('user', 'User Shared'),
        ('group', 'Group Shared'),
        ('public', 'Public'),
    ]
    
    name = models.CharField(max_length=255)
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Physical storage reference (NEW)
    storage = models.OneToOneField(FileStorage, on_delete=models.CASCADE, null=True, blank=True)
    
    # Thumbnail support (NEW)
    thumbnail = models.OneToOneField(FileThumbnail, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Ownership and visibility
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    
    # Logical deletion
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_files')
    
    # User and group sharing
    shared_users = models.ManyToManyField(User, blank=True, related_name='shared_files')
    shared_groups = models.ManyToManyField(Group, blank=True, related_name='shared_files')
    
    # Custom manager
    objects = FileItemManager()
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['item_type']),
            models.Index(fields=['parent']),
            models.Index(fields=['visibility']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_deleted']),
        ]
        # Note: SQLite doesn't handle NULL values in unique constraints properly
        # We'll handle uniqueness validation for both files and directories in the model's clean() method
    
    def __str__(self):
        status = " [DELETED]" if self.is_deleted else ""
        return f"{self.name} ({self.item_type}){status}"
    
    def clean(self):
        """Custom validation for file and directory name uniqueness"""
        from django.core.exceptions import ValidationError
        
        # Check for duplicate names within the same parent and owner
        existing = FileItem.objects.filter(
            name=self.name,
            parent=self.parent,
            item_type=self.item_type,
            owner=self.owner,
            is_deleted=False
        ).exclude(pk=self.pk)
        
        if existing.exists():
            item_type_name = 'directory' if self.item_type == 'directory' else 'file'
            raise ValidationError({
                'name': f'A {item_type_name} with this name already exists in this location for this user.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to call clean()"""
        self.clean()
        super().save(*args, **kwargs)
    
    def get_absolute_path(self):
        """Get the absolute file system path (internal use only)"""
        if self.storage:
            return self.storage.get_file_path()
        return None
    
    def get_relative_path(self):
        """Get path relative to the root directory"""
        if self.parent:
            return os.path.join(self.parent.get_relative_path(), self.name)
        return self.name
    
    def get_display_path(self):
        """Get a safe display path (relative or just filename)"""
        return self.get_relative_path()
    
    def get_file_info(self):
        """Get detailed file information"""
        if self.item_type == 'file' and self.storage:
            try:
                file_path = self.storage.get_file_path()
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    return {
                        'size': stat.st_size,
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime,
                        'accessed': stat.st_atime,
                        'permissions': oct(stat.st_mode)[-3:],
                    }
            except (OSError, FileNotFoundError):
                pass
        return None
    
    def update_from_filesystem(self):
        """Update model from actual file system"""
        if self.storage and os.path.exists(self.storage.get_file_path()):
            stat = os.stat(self.storage.get_file_path())
            
            if self.item_type == 'file':
                self.storage.file_size = stat.st_size
                
                # Get mime type, fallback to 'application/octet-stream' if None
                mime_type_result = mimetypes.guess_type(self.storage.get_file_path())
                mime_type = mime_type_result[0] if mime_type_result else None
                self.storage.mime_type = mime_type or 'application/octet-stream'
                
                self.storage.extension = Path(self.storage.original_filename).suffix.lower()
                
                # Update checksum
                self.storage.checksum = self.storage.calculate_checksum()
                self.storage.save()
            
            self.save()
    
    def get_children(self):
        """Get immediate children (files and directories)"""
        if self.item_type == 'directory':
            return FileItem.objects.filter(parent=self)
        return FileItem.objects.none()
    
    def get_all_children(self):
        """Get all descendants recursively"""
        children = []
        for child in self.get_children():
            children.append(child)
            if child.item_type == 'directory':
                children.extend(child.get_all_children())
        return children
    
    def can_access(self, user, permission_type='read'):
        """Check if user can access this file with given permission
        
        Priority order:
        1. Superuser - full access
        2. Owner - full access  
        3. Explicit user permissions (FileAccessPermission)
        4. Explicit group permissions (FileAccessPermission)
        5. Visibility-based access (fallback)
        """
        if not user.is_authenticated:
            return False
        
        # Superuser can do everything
        if user.is_superuser:
            return True
        
        # Owner has full access
        if self.owner == user:
            return True
        
        # Check explicit user permissions first (highest priority)
        user_permission = self.get_user_permission(user)
        if user_permission and user_permission.has_permission(permission_type):
            return True
        
        # Check explicit group permissions
        group_permission = self.get_group_permission(user)
        if group_permission and group_permission.has_permission(permission_type):
            return True
        
        # Fall back to visibility-based access only if no explicit permissions exist
        if self.visibility == 'public':
            return True  # Public files are readable by everyone
        
        elif self.visibility == 'user':
            # Check if user is in shared_users
            if user in self.shared_users.all():
                return True
        
        elif self.visibility == 'group':
            # Check if user is in any of the shared groups
            user_groups = user.groups.all()
            shared_groups = self.shared_groups.all()
            
            if user_groups.filter(id__in=shared_groups.values_list('id', flat=True)).exists():
                return True
        
        # Private files - only owner can access
        return False
    
    def can_write(self, user):
        """Check if user can write/modify this file"""
        return self.can_access(user, 'write')
    
    def can_delete(self, user):
        """Check if user can delete this file"""
        return self.can_access(user, 'delete')
    
    def can_share(self, user):
        """Check if user can share this file"""
        return self.can_access(user, 'share')
    
    def can_admin(self, user):
        """Check if user has admin access to this file"""
        return self.can_access(user, 'admin')
    
    def soft_delete(self, user):
        """Mark file as deleted (logical deletion)"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restore a soft-deleted file"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    def hard_delete(self):
        """Permanently delete the file (physical deletion)"""
        try:
            if self.item_type == 'file' and self.storage:
                # For files, delete physical file and storage
                file_path = self.storage.get_file_path()
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete thumbnails
                for thumb in self.storage.thumbnails.all():
                    thumb_path = thumb.get_thumbnail_path()
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                    thumb.delete()
                
                # Delete storage record
                self.storage.delete()
            elif self.item_type == 'directory':
                # For directories, recursively delete all children first
                # This ensures we clean up any files that might have storage
                children = self.get_children()
                for child in children:
                    child.hard_delete()
        except (OSError, FileNotFoundError):
            pass
        
        # Delete from database
        self.delete()
    
    def get_user_permission(self, user):
        """Get the highest priority permission for a user"""
        user_permissions = self.access_permissions.filter(
            user=user, 
            group__isnull=True, 
            is_active=True
        ).order_by('-priority')
        
        return user_permissions.first() if user_permissions.exists() else None
    
    def get_group_permission(self, user):
        """Get best group permission for a user"""
        user_groups = user.groups.all()
        if not user_groups.exists():
            return None
        
        # Get the highest priority permission from user's groups
        group_permissions = self.access_permissions.filter(
            group__in=user_groups,
            user__isnull=True,
            is_active=True
        ).order_by('-priority')
        
        return group_permissions.first() if group_permissions.exists() else None
    
    def get_effective_permissions(self, user):
        """Get all effective permissions for a user"""
        permissions = set()
        
        if user.is_superuser:
            permissions.update(['read', 'write', 'delete', 'share', 'admin'])
            return permissions
        
        if self.owner == user:
            permissions.update(['read', 'write', 'delete', 'share', 'admin'])
            return permissions
        
        # Check user-specific permissions
        user_permission = self.get_user_permission(user)
        if user_permission:
            permissions.update(user_permission.get_permission_list())
        
        # Check group permissions
        group_permission = self.get_group_permission(user)
        if group_permission:
            permissions.update(group_permission.get_permission_list())
        
        return permissions
    
    def update_visibility_from_sharing(self):
        """Update visibility field based on current sharing status
        
        This ensures visibility accurately reflects the sharing state:
        - 'private': No sharing, no explicit permissions
        - 'user': Shared with specific users (via shared_users or explicit user permissions)
        - 'group': Shared with groups (via shared_groups or explicit group permissions)  
        - 'public': Publicly accessible
        """
        # Check if there are any explicit permissions
        has_user_permissions = self.access_permissions.filter(
            user__isnull=False, 
            is_active=True
        ).exists()
        
        has_group_permissions = self.access_permissions.filter(
            group__isnull=False, 
            is_active=True
        ).exists()
        
        # Check shared_users and shared_groups
        has_shared_users = self.shared_users.exists()
        has_shared_groups = self.shared_groups.exists()
        
        # Determine visibility based on sharing status
        if self.visibility == 'public':
            # Keep public as is
            pass
        elif has_user_permissions or has_shared_users:
            # Has user-level sharing
            if self.visibility != 'user':
                self.visibility = 'user'
                self.save(update_fields=['visibility'])
        elif has_group_permissions or has_shared_groups:
            # Has group-level sharing
            if self.visibility != 'group':
                self.visibility = 'group'
                self.save(update_fields=['visibility'])
        else:
            # No sharing - should be private
            if self.visibility != 'private':
                self.visibility = 'private'
                self.save(update_fields=['visibility'])
    
    def get_sharing_status(self):
        """Get detailed sharing status for display purposes"""
        status = {
            'visibility': self.visibility,
            'has_explicit_permissions': False,
            'user_permissions_count': 0,
            'group_permissions_count': 0,
            'shared_users_count': self.shared_users.count(),
            'shared_groups_count': self.shared_groups.count(),
        }
        
        # Count explicit permissions
        user_perms = self.access_permissions.filter(user__isnull=False, is_active=True)
        group_perms = self.access_permissions.filter(group__isnull=False, is_active=True)
        
        status['user_permissions_count'] = user_perms.count()
        status['group_permissions_count'] = group_perms.count()
        status['has_explicit_permissions'] = user_perms.exists() or group_perms.exists()
        
        return status


class FileAccessPermission(models.Model):
    """Granular access permissions for files"""
    PERMISSION_TYPES = [
        ('read', 'Read'),
        ('write', 'Write'),
        ('delete', 'Delete'),
        ('share', 'Share'),
        ('admin', 'Admin'),
    ]
    
    PERMISSION_PRIORITY = {
        'read': 1,
        'write': 2,
        'delete': 3,
        'share': 4,
        'admin': 5,
    }
    
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='access_permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='file_permissions')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name='file_permissions')
    permission_type = models.CharField(max_length=10, choices=PERMISSION_TYPES)
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="Higher priority overrides lower priority permissions")
    
    class Meta:
        unique_together = [
            ('file', 'user', 'permission_type'),
            ('file', 'group', 'permission_type'),
        ]
        indexes = [
            models.Index(fields=['file', 'user', 'permission_type']),
            models.Index(fields=['file', 'group', 'permission_type']),
            models.Index(fields=['expires_at', 'is_active']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        target = self.user.username if self.user else f"Group: {self.group.name}"
        return f"{target} -> {self.file.name} ({self.permission_type})"
    
    def is_valid(self):
        """Check if permission is still valid (not expired)"""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def has_permission(self, permission_type):
        """Check if this permission grants the specified permission type"""
        if not self.is_valid():
            return False
        
        # Admin permission grants all permissions
        if self.permission_type == 'admin':
            return True
        
        # Direct permission match
        if self.permission_type == permission_type:
            return True
        
        # Permission hierarchy: write includes read, delete includes write, etc.
        if permission_type == 'read' and self.permission_type in ['write', 'delete', 'share']:
            return True
        elif permission_type == 'write' and self.permission_type in ['delete']:
            return True
        
        return False
    
    def get_permission_list(self):
        """Get list of all permissions this grants"""
        if self.permission_type == 'admin':
            return ['read', 'write', 'delete', 'share', 'admin']
        elif self.permission_type == 'delete':
            return ['read', 'write', 'delete']
        elif self.permission_type == 'write':
            return ['read', 'write']
        elif self.permission_type == 'share':
            return ['read', 'share']
        elif self.permission_type == 'read':
            return ['read']
        return []
    
    def save(self, *args, **kwargs):
        # Set priority based on permission type
        self.priority = self.PERMISSION_PRIORITY.get(self.permission_type, 1)
        super().save(*args, **kwargs)
        
        # Update file visibility to reflect sharing status
        if hasattr(self, 'file') and self.file:
            self.file.update_visibility_from_sharing()
    
    def delete(self, *args, **kwargs):
        # Store file reference before deletion
        file_item = self.file
        super().delete(*args, **kwargs)
        
        # Update file visibility after permission deletion
        if file_item:
            file_item.update_visibility_from_sharing()


class FileTag(models.Model):
    """Tags for categorizing files"""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class FileTagRelation(models.Model):
    """Many-to-many relationship between files and tags"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='tag_relations')
    tag = models.ForeignKey(FileTag, on_delete=models.CASCADE, related_name='file_relations')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['file', 'tag']


class FileAccessLog(models.Model):
    """Log of file access for analytics"""
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=[
        ('view', 'View'),
        ('download', 'Download'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('upload', 'Upload'),
        ('permission_granted', 'Permission Granted'),
        ('permission_revoked', 'Permission Revoked'),
        ('visibility_change', 'Visibility Change'),
        ('shared', 'Shared'),
        ('unshared', 'Unshared'),
        ('user_shared', 'User Shared'),
        ('group_shared', 'Group Shared'),
    ])
    ip_address = models.CharField(max_length=45, null=True, blank=True)  # IPv6 max length is 45
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['file', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]


class FilePermissionRequest(models.Model):
    """Requests for file access permissions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    file = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='permission_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_requests')
    requested_permissions = models.CharField(max_length=100)  # Comma-separated permissions
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file', 'status']),
            models.Index(fields=['requester', 'status']),
        ]
    
    def __str__(self):
        return f"{self.requester.username} -> {self.file.name} ({self.status})"
