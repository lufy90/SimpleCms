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
    FileAccessPermission, FilePermissionRequest
)
from .serializers import (
    FileSystemItemSerializer, FileSystemItemCreateSerializer, FileSystemItemUpdateSerializer,
    FileTagSerializer, FileTagRelationSerializer, FileAccessLogSerializer,
    DirectoryTreeSerializer, FileSearchSerializer, FileUploadSerializer, FileOperationSerializer,
    FileAccessPermissionSerializer, FileAccessPermissionCreateSerializer,
    FileVisibilityUpdateSerializer, FilePermissionRequestSerializer,
    FilePermissionRequestCreateSerializer, FilePermissionRequestReviewSerializer
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
        
        if not os.path.exists(file_item.path):
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
            response = FileResponse(open(file_item.path, 'rb'))
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
    def tree(self, request):
        """Get directory tree structure"""
        root_path = request.query_params.get('root', '/')
        
        try:
            tree_data = self._build_directory_tree(root_path, request.user)
            return Response(tree_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
                'relative_path': file_item.get_relative_path()
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
                
                parent_info = {
                    'id': parent_item.id,
                    'name': parent_item.name,
                    'relative_path': parent_item.get_relative_path()
                }
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

    def _build_directory_tree(self, root_path, user):
        """Build directory tree structure with permission filtering"""
        if not os.path.exists(root_path):
            raise ValueError(f"Path {root_path} does not exist")
        
        def build_tree(path):
            try:
                items = []
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        items.append({
                            'name': item,
                            'path': item_path,
                            'item_type': 'directory',
                            'children': build_tree(item_path)
                        })
                    else:
                        # Try to get existing database item
                        try:
                            db_item = FileSystemItem.objects.get(path=item_path)
                            
                            # Check if user can access this file
                            if user.is_authenticated and not user.is_superuser:
                                if not db_item.can_access(user, 'read'):
                                    continue  # Skip files user can't access
                            
                            items.append({
                                'id': db_item.id,
                                'name': item,
                                'path': item_path,
                                'item_type': 'file',
                                'size': db_item.size,
                                'mime_type': db_item.mime_type,
                                'extension': db_item.extension,
                                'last_modified': db_item.last_modified,
                                'visibility': db_item.visibility
                            })
                        except FileSystemItem.DoesNotExist:
                            items.append({
                                'name': item,
                                'path': item_path,
                                'item_type': 'file'
                            })
                return items
            except PermissionError:
                return []
        
        return build_tree(root_path)
    
    def _scan_directory_recursive(self, directory_path, user):
        """Recursively scan directory and add items to database"""
        scanned_count = 0
        
        for root, dirs, files in os.walk(directory_path):
            # Add directories
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not FileSystemItem.objects.filter(path=dir_path).exists():
                    FileSystemItem.objects.create(
                        name=dir_name,
                        path=dir_path,
                        item_type='directory',
                        owner=user
                    )
                    scanned_count += 1
            
            # Add files
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if not FileSystemItem.objects.filter(path=file_path).exists():
                    file_item = FileSystemItem.objects.create(
                        name=file_name,
                        path=file_path,
                        item_type='file',
                        owner=user
                    )
                    
                    try:
                        file_item.update_from_filesystem()
                    except Exception as e:
                        print(f'Error updating file metadata: {e}')
                    
                    scanned_count += 1
        
        return scanned_count
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FileUploadView(generics.CreateAPIView):
    """Handle file uploads"""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    serializer_class = FileUploadSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        relative_path = serializer.validated_data.get('path', '')  # Changed from destination_path to path
        tags = serializer.validated_data.get('tags', [])
        visibility = serializer.validated_data.get('visibility', 'private')
        shared_users = serializer.validated_data.get('shared_users', [])
        shared_groups = serializer.validated_data.get('shared_groups', [])
        
        try:
            # Get safe upload path using the path manager
            file_path = file_path_manager.get_upload_path(uploaded_file.name, relative_path)
            
            # Save file to destination
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Create database record with relative path for display
            file_item = FileSystemItem.objects.create(
                name=uploaded_file.name,
                path=file_path,  # Absolute path for internal use
                relative_path=file_path_manager.get_relative_path(file_path),  # Relative path for display
                item_type='file',
                owner=request.user,
                visibility=visibility
            )
            
            # Add shared users if visibility is 'user'
            if visibility == 'user' and shared_users:
                users = User.objects.filter(id__in=shared_users)  # Fixed: was Group.objects
                file_item.shared_users.set(users)
            
            # Add shared groups if visibility is 'group'
            if visibility == 'group' and shared_groups:
                groups = Group.objects.filter(id__in=shared_groups)
                file_item.shared_groups.set(groups)
            
            # Update file metadata
            file_item.update_from_filesystem()
            
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
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FileOperationView(generics.CreateAPIView):
    """Handle file operations (copy, move, delete)"""
    permission_classes = [IsAuthenticated]
    serializer_class = FileOperationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        operation = serializer.validated_data['operation']
        source_paths = serializer.validated_data['source_paths']
        destination_path = serializer.validated_data.get('destination_path')
        
        results = []
        
        try:
            for source_path in source_paths:
                if not os.path.exists(source_path):
                    results.append({
                        'path': source_path,
                        'success': False,
                        'error': 'Source path does not exist'
                    })
                    continue
                
                # Check if user has permission to operate on this file
                try:
                    file_item = FileSystemItem.objects.get(path=source_path)
                    if operation == 'delete' and not file_item.can_delete(request.user):
                        results.append({
                            'path': source_path,
                            'success': False,
                            'error': 'Permission denied'
                        })
                        continue
                    elif operation in ['copy', 'move'] and not file_item.can_access(request.user, 'read'):
                        results.append({
                            'path': source_path,
                            'success': False,
                            'error': 'Permission denied'
                        })
                        continue
                except FileSystemItem.DoesNotExist:
                    # File not in database, proceed with operation
                    pass
                
                if operation == 'delete':
                    success, error = self._delete_file(source_path)
                elif operation == 'copy':
                    success, error = self._copy_file(source_path, destination_path)
                elif operation == 'move':
                    success, error = self._move_file(source_path, destination_path)
                
                results.append({
                    'path': source_path,
                    'success': success,
                    'error': error
                })
            
            return Response({
                'operation': operation,
                'results': results
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _delete_file(self, file_path):
        """Delete a file or directory"""
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            
            # Remove from database
            FileSystemItem.objects.filter(path=file_path).delete()
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _copy_file(self, source_path, destination_path):
        """Copy a file or directory"""
        try:
            if os.path.isfile(source_path):
                shutil.copy2(source_path, destination_path)
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, destination_path)
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _move_file(self, source_path, destination_path):
        """Move a file or directory"""
        try:
            shutil.move(source_path, destination_path)
            
            # Update database record
            try:
                file_item = FileSystemItem.objects.get(path=source_path)
                file_item.path = destination_path
                file_item.save()
            except FileSystemItem.DoesNotExist:
                pass
            
            return True, None
        except Exception as e:
            return False, str(e)


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
