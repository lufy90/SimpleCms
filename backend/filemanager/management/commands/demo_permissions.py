#!/usr/bin/env python
"""
Management command to demonstrate the enhanced permission system.
This command creates test users, groups, and files to show how the
permission system works with user-specific sharing and granular permissions.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from filemanager.models import FileItem, FileAccessPermission
from pathlib import Path
import os
import tempfile


class Command(BaseCommand):
    help = 'Demonstrate the enhanced permission system with user-specific sharing and granular permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up demo data after showing examples'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Setting up enhanced permission system demo...')
        
        # Create demo users
        users = self._create_demo_users()
        
        # Create demo groups
        groups = self._create_demo_groups()
        
        # Add users to groups
        self._setup_user_groups(users, groups)
        
        # Create demo files
        files = self._create_demo_files(users)
        
        # Demonstrate different permission scenarios
        self._demonstrate_permissions(users, groups, files)
        
        if options['cleanup']:
            self._cleanup_demo_data(users, groups, files)
            self.stdout.write('🧹 Demo data cleaned up!')
        else:
            self.stdout.write('\n💡 Demo completed! Use --cleanup to remove demo data.')
            self.stdout.write('🔍 Check the admin interface to see the permission system in action.')

    def _create_demo_users(self):
        """Create demo users with different roles"""
        users = {}
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'password': make_password('admin123'),
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        users['admin'] = admin_user
        if created:
            self.stdout.write('✅ Created admin user: admin/admin123')
        
        # Create regular users
        user_data = [
            ('alice', 'Alice', 'Johnson', 'alice@example.com'),
            ('bob', 'Bob', 'Smith', 'bob@example.com'),
            ('charlie', 'Charlie', 'Brown', 'charlie@example.com'),
            ('diana', 'Diana', 'Prince', 'diana@example.com'),
        ]
        
        for username, first_name, last_name, email in user_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'password': make_password('password123'),
                    'first_name': first_name,
                    'last_name': last_name
                }
            )
            users[username] = user
            if created:
                self.stdout.write(f'✅ Created user: {username}/password123')
        
        return users

    def _create_demo_groups(self):
        """Create demo groups"""
        groups = {}
        
        group_data = [
            ('developers', 'Software Developers'),
            ('designers', 'UI/UX Designers'),
            ('managers', 'Project Managers'),
            ('viewers', 'Read-only Users'),
        ]
        
        for group_name, group_display in group_data:
            group, created = Group.objects.get_or_create(
                name=group_name,
                defaults={'name': group_name}
            )
            groups[group_name] = group
            if created:
                self.stdout.write(f'✅ Created group: {group_display}')
        
        return groups

    def _setup_user_groups(self, users, groups):
        """Add users to appropriate groups"""
        # Alice is a developer and designer
        users['alice'].groups.add(groups['developers'], groups['designers'])
        
        # Bob is a developer
        users['bob'].groups.add(groups['developers'])
        
        # Charlie is a designer and manager
        users['charlie'].groups.add(groups['designers'], groups['managers'])
        
        # Diana is a viewer
        users['diana'].groups.add(groups['viewers'])
        
        self.stdout.write('✅ Set up user-group relationships')

    def _create_demo_files(self, users):
        """Create demo files with different sharing scenarios"""
        files = {}
        
        # Create a temporary directory for demo files
        temp_dir = tempfile.mkdtemp(prefix='demo_cms_')
        self.stdout.write(f'📁 Created demo directory: {temp_dir}')
        
        # File 1: Private file (only owner can access)
        private_file_path = os.path.join(temp_dir, 'private_document.txt')
        with open(private_file_path, 'w') as f:
            f.write('This is a private document that only the owner can access.')
        
        private_file = FileItem.objects.create(
            name='private_document.txt',
            path=private_file_path,
            item_type='file',
            owner=users['alice'],
            visibility='private'
        )
        files['private'] = private_file
        self.stdout.write('📄 Created private file (Alice only)')
        
        # File 2: User-shared file (specific users can access)
        user_shared_path = os.path.join(temp_dir, 'user_shared_project.txt')
        with open(user_shared_path, 'w') as f:
            f.write('This project file is shared with specific users.')
        
        user_shared_file = FileItem.objects.create(
            name='user_shared_project.txt',
            path=user_shared_path,
            item_type='file',
            owner=users['alice'],
            visibility='user'
        )
        user_shared_file.shared_users.add(users['bob'], users['charlie'])
        files['user_shared'] = user_shared_file
        self.stdout.write('📄 Created user-shared file (Alice, Bob, Charlie)')
        
        # File 3: Group-shared file (group members can access)
        group_shared_path = os.path.join(temp_dir, 'group_shared_design.txt')
        with open(group_shared_path, 'w') as f:
            f.write('This design file is shared with the designers group.')
        
        group_shared_file = FileItem.objects.create(
            name='group_shared_design.txt',
            path=group_shared_path,
            item_type='file',
            owner=users['alice'],
            visibility='group'
        )
        group_shared_file.shared_groups.add(Group.objects.get(name='designers'))
        files['group_shared'] = group_shared_file
        self.stdout.write('📄 Created group-shared file (designers group)')
        
        # File 4: Public file (everyone can access)
        public_path = os.path.join(temp_dir, 'public_readme.txt')
        with open(public_path, 'w') as f:
            f.write('This is a public readme file that everyone can access.')
        
        public_file = FileItem.objects.create(
            name='public_readme.txt',
            path=public_path,
            item_type='file',
            owner=users['alice'],
            visibility='public'
        )
        files['public'] = public_file
        self.stdout.write('📄 Created public file (everyone)')
        
        return files

    def _demonstrate_permissions(self, users, groups, files):
        """Demonstrate different permission scenarios"""
        self.stdout.write('\n🔐 Demonstrating permission system...')
        
        # Test 1: Private file access
        self.stdout.write('\n📋 Test 1: Private File Access')
        private_file = files['private']
        self._test_file_access(private_file, users['alice'], 'read', 'Owner should have access')
        self._test_file_access(private_file, users['bob'], 'read', 'Non-owner should not have access')
        
        # Test 2: User-shared file access
        self.stdout.write('\n📋 Test 2: User-Shared File Access')
        user_shared_file = files['user_shared']
        self._test_file_access(user_shared_file, users['alice'], 'read', 'Owner should have access')
        self._test_file_access(user_shared_file, users['bob'], 'read', 'Shared user should have access')
        self._test_file_access(user_shared_file, users['diana'], 'read', 'Non-shared user should not have access')
        
        # Test 3: Group-shared file access
        self.stdout.write('\n📋 Test 3: Group-Shared File Access')
        group_shared_file = files['group_shared']
        self._test_file_access(group_shared_file, users['alice'], 'read', 'Owner should have access')
        self._test_file_access(group_shared_file, users['charlie'], 'read', 'Group member should have access')
        self._test_file_access(group_shared_file, users['bob'], 'read', 'Non-group member should not have access')
        
        # Test 4: Public file access
        self.stdout.write('\n📋 Test 4: Public File Access')
        public_file = files['public']
        self._test_file_access(public_file, users['alice'], 'read', 'Owner should have access')
        self._test_file_access(public_file, users['diana'], 'read', 'Any user should have access')
        
        # Test 5: Granular permissions
        self.stdout.write('\n📋 Test 5: Granular Permissions')
        self._setup_granular_permissions(files, users, groups)
        self._test_granular_permissions(files, users)

    def _test_file_access(self, file_item, user, permission_type, description):
        """Test if a user can access a file with given permission"""
        can_access = file_item.can_access(user, permission_type)
        status = '✅' if can_access else '❌'
        self.stdout.write(f'  {status} {description}: {user.username} can {permission_type} {file_item.name}')

    def _setup_granular_permissions(self, files, users, groups):
        """Set up granular permissions for demonstration"""
        # Give Bob read permission on private file
        FileAccessPermission.objects.create(
            file=files['private'],
            user=users['bob'],
            permission_type='read',
            granted_by=users['alice']
        )
        
        # Give Charlie write permission on user-shared file
        FileAccessPermission.objects.create(
            file=files['user_shared'],
            user=users['charlie'],
            permission_type='write',
            granted_by=users['alice']
        )
        
        # Give designers group admin permission on group-shared file
        FileAccessPermission.objects.create(
            file=files['group_shared'],
            group=groups['designers'],
            permission_type='admin',
            granted_by=users['alice']
        )
        
        self.stdout.write('✅ Set up granular permissions')

    def _test_granular_permissions(self, files, users):
        """Test granular permissions"""
        # Test Bob's read permission on private file
        private_file = files['private']
        can_read = private_file.can_access(users['bob'], 'read')
        can_write = private_file.can_access(users['bob'], 'write')
        self.stdout.write(f'  📋 Bob on private file: read={can_read}, write={can_write}')
        
        # Test Charlie's write permission on user-shared file
        user_shared_file = files['user_shared']
        can_read = user_shared_file.can_access(users['charlie'], 'read')
        can_write = user_shared_file.can_access(users['charlie'], 'write')
        can_delete = user_shared_file.can_access(users['charlie'], 'delete')
        self.stdout.write(f'  📋 Charlie on user-shared file: read={can_read}, write={can_write}, delete={can_delete}')
        
        # Test designers group admin permission
        group_shared_file = files['group_shared']
        alice_can_admin = group_shared_file.can_access(users['alice'], 'admin')
        charlie_can_admin = group_shared_file.can_access(users['charlie'], 'admin')
        self.stdout.write(f'  📋 Admin access: Alice={alice_can_admin}, Charlie={charlie_can_admin}')

    def _cleanup_demo_data(self, users, groups, files):
        """Clean up demo data"""
        # Remove files from filesystem
        for file_item in files.values():
            if file_item.storage and os.path.exists(file_item.storage.get_file_path()):
                os.remove(file_item.storage.get_file_path())
        
        # Remove demo directory (if it exists)
        # Note: In new UUID-based system, directories don't have physical storage
        
        # Remove database records
        for file_item in files.values():
            file_item.delete()
        
        # Remove demo users (except admin)
        for username, user in users.items():
            if username != 'admin':
                user.delete()
        
        # Remove demo groups
        for group in groups.values():
            group.delete()
        
        self.stdout.write('🧹 Cleaned up demo data')
