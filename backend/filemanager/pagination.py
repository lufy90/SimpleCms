from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from math import ceil


class EnhancedPageNumberPagination(PageNumberPagination):
    """
    Enhanced pagination class that provides detailed pagination information
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000
    
    def get_paginated_response(self, data):
        """
        Return enhanced pagination response with detailed metadata
        """
        total_count = self.page.paginator.count
        page_size = self.get_page_size(self.request)
        current_page = self.page.number
        total_pages = ceil(total_count / page_size)
        
        # Build next and previous URLs
        next_url = None
        previous_url = None
        
        if self.page.has_next():
            next_url = self.get_next_link()
        
        if self.page.has_previous():
            previous_url = self.get_previous_link()
        
        pagination_data = {
            'count': total_count,
            'next': next_url,
            'previous': previous_url,
            'page_size': page_size,
            'current_page': current_page,
            'total_pages': total_pages,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
        }
        
        return Response({
            'pagination': pagination_data,
            'results': data
        })
    
    def get_page_size(self, request):
        """
        Get page size from request parameters or use default
        """
        page_size = request.query_params.get(self.page_size_query_param, self.page_size)
        
        try:
            page_size = int(page_size)
            if page_size > 0:
                return min(page_size, self.max_page_size)
        except (ValueError, TypeError):
            pass
        
        return self.page_size


class FileItemPagination(EnhancedPageNumberPagination):
    """
    Pagination specifically for FileItem with optimized page size
    """
    page_size = 25  # Smaller page size for file listings
    max_page_size = 500


class FileAccessLogPagination(EnhancedPageNumberPagination):
    """
    Pagination for FileAccessLog with larger page size for logs
    """
    page_size = 100
    max_page_size = 1000


class FileTagPagination(EnhancedPageNumberPagination):
    """
    Pagination for FileTag with medium page size
    """
    page_size = 50
    max_page_size = 200
