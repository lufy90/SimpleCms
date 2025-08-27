from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from .serializers import UserSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view with additional user information"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Add user information to the response
            user = User.objects.get(username=request.data['username'])
            user_data = UserSerializer(user).data
            
            response.data.update({
                'user': user_data,
                'message': 'Login successful'
            })
        
        return response


class UserRegistrationView(generics.CreateAPIView):
    """User registration view"""
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Create user
                    user = User.objects.create_user(
                        username=serializer.validated_data['username'],
                        email=serializer.validated_data.get('email', ''),
                        password=request.data.get('password'),
                        first_name=serializer.validated_data.get('first_name', ''),
                        last_name=serializer.validated_data.get('last_name', '')
                    )
                    
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = refresh.access_token
                    
                    return Response({
                        'message': 'User registered successfully',
                        'user': UserSerializer(user).data,
                        'tokens': {
                            'access': str(access_token),
                            'refresh': str(refresh),
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({
                    'error': f'Registration failed: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.UpdateAPIView):
    """Change password view"""
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({
                'error': 'Both old_password and new_password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify old password
        if not user.check_password(old_password):
            return Response({
                'error': 'Invalid old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                'error': f'Invalid new password: {e.messages[0]}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        # Invalidate all existing tokens
        RefreshToken.for_user(user)
        
        return Response({
            'message': 'Password changed successfully. Please login again.'
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    """Logout view that blacklists the refresh token"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Logged out successfully'
            })
        except Exception as e:
            return Response({
                'error': f'Logout failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(generics.GenericAPIView):
    """Custom token refresh view with user information"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({
                    'error': 'refresh_token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify and refresh token
            token = RefreshToken(refresh_token)
            access_token = token.access_token
            
            # Get user information
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            user_data = UserSerializer(user).data
            
            return Response({
                'access': str(access_token),
                'refresh': str(token),
                'user': user_data,
                'message': 'Token refreshed successfully'
            })
            
        except Exception as e:
            return Response({
                'error': f'Token refresh failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
