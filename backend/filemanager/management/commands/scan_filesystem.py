from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from filemanager.models import FileItem
import os
import time
from pathlib import Path
from datetime import timezone as dt_timezone


class Command(BaseCommand):
    help = 'Scan filesystem and populate database with file information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='/',
            help='Root path to start scanning from (default: /)'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username to assign as owner (default: admin)'
        )
        parser.add_argument(
            '--max-depth',
            type=int,
            default=10,
            help='Maximum directory depth to scan (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scanned without making changes'
        )

    def handle(self, *args, **options):
        root_path = options['path']
        username = options['user']
        max_depth = options['max_depth']
        dry_run = options['dry_run']

        # Validate root path
        if not os.path.exists(root_path):
            raise CommandError(f'Path "{root_path}" does not exist')

        if not os.path.isdir(root_path):
            raise CommandError(f'Path "{root_path}" is not a directory')

        # Get or create user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if not dry_run:
                user = User.objects.create_user(username=username, password='admin123')
                self.stdout.write(f'Created user "{username}" with password "admin123"')
            else:
                self.stdout.write(f'Would create user "{username}"')

        self.stdout.write(f'Starting filesystem scan from: {root_path}')
        self.stdout.write(f'Max depth: {max_depth}')
        self.stdout.write(f'Owner: {username}')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write('-' * 50)

        start_time = time.time()
        stats = {
            'directories': 0,
            'files': 0,
            'errors': 0,
            'skipped': 0
        }

        try:
            if not dry_run:
                with transaction.atomic():
                    self._scan_directory_recursive(root_path, user, max_depth, 0, stats)
            else:
                self._scan_directory_recursive(root_path, user, max_depth, 0, stats, dry_run=True)

        except KeyboardInterrupt:
            self.stdout.write('\nScan interrupted by user')
        except Exception as e:
            self.stdout.write(f'\nError during scan: {e}')
            if not dry_run:
                raise CommandError(f'Scan failed: {e}')

        elapsed_time = time.time() - start_time

        self.stdout.write('-' * 50)
        self.stdout.write('Scan completed!')
        self.stdout.write(f'Directories processed: {stats["directories"]}')
        self.stdout.write(f'Files processed: {stats["files"]}')
        self.stdout.write(f'Errors encountered: {stats["errors"]}')
        self.stdout.write(f'Skipped items: {stats["skipped"]}')
        self.stdout.write(f'Total time: {elapsed_time:.2f} seconds')

    def _scan_directory_recursive(self, directory_path, user, max_depth, current_depth, stats, dry_run=False):
        """Recursively scan directory and add items to database"""
        if current_depth > max_depth:
            stats['skipped'] += 1
            return

        try:
            items = os.listdir(directory_path)
        except PermissionError:
            stats['errors'] += 1
            self.stdout.write(f'Permission denied: {directory_path}')
            return
        except Exception as e:
            stats['errors'] += 1
            self.stdout.write(f'Error reading directory {directory_path}: {e}')
            return

        for item_name in items:
            item_path = os.path.join(directory_path, item_name)
            
            try:
                if os.path.isdir(item_path):
                    self._process_directory(item_path, user, stats, dry_run)
                    stats['directories'] += 1
                    
                    # Recursively scan subdirectories
                    self._scan_directory_recursive(item_path, user, max_depth, current_depth + 1, stats, dry_run)
                    
                elif os.path.isfile(item_path):
                    self._process_file(item_path, user, stats, dry_run)
                    stats['files'] += 1
                    
                else:
                    # Skip symbolic links, sockets, etc.
                    stats['skipped'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(f'Error processing {item_path}: {e}')

    def _process_directory(self, dir_path, user, stats, dry_run=False):
        """Process a directory and add to database"""
        try:
            if not dry_run:
                # Check if directory already exists in database
                if not FileItem.objects.filter(path=dir_path).exists():
                    # Calculate relative path
                    relative_path = self._get_relative_path(dir_path)
                    
                    FileItem.objects.create(
                        name=os.path.basename(dir_path),
                        path=dir_path,
                        relative_path=relative_path,
                        item_type='directory',
                        owner=user
                    )
                    self.stdout.write(f'Added directory: {relative_path}')
            else:
                self.stdout.write(f'Would add directory: {dir_path}')
                
        except Exception as e:
            stats['errors'] += 1
            self.stdout.write(f'Error adding directory {dir_path}: {e}')

    def _process_file(self, file_path, user, stats, dry_run=False):
        """Process a file and add to database"""
        try:
            if not dry_run:
                # Check if file already exists in database
                if not FileItem.objects.filter(path=file_path).exists():
                    # Calculate relative path
                    relative_path = self._get_relative_path(file_path)
                    
                    file_item = FileItem.objects.create(
                        name=os.path.basename(file_path),
                        path=file_path,
                        relative_path=relative_path,
                        item_type='file',
                        owner=user
                    )
                    
                    # Update file metadata from filesystem
                    try:
                        file_item.update_from_filesystem()
                    except Exception as e:
                        self.stdout.write(f'Error updating file metadata: {e}')
                    
                    self.stdout.write(f'Added file: {relative_path}')
            else:
                self.stdout.write(f'Would add file: {file_path}')
                
        except Exception as e:
            stats['errors'] += 1
            self.stdout.write(f'Error adding file {file_path}: {e}')
    
    def _get_relative_path(self, absolute_path):
        """Calculate relative path from the root scan directory"""
        try:
            # Get the root path from command arguments
            root_path = self.scan_root_path if hasattr(self, 'scan_root_path') else '/'
            
            # Make paths absolute and normalize
            root_path = os.path.abspath(root_path)
            absolute_path = os.path.abspath(absolute_path)
            
            # If the path is the root, return just the name
            if absolute_path == root_path:
                return os.path.basename(root_path)
            
            # Calculate relative path
            try:
                relative = os.path.relpath(absolute_path, root_path)
                # Ensure we don't start with ../
                if relative.startswith('..'):
                    return os.path.basename(absolute_path)
                return relative
            except ValueError:
                # If paths are on different drives, just return the name
                return os.path.basename(absolute_path)
                
        except Exception:
            # Fallback to just the filename
            return os.path.basename(absolute_path)
