"""
Configuration for permission cleanup policies.
"""

# Default cleanup settings
DEFAULT_CLEANUP_SETTINGS = {
    # How many days to keep inactive permissions before deleting them
    'INACTIVE_RETENTION_DAYS': 90,
    
    # How many days to keep expired permissions before deleting them
    'EXPIRED_RETENTION_DAYS': 30,
    
    # Batch size for cleanup operations
    'BATCH_SIZE': 1000,
    
    # Whether to automatically deactivate expired permissions
    'AUTO_DEACTIVATE_EXPIRED': True,
    
    # Whether to automatically clean up old inactive permissions
    'AUTO_CLEANUP_INACTIVE': True,
    
    # Whether to run cleanup when permissions are deactivated
    'CLEANUP_ON_DEACTIVATION': True,
    
    # Maximum number of permissions to clean up in a single operation
    'MAX_CLEANUP_PER_BATCH': 10000,
}

# Environment-specific settings
CLEANUP_SETTINGS = {
    'development': {
        'INACTIVE_RETENTION_DAYS': 30,  # Shorter retention for dev
        'EXPIRED_RETENTION_DAYS': 7,
        'BATCH_SIZE': 100,
        'AUTO_CLEANUP_INACTIVE': False,  # Disable auto cleanup in dev
    },
    
    'testing': {
        'INACTIVE_RETENTION_DAYS': 1,  # Very short retention for tests
        'EXPIRED_RETENTION_DAYS': 1,
        'BATCH_SIZE': 10,
        'AUTO_CLEANUP_INACTIVE': False,
    },
    
    'production': {
        'INACTIVE_RETENTION_DAYS': 365,  # Keep for a year in production
        'EXPIRED_RETENTION_DAYS': 90,
        'BATCH_SIZE': 1000,
        'AUTO_CLEANUP_INACTIVE': True,
    },
}

def get_cleanup_settings(environment='development'):
    """
    Get cleanup settings for the specified environment.
    """
    settings = DEFAULT_CLEANUP_SETTINGS.copy()
    if environment in CLEANUP_SETTINGS:
        settings.update(CLEANUP_SETTINGS[environment])
    return settings

def get_cleanup_setting(key, environment='development', default=None):
    """
    Get a specific cleanup setting.
    """
    settings = get_cleanup_settings(environment)
    return settings.get(key, default)
