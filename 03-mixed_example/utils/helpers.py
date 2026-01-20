# utils/helpers.py

"""
Helper utility functions - directly in utils package
"""

from datetime import datetime

def log_message(message, level="INFO"):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] [{level}] {message}"

def validate_input(value, min_val=0, max_val=100):
    """Validate if input is within range"""
    if not isinstance(value, (int, float)):
        return False, "Value must be a number"
    
    if value < min_val or value > max_val:
        return False, f"Value must be between {min_val} and {max_val}"
    
    return True, "Valid"
