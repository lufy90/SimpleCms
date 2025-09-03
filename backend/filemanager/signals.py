from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import FileAccessPermission
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FileAccessPermission)
def handle_permission_cleanup(sender, instance, created, **kwargs):
    """
    Automatically clean up old inactive permissions when a new permission is created
    or when a permission is deactivated.
    """
    # Only run cleanup if this is a new permission or if an existing permission was deactivated
    if created or (not created and not instance.is_active):
        # Run cleanup in a separate transaction to avoid issues
        try:
            cleanup_old_inactive_permissions()
        except Exception as e:
            logger.error(f'Automatic permission cleanup failed: {str(e)}')


def cleanup_old_inactive_permissions(days=90, batch_size=100):
    """
    Clean up old inactive permissions automatically.
    This function can be called from signals or manually.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Find old inactive permissions
    old_permissions = FileAccessPermission.objects.filter(
        is_active=False,
        granted_at__lt=cutoff_date
    )[:batch_size]  # Limit to batch size for performance
    
    if old_permissions.exists():
        try:
            with transaction.atomic():
                deleted_count = old_permissions.delete()[0]
                logger.info(f'Automatically cleaned up {deleted_count} old inactive permissions')
        except Exception as e:
            logger.error(f'Failed to clean up old inactive permissions: {str(e)}')


@receiver(pre_delete, sender=FileAccessPermission)
def log_permission_deletion(sender, instance, **kwargs):
    """
    Log when permissions are permanently deleted for audit purposes.
    """
    target = instance.user.username if instance.user else instance.group.name
    logger.info(
        f'Permission permanently deleted: {instance.file.name} -> {target} '
        f'({instance.permission_type}) granted by {instance.granted_by.username} '
        f'on {instance.granted_at.strftime("%Y-%m-%d %H:%M:%S")}'
    )
