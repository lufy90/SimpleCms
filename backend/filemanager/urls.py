from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import office_views

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
    path('api/create-file/', views.FileCreationView.as_view(), name='file-creation'),
    path('api/operations/', views.FileOperationView.as_view(), name='file-operations'),
    path('api/deleted-files/', views.DeletedFilesViewSet.as_view({'get': 'list'}), name='deleted-files-list'),
    path('api/deleted-files/restore/', views.DeletedFilesViewSet.as_view({'post': 'restore'}), name='deleted-files-restore'),
    path('api/deleted-files/hard-delete/', views.DeletedFilesViewSet.as_view({'post': 'hard_delete'}), name='deleted-files-hard-delete'),
    
    # User and Group search for file sharing
    path('api/users/search/', views.UserSearchView.as_view(), name='user-search'),
    path('api/groups/search/', views.GroupSearchView.as_view(), name='group-search'),
    
    # OnlyOffice Document Server integration
    path('api/office/settings/', office_views.get_onlyoffice_settings, name='office-settings'),
    path('api/office/config/<int:file_id>/', office_views.get_document_config, name='office-document-config'),
    path('api/office/upload/<int:file_id>/', office_views.office_upload, name='office-upload'),
    path('api/office/callback/', office_views.document_callback, name='office-document-callback'),
    path('api/office/info/', office_views.get_document_server_info, name='office-server-info'),
    path('api/office/convert/<int:file_id>/', office_views.convert_document, name='office-convert-document'),
    path('api/office/download/<int:file_id>/', office_views.office_download, name='office-download'),
]
