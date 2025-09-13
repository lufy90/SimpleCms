from rest_framework import serializers
from .models import FileItem, FileStorage, FileThumbnail, FileTag, FileTagRelation, FileAccessLog, FileAccessPermission, FilePermissionRequest
from django.contrib.auth.models import User, Group
from django.db import models
from django.utils import timezone
from pathlib import Path


class PaginationSerializer(serializers.Serializer):
    """Serializer for pagination metadata"""
    count = serializers.IntegerField(help_text="Total number of items")
    next = serializers.URLField(allow_null=True, help_text="URL for next page")
    previous = serializers.URLField(allow_null=True, help_text="URL for previous page")
    page_size = serializers.IntegerField(help_text="Number of items per page")
    current_page = serializers.IntegerField(help_text="Current page number")
    total_pages = serializers.IntegerField(help_text="Total number of pages")
    has_next = serializers.BooleanField(help_text="Whether there is a next page")
    has_previous = serializers.BooleanField(help_text="Whether there is a previous page")


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'members']
    
    def get_members(self, obj):
        try:
            return list(obj.user_set.values_list('id', flat=True))
        except Exception as e:
            # Fallback in case of any query issues
            return []


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    groups = serializers.ListField(child=serializers.IntegerField(), required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'groups']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password required only for creation, not for updates
        if self.instance is None:
            # Creating a new user - password is required
            self.fields['password'].required = True
        else:
            # Updating an existing user - password is optional
            self.fields['password'].required = False
    
    def validate_username(self, value):
        if self.instance and self.instance.username == value:
            return value
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        if self.instance and self.instance.email == value:
            return value
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class GroupCreateUpdateSerializer(serializers.ModelSerializer):
    members = serializers.ListField(child=serializers.IntegerField(), required=False)
    
    class Meta:
        model = Group
        fields = ['name', 'members']
    
    def validate_name(self, value):
        if self.instance and self.instance.name == value:
            return value
        if Group.objects.filter(name=value).exists():
            raise serializers.ValidationError("A group with this name already exists.")
        return value


class FileStorageSerializer(serializers.ModelSerializer):
    """Serializer for FileStorage model - excludes sensitive fields"""
    class Meta:
        model = FileStorage
        fields = ['original_filename', 'file_size', 'mime_type', 'extension', 'created_at']




class FileTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileTag
        fields = ['id', 'name', 'color', 'created_at']


class FileTagRelationSerializer(serializers.Serializer):
    tag = FileTagSerializer(read_only=True)
    
    class Meta:
        model = FileTagRelation
        fields = ['id', 'tag', 'created_at']


class FileAccessPermissionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    granted_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FileAccessPermission
        fields = [
            'id', 'file', 'user', 'group', 'permission_type', 'granted_by', 
            'granted_at', 'expires_at', 'is_active', 'priority'
        ]
        read_only_fields = ['granted_by', 'granted_at', 'priority']


class FileAccessPermissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAccessPermission
        fields = ['file', 'user', 'group', 'permission_type', 'expires_at']
    
    def validate(self, data):
        # Either user or group must be specified, but not both
        if data.get('user') and data.get('group'):
            raise serializers.ValidationError("Cannot specify both user and group")
        if not data.get('user') and not data.get('group'):
            raise serializers.ValidationError("Must specify either user or group")
        
        return data


class FileItemSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=FileItem.objects.all(), required=False)
    parents = serializers.SerializerMethodField()
    owner = UserSerializer(read_only=True)
    shared_users = UserSerializer(many=True, read_only=True)
    shared_groups = GroupSerializer(many=True, read_only=True)
    children_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    file_info = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    can_read = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    can_share = serializers.SerializerMethodField()
    can_admin = serializers.SerializerMethodField()
    effective_permissions = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    
    # New fields for UUID-based system
    thumbnail = serializers.SerializerMethodField()
    sharing_status = serializers.SerializerMethodField()
    
    class Meta:
        model = FileItem
        fields = [
            'id', 'name', 'item_type', 'parent', 'parents', 'created_at', 'updated_at',
            'owner', 'visibility', 'shared_users', 'shared_groups', 'children_count', 'tags', 
            'file_info', 'permissions', 'can_read', 'can_write', 'can_delete', 
            'can_share', 'can_admin', 'effective_permissions', 'thumbnail', 'sharing_status', 'url'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner', 'children_count', 
                           'tags', 'file_info', 'permissions', 'can_read', 'can_write', 
                           'can_delete', 'can_share', 'can_admin', 'effective_permissions', 'url']
    
    def get_parents(self, obj):
        """Build parent hierarchy for breadcrumb navigation - only for user's own files"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        # Only show breadcrumb for user's own files to avoid exposing others' directory structure
        if obj.owner != request.user:
            return []
        
        parents = []
        current_item = obj
        while current_item.parent:
            parents.append({
                'id': current_item.parent.id,
                'name': current_item.parent.name,
                'item_type': current_item.parent.item_type
            })
            current_item = current_item.parent
        return parents[::-1] # Reverse to show from root to current
    
    def get_children_count(self, obj):
        if obj.item_type == 'directory':
            return obj.get_children().count()
        return 0
    
    def get_tags(self, obj):
        tag_relations = obj.tag_relations.all()
        return FileTagRelationSerializer(tag_relations, many=True).data
    
    def get_file_info(self, obj):
        """Get file information from storage"""
        if obj.storage:
            return {
                'size': obj.storage.file_size,
                'mime_type': obj.storage.mime_type,
                'extension': obj.storage.extension
            }
        return None
    
    def get_permissions(self, obj):
        """Get current user's permissions for this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            permissions = FileAccessPermission.objects.filter(
                file=obj,
                is_active=True,
                expires_at__isnull=True
            ).filter(
                models.Q(user=request.user) | 
                models.Q(group__in=request.user.groups.all())
            )
            return [perm.permission_type for perm in permissions if perm.is_valid()]
        return []
    
    def get_can_read(self, obj):
        """Check if current user can read this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_access(request.user, 'read')
        return False
    
    def get_can_write(self, obj):
        """Check if current user can write this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_write(request.user)
        return False
    
    def get_can_delete(self, obj):
        """Check if current user can delete this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_delete(request.user)
        return False
    
    def get_can_share(self, obj):
        """Check if current user can share this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_share(request.user)
        return False
    
    def get_can_admin(self, obj):
        """Check if current user has admin access to this file"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_admin(request.user)
        return False
    
    def get_effective_permissions(self, obj):
        """Get all effective permissions for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return list(obj.get_effective_permissions(request.user))
        return []
    
    def get_sharing_status(self, obj):
        """Get detailed sharing status for display purposes"""
        return obj.get_sharing_status()
    
    def get_thumbnail(self, obj):
        """Get thumbnail information and URL if available"""
        if obj.thumbnail:
            request = self.context.get('request')
            thumbnail_data = {
                'thumbnail_size': obj.thumbnail.thumbnail_size,
                'width': obj.thumbnail.width,
                'height': obj.thumbnail.height,
                'file_size': obj.thumbnail.file_size,
                'created_at': obj.thumbnail.created_at
            }
            
            # Add URL if request context is available
            if request:
                thumbnail_data['url'] = request.build_absolute_uri(f'/api/files/{obj.id}/thumbnail/')
            
            return thumbnail_data
        return None
    
    def get_url(self, obj):
        """Get the URL for the file"""
        request = self.context.get('request')
        if request and obj.item_type == 'file':
            return request.build_absolute_uri(f'/api/files/{obj.id}/download/')
        return None
    
    def to_representation(self, instance):
        """Override to hide parent field for non-owned files"""
        data = super().to_representation(instance)
        
        # Only show parent field for user's own files to avoid exposing others' directory structure
        request = self.context.get('request')
        if request and request.user.is_authenticated and instance.owner != request.user:
            data['parent'] = None
        
        return data
    



class FileItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileItem
        fields = ['name', 'item_type', 'parent', 'visibility']
    
    def create(self, validated_data):
        # Set the current user as owner
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class FileItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileItem
        fields = ['name', 'visibility']
    
    def update(self, instance, validated_data):
        # First update the instance with new data
        updated_instance = super().update(instance, validated_data)
        
        # If we're renaming a file, update the storage metadata accordingly
        if 'name' in validated_data and instance.item_type == 'file' and instance.storage:
            # Update the original_filename in storage to match the new name
            instance.storage.original_filename = validated_data['name']
            # Update extension based on new name
            instance.storage.extension = Path(validated_data['name']).suffix.lower()
            instance.storage.save()
        
        # For rename operations, we don't need to call update_from_filesystem()
        # as it would try to refresh metadata that doesn't need refreshing
        # Only call it for other types of updates if needed
        
        return updated_instance


