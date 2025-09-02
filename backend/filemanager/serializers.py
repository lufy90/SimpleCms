from rest_framework import serializers
from .models import FileSystemItem, FileStorage, FileThumbnail, FileTag, FileTagRelation, FileAccessLog, FileAccessPermission, FilePermissionRequest
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
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups']


class FileStorageSerializer(serializers.ModelSerializer):
    """Serializer for FileStorage model"""
    class Meta:
        model = FileStorage
        fields = ['uuid', 'original_filename', 'file_size', 'mime_type', 'extension', 'checksum', 'created_at']


class FileThumbnailSerializer(serializers.ModelSerializer):
    """Serializer for FileThumbnail model"""
    class Meta:
        model = FileThumbnail
        fields = ['uuid', 'thumbnail_size', 'width', 'height', 'file_size', 'created_at']


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


class FileSystemItemSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=FileSystemItem.objects.all(), required=False)
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
    
    # New fields for UUID-based system
    storage = FileStorageSerializer(read_only=True)
    thumbnail = FileThumbnailSerializer(read_only=True)
    
    class Meta:
        model = FileSystemItem
        fields = [
            'id', 'name', 'item_type', 'parent', 'parents', 'created_at', 'updated_at',
            'owner', 'visibility', 'shared_users', 'shared_groups', 'children_count', 'tags', 
            'file_info', 'permissions', 'can_read', 'can_write', 'can_delete', 
            'can_share', 'can_admin', 'effective_permissions', 'storage', 'thumbnail'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner', 'children_count', 
                           'tags', 'file_info', 'permissions', 'can_read', 'can_write', 
                           'can_delete', 'can_share', 'can_admin', 'effective_permissions']
    
    def get_parents(self, obj):
        """Recursively build parent hierarchy for breadcrumb navigation"""
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
                'extension': obj.storage.extension,
                'checksum': obj.storage.checksum,
                'uuid': str(obj.storage.uuid)
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
    



class FileSystemItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileSystemItem
        fields = ['name', 'item_type', 'parent', 'visibility']
    
    def create(self, validated_data):
        # Set the current user as owner
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class FileSystemItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileSystemItem
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
        model = FileSystemItem
        fields = ['visibility', 'shared_users', 'shared_groups']


class FileAccessLogSerializer(serializers.ModelSerializer):
    """Serializer for file access logs"""
    file = serializers.PrimaryKeyRelatedField(read_only=True)  # Avoid circular import
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = FileAccessLog
        fields = ['id', 'file', 'user', 'action', 'ip_address', 'user_agent', 'timestamp']


class DirectoryTreeSerializer(serializers.Serializer):
    """Serializer for directory tree structure"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    item_type = serializers.CharField()
    parent = serializers.IntegerField(required=False)
    parents = serializers.ListField(child=serializers.DictField(), required=False)
    children = serializers.ListField(child=serializers.DictField(), required=False)
    visibility = serializers.CharField(required=False)


class FileSearchSerializer(serializers.Serializer):
    """Serializer for file search results"""
    query = serializers.CharField()
    results = FileSystemItemSerializer(many=True)
    total_count = serializers.IntegerField()
    search_time = serializers.FloatField()
    pagination = PaginationSerializer(required=False)


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
        model = FileSystemItem
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
    file = FileSystemItemSerializer(read_only=True)
    
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
