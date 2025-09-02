from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.models import Group, User
import os
import shutil
import time
from pathlib import Path

from .models import (
    FileSystemItem, FileTag, FileTagRelation, FileAccessLog, 
    FileAccessPermission, FilePermissionRequest, FileStorage, FileThumbnail
)
from .serializers import (
    FileSystemItemSerializer, FileSystemItemCreateSerializer, FileSystemItemUpdateSerializer,
    FileTagSerializer, FileTagRelationSerializer, FileAccessLogSerializer,
    DirectoryTreeSerializer, FileSearchSerializer, FileUploadSerializer, FileOperationSerializer,
    FileAccessPermissionSerializer, FileAccessPermissionCreateSerializer,
    FileVisibilityUpdateSerializer, FilePermissionRequestSerializer,
    FilePermissionRequestCreateSerializer, FilePermissionRequestReviewSerializer,
    DeletedFileSerializer, FileRestoreSerializer, FileHardDeleteSerializer,
    UserSerializer, GroupSerializer,
    # DirectoryUploadSerializer removed
)
from .pagination import (
    FileSystemItemPagination, FileAccessLogPagination, FileTagPagination
)
from .pagination import (
    FileSystemItemPagination, FileAccessLogPagination, FileTagPagination
)
from .utils import file_path_manager


class FileSystemItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file system items"""
    queryset = FileSystemItem.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = FileSystemItemPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FileSystemItemCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FileSystemItemUpdateSerializer
        return FileSystemItemSerializer
    
    def get_queryset(self):
        queryset = FileSystemItem.objects.all()
        user = self.request.user
        
        # Filter based on user permissions
        if user.is_authenticated and not user.is_superuser:
            # User can see: their own files, public files, files shared with them, and files shared with their groups
            user_groups = user.groups.all()
            queryset = queryset.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups)  # Group shared files
            ).distinct()
        
        # Filter by item type
        item_type = self.request.query_params.get('type', None)
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Filter by parent directory
        parent_id = self.request.query_params.get('parent', None)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        
        # Filter by owner
        owner_id = self.request.query_params.get('owner', None)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        # Filter by visibility
        visibility = self.request.query_params.get('visibility', None)
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        
        # Filter by extension
        extension = self.request.query_params.get('extension', None)
        if extension:
            queryset = queryset.filter(extension__icontains=extension)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def perform_update(self, serializer):
        # Check if user can write to this file
        instance = self.get_object()
        if not instance.can_write(self.request.user):
            raise PermissionError("You don't have permission to modify this file")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Check if user can delete this file
        if not instance.can_delete(self.request.user):
            raise PermissionError("You don't have permission to delete this file")
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a file"""
        file_item = self.get_object()
        
        if file_item.item_type != 'file':
            return Response({'error': 'Item is not a file'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_item.can_access(request.user, 'read'):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if not file_item.storage:
            return Response({'error': 'File storage not found'}, status=status.HTTP_404_NOT_FOUND)
        
        file_path = file_item.storage.get_file_path()
        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Log the download
        FileAccessLog.objects.create(
            file=file_item,
            user=request.user if request.user.is_authenticated else None,
            action='download',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{file_item.name}"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get file preview information"""
        file_item = self.get_object()
        
        if file_item.item_type != 'file':
            return Response({'error': 'Item is not a file'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_item.can_access(request.user, 'read'):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Log the preview
        FileAccessLog.objects.create(
            file=file_item,
            user=request.user if request.user.is_authenticated else None,
            action='view',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Update file metadata from filesystem
        file_item.update_from_filesystem()
        
        return Response(FileSystemItemSerializer(file_item, context={'request': request}).data)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_visibility(self, request, pk=None):
        """Update file visibility and sharing"""
        file_item = self.get_object()
        
        if not file_item.can_write(request.user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FileVisibilityUpdateSerializer(file_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the visibility change
            action_type = 'visibility_change'
            if 'shared_users' in serializer.validated_data:
                action_type = 'user_shared' if file_item.visibility == 'user' else 'visibility_change'
            elif 'shared_groups' in serializer.validated_data:
                action_type = 'group_shared' if file_item.visibility == 'group' else 'visibility_change'
            
            FileAccessLog.objects.create(
                file=file_item,
                user=request.user,
                action=action_type,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(FileSystemItemSerializer(file_item, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get file permissions for current user"""
        file_item = self.get_object()
        
        if not file_item.can_access(request.user, 'read'):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get user's effective permissions
        effective_permissions = file_item.get_effective_permissions(request.user)
        
        # Get specific permissions if user has admin access
        specific_permissions = []
        if file_item.can_admin(request.user):
            specific_permissions = FileAccessPermission.objects.filter(
                file=file_item,
                is_active=True
            ).select_related('user', 'group', 'granted_by')
            specific_permissions = FileAccessPermissionSerializer(specific_permissions, many=True).data
        
        return Response({
            'effective_permissions': list(effective_permissions),
            'specific_permissions': specific_permissions,
            'can_read': file_item.can_access(request.user, 'read'),
            'can_write': file_item.can_write(request.user),
            'can_delete': file_item.can_delete(request.user),
            'can_share': file_item.can_share(request.user),
            'can_admin': file_item.can_admin(request.user),
        })
    
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search for files and directories"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Search query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_time = time.time()
        
        # Search in database first
        queryset = FileSystemItem.objects.filter(
            Q(name__icontains=query) | Q(path__icontains=query)
        )
        
        # Apply permission filtering
        user = request.user
        if user.is_authenticated and not user.is_superuser:
            user_groups = user.groups.all()
            queryset = queryset.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups)  # Group shared files
            ).distinct()
        
        # Apply filters
        item_type = request.query_params.get('type', None)
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Limit results
        limit = int(request.query_params.get('limit', 100))
        queryset = queryset[:limit]
        
        search_time = time.time() - start_time
        
        serializer = FileSystemItemSerializer(queryset, many=True, context={'request': request})
        
        return Response({
            'query': query,
            'results': serializer.data,
            'total_count': queryset.count(),
            'search_time': search_time
        })
    
    @action(detail=False, methods=['get'])
    def shared_to_me(self, request):
        """Get files shared directly to the current user"""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get files shared directly to the user through permissions
        shared_files = FileSystemItem.objects.filter(
            Q(access_permissions__user=user, access_permissions__is_active=True) |
            Q(visibility='user', shared_users=user)
        ).exclude(owner=user).distinct()
        
        # Apply pagination
        page = self.paginate_queryset(shared_files)
        if page is not None:
            serializer = FileSystemItemSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = FileSystemItemSerializer(shared_files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared_to_my_groups(self, request):
        """Get files shared to groups the current user belongs to"""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get user's groups
        user_groups = user.groups.all()
        if not user_groups.exists():
            return Response({'results': []})
        
        # Get files shared to user's groups through permissions
        shared_files = FileSystemItem.objects.filter(
            Q(access_permissions__group__in=user_groups, access_permissions__is_active=True) |
            Q(visibility='group', shared_groups__in=user_groups)
        ).exclude(owner=user).distinct()
        
        # Apply pagination
        page = self.paginate_queryset(shared_files)
        if page is not None:
            serializer = FileSystemItemSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = FileSystemItemSerializer(shared_files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def scan_directory(self, request):
        """Scan a directory and add its contents to the database"""
        directory_path = request.data.get('path')
        if not directory_path or not os.path.isdir(directory_path):
            return Response({'error': 'Valid directory path is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            scanned_count = self._scan_directory_recursive(directory_path, request.user)
            return Response({
                'message': f'Successfully scanned {scanned_count} items',
                'results': [],
                'scanned_count': scanned_count
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def create_directory(self, request):
        """Create a new directory"""
        name = request.data.get('name')
        parent_id = request.data.get('parent_id')
        visibility = request.data.get('visibility', 'private')
        
        if not name:
            return Response({'error': 'Directory name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate directory name
        if not name or '/' in name or '\\' in name:
            return Response({'error': 'Invalid directory name. Cannot contain slashes or backslashes.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get parent directory if specified
            parent_directory = None
            if parent_id:
                try:
                    parent_directory = FileSystemItem.objects.get(id=parent_id, item_type='directory')
                    # Check if user can write to parent directory
                    if not parent_directory.can_write(request.user):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileSystemItem.DoesNotExist:
                    return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if directory already exists in database
            if parent_directory:
                if FileSystemItem.objects.filter(parent=parent_directory, name=name, item_type='directory').exists():
                    return Response({'error': 'Directory already exists'}, status=status.HTTP_409_CONFLICT)
            else:
                if FileSystemItem.objects.filter(parent__isnull=True, name=name, item_type='directory').exists():
                    return Response({'error': 'Directory already exists'}, status=status.HTTP_409_CONFLICT)
            
            # Create database record (directories don't need physical storage)
            directory_item = FileSystemItem.objects.create(
                name=name,
                item_type='directory',
                parent=parent_directory,
                owner=request.user,
                visibility=visibility
            )
            
            # Log the directory creation
            FileAccessLog.objects.create(
                file=directory_item,
                user=request.user,
                action='create',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Directory created successfully',
                'directory': FileSystemItemSerializer(directory_item, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': f'Failed to create directory: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def get_children(self, request, pk=None):
        """Get direct children of a directory by ID without pagination"""
        file_item = self.get_object()
        
        # Check if it's a directory
        if file_item.item_type != 'directory':
            return Response({'error': 'Item is not a directory'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user can access this directory
        if not file_item.can_access(request.user, 'read'):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get direct children (not recursive)
        children = FileSystemItem.objects.filter(
            parent=file_item,
            is_active=True
        ).order_by('item_type', 'name')  # Directories first, then files, alphabetically
        
        # Apply permission filtering for children
        user = request.user
        if user.is_authenticated and not user.is_superuser:
            user_groups = user.groups.all()
            children = children.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups)  # Group shared files
            ).distinct()
        
        # Serialize children with full context
        serializer = FileSystemItemSerializer(children, many=True, context={'request': request})
        
        return Response({
            'parent': {
                'id': file_item.id,
                'name': file_item.name,
                'item_type': file_item.item_type
            },
            'children': serializer.data,
            'total_count': len(serializer.data)
        })

    @action(detail=False, methods=['get'])
    def list_children(self, request):
        """Get children by parent ID from query params, or list top-level files if no parent given"""
        parent_id = request.query_params.get('parent_id', None)
        
        if parent_id:
            # Get children of specific parent
            try:
                parent_item = FileSystemItem.objects.get(id=parent_id)
                
                # Check if it's a directory
                if parent_item.item_type != 'directory':
                    return Response({'error': 'Parent item is not a directory'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if user can access this directory
                if not parent_item.can_access(request.user, 'read'):
                    return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
                
                # Get direct children (not recursive)
                children = FileSystemItem.objects.filter(
                    parent=parent_item
                ).order_by('item_type', 'name')  # Directories first, then files, alphabetically
                
                # Use full serializer for parent to include parents field
                parent_serializer = FileSystemItemSerializer(parent_item, context={'request': request})
                parent_info = parent_serializer.data
            except FileSystemItem.DoesNotExist:
                return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # List top-level files (no parent)
            children = FileSystemItem.objects.filter(
                parent__isnull=True
            ).order_by('item_type', 'name')  # Directories first, then files, alphabetically
            
            parent_info = None
        
        # Apply permission filtering for children
        user = request.user
        if user.is_authenticated and not user.is_superuser:
            user_groups = user.groups.all()
            children = children.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups)  # Group shared files
            ).distinct()
        
        # Serialize children with full context
        serializer = FileSystemItemSerializer(children, many=True, context={'request': request})
        
        response_data = {
            'children': serializer.data,
            'total_count': len(serializer.data)
        }
        
        if parent_info:
            response_data['parent'] = parent_info
        else:
            response_data['parent'] = None
            response_data['message'] = 'Listing top-level files and directories'
        
        return Response(response_data)

    
    def _scan_directory_recursive(self, directory_path, user):
        """Recursively scan directory and add items to database"""
        scanned_count = 0
        
        try:
            # Get the relative path from the scan root
            scan_root = directory_path
            for root, dirs, files in os.walk(directory_path):
                # Calculate relative path from scan root
                rel_path = os.path.relpath(root, scan_root) if root != scan_root else ""
                
                # Add directories
                for dir_name in dirs:
                    # Check if directory already exists by name and parent
                    parent_dir = None
                    if rel_path:
                        # Find parent directory in database
                        parent_parts = rel_path.split(os.sep)
                        current_parent = None
                        for part in parent_parts:
                            if current_parent:
                                current_parent = FileSystemItem.objects.filter(
                                    parent=current_parent, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                            else:
                                current_parent = FileSystemItem.objects.filter(
                                    parent__isnull=True, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                        parent_dir = current_parent
                    
                    if not FileSystemItem.objects.filter(parent=parent_dir, name=dir_name, item_type='directory').exists():
                        FileSystemItem.objects.create(
                            name=dir_name,
                            item_type='directory',
                            parent=parent_dir,
                            owner=user
                        )
                        scanned_count += 1
                
                # Add files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    # Find parent directory
                    parent_dir = None
                    if rel_path:
                        parent_parts = rel_path.split(os.sep)
                        current_parent = None
                        for part in parent_parts:
                            if current_parent:
                                current_parent = FileSystemItem.objects.filter(
                                    parent=current_parent, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                            else:
                                current_parent = FileSystemItem.objects.filter(
                                    parent__isnull=True, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                        parent_dir = current_parent
                    
                    # Check if file already exists by name and parent
                    if not FileSystemItem.objects.filter(parent=parent_dir, name=file_name, item_type='file').exists():
                        # Create FileStorage record
                        file_info = file_path_manager.get_file_info(file_path)
                        if file_info:
                            # Generate UUID filename and copy file
                            new_uuid_filename = file_path_manager.generate_uuid_filename(file_name)
                            new_file_path, new_relative_path = file_path_manager.get_upload_path(file_name, rel_path)
                            
                            # Copy file to new location
                            import shutil
                            shutil.copy2(file_path, new_file_path)
                            
                            # Create FileStorage record
                            file_storage = FileStorage.objects.create(
                                original_filename=file_name,
                                file_path=new_relative_path,
                                file_size=file_info['size'],
                                mime_type=file_info['mime_type'],
                                extension=file_info['extension'],
                                checksum=''  # Will be calculated below
                            )
                            
                            # Calculate and update checksum
                            file_storage.checksum = file_storage.calculate_checksum()
                            file_storage.save()
                            
                            # Create FileSystemItem record
                            file_item = FileSystemItem.objects.create(
                                name=file_name,
                                item_type='file',
                                parent=parent_dir,
                                storage=file_storage,
                                owner=user
                            )
                            
                            scanned_count += 1
        except Exception as e:
            print(f'Error scanning directory {directory_path}: {e}')
        
        return scanned_count
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @action(detail=True, methods=['post'])
    def share_recursively(self, request, pk=None):
        """Share a directory and all its contents recursively with a user or group"""
        file_item = self.get_object()
        
        if file_item.item_type != 'directory':
            return Response({'error': 'Can only share directories recursively'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_item.can_share(request.user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get sharing parameters
        share_type = request.data.get('share_type')  # 'user' or 'group'
        target_id = request.data.get('target_id')
        permission_types = request.data.get('permission_types', ['read'])
        expires_at = request.data.get('expires_at')
        
        if not share_type or not target_id or not permission_types:
            return Response({'error': 'share_type, target_id, and permission_types are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get all files and subdirectories recursively
            all_items = self._get_recursive_items(file_item)
            
            # Create permissions for each item
            created_permissions = []
            failed_items = []
            
            for item in all_items:
                try:
                    # Create permissions for each permission type
                    for permission_type in permission_types:
                        permission_data = {
                            'file': item.id,  # Use ID for serializer
                            'permission_type': permission_type,
                            'expires_at': expires_at
                        }
                        
                        if share_type == 'user':
                            permission_data['user'] = target_id
                            permission_data['group'] = None
                        else:
                            permission_data['user'] = None
                            permission_data['group'] = target_id
                        
                        # Check if permission already exists
                        existing_permission = FileAccessPermission.objects.filter(
                            file=item,
                            user=permission_data.get('user'),
                            group=permission_data.get('group'),
                            permission_type=permission_type
                        ).first()
                        
                        if existing_permission:
                            # Update existing permission
                            existing_permission.expires_at = expires_at
                            existing_permission.is_active = True
                            existing_permission.save()
                            created_permissions.append(existing_permission)
                        else:
                            # Create new permission using serializer
                            serializer = FileAccessPermissionCreateSerializer(data=permission_data, context={'request': request})
                            if serializer.is_valid():
                                permission = serializer.save(granted_by=request.user)
                                created_permissions.append(permission)
                            else:
                                failed_items.append({
                                    'item': item.name,
                                    'error': f'Serializer validation failed: {serializer.errors}'
                                })
                            
                except Exception as e:
                    failed_items.append({
                        'item': item.name,
                        'error': str(e)
                    })
            
            # Log the recursive sharing
            FileAccessLog.objects.create(
                file=file_item,
                user=request.user,
                action='recursive_share',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': f'Successfully shared {len(created_permissions)} items',
                'shared_items_count': len(created_permissions),
                'failed_items': failed_items,
                'total_items': len(all_items)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': f'Failed to share recursively: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_recursive_items(self, directory):
        """Get all files and subdirectories within a directory recursively"""
        items = [directory]  # Include the directory itself
        
        def _traverse(current_dir):
            children = current_dir.get_children()
            for child in children:
                items.append(child)
                if child.item_type == 'directory':
                    _traverse(child)
        
        _traverse(directory)
        return items

    @action(detail=True, methods=['post'])
    def unshare_recursively(self, request, pk=None):
        """Unshare a directory and all its contents recursively from a user or group"""
        file_item = self.get_object()
        
        if file_item.item_type != 'directory':
            return Response({'error': 'Can only unshare directories recursively'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_item.can_share(request.user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get unsharing parameters
        share_type = request.data.get('share_type')  # 'user' or 'group'
        target_id = request.data.get('target_id')
        permission_types = request.data.get('permission_types', [])  # Empty list means all permissions
        
        if not share_type or not target_id:
            return Response({'error': 'share_type and target_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get all files and subdirectories recursively
            all_items = self._get_recursive_items(file_item)
            
            # Revoke permissions for each item
            revoked_permissions = []
            failed_items = []
            
            for item in all_items:
                try:
                    # Build filter for permissions to revoke
                    permission_filter = {
                        'file': item,
                        'is_active': True
                    }
                    
                    if share_type == 'user':
                        permission_filter['user_id'] = target_id
                        permission_filter['group__isnull'] = True
                    else:
                        permission_filter['group_id'] = target_id
                        permission_filter['user__isnull'] = True
                    
                    # Filter by specific permission types if provided
                    if permission_types:
                        permission_filter['permission_type__in'] = permission_types
                    
                    # Find and revoke permissions
                    permissions_to_revoke = FileAccessPermission.objects.filter(**permission_filter)
                    
                    for permission in permissions_to_revoke:
                        permission.is_active = False
                        permission.save()
                        revoked_permissions.append(permission)
                        
                except Exception as e:
                    failed_items.append({
                        'item': item.name,
                        'error': str(e)
                    })
            
            # Log the recursive unsharing
            FileAccessLog.objects.create(
                file=file_item,
                user=request.user,
                action='recursive_unshare',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': f'Successfully unshared {len(revoked_permissions)} permissions',
                'revoked_permissions_count': len(revoked_permissions),
                'failed_items': failed_items,
                'total_items': len(all_items)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': f'Failed to unshare recursively: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadView(generics.CreateAPIView):
    """Handle file uploads with UUID-based storage"""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    serializer_class = FileUploadSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        parent_id = serializer.validated_data.get('parent_id')
        relative_path = serializer.validated_data.get('relative_path', '')
        tags = serializer.validated_data.get('tags', [])
        visibility = serializer.validated_data.get('visibility', 'private')
        shared_users = serializer.validated_data.get('shared_users', [])
        shared_groups = serializer.validated_data.get('shared_groups', [])
        
        try:
            # Get parent directory if specified
            parent_directory = None
            if parent_id:
                try:
                    parent_directory = FileSystemItem.objects.get(id=parent_id, item_type='directory')
                    # Check if user can write to parent directory
                    if not parent_directory.can_write(request.user):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileSystemItem.DoesNotExist:
                    return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Handle relative path and create directories if needed
            final_parent_directory = parent_directory
            if relative_path:
                # Create directory structure for the relative path
                # Use safe method to handle concurrent uploads with database constraints
                final_parent_directory = self._get_or_create_directory_path_safe(
                    relative_path, parent_directory, request.user, visibility
                )
            
            # Get safe upload path using the path manager (now returns tuple)
            # In the new UUID-based system, all files go to the root upload directory
            # The relative_path is only used for database organization
            file_path, relative_path_for_db = file_path_manager.get_upload_path(uploaded_file.name, relative_path)
            
            # Extract just the UUID filename for storage in FileStorage.file_path
            # The file_path field should only contain the filename, not the full relative path
            uuid_filename = os.path.basename(file_path)
            
            # Save file to destination
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Get file information
            file_info = file_path_manager.get_file_info(file_path)
            
            # Create FileStorage record
            file_storage = FileStorage.objects.create(
                original_filename=uploaded_file.name,
                file_path=uuid_filename,  # Store only the UUID filename, not the full relative path
                file_size=file_info['size'],
                mime_type=file_info['mime_type'],
                extension=file_info['extension'],
                checksum=file_info.get('checksum', '')  # Will be calculated below
            )
            
            # Calculate and update checksum
            file_storage.checksum = file_storage.calculate_checksum()
            file_storage.save()
            
            # Create FileSystemItem record
            file_item = FileSystemItem.objects.create(
                name=uploaded_file.name,
                item_type='file',
                parent=final_parent_directory,
                storage=file_storage,
                owner=request.user,
                visibility=visibility
            )
            
            # Generate thumbnail if it's an image
            if file_info['mime_type'].startswith('image/'):
                thumbnail = self._generate_thumbnail(file_storage)
                if thumbnail:
                    file_item.thumbnail = thumbnail
                    file_item.save()
            
            # Add shared users if visibility is 'user'
            if visibility == 'user' and shared_users:
                users = User.objects.filter(id__in=shared_users)
                file_item.shared_users.set(users)
            
            # Add shared groups if visibility is 'group'
            if visibility == 'group' and shared_groups:
                groups = Group.objects.filter(id__in=shared_groups)
                file_item.shared_groups.set(groups)
            
            # Add tags
            for tag_name in tags:
                tag, created = FileTag.objects.get_or_create(name=tag_name)
                FileTagRelation.objects.create(file=file_item, tag=tag)
            
            # Log the upload
            FileAccessLog.objects.create(
                file=file_item,
                user=request.user,
                action='upload',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(FileSystemItemSerializer(file_item, context={'request': request}).data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_thumbnail(self, file_storage):
        """Generate thumbnail for image files"""
        try:
            from PIL import Image
            import io
            
            # Open the image
            image_path = file_storage.get_file_path()
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Generate different thumbnail sizes
                thumbnail_sizes = [
                    ('150x150', 150, 150),
                    ('300x300', 300, 300),
                    ('600x600', 600, 600)
                ]
                
                # Create the first thumbnail (150x150) as default
                size_name, width, height = thumbnail_sizes[0]
                
                # Create thumbnail
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumbnail_path, relative_path_for_db = file_path_manager.get_thumbnail_path(
                    str(file_storage.uuid), size_name, file_storage.extension
                )
                
                # Save thumbnail to filesystem
                img.save(thumbnail_path, 'JPEG', quality=85)
                
                # Get thumbnail file info
                thumb_info = file_path_manager.get_file_info(thumbnail_path)
                
                # Create FileThumbnail record
                thumbnail = FileThumbnail.objects.create(
                    original_file=file_storage,
                    thumbnail_path=relative_path_for_db,
                    thumbnail_size=size_name,
                    width=img.width,
                    height=img.height,
                    file_size=thumb_info['size']
                )
                
                return thumbnail
                
        except ImportError:
            # PIL not available, skip thumbnail generation
            pass
        except Exception as e:
            # Log error but don't fail the upload
            print(f"Thumbnail generation failed: {e}")
        
        return None
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    

    
    def _find_deepest_existing_directory(self, start_parent, path_parts):
        """Find the deepest existing directory in a path without creating anything"""
        current = start_parent
        for part in path_parts:
            if current:
                next_dir = FileSystemItem.objects.filter(
                    name=part,
                    parent=current,
                    item_type='directory'
                ).first()
                if next_dir:
                    current = next_dir
                else:
                    break  # Stop at first missing directory
            else:
                break
        
        return current
    
    def _get_or_create_directory_path_safe(self, relative_path, parent_directory, user, visibility):
        """Get or create directory path with database-level safety
        
        This method handles race conditions by using get_or_create with proper
        error handling. It ensures that multiple concurrent uploads to the same
        directory path will not create duplicate directories.
        """
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError, transaction
        
        if not relative_path:
            return parent_directory
        
        path_parts = [part for part in relative_path.split('/') if part]
        if not path_parts:
            return parent_directory
        
        current_parent = parent_directory
        
        for part in path_parts:
            # Use get_or_create with atomic transaction to prevent race conditions
            with transaction.atomic():
                try:
                    # First try to get existing directory
                    existing_dir = FileSystemItem.objects.get(
                        name=part,
                        parent=current_parent,
                        item_type='directory',
                        owner=user,
                        is_deleted=False
                    )
                except FileSystemItem.DoesNotExist:
                    # Directory doesn't exist, create it
                    try:
                        existing_dir = FileSystemItem.objects.create(
                            name=part,
                            parent=current_parent,
                            item_type='directory',
                            owner=user,
                            visibility=visibility
                        )
                    except ValidationError:
                        # Another thread created it between our check and create
                        # Try to get it again
                        existing_dir = FileSystemItem.objects.get(
                            name=part,
                            parent=current_parent,
                            item_type='directory',
                            owner=user,
                            is_deleted=False
                        )
                    except IntegrityError:
                        # Database constraint violation, try to get existing
                        existing_dir = FileSystemItem.objects.get(
                            name=part,
                            parent=current_parent,
                            item_type='directory',
                            owner=user,
                            is_deleted=False
                        )
            
            current_parent = existing_dir
        
        return current_parent


class FileOperationView(generics.CreateAPIView):
    """Handle file operations (copy, move, delete)"""
    permission_classes = [IsAuthenticated]
    serializer_class = FileOperationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        operation = serializer.validated_data['operation']
        file_ids = serializer.validated_data['file_ids']
        destination_id = serializer.validated_data.get('destination_id')
        
        results = []
        
        try:
            for file_id in file_ids:
                try:
                    file_item = FileSystemItem.objects.with_deleted().get(id=file_id)
                    
                    # Check permissions
                    if operation == 'delete' and not file_item.can_delete(request.user):
                        results.append({
                            'id': file_id,
                            'name': file_item.name,
                            'success': False,
                            'error': 'Permission denied'
                        })
                        continue
                    elif operation in ['copy', 'move'] and not file_item.can_access(request.user, 'read'):
                        results.append({
                            'id': file_id,
                            'name': file_item.name,
                            'success': False,
                            'error': 'Permission denied'
                        })
                        continue
                    
                    # Check if file is already deleted
                    if file_item.is_deleted:
                        results.append({
                            'id': file_id,
                            'name': file_item.name,
                            'success': False,
                            'error': 'Cannot operate on deleted files'
                        })
                        continue
                    
                    # Execute operation
                    if operation == 'delete':
                        success, error = self._soft_delete_file(file_item, request.user)
                    elif operation == 'copy':
                        success, error = self._copy_file(file_item, destination_id, request.user)
                    elif operation == 'move':
                        success, error = self._move_file(file_item, destination_id, request.user)
                    
                    results.append({
                        'id': file_id,
                        'name': file_item.name,
                        'success': success,
                        'error': error
                    })
                    
                except FileSystemItem.DoesNotExist:
                    results.append({
                        'id': file_id,
                        'name': 'Unknown',
                        'success': False,
                        'error': 'File not found'
                    })
            
            return Response({
                'operation': operation,
                'results': results
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _soft_delete_file(self, file_item, user):
        """Soft delete a file (logical deletion)"""
        try:
            file_item.soft_delete(user)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _copy_file(self, file_item, destination_id, user):
        """Copy a file to a new destination"""
        try:
            # Handle root directory (destination_id == 0)
            if destination_id == 0:
                # Copy to root directory
                destination_dir = None
                # Generate unique name for root directory first
                new_name = self._generate_unique_name_root(file_item.name)

            else:
                # Get destination directory
                try:
                    destination_dir = FileSystemItem.objects.get(id=destination_id, item_type='directory')
                except FileSystemItem.DoesNotExist:
                    return False, 'Destination directory not found'
                
                # Check if user can write to destination
                if not destination_dir.can_access(user, 'write'):
                    return False, 'No write permission to destination directory'
                
                # Generate new name
                new_name = self._generate_unique_name(file_item.name, destination_dir)
            
            if file_item.item_type == 'file':
                # For files, we need to copy the physical file and create new storage
                if not file_item.storage:
                    return False, 'File storage not found'
                
                # Copy physical file with new UUID
                source_path = file_item.storage.get_file_path()
                if not os.path.exists(source_path):
                    return False, 'Source file not found'
                
                # Generate new UUID filename and copy file
                new_uuid_filename = file_path_manager.generate_uuid_filename(new_name)
                if destination_dir:
                    new_file_path, new_relative_path = file_path_manager.get_upload_path(
                        new_name, destination_dir.get_relative_path()
                    )
                else:
                    new_file_path, new_relative_path = file_path_manager.get_upload_path(new_name, '')
                
                import shutil
                shutil.copy2(source_path, new_file_path)
                
                # Get file info for new storage
                file_info = file_path_manager.get_file_info(new_file_path)
                
                # Create new FileStorage record
                new_storage = FileStorage.objects.create(
                    original_filename=new_name,
                    file_path=new_relative_path,
                    file_size=file_info['size'],
                    mime_type=file_info['mime_type'],
                    extension=file_info['extension'],
                    checksum=''  # Will be calculated below
                )
                
                # Calculate and update checksum
                new_storage.checksum = new_storage.calculate_checksum()
                new_storage.save()
                
                # Create new database record
                new_file_item = FileSystemItem.objects.create(
                    name=new_name, 
                    item_type=file_item.item_type,
                    parent=destination_dir,
                    storage=new_storage,
                    owner=user,
                    visibility=file_item.visibility
                )
                
                # Copy permissions and sharing
                new_file_item.shared_users.set(file_item.shared_users.all())
                new_file_item.shared_groups.set(file_item.shared_groups.all())
                
            elif file_item.item_type == 'directory':
                # For directories, just create the logical structure
                new_file_item = FileSystemItem.objects.create(
                    name=new_name,
                    item_type=file_item.item_type,
                    parent=destination_dir,
                    owner=user,
                    visibility=file_item.visibility
                )
                
                # Copy permissions and sharing
                new_file_item.shared_users.set(file_item.shared_users.all())
                new_file_item.shared_groups.set(file_item.shared_groups.all())
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _move_file(self, file_item, destination_id, user):
        """Move a file to a new destination"""
        try:
            # Handle root directory (destination_id is 0)
            if destination_id == 0:
                # Move to root directory
                destination_dir = None
                # Generate unique name for root directory first
                new_name = self._generate_unique_name_root(file_item.name)


            else:
                # Get destination directory
                try:
                    destination_dir = FileSystemItem.objects.get(id=destination_id, item_type='directory')
                except FileSystemItem.DoesNotExist:
                    return False, 'Destination directory not found'
                
                # Check if user can write to destination
                if not destination_dir.can_access(user, 'write'):
                    return False, 'No write permission to destination directory'
                
                # Check if user can delete from current location
                if not file_item.can_delete(user):
                    return False, 'No permission to move file from current location'
                
                # Generate new name
                new_name = self._generate_unique_name(file_item.name, destination_dir)
            
            if file_item.item_type == 'file':
                # For files, we only update the database - no physical file movement
                # The physical file stays in its original UUID-based location
                if not file_item.storage:
                    return False, 'File storage not found'
                
                # No physical file movement needed - just update database
                pass
            
            # Update database record
            file_item.name = new_name
            file_item.parent = destination_dir
            file_item.save()
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _generate_unique_name(self, original_name, destination_dir):
        """Generate a unique name in the destination directory"""
        base_name, extension = os.path.splitext(original_name)
        counter = 1
        new_name = original_name
        
        while FileSystemItem.objects.filter(parent=destination_dir, name=new_name).exists():
            if extension:
                new_name = f"{base_name} ({counter}){extension}"
            else:
                new_name = f"{base_name} ({counter})"
            counter += 1
        
        return new_name
    
    def _generate_unique_name_root(self, original_name):
        """Generate a unique name in the root directory"""
        base_name, extension = os.path.splitext(original_name)
        counter = 1
        new_name = original_name
        
        while FileSystemItem.objects.filter(parent__isnull=True, name=new_name).exists():
            if extension:
                new_name = f"{base_name} ({counter}){extension}"
            else:
                new_name = f"{base_name} ({counter})"
            counter += 1
        
        return new_name


class DeletedFilesViewSet(viewsets.ModelViewSet):
    """ViewSet for managing deleted files"""
    permission_classes = [IsAuthenticated]
    serializer_class = DeletedFileSerializer
    
    def get_queryset(self):
        """Only show deleted files"""
        return FileSystemItem.objects.deleted_only()
    
    def list(self, request, *args, **kwargs):
        """List all deleted files"""
        queryset = self.get_queryset()
        
        # Filter by owner if not superuser
        if not request.user.is_superuser:
            queryset = queryset.filter(owner=request.user)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def restore(self, request, *args, **kwargs):
        """Restore deleted files"""
        serializer = FileRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file_ids = serializer.validated_data['file_ids']
        results = []
        
        for file_id in file_ids:
            try:
                file_item = FileSystemItem.objects.deleted_only().get(id=file_id)
                
                # Check permissions
                if not file_item.can_access(request.user, 'write'):
                    results.append({
                        'id': file_id,
                        'name': file_item.name,
                        'success': False,
                        'error': 'Permission denied'
                    })
                    continue
                
                # Restore file
                file_item.restore()
                results.append({
                    'id': file_id,
                    'name': file_item.name,
                    'success': True,
                    'error': None
                })
                
            except FileSystemItem.DoesNotExist:
                results.append({
                    'id': file_id,
                    'name': 'Unknown',
                    'success': False,
                    'error': 'File not found'
                })
        
        return Response({'results': results})
    
    def hard_delete(self, request, *args, **kwargs):
        """Permanently delete files"""
        serializer = FileHardDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file_ids = serializer.validated_data['file_ids']
        results = []
        
        for file_id in file_ids:
            try:
                file_item = FileSystemItem.objects.deleted_only().get(id=file_id)
                
                # Check permissions
                if not file_item.can_delete(request.user):
                    results.append({
                        'id': file_id,
                        'name': file_item.name,
                        'success': False,
                        'error': 'Permission denied'
                    })
                    continue
                
                # Permanently delete file
                file_item.hard_delete()
                results.append({
                    'id': file_id,
                    'name': file_item.name,
                    'success': True,
                    'error': None
                })
                
            except FileSystemItem.DoesNotExist:
                results.append({
                    'id': file_id,
                    'name': 'Unknown',
                    'success': False,
                    'error': 'File not found'
                })
        
        return Response({'results': results})


class FileAccessPermissionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file access permissions"""
    queryset = FileAccessPermission.objects.all()
    serializer_class = FileAccessPermissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FileAccessPermissionCreateSerializer
        return FileAccessPermissionSerializer
    
    def get_queryset(self):
        queryset = FileAccessPermission.objects.all()
        user = self.request.user
        
        # Filter by file if specified
        file_id = self.request.query_params.get('file', None)
        if file_id:
            try:
                file_id = int(file_id)
                queryset = queryset.filter(file_id=file_id)
            except (ValueError, TypeError):
                # Invalid file ID, return empty queryset
                return FileAccessPermission.objects.none()
        
        # Users can only see permissions for files they own or have admin access to
        if not user.is_superuser:
            queryset = queryset.filter(
                Q(file__owner=user) |  # Own files
                Q(file__access_permissions__user=user, file__access_permissions__permission_type='admin')  # Admin access
            ).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        # Set the user who granted the permission
        serializer.save(granted_by=self.request.user)
        
        # Log the permission grant
        FileAccessLog.objects.create(
            file=serializer.instance.file,
            user=self.request.user,
            action='permission_granted',
            ip_address=self._get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FilePermissionRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file permission requests"""
    queryset = FilePermissionRequest.objects.all()
    serializer_class = FilePermissionRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FilePermissionRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FilePermissionRequestReviewSerializer
        return FilePermissionRequestSerializer
    
    def get_queryset(self):
        queryset = FilePermissionRequest.objects.all()
        user = self.request.user
        
        # Users can see their own requests and requests for files they own/admin
        if not user.is_superuser:
            queryset = queryset.filter(
                Q(requester=user) |  # Own requests
                Q(file__owner=user) |  # Own files
                Q(file__access_permissions__user=user, file__access_permissions__permission_type='admin')  # Admin access
            ).distinct()
        
        return queryset


class FileTagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file tags"""
    queryset = FileTag.objects.all()
    serializer_class = FileTagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = FileTagPagination


class FileTagRelationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file-tag relationships"""
    queryset = FileTagRelation.objects.all()
    serializer_class = FileTagRelationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class FileAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing file access logs"""
    queryset = FileAccessLog.objects.all()
    serializer_class = FileAccessLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FileAccessLogPagination
    
    def get_queryset(self):
        queryset = FileAccessLog.objects.all()
        user = self.request.user
        
        # Users can only see logs for files they own or have admin access to
        if not user.is_superuser:
            queryset = queryset.filter(
                Q(file__owner=user) |  # Own files
                Q(file__access_permissions__user=user, file__access_permissions__permission_type='admin')  # Admin access
            ).distinct()
        
        # Filter by file
        file_id = self.request.query_params.get('file', None)
        if file_id:
            queryset = queryset.filter(file_id=file_id)
        
        # Filter by user
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action
        action = self.request.query_params.get('action', None)
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        end_date = self.request.query_params.get('end_date', None)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset


class UserSearchView(generics.ListAPIView):
    """View for searching users for file sharing"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.filter(is_active=True)
        query = self.request.query_params.get('q', '')
        
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        
        # Limit results for performance
        return queryset[:50]


class GroupSearchView(generics.ListAPIView):
    """View for searching groups for file sharing"""
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Group.objects.all()
        query = self.request.query_params.get('q', '')
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        # Limit results for performance
        return queryset[:50]
