# Permission Cleanup System

This document describes the automatic cleanup system for file access permissions in the file manager.

## Overview

The system provides multiple approaches to automatically clean up old and expired permissions:

1. **Management Commands** - Manual or cron-based cleanup
2. **Django Signals** - Automatic cleanup when permissions are modified
3. **Celery Tasks** - Background task-based cleanup for production
4. **Configuration-based** - Environment-specific cleanup policies

## Why Use `is_active` Flag?

The system uses an `is_active` flag instead of simply deleting permissions because:

- **Audit Trail**: Maintains complete history of all permissions
- **Temporary Disable**: Easy to temporarily disable without losing metadata
- **Expiration Handling**: Clear distinction between revoked and expired permissions
- **Rollback Capability**: Easy to restore previously granted permissions
- **Compliance**: Many organizations require permission history for audits

## Cleanup Strategies

### 1. Expired Permissions
- **Action**: Deactivate (set `is_active=False`)
- **When**: Permissions with `expires_at < current_time`
- **Frequency**: Daily (recommended)

### 2. Old Inactive Permissions
- **Action**: Delete permanently
- **When**: Permissions with `is_active=False` and `granted_at < cutoff_date`
- **Frequency**: Weekly/Monthly (recommended)
- **Retention**: 90 days (configurable)

## Management Commands

### Basic Commands

```bash
# Deactivate expired permissions
python manage.py cleanup_expired_permissions

# Delete old inactive permissions (90 days default)
python manage.py cleanup_inactive_permissions

# Comprehensive cleanup (both expired and old inactive)
python manage.py cleanup_permissions
```

### Advanced Options

```bash
# Custom retention period
python manage.py cleanup_permissions --days 30

# Dry run (show what would be done)
python manage.py cleanup_permissions --dry-run

# Skip confirmation prompts
python manage.py cleanup_permissions --force

# Custom batch size
python manage.py cleanup_permissions --batch-size 500

# Skip specific operations
python manage.py cleanup_permissions --skip-expired
python manage.py cleanup_permissions --skip-inactive
```

## Cron Job Setup

Add these to your crontab (`crontab -e`):

```bash
# Deactivate expired permissions daily at 2 AM
0 2 * * * cd /path/to/your/project && python manage.py cleanup_expired_permissions --force

# Clean up old inactive permissions weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/your/project && python manage.py cleanup_inactive_permissions --days 90 --force

# Comprehensive cleanup monthly on the 1st at 4 AM
0 4 1 * * cd /path/to/your/project && python manage.py cleanup_permissions --days 90 --force
```

## Celery Tasks (Production)

For production environments with Celery:

```python
from filemanager.tasks import cleanup_expired_permissions, cleanup_old_inactive_permissions

# Schedule daily cleanup of expired permissions
cleanup_expired_permissions.delay()

# Schedule weekly cleanup of old inactive permissions
cleanup_old_inactive_permissions.delay(days=90, batch_size=1000)
```

## Configuration

### Environment-specific Settings

```python
# In your settings.py
from filemanager.cleanup_config import get_cleanup_settings

CLEANUP_SETTINGS = get_cleanup_settings('production')
```

### Available Settings

- `INACTIVE_RETENTION_DAYS`: Days to keep inactive permissions (default: 90)
- `EXPIRED_RETENTION_DAYS`: Days to keep expired permissions (default: 30)
- `BATCH_SIZE`: Number of permissions to process per batch (default: 1000)
- `AUTO_DEACTIVATE_EXPIRED`: Auto-deactivate expired permissions (default: True)
- `AUTO_CLEANUP_INACTIVE`: Auto-cleanup old inactive permissions (default: True)
- `CLEANUP_ON_DEACTIVATION`: Run cleanup when permissions are deactivated (default: True)

## Automatic Cleanup (Signals)

The system automatically runs cleanup when:
- New permissions are created
- Existing permissions are deactivated

This is handled by Django signals in `filemanager/signals.py`.

## Monitoring and Logging

All cleanup operations are logged with:
- Number of permissions processed
- Timestamps
- Error details (if any)

Check your Django logs for cleanup activity:

```bash
# View recent cleanup logs
tail -f /path/to/your/logs/django.log | grep "permission cleanup"
```

## Best Practices

### Development Environment
- Use shorter retention periods (30 days)
- Disable automatic cleanup
- Run cleanup manually for testing

### Production Environment
- Use longer retention periods (90-365 days)
- Enable automatic cleanup
- Set up monitoring and alerts
- Use Celery for background processing

### Testing
- Use very short retention periods (1 day)
- Disable automatic cleanup
- Clean up after tests

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the user running the command has database access
2. **Memory Issues**: Reduce batch size for large datasets
3. **Long Running**: Use `--batch-size` to process in smaller chunks
4. **Signal Errors**: Check that signals are properly registered in `apps.py`

### Debug Mode

```bash
# Run with verbose output
python manage.py cleanup_permissions --verbosity 2

# Dry run to see what would be processed
python manage.py cleanup_permissions --dry-run --verbosity 2
```

## Performance Considerations

- **Batch Processing**: Always use batch processing for large datasets
- **Database Indexes**: Ensure proper indexes on `is_active`, `expires_at`, and `granted_at`
- **Timing**: Run cleanup during low-traffic periods
- **Monitoring**: Monitor database performance during cleanup operations

## Security Considerations

- **Audit Trail**: Deleted permissions are logged before deletion
- **Access Control**: Only users with appropriate permissions can run cleanup
- **Backup**: Consider backing up permissions before major cleanup operations
- **Compliance**: Ensure cleanup policies meet your organization's compliance requirements
