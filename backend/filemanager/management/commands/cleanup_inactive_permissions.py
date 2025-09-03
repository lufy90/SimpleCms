from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from filemanager.models import FileAccessPermission
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old inactive file access permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to keep inactive permissions (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of permissions to delete in each batch (default: 1000)'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        force = options['force']
        batch_size = options['batch_size']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleanup Configuration:')
        )
        self.stdout.write(f'  - Days to keep: {days}')
        self.stdout.write(f'  - Cutoff date: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'  - Batch size: {batch_size}')
        self.stdout.write(f'  - Dry run: {dry_run}')
        self.stdout.write('')

        # Find inactive permissions older than cutoff date
        old_inactive_permissions = FileAccessPermission.objects.filter(
            is_active=False,
            granted_at__lt=cutoff_date
        ).order_by('granted_at')

        total_count = old_inactive_permissions.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No old inactive permissions found to clean up.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {total_count} old inactive permissions to clean up.')
        )

        # Show some examples
        if total_count > 0:
            self.stdout.write('\nExamples of permissions that will be deleted:')
            for perm in old_inactive_permissions[:5]:
                target = perm.user.username if perm.user else perm.group.name
                self.stdout.write(
                    f'  - {perm.file.name} -> {target} ({perm.permission_type}) '
                    f'granted {perm.granted_at.strftime("%Y-%m-%d")} by {perm.granted_by.username}'
                )
            
            if total_count > 5:
                self.stdout.write(f'  ... and {total_count - 5} more')

        # Confirmation
        if not dry_run and not force:
            confirm = input(f'\nAre you sure you want to delete {total_count} old inactive permissions? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Cleanup cancelled.'))
                return

        # Perform cleanup
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would delete {total_count} old inactive permissions.')
            )
            return

        # Delete in batches to avoid memory issues
        deleted_count = 0
        try:
            with transaction.atomic():
                while True:
                    # Get a batch of permissions to delete
                    batch = list(old_inactive_permissions[:batch_size])
                    if not batch:
                        break
                    
                    # Delete the batch
                    batch_ids = [perm.id for perm in batch]
                    deleted_batch = FileAccessPermission.objects.filter(id__in=batch_ids).delete()
                    deleted_count += deleted_batch[0]
                    
                    self.stdout.write(f'Deleted batch: {deleted_batch[0]} permissions')
                    
                    # Update the queryset to get the next batch
                    old_inactive_permissions = FileAccessPermission.objects.filter(
                        is_active=False,
                        granted_at__lt=cutoff_date
                    ).order_by('granted_at')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during cleanup: {str(e)}')
            )
            raise CommandError(f'Cleanup failed: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} old inactive permissions.')
        )

        # Log the cleanup
        logger.info(f'Cleaned up {deleted_count} old inactive permissions older than {days} days')
