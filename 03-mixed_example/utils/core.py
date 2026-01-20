# utils/core.py

"""
Core utility functions - directly in utils package
"""

def get_version():
    """Return the current version"""
    return "2.0.0"

def get_config():
    """Return configuration dictionary"""
    return {
        'app_name': 'Utils Library',
        'debug': False,
        'max_retries': 3
    }
