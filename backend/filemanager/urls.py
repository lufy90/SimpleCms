from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'files', views.FileItemViewSet, basename='fileitem')
router.register(r'tags', views.FileTagViewSet, basename='filetag')
router.register(r'tag-relations', views.FileTagRelationViewSet, basename='filetagrelation')
router.register(r'access-logs', views.FileAccessLogViewSet, basename='fileaccesslog')
router.register(r'permissions', views.FileAccessPermissionViewSet, basename='fileaccesspermission')
router.register(r'permission-requests', views.FilePermissionRequestViewSet, basename='filepermissionrequest')
router.register(r'users', views.UserManagementViewSet, basename='usermanagement')
router.register(r'groups', views.GroupManagementViewSet, basename='groupmanagement')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload/', views.FileUploadView.as_view(), name='file-upload'),
    # Directory upload functionality now integrated into FileUploadView
    path('api/operations/', views.FileOperationView.as_view(), name='file-operations'),
    path('api/deleted-files/', views.DeletedFilesViewSet.as_view({'get': 'list'}), name='deleted-files-list'),
    path('api/deleted-files/restore/', views.DeletedFilesViewSet.as_view({'post': 'restore'}), name='deleted-files-restore'),
    path('api/deleted-files/hard-delete/', views.DeletedFilesViewSet.as_view({'post': 'hard_delete'}), name='deleted-files-hard-delete'),
    
    # User and Group search for file sharing
    path('api/users/search/', views.UserSearchView.as_view(), name='user-search'),
    path('api/groups/search/', views.GroupSearchView.as_view(), name='group-search'),
]
