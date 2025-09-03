from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from filemanager.models import FileAccessPermission
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Comprehensive cleanup of file access permissions (expired and old inactive)'

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
            help='Show what would be processed without actually processing'
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
            help='Number of permissions to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--skip-expired',
            action='store_true',
            help='Skip deactivating expired permissions'
        )
        parser.add_argument(
            '--skip-inactive',
            action='store_true',
            help='Skip deleting old inactive permissions'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        force = options['force']
        batch_size = options['batch_size']
        skip_expired = options['skip_expired']
        skip_inactive = options['skip_inactive']

        current_time = timezone.now()
        cutoff_date = current_time - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Permission Cleanup Summary:')
        )
        self.stdout.write(f'  - Current time: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'  - Inactive cutoff: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")} ({days} days)')
        self.stdout.write(f'  - Batch size: {batch_size}')
        self.stdout.write(f'  - Dry run: {dry_run}')
        self.stdout.write(f'  - Skip expired: {skip_expired}')
        self.stdout.write(f'  - Skip inactive: {skip_inactive}')
        self.stdout.write('')

        total_processed = 0

        # Step 1: Handle expired permissions
        if not skip_expired:
            expired_count = self._handle_expired_permissions(
                current_time, batch_size, dry_run, force
            )
            total_processed += expired_count

        # Step 2: Handle old inactive permissions
        if not skip_inactive:
            inactive_count = self._handle_old_inactive_permissions(
                cutoff_date, batch_size, dry_run, force
            )
            total_processed += inactive_count

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Cleanup completed. Total permissions processed: {total_processed}')
        )

    def _handle_expired_permissions(self, current_time, batch_size, dry_run, force):
        """Handle expired permissions by deactivating them"""
        self.stdout.write(self.style.SUCCESS('=== Processing Expired Permissions ==='))
        
        expired_permissions = FileAccessPermission.objects.filter(
            is_active=True,
            expires_at__isnull=False,
            expires_at__lt=current_time
        ).order_by('expires_at')

        total_count = expired_permissions.count()
        
        if total_count == 0:
            self.stdout.write('No expired permissions found.')
            return 0

        self.stdout.write(f'Found {total_count} expired permissions to deactivate.')

        # Show examples
        self.stdout.write('\nExamples:')
        for perm in expired_permissions[:3]:
            target = perm.user.username if perm.user else perm.group.name
            self.stdout.write(
                f'  - {perm.file.name} -> {target} ({perm.permission_type}) '
                f'expired {perm.expires_at.strftime("%Y-%m-%d %H:%M")}'
            )

        # Confirmation
        if not dry_run and not force:
            confirm = input(f'\nDeactivate {total_count} expired permissions? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Skipped expired permissions.')
                return 0

        # Process
        if dry_run:
            self.stdout.write(f'DRY RUN: Would deactivate {total_count} expired permissions.')
            return total_count

        deactivated_count = 0
        try:
            with transaction.atomic():
                while True:
                    batch = list(expired_permissions[:batch_size])
                    if not batch:
                        break
                    
                    batch_ids = [perm.id for perm in batch]
                    updated_count = FileAccessPermission.objects.filter(
                        id__in=batch_ids
                    ).update(is_active=False)
                    
                    deactivated_count += updated_count
                    self.stdout.write(f'Deactivated: {updated_count} permissions')
                    
                    expired_permissions = FileAccessPermission.objects.filter(
                        is_active=True,
                        expires_at__isnull=False,
                        expires_at__lt=current_time
                    ).order_by('expires_at')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise CommandError(f'Failed to deactivate expired permissions: {str(e)}')

        self.stdout.write(f'Successfully deactivated {deactivated_count} expired permissions.')
        return deactivated_count

    def _handle_old_inactive_permissions(self, cutoff_date, batch_size, dry_run, force):
        """Handle old inactive permissions by deleting them"""
        self.stdout.write(self.style.SUCCESS('=== Processing Old Inactive Permissions ==='))
        
        old_inactive_permissions = FileAccessPermission.objects.filter(
            is_active=False,
            granted_at__lt=cutoff_date
        ).order_by('granted_at')

        total_count = old_inactive_permissions.count()
        
        if total_count == 0:
            self.stdout.write('No old inactive permissions found.')
            return 0

        self.stdout.write(f'Found {total_count} old inactive permissions to delete.')

        # Show examples
        self.stdout.write('\nExamples:')
        for perm in old_inactive_permissions[:3]:
            target = perm.user.username if perm.user else perm.group.name
            self.stdout.write(
                f'  - {perm.file.name} -> {target} ({perm.permission_type}) '
                f'granted {perm.granted_at.strftime("%Y-%m-%d")} by {perm.granted_by.username}'
            )

        # Confirmation
        if not dry_run and not force:
            confirm = input(f'\nDelete {total_count} old inactive permissions? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Skipped old inactive permissions.')
                return 0

        # Process
        if dry_run:
            self.stdout.write(f'DRY RUN: Would delete {total_count} old inactive permissions.')
            return total_count

        deleted_count = 0
        try:
            with transaction.atomic():
                while True:
                    batch = list(old_inactive_permissions[:batch_size])
                    if not batch:
                        break
                    
                    batch_ids = [perm.id for perm in batch]
                    deleted_batch = FileAccessPermission.objects.filter(
                        id__in=batch_ids
                    ).delete()
                    
                    deleted_count += deleted_batch[0]
                    self.stdout.write(f'Deleted: {deleted_batch[0]} permissions')
                    
                    old_inactive_permissions = FileAccessPermission.objects.filter(
                        is_active=False,
                        granted_at__lt=cutoff_date
                    ).order_by('granted_at')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise CommandError(f'Failed to delete old inactive permissions: {str(e)}')

        self.stdout.write(f'Successfully deleted {deleted_count} old inactive permissions.')
        return deleted_count
