"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from filemanager.auth_views import (
    CustomTokenObtainPairView,
    UserRegistrationView,
    ChangePasswordView,
    UserProfileView,
    LogoutView,
    TokenRefreshView as CustomTokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('filemanager.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # JWT Authentication endpoints
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('api/auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
