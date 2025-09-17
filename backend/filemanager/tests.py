from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import FileItem, FileStorage
import tempfile
import os


class FileStreamingTestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.temp_file.write(b'Test video content for streaming')
        self.temp_file.close()
        
        # Create FileStorage
        self.file_storage = FileStorage.objects.create(
            file_path=self.temp_file.name,
            mime_type='video/mp4',
            file_size=os.path.getsize(self.temp_file.name)
        )
        
        # Create FileItem
        self.file_item = FileItem.objects.create(
            name='test_video.mp4',
            item_type='file',
            owner=self.user,
            storage=self.file_storage,
            visibility='private'
        )
    
    def tearDown(self):
        """Clean up test data"""
        os.unlink(self.temp_file.name)
    
    def test_stream_file_success(self):
        """Test successful file streaming"""
        url = reverse('fileitem-stream', kwargs={'pk': self.file_item.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertIn('Cache-Control', response)
    
    def test_stream_file_with_range(self):
        """Test file streaming with Range header"""
        url = reverse('fileitem-stream', kwargs={'pk': self.file_item.pk})
        response = self.client.get(url, HTTP_RANGE='bytes=0-10')
        
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertIn('Content-Range', response)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
    
    def test_stream_file_unauthorized(self):
        """Test streaming file without authentication"""
        self.client.logout()
        url = reverse('fileitem-stream', kwargs={'pk': self.file_item.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_stream_nonexistent_file(self):
        """Test streaming non-existent file"""
        url = reverse('fileitem-stream', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_stream_directory(self):
        """Test streaming a directory (should fail)"""
        # Create a directory item
        directory = FileItem.objects.create(
            name='test_directory',
            item_type='directory',
            owner=self.user,
            visibility='private'
        )
        
        url = reverse('fileitem-stream', kwargs={'pk': directory.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Item is not a file', response.data['error'])