class FileContentUpdateSerializer(serializers.Serializer):
    """Serializer for updating file content"""
    file = serializers.FileField(required=True)
    
    def validate_file(self, value):
        """Validate the uploaded file"""
        # Check file size (using the same limit as upload)
        from django.conf import settings
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 104857600)  # 100MB default
        
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds maximum allowed size of {max_size} bytes")
        
        return value
    
    def validate(self, attrs):
        """Validate the entire serializer data"""
        # Check if the instance is a file (not directory)
        if self.instance and self.instance.item_type != 'file':
            raise serializers.ValidationError("Can only update content of files, not directories")
        
        # Check if the instance has storage
        if self.instance and not self.instance.storage:
            raise serializers.ValidationError("File has no storage record")
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update the file content"""
        # Get the new file
        new_file = validated_data['file']
        
        # Import required modules
        from django.conf import settings
        from filemanager.utils import FilePathManager
        import os
        import uuid
        
        # Initialize path manager
        file_path_manager = FilePathManager()
        
        # Generate new UUID filename for the updated file
        new_uuid_filename = file_path_manager.generate_uuid_filename(new_file.name)
        new_file_path = os.path.join(str(file_path_manager.root_dir), new_uuid_filename)
        
        # Save the new file content
        with open(new_file_path, 'wb+') as destination:
            for chunk in new_file.chunks():
                destination.write(chunk)
        
        # Get file information for the new file
        file_info = file_path_manager.get_file_info(new_file_path)
        
        # Delete the old file
        old_file_path = instance.storage.get_file_path()
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
        
        # Delete old thumbnails
        for thumb in instance.storage.thumbnails.all():
            thumb_path = thumb.get_thumbnail_path()
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            thumb.delete()
        
        # Update the storage record
        instance.storage.original_filename = new_file.name
        instance.storage.file_path = new_uuid_filename
        instance.storage.file_size = file_info['size']
        instance.storage.mime_type = file_info['mime_type']
        instance.storage.extension = file_info['extension']
        instance.storage.checksum = ''  # Will be calculated below
        instance.storage.save()
        
        # Calculate and update checksum
        instance.storage.checksum = instance.storage.calculate_checksum()
        instance.storage.save()
        
        # Generate new thumbnail if it's an image
        if file_info['mime_type'].startswith('image/'):
            from filemanager.views import FileUploadView
            view = FileUploadView()
            thumbnail = view._generate_thumbnail(instance.storage)
            if thumbnail:
                instance.thumbnail = thumbnail
                instance.save()
        
        # Update the file item name if it changed
        if new_file.name != instance.name:
            instance.name = new_file.name
            instance.save()
        
        return instance


class FileVisibilityUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating file visibility and sharing"""
    shared_users = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(), 
        required=False
    )
    shared_groups = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Group.objects.all(), 
        required=False
    )
    
    class Meta:
        model = FileItem
        fields = ['visibility', 'shared_users', 'shared_groups']


class FileAccessLogSerializer(serializers.ModelSerializer):
    """Serializer for file access logs"""
    file = serializers.PrimaryKeyRelatedField(read_only=True)  # Avoid circular import
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = FileAccessLog
        fields = ['id', 'file', 'user', 'action', 'ip_address', 'user_agent', 'timestamp']



class FileUploadSerializer(serializers.Serializer):
    """Serializer for file uploads"""
    file = serializers.FileField()
    parent_id = serializers.IntegerField(required=False, help_text="ID of parent directory (optional, uploads to root if not specified)")
    relative_path = serializers.CharField(required=False, help_text="Relative path within the parent directory (e.g., 'images/thumbnails')")
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    visibility = serializers.CharField(required=False)
    shared_users = serializers.ListField(child=serializers.IntegerField(), required=False)
    shared_groups = serializers.ListField(child=serializers.IntegerField(), required=False)
    
    def validate_visibility(self, value):
        valid_choices = ['private', 'user', 'group', 'public']
        if value and value not in valid_choices:
            raise serializers.ValidationError(f"Visibility must be one of: {valid_choices}")
        return value



class FileOperationSerializer(serializers.Serializer):
    """Serializer for file operations (copy, move, delete)"""
    operation = serializers.ChoiceField(choices=['copy', 'move', 'delete'])
    file_ids = serializers.ListField(child=serializers.IntegerField(), help_text="List of file IDs to operate on")
    destination_id = serializers.IntegerField(required=False, help_text="ID of destination directory for copy/move operations")
    
    def validate(self, data):
        if data['operation'] in ['copy', 'move'] and 'destination_id' not in data:
            raise serializers.ValidationError("Destination directory ID is required for copy and move operations")
        return data


class DeletedFileSerializer(serializers.ModelSerializer):
    """Serializer for deleted files"""
    deleted_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FileItem
        fields = [
            'id', 'name', 'item_type', 'parent', 'created_at', 'updated_at', 'owner', 
            'visibility', 'is_deleted', 'deleted_at', 'deleted_by'
        ]
        read_only_fields = ['is_deleted', 'deleted_at', 'deleted_by']


class FileRestoreSerializer(serializers.Serializer):
    """Serializer for restoring deleted files"""
    file_ids = serializers.ListField(child=serializers.IntegerField(), help_text="List of deleted file IDs to restore")


class FileHardDeleteSerializer(serializers.Serializer):
    """Serializer for permanently deleting files"""
    file_ids = serializers.ListField(child=serializers.IntegerField(), help_text="List of deleted file IDs to permanently delete")


class FilePermissionRequestSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    file = FileItemSerializer(read_only=True)
    
    class Meta:
        model = FilePermissionRequest
        fields = [
            'id', 'file', 'requester', 'requested_permissions', 'reason', 
            'status', 'reviewed_by', 'reviewed_at', 'review_notes', 'created_at'
        ]
        read_only_fields = ['requester', 'status', 'reviewed_by', 'reviewed_at', 'review_notes']


class FilePermissionRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilePermissionRequest
        fields = ['file', 'requested_permissions', 'reason']
    
    def create(self, validated_data):
        validated_data['requester'] = self.context['request'].user
        return super().create(validated_data)


class FilePermissionRequestReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilePermissionRequest
        fields = ['status', 'review_notes']
    
    def update(self, instance, validated_data):
        instance.reviewed_by = self.context['request'].user
        instance.reviewed_at = timezone.now()
        return super().update(instance, validated_data)
