from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
import os
import mimetypes
from pathlib import Path
from datetime import timezone as dt_timezone


class FileSystemItemManager(models.Manager):
    """Custom manager to filter out deleted items by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Include deleted items in the queryset"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Only deleted items"""
        return super().get_queryset().filter(is_deleted=True)


class FileSystemItem(models.Model):
    """Base model for both files and directories"""
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
    path = models.CharField(max_length=1000, unique=True)  # Absolute path (internal use only)
    relative_path = models.CharField(max_length=1000, blank=True)  # Relative path for display
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # File-specific fields
    size = models.BigIntegerField(null=True, blank=True)  # File size in bytes
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    extension = models.CharField(max_length=20, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_modified = models.DateTimeField(null=True, blank=True)  # File system last modified time
    
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
    objects = FileSystemItemManager()
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['relative_path']),
            models.Index(fields=['item_type']),
            models.Index(fields=['parent']),
            models.Index(fields=['visibility']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        status = " [DELETED]" if self.is_deleted else ""
        return f"{self.name} ({self.item_type}){status}"
    
    def get_absolute_path(self):
        """Get the absolute file system path (internal use only)"""
        return self.path
    
    def get_relative_path(self):
        """Get path relative to the root directory"""
        if self.relative_path:
            return self.relative_path
        if self.parent:
            return os.path.join(self.parent.get_relative_path(), self.name)
        return self.name
    
    def get_display_path(self):
        """Get a safe display path (relative or just filename)"""
        if self.relative_path:
            return self.relative_path
        return self.name
    
    def get_file_info(self):
        """Get detailed file information"""
        if self.item_type == 'file':
            try:
                stat = os.stat(self.path)
                return {
                    'size': stat.st_size,
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime,
                    'accessed': stat.st_atime,
                    'permissions': oct(stat.st_mode)[-3:],
                }
            except (OSError, FileNotFoundError):
                return None
        return None
    
    def update_from_filesystem(self):
        """Update model from actual file system"""
        if os.path.exists(self.path):
            stat = os.stat(self.path)
            self.last_modified = timezone.datetime.fromtimestamp(stat.st_mtime, tz=dt_timezone.utc)
            
            if self.item_type == 'file':
                self.size = stat.st_size
                self.mime_type, _ = mimetypes.guess_type(self.path)
                self.extension = Path(self.name).suffix.lower()
            
            self.save()
    
    def get_children(self):
        """Get immediate children (files and directories)"""
        if self.item_type == 'directory':
            return FileSystemItem.objects.filter(parent=self)
        return FileSystemItem.objects.none()
    
    def get_all_children(self):
        """Get all descendants recursively"""
        children = []
        for child in self.get_children():
            children.append(child)
            if child.item_type == 'directory':
                children.extend(child.get_all_children())
        return children
    
    def can_access(self, user, permission_type='read'):
        """Check if user can access this file with given permission"""
        if not user.is_authenticated:
            return False
        
        # Superuser can do everything
        if user.is_superuser:
            return True
        
        # Owner has full access
        if self.owner == user:
            return True
        
        # Check specific user permissions first
        user_permission = self.get_user_permission(user)
        if user_permission and user_permission.has_permission(permission_type):
            return True
        
        # Check group permissions
        group_permission = self.get_group_permission(user)
        if group_permission and group_permission.has_permission(permission_type):
            return True
        
        # Check visibility-based access
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
        # Remove from file system
        try:
            if os.path.exists(self.path):
                if self.item_type == 'file':
                    os.remove(self.path)
                elif self.item_type == 'directory':
                    import shutil
                    shutil.rmtree(self.path)
        except (OSError, FileNotFoundError):
            pass
        
        # Delete from database
        self.delete()
    
    def get_user_permission(self, user):
        """Get specific permission for a user"""
        try:
            return self.access_permissions.get(user=user, group__isnull=True, is_active=True)
        except FileAccessPermission.DoesNotExist:
            return None
    
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
    
    file = models.ForeignKey(FileSystemItem, on_delete=models.CASCADE, related_name='access_permissions')
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


class FileTag(models.Model):
    """Tags for categorizing files"""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class FileTagRelation(models.Model):
    """Many-to-many relationship between files and tags"""
    file = models.ForeignKey(FileSystemItem, on_delete=models.CASCADE, related_name='tag_relations')
    tag = models.ForeignKey(FileTag, on_delete=models.CASCADE, related_name='file_relations')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['file', 'tag']


class FileAccessLog(models.Model):
    """Log of file access for analytics"""
    file = models.ForeignKey(FileSystemItem, on_delete=models.CASCADE, related_name='access_logs')
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
    ip_address = models.GenericIPAddressField(null=True, blank=True)
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
    
    file = models.ForeignKey(FileSystemItem, on_delete=models.CASCADE, related_name='permission_requests')
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
