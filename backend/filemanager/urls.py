from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'files', views.FileSystemItemViewSet, basename='filesystemitem')
router.register(r'tags', views.FileTagViewSet, basename='filetag')
router.register(r'tag-relations', views.FileTagRelationViewSet, basename='filetagrelation')
router.register(r'access-logs', views.FileAccessLogViewSet, basename='fileaccesslog')
router.register(r'permissions', views.FileAccessPermissionViewSet, basename='fileaccesspermission')
router.register(r'permission-requests', views.FilePermissionRequestViewSet, basename='filepermissionrequest')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('api/operations/', views.FileOperationView.as_view(), name='file-operations'),
]
