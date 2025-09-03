from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import FileAccessPermission
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_permissions():
    """
    Celery task to deactivate expired permissions.
    This should be run periodically (e.g., daily).
    """
    current_time = timezone.now()
    
    expired_permissions = FileAccessPermission.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lt=current_time
    )
    
    count = expired_permissions.count()
    if count == 0:
        logger.info('No expired permissions found')
        return 0
    
    try:
        with transaction.atomic():
            deactivated_count = expired_permissions.update(is_active=False)
        
        logger.info(f'Deactivated {deactivated_count} expired permissions')
        return deactivated_count
        
    except Exception as e:
        logger.error(f'Failed to deactivate expired permissions: {str(e)}')
        raise


@shared_task
def cleanup_old_inactive_permissions(days=90, batch_size=1000):
    """
    Celery task to delete old inactive permissions.
    This should be run less frequently (e.g., weekly).
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_permissions = FileAccessPermission.objects.filter(
        is_active=False,
        granted_at__lt=cutoff_date
    )
    
    count = old_permissions.count()
    if count == 0:
        logger.info('No old inactive permissions found')
        return 0
    
    deleted_count = 0
    try:
        with transaction.atomic():
            # Delete in batches to avoid memory issues
            while True:
                batch = list(old_permissions[:batch_size])
                if not batch:
                    break
                
                batch_ids = [perm.id for perm in batch]
                deleted_batch = FileAccessPermission.objects.filter(
                    id__in=batch_ids
                ).delete()
                
                deleted_count += deleted_batch[0]
                logger.info(f'Deleted batch: {deleted_batch[0]} permissions')
                
                # Update queryset for next batch
                old_permissions = FileAccessPermission.objects.filter(
                    is_active=False,
                    granted_at__lt=cutoff_date
                )
        
        logger.info(f'Successfully deleted {deleted_count} old inactive permissions')
        return deleted_count
        
    except Exception as e:
        logger.error(f'Failed to delete old inactive permissions: {str(e)}')
        raise


@shared_task
def comprehensive_permission_cleanup(days=90, batch_size=1000):
    """
    Comprehensive cleanup task that handles both expired and old inactive permissions.
    """
    logger.info('Starting comprehensive permission cleanup')
    
    # Step 1: Deactivate expired permissions
    expired_count = cleanup_expired_permissions.delay().get()
    
    # Step 2: Delete old inactive permissions
    inactive_count = cleanup_old_inactive_permissions.delay(days, batch_size).get()
    
    total_processed = expired_count + inactive_count
    logger.info(f'Comprehensive cleanup completed. Total processed: {total_processed}')
    
    return {
        'expired_deactivated': expired_count,
        'inactive_deleted': inactive_count,
        'total_processed': total_processed
    }
