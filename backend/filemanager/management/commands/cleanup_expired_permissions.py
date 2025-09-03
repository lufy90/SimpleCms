from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from filemanager.models import FileAccessPermission
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deactivate expired file access permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deactivated without actually deactivating'
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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        batch_size = options['batch_size']

        current_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Expired Permission Cleanup:')
        )
        self.stdout.write(f'  - Current time: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'  - Batch size: {batch_size}')
        self.stdout.write(f'  - Dry run: {dry_run}')
        self.stdout.write('')

        # Find expired permissions that are still active
        expired_permissions = FileAccessPermission.objects.filter(
            is_active=True,
            expires_at__isnull=False,
            expires_at__lt=current_time
        ).order_by('expires_at')

        total_count = expired_permissions.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired permissions found to deactivate.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {total_count} expired permissions to deactivate.')
        )

        # Show some examples
        if total_count > 0:
            self.stdout.write('\nExamples of permissions that will be deactivated:')
            for perm in expired_permissions[:5]:
                target = perm.user.username if perm.user else perm.group.name
                self.stdout.write(
                    f'  - {perm.file.name} -> {target} ({perm.permission_type}) '
                    f'expired {perm.expires_at.strftime("%Y-%m-%d %H:%M")} '
                    f'(granted by {perm.granted_by.username})'
                )
            
            if total_count > 5:
                self.stdout.write(f'  ... and {total_count - 5} more')

        # Confirmation
        if not dry_run and not force:
            confirm = input(f'\nAre you sure you want to deactivate {total_count} expired permissions? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Cleanup cancelled.'))
                return

        # Perform deactivation
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would deactivate {total_count} expired permissions.')
            )
            return

        # Deactivate in batches
        deactivated_count = 0
        try:
            with transaction.atomic():
                while True:
                    # Get a batch of permissions to deactivate
                    batch = list(expired_permissions[:batch_size])
                    if not batch:
                        break
                    
                    # Deactivate the batch
                    batch_ids = [perm.id for perm in batch]
                    updated_count = FileAccessPermission.objects.filter(
                        id__in=batch_ids
                    ).update(is_active=False)
                    
                    deactivated_count += updated_count
                    self.stdout.write(f'Deactivated batch: {updated_count} permissions')
                    
                    # Update the queryset to get the next batch
                    expired_permissions = FileAccessPermission.objects.filter(
                        is_active=True,
                        expires_at__isnull=False,
                        expires_at__lt=current_time
                    ).order_by('expires_at')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during deactivation: {str(e)}')
            )
            raise CommandError(f'Deactivation failed: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deactivated {deactivated_count} expired permissions.')
        )

        # Log the cleanup
        logger.info(f'Deactivated {deactivated_count} expired permissions')
