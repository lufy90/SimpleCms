from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse, HttpResponse, StreamingHttpResponse

from django.contrib.auth.models import Group, User
import os
import shutil
import time

from .models import (
    FileItem, FileTag, FileTagRelation, FileAccessLog, 
    FileAccessPermission, FilePermissionRequest, FileStorage, FileThumbnail
)
from .utils import FilePathManager
from .serializers import (
    FileItemSerializer, FileItemCreateSerializer, FileItemUpdateSerializer,
    FileTagSerializer, FileTagRelationSerializer, FileAccessLogSerializer,
    FileUploadSerializer, FileOperationSerializer,
    FileAccessPermissionSerializer, FileAccessPermissionCreateSerializer,
    FileVisibilityUpdateSerializer, FilePermissionRequestSerializer,
    FilePermissionRequestCreateSerializer, FilePermissionRequestReviewSerializer,
    DeletedFileSerializer, FileRestoreSerializer, FileHardDeleteSerializer,
    UserSerializer, GroupSerializer, UserCreateUpdateSerializer, GroupCreateUpdateSerializer,
    FileContentUpdateSerializer
)
from .pagination import (
    FileItemPagination, FileAccessLogPagination, FileTagPagination
)
from .utils import file_path_manager, determine_file_sharing


class FileItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file system items"""
    queryset = FileItem.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = FileItemPagination
    
    def get_permissions(self):
        """
        Override permissions for specific actions
        """
        if self.action == 'stream':
            # For streaming, we handle authentication manually in the method
            return []
        return super().get_permissions()
    
    def get_object(self):
        """
        Override get_object for stream action to bypass permission filtering
        """
        if self.action == 'stream':
            # For streaming, get the object directly without permission filtering
            # Authentication will be handled in the stream method
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            lookup_value = self.kwargs[lookup_url_kwarg]
            return FileItem.objects.get(**{self.lookup_field: lookup_value})
        return super().get_object()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FileItemCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FileItemUpdateSerializer
        return FileItemSerializer
    
    def get_queryset(self):
        queryset = FileItem.objects.all()
        user = self.request.user
        
        # Ensure user is authenticated (this should be handled by permission_classes, but double-check)
        if not user.is_authenticated:
            return FileItem.objects.none()
        
        # Filter based on user permissions
        if not user.is_superuser:
            # User can see: their own files, public files, files shared with them, and files shared with their groups
            user_groups = user.groups.all()
            queryset = queryset.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups) |  # Group shared files
                Q(access_permissions__user=user, access_permissions__is_active=True) |  # Explicit user permissions
                Q(access_permissions__group__in=user_groups, access_permissions__is_active=True)  # Explicit group permissions
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
            
            # Set appropriate content type
            mime_type = file_item.storage.mime_type or 'application/octet-stream'
            response['Content-Type'] = mime_type
            
            # Check if file should be displayed inline (browser preview) or downloaded
            browser_supported_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml', 'image/bmp',
                'application/pdf', 'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json',
                'text/xml', 'application/xml', 'text/csv',
                'audio/mpeg', 'audio/wav', 'audio/ogg', 'video/mp4', 'video/webm', 'video/ogg'
            ]
            
            # Check if user wants to force download (via query parameter)
            force_download = request.GET.get('download', '').lower() == 'true'
            
            if mime_type in browser_supported_types and not force_download:
                # Display in browser
                response['Content-Disposition'] = f'inline; filename="{file_item.name}"'
            else:
                # Force download
                response['Content-Disposition'] = f'attachment; filename="{file_item.name}"'
            
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def stream(self, request, pk=None):
        """
        Stream a file with HTTP Range support for video/audio playback
        
        This endpoint provides efficient streaming of large files with support for:
        - HTTP Range requests for partial content (seek/scrub in video players)
        - Chunked transfer encoding for memory-efficient streaming
        - Proper caching headers for better performance
        - Media-specific headers for video/audio playback
        
        URL: /api/files/{id}/stream/
        Method: GET
        Headers: 
            - Range: bytes=start-end (optional, for partial content)
        Response: 
            - 200: Full file stream
            - 206: Partial content (when Range header provided)
            - 416: Range Not Satisfiable (invalid range)
            - 403: Access denied
            - 404: File not found
        
        Example usage:
        - Full file: GET /api/files/123/stream/
        - Partial content: GET /api/files/123/stream/ with Range: bytes=0-1023
        - Video seeking: GET /api/files/123/stream/ with Range: bytes=1048576-2097151
        """
        file_item = self.get_object()
        
        if file_item.item_type != 'file':
            return Response({'error': 'Item is not a file'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check authentication - either via user session or token query parameter
        user = request.user
        token = request.GET.get('token')
        
        print(f"Stream authentication - User: {user}, Token: {token[:10] if token else 'None'}...")
        
        if token:
            # Authenticate using JWT token from query parameter
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                
                # Validate and decode the JWT token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                user = User.objects.get(id=user_id)
                print(f"JWT token authentication successful for user: {user}")
            except (InvalidToken, TokenError, User.DoesNotExist) as e:
                print(f"JWT token authentication failed: {e}")
                return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            print("No token provided, using session authentication")
        
        if not file_item.can_access(user, 'read'):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if not file_item.storage:
            return Response({'error': 'File storage not found'}, status=status.HTTP_404_NOT_FOUND)
        
        file_path = file_item.storage.get_file_path()
        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Log the stream access
        FileAccessLog.objects.create(
            file=file_item,
            user=user if user.is_authenticated else None,
            action='stream',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            file_size = os.path.getsize(file_path)
            mime_type = file_item.storage.mime_type or 'application/octet-stream'
            
            # Parse Range header
            range_header = request.META.get('HTTP_RANGE')
            if range_header:
                # Parse range header (e.g., "bytes=0-1023")
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1
                
                # Ensure end doesn't exceed file size
                end = min(end, file_size - 1)
                
                # Ensure start is not greater than end
                if start > end:
                    return HttpResponse('Requested Range Not Satisfiable', status=416)
                
                content_length = end - start + 1
                
                def file_generator():
                    with open(file_path, 'rb') as f:
                        f.seek(start)
                        remaining = content_length
                        while remaining > 0:
                            chunk_size = min(8192, remaining)  # 8KB chunks
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                
                response = StreamingHttpResponse(
                    file_generator(),
                    status=206,  # Partial Content
                    content_type=mime_type
                )
                
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Content-Length'] = str(content_length)
                response['Accept-Ranges'] = 'bytes'
                response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
                
            else:
                # No range header - stream entire file
                def file_generator():
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)  # 8KB chunks
                            if not chunk:
                                break
                            yield chunk
                
                response = StreamingHttpResponse(
                    file_generator(),
                    content_type=mime_type
                )
                response['Content-Length'] = str(file_size)
                response['Accept-Ranges'] = 'bytes'
                response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            
            # Set appropriate headers for media files
            if mime_type.startswith('video/') or mime_type.startswith('audio/'):
                response['Content-Disposition'] = f'inline; filename="{file_item.name}"'
                # Add headers to help with media playback
                response['X-Content-Type-Options'] = 'nosniff'
            else:
                response['Content-Disposition'] = f'inline; filename="{file_item.name}"'
            
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
        
        return Response(FileItemSerializer(file_item, context={'request': request}).data)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_visibility(self, request, pk=None):
        """Update file visibility and sharing"""
        file_item = self.get_object()
        
        if not file_item.can_write(request.user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FileVisibilityUpdateSerializer(file_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Update visibility to reflect current sharing status
            file_item.update_visibility_from_sharing()
            
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
            
            return Response(FileItemSerializer(file_item, context={'request': request}).data)
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
        """Search for files and directories - supports both global and node-specific search"""
        query = request.query_params.get('q', '')
        node_id = request.query_params.get('node_id', None)
        recursive = request.query_params.get('recursive', 'true').lower() == 'true'
        
        if not query:
            return Response({'error': 'Search query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_time = time.time()
        
        # Get the target node if specified
        target_node = None
        if node_id:
            try:
                target_node = FileItem.objects.get(id=node_id, item_type='directory')
            except FileItem.DoesNotExist:
                return Response({'error': 'Node not found or is not a directory'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user can access the target node
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            if not target_node.can_access(user, 'read'):
                return Response({'error': 'Access denied to target node'}, status=status.HTTP_403_FORBIDDEN)
        
        # Build search queryset
        if target_node:
            # Node-specific search
            if recursive:
                # Get all descendant nodes (files and directories) under the target node
                descendant_ids = self._get_descendant_ids(target_node)
                queryset = FileItem.objects.filter(
                    id__in=descendant_ids,
                    name__icontains=query
                )
            else:
                # Search only direct children of the target node
                queryset = FileItem.objects.filter(
                    parent=target_node,
                    name__icontains=query
                )
        else:
            # Global search
            queryset = FileItem.objects.filter(
                Q(name__icontains=query)
            )
        
        # Apply permission filtering
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_superuser:
            user_groups = user.groups.all()
            queryset = queryset.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups) |  # Group shared files
                Q(access_permissions__user=user, access_permissions__is_active=True) |  # Explicit user permissions
                Q(access_permissions__group__in=user_groups, access_permissions__is_active=True)  # Explicit group permissions
            ).distinct()
        
        # Apply additional filters
        item_type = request.query_params.get('type', None)
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Limit results
        limit = int(request.query_params.get('limit', 100))
        queryset = queryset[:limit]
        
        search_time = time.time() - start_time
        
        serializer = FileItemSerializer(queryset, many=True, context={'request': request})
        
        response_data = {
            'query': query,
            'results': serializer.data,
            'total_count': queryset.count(),
            'search_time': search_time
        }
        
        # Add node-specific information if searching within a node
        if target_node:
            response_data.update({
                'node_id': int(node_id),
                'node_name': target_node.name,
                'recursive': recursive
            })
        
        return Response(response_data)
    
    def _get_descendant_ids(self, directory):
        """Get all descendant node IDs under a directory recursively"""
        descendant_ids = []
        
        def _traverse(current_dir):
            # Get direct children
            children = FileItem.objects.filter(parent=current_dir, is_deleted=False)
            for child in children:
                descendant_ids.append(child.id)
                # If it's a directory, traverse its children too
                if child.item_type == 'directory':
                    _traverse(child)
        
        _traverse(directory)
        return descendant_ids

    
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
                    parent_directory = FileItem.objects.get(id=parent_id, item_type='directory')
                    # Check if user can write to parent directory
                    if not parent_directory.can_write(request.user):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileItem.DoesNotExist:
                    return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if directory already exists in database
            if parent_directory:
                if FileItem.objects.filter(parent=parent_directory, name=name, item_type='directory').exists():
                    return Response({'error': 'Directory already exists'}, status=status.HTTP_409_CONFLICT)
            else:
                if FileItem.objects.filter(parent__isnull=True, name=name, item_type='directory').exists():
                    return Response({'error': 'Directory already exists'}, status=status.HTTP_409_CONFLICT)
            
            # Determine directory visibility and sharing based on parent directory
            dir_visibility, dir_shared_users, dir_shared_groups = determine_file_sharing(
                parent_directory, visibility, [], [], request.user
            )
            
            # Create database record (directories don't need physical storage)
            directory_item = FileItem.objects.create(
                name=name,
                item_type='directory',
                parent=parent_directory,
                owner=request.user,
                visibility=dir_visibility
            )
            
            # Add shared users if visibility is 'user'
            if dir_visibility == 'user' and dir_shared_users:
                users = User.objects.filter(id__in=dir_shared_users)
                directory_item.shared_users.set(users)
            
            # Add shared groups if visibility is 'group'
            if dir_visibility == 'group' and dir_shared_groups:
                groups = Group.objects.filter(id__in=dir_shared_groups)
                directory_item.shared_groups.set(groups)
            
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
                'directory': FileItemSerializer(directory_item, context={'request': request}).data
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
        children = FileItem.objects.filter(
            parent=file_item,
            is_active=True
        ).order_by('item_type', 'name')  # Directories first, then files, alphabetically
        
        # Apply permission filtering for children
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_superuser:
            user_groups = user.groups.all()
            children = children.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups) |  # Group shared files
                Q(access_permissions__user=user, access_permissions__is_active=True) |  # Explicit user permissions
                Q(access_permissions__group__in=user_groups, access_permissions__is_active=True)  # Explicit group permissions
            ).distinct()
        
        # Serialize children with full context
        serializer = FileItemSerializer(children, many=True, context={'request': request})
        
        return Response({
            'parent': {
                'id': file_item.id,
                'name': file_item.name,
                'item_type': file_item.item_type
            },
            'children': serializer.data,
            'total_count': len(serializer.data)
        })

    def _get_orphaned_shared_items(self, user):
        """Get items that user has access to but whose parents they don't have access to
        
        This handles the case where a user is shared with a deep directory
        but doesn't have access to the parent directories.
        """
        if user.is_superuser:
            return FileItem.objects.none()
        
        user_groups = user.groups.all()
        
        # Get all items the user has access to
        accessible_items = FileItem.objects.filter(
            Q(owner=user) |  # Own files
            Q(visibility='public') |  # Public files
            Q(visibility='user', shared_users=user) |  # User shared files
            Q(visibility='group', shared_groups__in=user_groups) |  # Group shared files
            Q(access_permissions__user=user, access_permissions__is_active=True) |  # Explicit user permissions
            Q(access_permissions__group__in=user_groups, access_permissions__is_active=True)  # Explicit group permissions
        ).distinct()
        
        # Filter out items that are already at root level
        non_root_items = accessible_items.filter(parent__isnull=False)
        
        # Find items whose parents the user cannot access
        orphaned_items = []
        for item in non_root_items:
            if item.parent and not item.parent.can_access(user, 'read'):
                orphaned_items.append(item)
        
        return FileItem.objects.filter(id__in=[item.id for item in orphaned_items])

    @action(detail=False, methods=['get'])
    def list_children(self, request):
        """Get children by parent ID from query params, or list top-level files if no parent given"""
        parent_id = request.query_params.get('parent_id', None)
        
        if parent_id:
            # Get children of specific parent
            try:
                parent_item = FileItem.objects.get(id=parent_id)
                
                # Check if it's a directory
                if parent_item.item_type != 'directory':
                    return Response({'error': 'Parent item is not a directory'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if user can access this directory
                if not parent_item.can_access(request.user, 'read'):
                    return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
                
                # Get direct children (not recursive)
                children = FileItem.objects.filter(
                    parent=parent_item
                )  # Will be ordered later
                
                # Use full serializer for parent to include parents field
                parent_serializer = FileItemSerializer(parent_item, context={'request': request})
                parent_info = parent_serializer.data
            except FileItem.DoesNotExist:
                return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # List top-level files (no parent)
            children = FileItem.objects.filter(
                parent__isnull=True
            )  # Will be ordered later
            
            parent_info = None
        
        # Apply permission filtering for children
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_superuser:
            user_groups = user.groups.all()
            children = children.filter(
                Q(owner=user) |  # Own files
                Q(visibility='public') |  # Public files
                Q(visibility='user', shared_users=user) |  # User shared files
                Q(visibility='group', shared_groups__in=user_groups) |  # Group shared files
                Q(access_permissions__user=user, access_permissions__is_active=True) |  # Explicit user permissions
                Q(access_permissions__group__in=user_groups, access_permissions__is_active=True)  # Explicit group permissions
            ).distinct()
        
        # If listing root directory, also include orphaned shared items
        if parent_id is None:
            orphaned_items = self._get_orphaned_shared_items(user)
            # Get IDs from both querysets and combine them
            children_ids = list(children.values_list('id', flat=True))
            orphaned_ids = list(orphaned_items.values_list('id', flat=True))
            all_ids = children_ids + orphaned_ids
            
            # Get all items with the combined IDs and order them
            all_items = FileItem.objects.filter(id__in=all_ids).order_by('item_type', 'name')
        else:
            # For specific parent directories, just apply ordering
            all_items = children.order_by('item_type', 'name')
        
        # Serialize children with full context
        serializer = FileItemSerializer(all_items, many=True, context={'request': request})
        
        response_data = {
            'children': serializer.data,
            'total_count': len(serializer.data)
        }
        
        if parent_info:
            response_data['parent'] = parent_info
        else:
            response_data['parent'] = None
            response_data['message'] = 'Listing top-level files and directories'
            # Add info about orphaned items if any
            if parent_id is None:
                orphaned_count = len(self._get_orphaned_shared_items(user))
                if orphaned_count > 0:
                    response_data['orphaned_shared_count'] = orphaned_count
                    response_data['message'] += f' (including {orphaned_count} shared items from inaccessible parent directories)'
        
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
                                current_parent = FileItem.objects.filter(
                                    parent=current_parent, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                            else:
                                current_parent = FileItem.objects.filter(
                                    parent__isnull=True, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                        parent_dir = current_parent
                    
                    if not FileItem.objects.filter(parent=parent_dir, name=dir_name, item_type='directory').exists():
                        FileItem.objects.create(
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
                                current_parent = FileItem.objects.filter(
                                    parent=current_parent, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                            else:
                                current_parent = FileItem.objects.filter(
                                    parent__isnull=True, 
                                    name=part, 
                                    item_type='directory'
                                ).first()
                        parent_dir = current_parent
                    
                    # Check if file already exists by name and parent
                    if not FileItem.objects.filter(parent=parent_dir, name=file_name, item_type='file').exists():
                        # Create FileStorage record
                        file_info = file_path_manager.get_file_info(file_path)
                        if file_info:
                            # Generate UUID filename and copy file
                            new_uuid_filename = file_path_manager.generate_uuid_filename(file_name)
                            new_file_path, new_relative_path = file_path_manager.get_upload_path(file_name, rel_path)
                            
                            # Copy file to new location
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
                            
                            # Create FileItem record
                            file_item = FileItem.objects.create(
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

                    print(f"Permission filter: {permission_filter}")
                    
                    # Find and revoke permissions
                    permissions_to_revoke = FileAccessPermission.objects.filter(**permission_filter)
                    print(f"Permissions to revoke: {permissions_to_revoke}")
                    
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
    
    @action(detail=True, methods=['put', 'patch'], parser_classes=[MultiPartParser, FormParser])
    def update_content(self, request, pk=None):
        """Update file content"""
        file_item = self.get_object()
        
        # Check if it's a file (not directory)
        if file_item.item_type != 'file':
            return Response({'error': 'Can only update content of files, not directories'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check write permissions
        if not file_item.can_write(request.user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Use the FileContentUpdateSerializer
        serializer = FileContentUpdateSerializer(file_item, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                updated_file = serializer.save()
                
                # Log the content update
                FileAccessLog.objects.create(
                    file=updated_file,
                    user=request.user,
                    action='edit',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Return the updated file data
                return Response(FileItemSerializer(updated_file, context={'request': request}).data)
                
            except Exception as e:
                return Response({'error': f'Failed to update file content: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def thumbnail(self, request, pk=None):
        """Serve thumbnail for a file item"""
        file_item = self.get_object()
        
        if file_item.item_type != 'file':
            return Response({'error': 'Thumbnails are only available for files'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_item.thumbnail:
            return Response({'error': 'No thumbnail available for this file'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            thumbnail_path = file_item.thumbnail.get_thumbnail_path()
            if not os.path.exists(thumbnail_path):
                return Response({'error': 'Thumbnail file not found'}, status=status.HTTP_404_NOT_FOUND)
            
            return FileResponse(
                open(thumbnail_path, 'rb'),
                content_type='image/jpeg',
                filename=f"{file_item.name}_thumbnail.jpg"
            )
        except Exception as e:
            return Response({'error': f'Failed to serve thumbnail: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
                    parent_directory = FileItem.objects.get(id=parent_id, item_type='directory')
                    # Check if user can write to parent directory
                    if not parent_directory.can_write(request.user):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileItem.DoesNotExist:
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
            
            # Determine file visibility and sharing based on parent directory
            file_visibility, file_shared_users, file_shared_groups = determine_file_sharing(
                final_parent_directory, visibility, shared_users, shared_groups, request.user
            )
            
            # Create FileItem record
            file_item = FileItem.objects.create(
                name=uploaded_file.name,
                item_type='file',
                parent=final_parent_directory,
                storage=file_storage,
                owner=request.user,
                visibility=file_visibility
            )
            
            # Generate thumbnail if it's an image
            if file_info['mime_type'].startswith('image/'):
                thumbnail = self._generate_thumbnail(file_storage)
                if thumbnail:
                    file_item.thumbnail = thumbnail
                    file_item.save()
            
            # Add shared users if visibility is 'user'
            if file_visibility == 'user' and file_shared_users:
                users = User.objects.filter(id__in=file_shared_users)
                file_item.shared_users.set(users)
            
            # Add shared groups if visibility is 'group'
            if file_visibility == 'group' and file_shared_groups:
                groups = Group.objects.filter(id__in=file_shared_groups)
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
            
            return Response(FileItemSerializer(file_item, context={'request': request}).data, status=status.HTTP_201_CREATED)
            
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
                next_dir = FileItem.objects.filter(
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
                    existing_dir = FileItem.objects.get(
                        name=part,
                        parent=current_parent,
                        item_type='directory',
                        owner=user,
                        is_deleted=False
                    )
                except FileItem.DoesNotExist:
                    # Directory doesn't exist, create it
                    try:
                        existing_dir = FileItem.objects.create(
                            name=part,
                            parent=current_parent,
                            item_type='directory',
                            owner=user,
                            visibility=visibility
                        )
                    except ValidationError:
                        # Another thread created it between our check and create
                        # Try to get it again
                        existing_dir = FileItem.objects.get(
                            name=part,
                            parent=current_parent,
                            item_type='directory',
                            owner=user,
                            is_deleted=False
                        )
                    except IntegrityError:
                        # Database constraint violation, try to get existing
                        existing_dir = FileItem.objects.get(
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
                    file_item = FileItem.objects.with_deleted().get(id=file_id)
                    
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
                    
                except FileItem.DoesNotExist:
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
                    destination_dir = FileItem.objects.get(id=destination_id, item_type='directory')
                except FileItem.DoesNotExist:
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
                new_file_item = FileItem.objects.create(
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
                new_file_item = FileItem.objects.create(
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
                    destination_dir = FileItem.objects.get(id=destination_id, item_type='directory')
                except FileItem.DoesNotExist:
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
        
        while FileItem.objects.filter(parent=destination_dir, name=new_name).exists():
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
        
        while FileItem.objects.filter(parent__isnull=True, name=new_name).exists():
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
        return FileItem.objects.deleted_only()
    
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
                file_item = FileItem.objects.deleted_only().get(id=file_id)
                
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
                
            except FileItem.DoesNotExist:
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
                file_item = FileItem.objects.deleted_only().get(id=file_id)
                
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
                
            except FileItem.DoesNotExist:
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
        # Only show active permissions by default, unless include_inactive is requested
        include_inactive = self.request.query_params.get('include_inactive', 'false').lower() == 'true'
        
        if include_inactive:
            queryset = FileAccessPermission.objects.all()
        else:
            queryset = FileAccessPermission.objects.filter(is_active=True)
        
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
    permission_classes = [IsAuthenticated]
    pagination_class = FileTagPagination


class FileTagRelationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file-tag relationships"""
    queryset = FileTagRelation.objects.all()
    serializer_class = FileTagRelationSerializer
    permission_classes = [IsAuthenticated]


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


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        # Only superusers can manage users
        if not self.request.user.is_superuser:
            return User.objects.none()
        return User.objects.all()
    
    def create(self, request, *args, **kwargs):
        """Create a new user"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create user with password
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],  # Required for creation
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', '')
        )
        
        # Add to groups if specified
        if 'groups' in serializer.validated_data:
            user.groups.set(serializer.validated_data['groups'])
        
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update a user (partial update)"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Update user fields only if provided
        if 'username' in serializer.validated_data:
            user.username = serializer.validated_data['username']
        if 'email' in serializer.validated_data:
            user.email = serializer.validated_data['email']
        if 'first_name' in serializer.validated_data:
            user.first_name = serializer.validated_data['first_name']
        if 'last_name' in serializer.validated_data:
            user.last_name = serializer.validated_data['last_name']
        if 'password' in serializer.validated_data and serializer.validated_data['password']:
            user.set_password(serializer.validated_data['password'])
        
        user.save()
        
        # Update groups if specified
        if 'groups' in serializer.validated_data:
            user.groups.set(serializer.validated_data['groups'])
        
        return Response(UserSerializer(user).data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a user"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        # Prevent deleting the current user
        if user == request.user:
            return Response({'error': 'Cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing groups"""
    queryset = Group.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return GroupCreateUpdateSerializer
        return GroupSerializer
    
    def get_queryset(self):
        # Only superusers can manage groups
        if not self.request.user.is_superuser:
            return Group.objects.none()
        return Group.objects.all()
    
    def create(self, request, *args, **kwargs):
        """Create a new group"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group = Group.objects.create(
            name=serializer.validated_data['name']
        )
        
        # Add members if specified
        if 'members' in serializer.validated_data:
            group.user_set.set(serializer.validated_data['members'])
        
        return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update a group"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        group = self.get_object()
        serializer = self.get_serializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Update group fields
        if 'name' in serializer.validated_data:
            group.name = serializer.validated_data['name']
        
        group.save()
        
        # Update members if specified
        if 'members' in serializer.validated_data:
            group.user_set.set(serializer.validated_data['members'])
        
        return Response(GroupSerializer(group).data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a group"""
        if not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        group = self.get_object()
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileCreationView(generics.CreateAPIView):
    """Handle creation of new files (text files and office documents)"""
    permission_classes = [IsAuthenticated]
    
    def create_text_file(self, request):
        """Create a new text file"""
        try:
            name = request.data.get('name', '')
            content = request.data.get('content', '')
            parent_id = request.data.get('parent_id')
            visibility = request.data.get('visibility', 'private')
            
            if not name:
                return Response({'error': 'File name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Ensure .txt extension
            if not name.endswith('.txt'):
                name += '.txt'
            
            # Get parent directory
            parent_directory = None
            if parent_id:
                try:
                    parent_directory = FileItem.objects.get(id=parent_id, item_type='directory')
                    if not parent_directory.can_access(request.user, 'write'):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileItem.DoesNotExist:
                    return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Use the same pattern as file upload - get UUID-based path
            file_path_manager = FilePathManager()
            file_path, relative_path_for_db = file_path_manager.get_upload_path(name, '')
            
            # Extract just the UUID filename for storage in FileStorage.file_path
            uuid_filename = os.path.basename(file_path)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get file information
            file_info = file_path_manager.get_file_info(file_path)
            
            # Create FileStorage record
            file_storage = FileStorage.objects.create(
                original_filename=name,
                file_path=uuid_filename,  # Store only the UUID filename, not the full path
                file_size=file_info['size'],
                mime_type=file_info['mime_type'],
                extension=file_info['extension'],
                checksum=file_info.get('checksum', '')
            )
            
            # Calculate and update checksum
            file_storage.checksum = file_storage.calculate_checksum()
            file_storage.save()
            
            # Create FileItem record
            file_item = FileItem.objects.create(
                name=name,
                item_type='file',
                parent=parent_directory,
                storage=file_storage,
                owner=request.user,
                visibility=visibility
            )
            
            return Response({
                'message': 'Text file created successfully',
                'file': FileItemSerializer(file_item, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': f'Failed to create text file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create_office_document(self, request):
        """Create a new office document"""
        try:
            name = request.data.get('name', '')
            document_type = request.data.get('document_type', 'docx')  # docx, xlsx, pptx
            parent_id = request.data.get('parent_id')
            visibility = request.data.get('visibility', 'private')
            
            if not name:
                return Response({'error': 'File name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Map document types to extensions and templates
            document_templates = {
                'docx': {
                    'extension': '.docx',
                    'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'template_path': None  # We'll create empty documents
                },
                'xlsx': {
                    'extension': '.xlsx',
                    'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'template_path': None
                },
                'pptx': {
                    'extension': '.pptx',
                    'mime_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'template_path': None
                }
            }
            
            if document_type not in document_templates:
                return Response({'error': 'Invalid document type'}, status=status.HTTP_400_BAD_REQUEST)
            
            template = document_templates[document_type]
            
            # Ensure correct extension
            if not name.endswith(template['extension']):
                name += template['extension']
            
            # Get parent directory
            parent_directory = None
            if parent_id:
                try:
                    parent_directory = FileItem.objects.get(id=parent_id, item_type='directory')
                    if not parent_directory.can_access(request.user, 'write'):
                        return Response({'error': 'Access denied to parent directory'}, status=status.HTTP_403_FORBIDDEN)
                except FileItem.DoesNotExist:
                    return Response({'error': 'Parent directory not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Use the same pattern as file upload - get UUID-based path
            file_path_manager = FilePathManager()
            file_path, relative_path_for_db = file_path_manager.get_upload_path(name, '')
            
            # Extract just the UUID filename for storage in FileStorage.file_path
            uuid_filename = os.path.basename(file_path)
            
            # Create empty office document (we'll create minimal valid files)
            self._create_empty_office_document(file_path, document_type)
            
            # Get file information
            file_info = file_path_manager.get_file_info(file_path)
            
            # Create FileStorage record
            file_storage = FileStorage.objects.create(
                original_filename=name,
                file_path=uuid_filename,  # Store only the UUID filename, not the full path
                file_size=file_info['size'],
                mime_type=template['mime_type'],
                extension=template['extension'],
                checksum=file_info.get('checksum', '')
            )
            
            # Calculate and update checksum
            file_storage.checksum = file_storage.calculate_checksum()
            file_storage.save()
            
            # Create FileItem record
            file_item = FileItem.objects.create(
                name=name,
                item_type='file',
                parent=parent_directory,
                storage=file_storage,
                owner=request.user,
                visibility=visibility
            )
            
            return Response({
                'message': f'{document_type.upper()} document created successfully',
                'file': FileItemSerializer(file_item, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': f'Failed to create office document: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_empty_office_document(self, file_path, document_type):
        """Create an empty office document file"""
        import zipfile
        import xml.etree.ElementTree as ET
        
        if document_type == 'docx':
            # Create minimal Word document
            with zipfile.ZipFile(file_path, 'w') as docx:
                # Add minimal document.xml
                doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t></w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''
                docx.writestr('word/document.xml', doc_xml)
                
                # Add minimal [Content_Types].xml
                content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
                docx.writestr('[Content_Types].xml', content_types)
                
                # Add minimal _rels/.rels
                rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
                docx.writestr('_rels/.rels', rels)
                
                # Add minimal word/_rels/document.xml.rels
                word_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''
                docx.writestr('word/_rels/document.xml.rels', word_rels)
        
        elif document_type == 'xlsx':
            # Create minimal Excel document
            with zipfile.ZipFile(file_path, 'w') as xlsx:
                # Add minimal xl/workbook.xml
                workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>'''
                xlsx.writestr('xl/workbook.xml', workbook_xml)
                
                # Add minimal xl/worksheets/sheet1.xml
                sheet_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetData>
  </sheetData>
</worksheet>'''
                xlsx.writestr('xl/worksheets/sheet1.xml', sheet_xml)
                
                # Add xl/sharedStrings.xml (required for Excel)
                shared_strings_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="0" uniqueCount="0">
</sst>'''
                xlsx.writestr('xl/sharedStrings.xml', shared_strings_xml)
                
                # Add xl/styles.xml (required for Excel)
                styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="0"/>
  <fonts count="1">
    <font>
      <sz val="11"/>
      <color theme="1"/>
      <name val="Calibri"/>
      <family val="2"/>
      <scheme val="minor"/>
    </font>
  </fonts>
  <fills count="2">
    <fill>
      <patternFill patternType="none"/>
    </fill>
    <fill>
      <patternFill patternType="gray125"/>
    </fill>
  </fills>
  <borders count="1">
    <border>
      <left/>
      <right/>
      <top/>
      <bottom/>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>'''
                xlsx.writestr('xl/styles.xml', styles_xml)
                
                # Add xl/theme/theme1.xml (required for Excel)
                theme_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
  <a:themeElements>
    <a:clrScheme name="Office">
      <a:dk1>
        <a:sysClr val="windowText" lastClr="000000"/>
      </a:dk1>
      <a:lt1>
        <a:sysClr val="window" lastClr="FFFFFF"/>
      </a:lt1>
      <a:dk2>
        <a:srgbClr val="1F497D"/>
      </a:dk2>
      <a:lt2>
        <a:srgbClr val="EEECE1"/>
      </a:lt2>
      <a:accent1>
        <a:srgbClr val="4F81BD"/>
      </a:accent1>
      <a:accent2>
        <a:srgbClr val="F79646"/>
      </a:accent2>
      <a:accent3>
        <a:srgbClr val="9BBB59"/>
      </a:accent3>
      <a:accent4>
        <a:srgbClr val="8064A2"/>
      </a:accent4>
      <a:accent5>
        <a:srgbClr val="4BACC6"/>
      </a:accent5>
      <a:accent6>
        <a:srgbClr val="F24F75"/>
      </a:accent6>
      <a:hlink>
        <a:srgbClr val="0000FF"/>
      </a:hlink>
      <a:folHlink>
        <a:srgbClr val="800080"/>
      </a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface=""/>
        <a:cs typeface=""/>
        <a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/>
        <a:font script="Hang" typeface="맑은 고딕"/>
        <a:font script="Hans" typeface="宋体"/>
        <a:font script="Hant" typeface="新細明體"/>
        <a:font script="Arab" typeface="Times New Roman"/>
        <a:font script="Hebr" typeface="Times New Roman"/>
        <a:font script="Thai" typeface="Tahoma"/>
        <a:font script="Ethi" typeface="Nyala"/>
        <a:font script="Geor" typeface="Sylfaen"/>
        <a:font script="Gujr" typeface="Shruti"/>
        <a:font script="Khmr" typeface="MoolBoran"/>
        <a:font script="Knda" typeface="Tunga"/>
        <a:font script="Guru" typeface="Raavi"/>
        <a:font script="Cans" typeface="Euphemia"/>
        <a:font script="Cher" typeface="Plantagenet Cherokee"/>
        <a:font script="Yiii" typeface="Microsoft Yi Baiti"/>
        <a:font script="Tibt" typeface="Microsoft Himalaya"/>
        <a:font script="Thaa" typeface="MV Boli"/>
        <a:font script="Deva" typeface="Mangal"/>
        <a:font script="Telu" typeface="Gautami"/>
        <a:font script="Taml" typeface="Latha"/>
        <a:font script="Syrc" typeface="Estrangelo Edessa"/>
        <a:font script="Orya" typeface="Kalinga"/>
        <a:font script="Mlym" typeface="Kartika"/>
        <a:font script="Laoo" typeface="DokChampa"/>
        <a:font script="Sinh" typeface="Iskoola Pota"/>
        <a:font script="Mong" typeface="Mongolian Baiti"/>
        <a:font script="Viet" typeface="Times New Roman"/>
        <a:font script="Uigh" typeface="Microsoft Uighur"/>
        <a:font script="Geor" typeface="Sylfaen"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface=""/>
        <a:cs typeface=""/>
        <a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/>
        <a:font script="Hang" typeface="맑은 고딕"/>
        <a:font script="Hans" typeface="宋体"/>
        <a:font script="Hant" typeface="新細明體"/>
        <a:font script="Arab" typeface="Arial"/>
        <a:font script="Hebr" typeface="Arial"/>
        <a:font script="Thai" typeface="Tahoma"/>
        <a:font script="Ethi" typeface="Nyala"/>
        <a:font script="Geor" typeface="Sylfaen"/>
        <a:font script="Gujr" typeface="Shruti"/>
        <a:font script="Khmr" typeface="MoolBoran"/>
        <a:font script="Knda" typeface="Tunga"/>
        <a:font script="Guru" typeface="Raavi"/>
        <a:font script="Cans" typeface="Euphemia"/>
        <a:font script="Cher" typeface="Plantagenet Cherokee"/>
        <a:font script="Yiii" typeface="Microsoft Yi Baiti"/>
        <a:font script="Tibt" typeface="Microsoft Himalaya"/>
        <a:font script="Thaa" typeface="MV Boli"/>
        <a:font script="Deva" typeface="Mangal"/>
        <a:font script="Telu" typeface="Gautami"/>
        <a:font script="Taml" typeface="Latha"/>
        <a:font script="Syrc" typeface="Estrangelo Edessa"/>
        <a:font script="Orya" typeface="Kalinga"/>
        <a:font script="Mlym" typeface="Kartika"/>
        <a:font script="Laoo" typeface="DokChampa"/>
        <a:font script="Sinh" typeface="Iskoola Pota"/>
        <a:font script="Mong" typeface="Mongolian Baiti"/>
        <a:font script="Viet" typeface="Arial"/>
        <a:font script="Uigh" typeface="Microsoft Uighur"/>
        <a:font script="Geor" typeface="Sylfaen"/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Office">
      <a:fillStyleLst>
        <a:solidFill>
          <a:schemeClr val="phClr"/>
        </a:solidFill>
        <a:gradFill rotWithShape="1">
          <a:gsLst>
            <a:gs pos="0">
              <a:schemeClr val="phClr">
                <a:tint val="50000"/>
                <a:satMod val="300000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="35000">
              <a:schemeClr val="phClr">
                <a:tint val="37000"/>
                <a:satMod val="300000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="100000">
              <a:schemeClr val="phClr">
                <a:tint val="15000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
          </a:gsLst>
          <a:lin ang="16200000" scaled="1"/>
        </a:gradFill>
        <a:gradFill rotWithShape="1">
          <a:gsLst>
            <a:gs pos="0">
              <a:schemeClr val="phClr">
                <a:shade val="51000"/>
                <a:satMod val="130000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="80000">
              <a:schemeClr val="phClr">
                <a:shade val="93000"/>
                <a:satMod val="130000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="100000">
              <a:schemeClr val="phClr">
                <a:shade val="94000"/>
                <a:satMod val="135000"/>
              </a:schemeClr>
            </a:gs>
          </a:gsLst>
          <a:lin ang="16200000" scaled="0"/>
        </a:gradFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr">
          <a:solidFill>
            <a:schemeClr val="phClr">
              <a:shade val="95000"/>
              <a:satMod val="105000"/>
            </a:schemeClr>
          </a:solidFill>
          <a:prstDash val="solid"/>
        </a:ln>
        <a:ln w="25400" cap="flat" cmpd="sng" algn="ctr">
          <a:solidFill>
            <a:schemeClr val="phClr"/>
          </a:solidFill>
          <a:prstDash val="solid"/>
        </a:ln>
        <a:ln w="38100" cap="flat" cmpd="sng" algn="ctr">
          <a:solidFill>
            <a:schemeClr val="phClr"/>
          </a:solidFill>
          <a:prstDash val="solid"/>
        </a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle>
          <a:effectLst>
            <a:outerShdw blurRad="40000" dist="20000" dir="5400000" rotWithShape="0">
              <a:srgbClr val="000000">
                <a:alpha val="38000"/>
              </a:srgbClr>
            </a:outerShdw>
          </a:effectLst>
        </a:effectStyle>
        <a:effectStyle>
          <a:effectLst>
            <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
              <a:srgbClr val="000000">
                <a:alpha val="35000"/>
              </a:srgbClr>
            </a:outerShdw>
          </a:effectLst>
        </a:effectStyle>
        <a:effectStyle>
          <a:effectLst>
            <a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0">
              <a:srgbClr val="000000">
                <a:alpha val="35000"/>
              </a:srgbClr>
            </a:outerShdw>
          </a:effectLst>
          <a:scene3d>
            <a:camera prst="orthographicFront">
              <a:rot lat="0" lon="0" rev="0"/>
            </a:camera>
            <a:lightRig rig="threePt" dir="t">
              <a:rot lat="0" lon="0" rev="1200000"/>
            </a:lightRig>
          </a:scene3d>
          <a:sp3d>
            <a:bevelT w="63500" h="25400"/>
          </a:sp3d>
        </a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill>
          <a:schemeClr val="phClr"/>
        </a:solidFill>
        <a:gradFill rotWithShape="1">
          <a:gsLst>
            <a:gs pos="0">
              <a:schemeClr val="phClr">
                <a:tint val="40000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="40000">
              <a:schemeClr val="phClr">
                <a:tint val="45000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="100000">
              <a:schemeClr val="phClr">
                <a:tint val="49000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
          </a:gsLst>
          <a:path path="circle">
            <a:fillToRect l="50000" t="-80000" r="50000" b="180000"/>
          </a:path>
        </a:gradFill>
        <a:gradFill rotWithShape="1">
          <a:gsLst>
            <a:gs pos="0">
              <a:schemeClr val="phClr">
                <a:tint val="40000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="40000">
              <a:schemeClr val="phClr">
                <a:tint val="45000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
            <a:gs pos="100000">
              <a:schemeClr val="phClr">
                <a:tint val="49000"/>
                <a:satMod val="350000"/>
              </a:schemeClr>
            </a:gs>
          </a:gsLst>
          <a:path path="circle">
            <a:fillToRect l="50000" t="50000" r="50000" b="50000"/>
          </a:path>
        </a:gradFill>
      </a:bgFillStyleLst>
    </a:themeElements>
    <a:objectDefaults/>
    <a:extraClrSchemeLst/>
  </a:theme>
</a:theme>'''
                xlsx.writestr('xl/theme/theme1.xml', theme_xml)
                
                # Add xl/_rels/workbook.xml.rels (required for Excel)
                workbook_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>'''
                xlsx.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
                
                # Add minimal [Content_Types].xml
                content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
</Types>'''
                xlsx.writestr('[Content_Types].xml', content_types)
                
                # Add minimal _rels/.rels
                rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
                xlsx.writestr('_rels/.rels', rels)
        
        elif document_type == 'pptx':
            # Create minimal PowerPoint document
            with zipfile.ZipFile(file_path, 'w') as pptx:
                # Add minimal ppt/presentation.xml
                presentation_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId2"/>
  </p:sldIdLst>
</p:presentation>'''
                pptx.writestr('ppt/presentation.xml', presentation_xml)
                
                # Add minimal [Content_Types].xml
                content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>'''
                pptx.writestr('[Content_Types].xml', content_types)
                
                # Add minimal _rels/.rels
                rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
                pptx.writestr('_rels/.rels', rels)
    
    def post(self, request, *args, **kwargs):
        """Handle file creation based on type"""
        file_type = request.data.get('type', 'text')
        
        if file_type == 'text':
            return self.create_text_file(request)
        elif file_type == 'office':
            return self.create_office_document(request)
        else:
            return Response({'error': 'Invalid file type'}, status=status.HTTP_400_BAD_REQUEST)
