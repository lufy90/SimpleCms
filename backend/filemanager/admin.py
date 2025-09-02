from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    FileSystemItem, FileStorage, FileThumbnail, FileTag, FileTagRelation, FileAccessLog, 
    FileAccessPermission, FilePermissionRequest
)
from django.utils import timezone


@admin.register(FileStorage)
class FileStorageAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'original_filename', 'file_size_display', 'mime_type', 'extension', 'created_at']
    list_filter = ['mime_type', 'extension', 'created_at']
    search_fields = ['original_filename', 'uuid']
    readonly_fields = ['uuid', 'created_at', 'checksum']
    list_per_page = 50
    
    fieldsets = (
        ('File Information', {
            'fields': ('uuid', 'original_filename', 'file_path')
        }),
        ('File Details', {
            'fields': ('file_size', 'mime_type', 'extension', 'checksum'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            elif obj.file_size < 1024 * 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            else:
                return f"{obj.file_size / (1024 * 1024 * 1024):.1f} GB"
        return "-"
    file_size_display.short_description = "Size"


@admin.register(FileThumbnail)
class FileThumbnailAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'original_file', 'thumbnail_size', 'dimensions', 'file_size_display', 'created_at']
    list_filter = ['thumbnail_size', 'created_at']
    search_fields = ['uuid', 'original_file__original_filename']
    readonly_fields = ['uuid', 'created_at']
    list_per_page = 50
    
    def dimensions(self, obj):
        return f"{obj.width} × {obj.height}"
    dimensions.short_description = "Dimensions"
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            elif obj.file_size < 1024 * 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            else:
                return f"{obj.file_size / (1024 * 1024 * 1024):.1f} GB"
        return "-"
    file_size_display.short_description = "Size"


@admin.register(FileSystemItem)
class FileSystemItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'item_type', 'size_display', 'owner', 'visibility_display', 'created_at', 'storage_info']
    list_filter = ['item_type', 'visibility', 'owner', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'storage_info', 'thumbnail_info']
    list_per_page = 50
    filter_horizontal = ['shared_users', 'shared_groups']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'item_type', 'parent')
        }),
        ('Storage', {
            'fields': ('storage', 'thumbnail'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Ownership & Visibility', {
            'fields': ('owner', 'visibility', 'shared_users', 'shared_groups')
        }),
    )
    
    def size_display(self, obj):
        if obj.storage:
            size = obj.storage.file_size
            if size:
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    return f"{size / (1024 * 1024):.1f} MB"
                else:
                    return f"{size / (1024 * 1024 * 1024):.1f} GB"
        return "-"
    size_display.short_description = "Size"
    
    def visibility_display(self, obj):
        if obj.visibility == 'user':
            user_count = obj.shared_users.count()
            return f"User ({user_count} users)"
        elif obj.visibility == 'group':
            group_count = obj.shared_groups.count()
            return f"Group ({group_count} groups)"
        return obj.get_visibility_display()
    visibility_display.short_description = "Visibility"
    
    def storage_info(self, obj):
        if obj.storage:
            return f"{obj.storage.original_filename} ({obj.storage.extension})"
        return "-"
    storage_info.short_description = "Storage"
    
    def thumbnail_info(self, obj):
        if obj.thumbnail:
            return f"{obj.thumbnail.thumbnail_size} ({obj.thumbnail.width}×{obj.thumbnail.height})"
        return "No thumbnail"
    thumbnail_info.short_description = "Thumbnail"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'parent', 'storage', 'thumbnail').prefetch_related('shared_users', 'shared_groups')
    
    actions = ['mark_public', 'mark_user', 'mark_group', 'mark_private']
    
    def mark_public(self, request, queryset):
        updated = queryset.update(visibility='public')
        self.message_user(request, f"{updated} items marked as public.")
    mark_public.short_description = "Mark selected items as public"
    
    def mark_user(self, request, queryset):
        updated = queryset.update(visibility='user')
        self.message_user(request, f"{updated} items marked as user-shared.")
    mark_user.short_description = "Mark selected items as user-shared"
    
    def mark_group(self, request, queryset):
        updated = queryset.update(visibility='group')
        self.message_user(request, f"{updated} items marked as group-shared.")
    mark_group.short_description = "Mark selected items as group-shared"
    
    def mark_private(self, request, queryset):
        updated = queryset.update(visibility='private')
        self.message_user(request, f"{updated} items marked as private.")
    mark_private.short_description = "Mark selected items as private"


@admin.register(FileAccessPermission)
class FileAccessPermissionAdmin(admin.ModelAdmin):
    list_display = ['file', 'user_or_group', 'permission_type', 'granted_by', 'granted_at', 'expires_at', 'is_active']
    list_filter = ['permission_type', 'granted_at', 'expires_at', 'is_active']
    search_fields = ['file__name', 'user__username', 'group__name']
    readonly_fields = ['granted_by', 'granted_at']
    list_per_page = 50
    
    fieldsets = (
        ('Permission Details', {
            'fields': ('file', 'user', 'group', 'permission_type')
        }),
        ('Access Control', {
            'fields': ('expires_at', 'is_active')
        }),
        ('Metadata', {
            'fields': ('granted_by', 'granted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_or_group(self, obj):
        if obj.user:
            return f"User: {obj.user.username}"
        elif obj.group:
            return f"Group: {obj.group.name}"
        return "Unknown"
    user_or_group.short_description = "Target"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('file', 'user', 'group', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set granted_by for new permissions
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FilePermissionRequest)
class FilePermissionRequestAdmin(admin.ModelAdmin):
    list_display = ['file', 'requester', 'requested_permissions', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = ['file__name', 'requester__username', 'requested_permissions']
    readonly_fields = ['file', 'requester', 'requested_permissions', 'reason', 'created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Request Details', {
            'fields': ('file', 'requester', 'requested_permissions', 'reason')
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('file', 'requester', 'reviewed_by')
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"{updated} permission requests approved.")
    approve_requests.short_description = "Approve selected permission requests"
    
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"{updated} permission requests rejected.")
    reject_requests.short_description = "Reject selected permission requests"


@admin.register(FileTag)
class FileTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_preview', 'file_count', 'created_at']
    search_fields = ['name']
    list_per_page = 50
    
    def color_preview(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 3px;"></div>',
            obj.color
        )
    color_preview.short_description = "Color"
    
    def file_count(self, obj):
        return obj.file_relations.count()
    file_count.short_description = "Files"


@admin.register(FileTagRelation)
class FileTagRelationAdmin(admin.ModelAdmin):
    list_display = ['file', 'tag', 'created_at']
    list_filter = ['tag', 'created_at']
    search_fields = ['file__name', 'tag__name']
    list_per_page = 50
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('file', 'tag')


@admin.register(FileAccessLog)
class FileAccessLogAdmin(admin.ModelAdmin):
    list_display = ['file', 'user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action', 'user', 'timestamp']
    search_fields = ['file__name', 'user__username', 'ip_address']
    readonly_fields = ['file', 'user', 'action', 'ip_address', 'user_agent', 'timestamp']
    list_per_page = 100
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('file', 'user')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True
