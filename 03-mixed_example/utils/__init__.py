# utils/__init__.py

"""
Utils Package - Mixed Pattern
Has both direct modules AND subpackages.
"""

# Import from direct modules
from .core import get_version, get_config
from .helpers import log_message, validate_input

# Import from subpackages
from .math.operations import add, subtract, multiply, divide
from .text.formatting import capitalize_words, reverse_string, to_uppercase

__version__ = '2.0.0'

__all__ = [
    # From core module
    'get_version', 'get_config',
    # From helpers module
    'log_message', 'validate_input',
    # From math subpackage
    'add', 'subtract', 'multiply', 'divide',
    # From text subpackage
    'capitalize_words', 'reverse_string', 'to_uppercase'
]
