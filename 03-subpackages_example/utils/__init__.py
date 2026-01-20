# utils/__init__.py

"""
Utils Package - Subpackages Pattern
All functionality is organized in subpackages.
"""

# You can import from subpackages to make them easier to access
from .math.operations import add, subtract, multiply, divide
from .text.formatting import capitalize_words, reverse_string, to_uppercase

# Or you can leave it empty and let users import from subpackages directly

__version__ = '1.0.0'

__all__ = [
    'add', 'subtract', 'multiply', 'divide',
    'capitalize_words', 'reverse_string', 'to_uppercase'
]
