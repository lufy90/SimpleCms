"""
OnlyOffice Document Server Integration Views
"""
import os
import hashlib
import hmac
import json
import time
import jwt
from urllib.parse import urljoin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import requests
from .models import FileItem


# OnlyOffice Document Server Configuration
DOCUMENT_SERVER_URL = getattr(settings, 'ONLYOFFICE_DOCUMENT_SERVER_URL', 'http://192.168.1.101')
SECRET_KEY = getattr(settings, 'ONLYOFFICE_SECRET_KEY', 'oyLbTv339qrQgW8uRUJ2N0lXuRtFh7qd')
API_BASE_URL = getattr(settings, 'API_BASE_URL', 'http://10.0.1.2:8002')
FRONTEND_URL = getattr(settings, 'FRONTEND_URL', 'http://10.0.1.2:3000')


def generate_document_key(file_id, user_id):
    """Generate a unique document key for OnlyOffice"""
    return f"doc_{file_id}_{user_id}_{int(time.time())}"


def generate_signature(payload, secret_key):
    """Generate HMAC signature for OnlyOffice requests"""
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def generate_jwt_token(payload, secret_key):
    """Generate JWT token for OnlyOffice requests"""
    try:
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document_config(request, file_id):
    """
    Get OnlyOffice document configuration for a file
    """
    try:
        file_item = FileItem.objects.get(id=file_id)
        parent_id = file_item.parent.id if file_item.parent else None
        # Check if user has access to the file
        if not file_item.can_access(request.user, 'read'):
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate document key
        doc_key = generate_document_key(file_id, request.user.id)
        
        # Get file URL - use a special endpoint that doesn't require authentication for OnlyOffice
        file_url = f"{API_BASE_URL}/api/office/download/{file_id}/"
        
        # Get file extension
        file_extension = file_item.storage.extension if file_item.storage else 'docx'
        if file_extension.startswith('.'):
            file_extension = file_extension[1:]
        
        # OnlyOffice supported file types
        supported_extensions = {
            'docx': 'word',
            'doc': 'word', 
            'xlsx': 'cell',
            'xls': 'cell',
            'pptx': 'slide',
            'ppt': 'slide',
            'odt': 'word',
            'ods': 'cell',
            'odp': 'slide',
            'rtf': 'word',
            'txt': 'word',
            'pdf': 'word'  # PDF can be viewed as word-like
        }
        
        # Validate file extension
        if file_extension not in supported_extensions:
            file_extension = 'docx'
        
        document_type = supported_extensions[file_extension]
        
        # Build configuration
        config = {
            'document': {
                'fileType': file_extension,
                'key': doc_key,
                'title': file_item.name,
                'url': file_url,
                'permissions': {
                    'edit': file_item.can_write(request.user),
                    'download': True,
                    'print': True,
                    'review': True,
                    'comment': file_item.can_write(request.user)
                }
            },
            'documentType': document_type,
            'editorConfig': {
                'mode': 'edit' if file_item.can_write(request.user) else 'view',
                'lang': 'en',
                'location': 'en-US',
                'customization': {
                    'autosave': True,
                    'forcesave': True,
                    'chat': False,
                    'comments': file_item.can_write(request.user),
                    'help': True,
                    'hideRightMenu': False,
                    'hideRulers': False,
                    'submitForm': False,
                    'about': True,
                    'feedback': False,
                    'goback': {
                        'url': f"{FRONTEND_URL}/files?parent_id={parent_id}"
                    }
                },
                'callbackUrl': f"{API_BASE_URL}/api/office/callback/",
                'user': {
                    'id': str(request.user.id),
                    'name': request.user.username
                }
            }
        }
        
        # Generate JWT token for OnlyOffice
        if SECRET_KEY:
            token = generate_jwt_token(config, SECRET_KEY)
            if token:
                return Response({
                    'config': config,
                    'token': token
                })
            else:
                return Response({
                    'error': 'Failed to generate JWT token'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': 'OnlyOffice secret key not configured'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except FileItem.DoesNotExist:
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(["GET"])
def office_download(request, file_id):
    """
    Download file for OnlyOffice Document Server (no authentication required)
    """
    try:
        file_item = FileItem.objects.get(id=file_id)
        
        # Get file path
        file_path = file_item.storage.get_file_path()
        
        if not os.path.exists(file_path):
            return Response(
                {'error': 'File not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Determine content type
        content_type = 'application/octet-stream'
        if file_item.storage.extension:
            ext = file_item.storage.extension.lower()
            content_types = {
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'doc': 'application/msword',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'xls': 'application/vnd.ms-excel',
                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'ppt': 'application/vnd.ms-powerpoint',
                'pdf': 'application/pdf',
                'txt': 'text/plain',
                'rtf': 'application/rtf'
            }
            content_type = content_types.get(ext, 'application/octet-stream')
        
        print(f"Content type: {content_type}")
        
        # Return file content
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{file_item.name}"'
        response['Content-Length'] = len(file_content)
        
        print("Returning file response")
        return response
        
    except FileItem.DoesNotExist:
        print(f"FileItem with id {file_id} does not exist")
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error in office_download: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Failed to download file: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(["POST"])
def document_callback(request):
    """
    Handle OnlyOffice document server callbacks
    """
    try:
        # Parse the callback data
        callback_data = json.loads(request.body.decode('utf-8'))

        print(f"Document callback received: {callback_data}")
        
        # Verify the signature if provided
        if 'signature' in callback_data:
            payload = {k: v for k, v in callback_data.items() if k != 'signature'}
            expected_signature = generate_signature(payload, SECRET_KEY)
            
            if callback_data['signature'] != expected_signature:
                return JsonResponse({'error': 'Invalid signature'}, status=400)
        
        # Handle different callback statuses
        status_code = callback_data.get('status', 0)
        
        # Only status codes 2 and 6 should trigger file updates
        if status_code in [2, 6]:  # Document is being edited or document state is saved
            file_id = callback_data.get('key', '').split('_')[1] if '_' in callback_data.get('key', '') else None
            
            if file_id:
                try:
                    file_item = FileItem.objects.get(id=file_id)
                    
                    # Download the updated document from OnlyOffice
                    download_url = callback_data.get('url')
                    
                    if download_url:    
                        response = requests.get(download_url, stream=True)
                        if response.status_code == 200:
                            # Update the file content
                            file_path = file_item.storage.get_file_path()
                            with open(file_path, 'wb') as f:
                                f.write(response.content)
                            
                            # Get user information from callback data
                            user_info = None
                            try:
                                history = callback_data.get('history', {})
                                changes = history.get('changes', [])
                                if changes:
                                    user_info = changes[-1].get('user')
                            except (KeyError, IndexError, AttributeError) as e:
                                print(f"Could not extract user info from callback data: {e}")
                            
                            # Update file metadata
                            file_item.updated_at = timezone.now()
                            
                            # Update modifier if user info is available
                            if user_info and isinstance(user_info, dict):
                                user_id_str = user_info.get('id')
                                user_name = user_info.get('name', 'Unknown')
                                if user_id_str:
                                    try:
                                        # Convert string ID to integer
                                        user_id = int(user_id_str)
                                        # Try to find the user by ID
                                        from django.contrib.auth.models import User
                                        modifier = User.objects.get(id=user_id)
                                        file_item.modifier = modifier
                                        print(f"Updated modifier to user {user_name} (ID: {user_id})")
                                    except (ValueError, TypeError) as e:
                                        print(f"Invalid user ID format '{user_id_str}': {e}")
                                    except User.DoesNotExist:
                                        print(f"User with ID {user_id} not found, keeping current modifier")
                                else:
                                    print("No user ID found in callback data")
                            else:
                                print("No user information available in callback data")
                            
                            file_item.save()
                            
                            print(f"File {file_id} updated successfully for status code {status_code}")
                        else:
                            print(f"Failed to download updated document for file {file_id}, status: {response.status_code}")
                            if response.text:
                                print(f"Response content: {response.text}")
                    else:
                        print(f"No download URL provided for file {file_id} with status code {status_code}")
                            
                except FileItem.DoesNotExist:
                    print(f"FileItem with id {file_id} does not exist for status code {status_code}")
                except Exception as e:
                    print(f"Error updating file {file_id} for status code {status_code}: {e}")
            else:
                print(f"No valid file_id found in callback data for status code {status_code}")
        
        else:
            # Log other status codes without updating files
            status_messages = {
                0: "No document with the key identifier could be found",
                1: "Document is being edited",
                3: "Document is ready for saving",
                4: "Document saving error has occurred",
                5: "Document is closed with no changes",
                7: "Error has occurred while force saving the document",
                8: "Force saving document is in progress"
            }
            
            status_message = status_messages.get(status_code, f"Unknown status code: {status_code}")
            print(f"Document callback status {status_code}: {status_message}")
            print(f"Callback data: {callback_data}")
        
        return JsonResponse({'error': 0})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Callback error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document_server_info(request):
    """
    Get OnlyOffice document server information
    """
    try:
        # Test connection to document server
        response = requests.get(f"{DOCUMENT_SERVER_URL}/healthcheck", timeout=5)
        
        if response.status_code == 200:
            try:
                # Try to parse JSON response
                json_data = response.json()
                if isinstance(json_data, bool) and json_data:
                    # Health check returned just 'true'
                    return Response({
                        'status': 'connected',
                        'server_url': DOCUMENT_SERVER_URL,
                        'version': 'unknown',
                        'health_check': True
                    })
                else:
                    # Health check returned JSON object
                    return Response({
                        'status': 'connected',
                        'server_url': DOCUMENT_SERVER_URL,
                        'version': json_data.get('version', 'unknown'),
                        'health_check': json_data
                    })
            except ValueError:
                # Response is not JSON, treat as plain text
                return Response({
                    'status': 'connected',
                    'server_url': DOCUMENT_SERVER_URL,
                    'version': 'unknown',
                    'health_check': response.text
                })
        else:
            return Response({
                'status': 'error',
                'message': 'Document server not responding'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except requests.exceptions.RequestException as e:
        return Response({
            'status': 'error',
            'message': f'Cannot connect to document server: {str(e)}'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_document(request, file_id):
    """
    Convert a document to a different format using OnlyOffice
    """
    try:
        file_item = FileItem.objects.get(id=file_id)
        
        # Check if user has access to the file
        if not file_item.can_access(request.user, 'read'):
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        target_format = request.data.get('format', 'pdf')
        
        # Get file URL
        file_url = f"{API_BASE_URL}/api/files/{file_id}/download/"
        
        # Get file extension
        file_extension = file_item.storage.extension if file_item.storage else 'docx'
        
        # Build conversion request
        conversion_data = {
            'async': False,
            'filetype': file_extension,
            'key': generate_document_key(file_id, request.user.id),
            'outputtype': target_format,
            'title': file_item.name,
            'url': file_url
        }
        
        # Send conversion request to OnlyOffice
        conversion_url = f"{DOCUMENT_SERVER_URL}/ConvertService.ashx"
        response = requests.post(conversion_url, json=conversion_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('error') == 0:
                # Conversion successful
                return Response({
                    'status': 'success',
                    'download_url': result.get('fileUrl'),
                    'format': target_format
                })
            else:
                return Response({
                    'status': 'error',
                    'message': result.get('errorMessage', 'Conversion failed')
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'status': 'error',
                'message': 'Conversion service unavailable'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except FileItem.DoesNotExist:
        return Response(
            {'error': 'File not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
