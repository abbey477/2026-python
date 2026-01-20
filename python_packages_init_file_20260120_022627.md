# Python Packages & __init__.py File
**For Java Developers Learning Python**

Created: 2026-01-20 02:26:27

---

## Overview

This guide shows how to:
- Organize Python code into packages using `__init__.py`
- Understand the difference between modules and packages
- Import from packages properly
- Compare with Java package structure

---

## What is `__init__.py`?

The `__init__.py` file tells Python that a directory should be treated as a **package** (similar to Java packages).

**Key Points:**
- Makes a directory importable as a package
- Can be empty or contain initialization code
- Controls what gets exported from the package
- Similar to Java's package structure

---

## Project Structure Comparison

### Without Package (Simple)

```
my_project/
├── my_module.py
└── main.py
```

**Import in main.py:**
```python
from my_module import greet, Dog
```

---

### With Package (Organized)

```
my_project/
├── utils/
│   ├── __init__.py      # Makes 'utils' a package
│   └── my_module.py
└── main.py
```

**Import in main.py:**
```python
from utils.my_module import greet, Dog
```

---

## Java vs Python Package Structure

### Java:
```
com/
└── mycompany/
    └── utils/
        └── MyModule.java

// In MyModule.java:
package com.mycompany.utils;

public class MyModule {
    // ...
}

// Import in Main.java:
import com.mycompany.utils.MyModule;
```

### Python:
```
mycompany/
└── utils/
    ├── __init__.py
    └── my_module.py

# No package declaration needed in my_module.py

# Import in main.py:
from mycompany.utils.my_module import MyModule
```

---

## Complete Example with Package

### Project Structure:
```
my_project/
├── utils/
│   ├── __init__.py
│   └── my_module.py
└── main.py
```

---

### File 1: `utils/__init__.py` (Empty Version)

```python
# utils/__init__.py

# This file can be empty - it just marks 'utils' as a package
```

**When it's empty:**
- You must import using full path: `from utils.my_module import greet`
- Nothing is automatically available from `utils`

---

### File 1: `utils/__init__.py` (With Exports)

```python
# utils/__init__.py

# Import everything from my_module and make it available at package level
from .my_module import greet, add, multiply, Dog, PI, MAX_USERS

# Now you can use: from utils import greet
# Instead of: from utils.my_module import greet

# You can also define what gets exported when someone does: from utils import *
__all__ = ['greet', 'add', 'multiply', 'Dog', 'PI', 'MAX_USERS']
```

**The dot (.) in `from .my_module`:**
- `.` means "from the current package"
- `..` means "from the parent package"
- This is called **relative import**

---

### File 2: `utils/my_module.py`

```python
# utils/my_module.py

"""
This module provides basic utility functions and classes.
"""

# A couple of variables
PI = 3.14159
MAX_USERS = 100

# Three functions
def greet(name):
    """Greet a person by name."""
    return f"Hello, {name}!"

def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

# A simple class
class Dog:
    """A simple Dog class."""
    
    def __init__(self, name):
        """Initialize a dog with a name."""
        self.name = name
    
    def bark(self):
        """Make the dog bark."""
        return f"{self.name} says Woof!"
```

---

### File 3: `main.py`

```python
# main.py

import sys

# Method 1: Import from package.module (if __init__.py is empty)
# from utils.my_module import greet, add, multiply, Dog, PI, MAX_USERS

# Method 2: Import from package directly (if __init__.py has exports)
from utils import greet, add, multiply, Dog, PI, MAX_USERS

# Method 3: Import the whole package
# import utils
# Then use: utils.greet(), utils.Dog(), etc.

if len(sys.argv) < 2:
    print("Usage: python main.py <command>")
    print("Commands:")
    print("  greet <name>")
    print("  add <num1> <num2>")
    print("  multiply <num1> <num2>")
    print("  dog <name>")
    print("  variables")
    sys.exit(1)

command = sys.argv[1]

if command == "greet":
    if len(sys.argv) < 3:
        print("Please provide a name!")
    else:
        name = sys.argv[2]
        result = greet(name)
        print(result)

elif command == "add":
    if len(sys.argv) < 4:
        print("Please provide two numbers!")
    else:
        num1 = int(sys.argv[2])
        num2 = int(sys.argv[3])
        result = add(num1, num2)
        print(f"{num1} + {num2} = {result}")

elif command == "multiply":
    if len(sys.argv) < 4:
        print("Please provide two numbers!")
    else:
        num1 = int(sys.argv[2])
        num2 = int(sys.argv[3])
        result = multiply(num1, num2)
        print(f"{num1} * {num2} = {result}")

elif command == "dog":
    if len(sys.argv) < 3:
        print("Please provide a dog name!")
    else:
        dog_name = sys.argv[2]
        my_dog = Dog(dog_name)
        print(my_dog.bark())

elif command == "variables":
    print(f"PI = {PI}")
    print(f"MAX_USERS = {MAX_USERS}")

else:
    print(f"Unknown command: {command}")
    print("Use: greet, add, multiply, dog, or variables")
```

---

## Different Import Styles

### Style 1: Import from package.module
```python
from utils.my_module import greet, Dog

greet("Alice")
my_dog = Dog("Buddy")
```

### Style 2: Import from package (requires __init__.py with exports)
```python
from utils import greet, Dog

greet("Alice")
my_dog = Dog("Buddy")
```

### Style 3: Import entire package
```python
import utils

utils.greet("Alice")
my_dog = utils.Dog("Buddy")
```

### Style 4: Import entire module
```python
from utils import my_module

my_module.greet("Alice")
my_dog = my_module.Dog("Buddy")
```

---

## Advanced: Multiple Modules in Package

```
my_project/
├── utils/
│   ├── __init__.py
│   ├── math_utils.py
│   ├── string_utils.py
│   └── file_utils.py
└── main.py
```

### `utils/__init__.py` (Organized Exports)

```python
# utils/__init__.py

# Import from all modules
from .math_utils import add, subtract, multiply, divide
from .string_utils import capitalize_words, reverse_string
from .file_utils import read_file, write_file

# Control what gets exported with 'from utils import *'
__all__ = [
    # Math functions
    'add', 'subtract', 'multiply', 'divide',
    # String functions
    'capitalize_words', 'reverse_string',
    # File functions
    'read_file', 'write_file'
]

# You can also add package-level variables
VERSION = '1.0.0'
AUTHOR = 'Your Name'
```

### `utils/math_utils.py`

```python
# utils/math_utils.py

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### `utils/string_utils.py`

```python
# utils/string_utils.py

def capitalize_words(text):
    """Capitalize first letter of each word."""
    return text.title()

def reverse_string(text):
    """Reverse a string."""
    return text[::-1]
```

### `utils/file_utils.py`

```python
# utils/file_utils.py

def read_file(filename):
    """Read contents of a file."""
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, content):
    """Write content to a file."""
    with open(filename, 'w') as f:
        f.write(content)
```

### Using the Package:

```python
# main.py

from utils import add, multiply, capitalize_words, VERSION

print(add(10, 20))                    # 30
print(multiply(5, 7))                 # 35
print(capitalize_words("hello world")) # Hello World
print(f"Utils version: {VERSION}")    # Utils version: 1.0.0
```

---

## Understanding Relative Imports

### Relative Import (using dots)
```python
# In utils/math_utils.py, importing from string_utils.py
from .string_utils import capitalize_words  # Same package
from ..other_package import something      # Parent package
```

### Absolute Import
```python
# In utils/math_utils.py
from utils.string_utils import capitalize_words
```

**Best Practice:** Use relative imports within a package, absolute imports from outside.

---

## `__init__.py` Best Practices

### 1. Empty (Minimal)
```python
# utils/__init__.py
# Empty file - just marks directory as package
```
**Use when:** Package is simple, users know module names

---

### 2. Simple Exports
```python
# utils/__init__.py
from .my_module import greet, Dog

__all__ = ['greet', 'Dog']
```
**Use when:** You want to simplify imports for users

---

### 3. Organized Exports with Documentation
```python
# utils/__init__.py
"""
Utils Package
=============

This package provides utility functions for common tasks.

Available modules:
- math_utils: Mathematical operations
- string_utils: String manipulation
- file_utils: File operations
"""

from .math_utils import add, subtract, multiply, divide
from .string_utils import capitalize_words, reverse_string
from .file_utils import read_file, write_file

__version__ = '1.0.0'
__author__ = 'Your Name'

__all__ = [
    'add', 'subtract', 'multiply', 'divide',
    'capitalize_words', 'reverse_string',
    'read_file', 'write_file'
]
```
**Use when:** Building a professional library

---

## Common Patterns

### Pattern 1: Flat Package
```
utils/
├── __init__.py
└── helpers.py

# Import:
from utils import some_function
```

---

### Pattern 2: Subpackages
```
utils/
├── __init__.py
├── math/
│   ├── __init__.py
│   └── operations.py
└── text/
    ├── __init__.py
    └── formatting.py

# Import:
from utils.math import operations
from utils.text.formatting import capitalize
```

---

### Pattern 3: Mixed
```
utils/
├── __init__.py
├── core.py
├── math/
│   ├── __init__.py
│   └── operations.py
└── text/
    ├── __init__.py
    └── formatting.py
```

---

## Java Developer's Mental Model

| Python | Java | Notes |
|--------|------|-------|
| `utils/` directory | `package utils;` | Directory = package |
| `__init__.py` | No direct equivalent | Makes directory a package |
| `from utils import X` | `import utils.X;` | Import syntax |
| `.` in imports | Same package | Relative import |
| `__all__` | `public` members | Controls exports |

---

## Quick Reference

### Create a Package:
1. Create a directory (e.g., `utils/`)
2. Add `__init__.py` file (can be empty)
3. Add your Python modules (e.g., `my_module.py`)

### Import from Package:
```python
# If __init__.py is empty:
from utils.my_module import greet

# If __init__.py exports greet:
from utils import greet

# Import entire package:
import utils
utils.greet("Alice")
```

### Running Your Code:
```bash
python main.py greet Alice
python main.py add 10 20
python main.py dog Buddy
```

---

## Complete Working Example

Save these files:

**Directory Structure:**
```
my_project/
├── utils/
│   ├── __init__.py
│   └── my_module.py
└── main.py
```

**File: `utils/__init__.py`**
```python
from .my_module import greet, add, multiply, Dog, PI, MAX_USERS

__all__ = ['greet', 'add', 'multiply', 'Dog', 'PI', 'MAX_USERS']
```

**File: `utils/my_module.py`**
```python
PI = 3.14159
MAX_USERS = 100

def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

class Dog:
    def __init__(self, name):
        self.name = name
    
    def bark(self):
        return f"{self.name} says Woof!"
```

**File: `main.py`**
```python
import sys
from utils import greet, add, multiply, Dog, PI, MAX_USERS

if len(sys.argv) < 2:
    print("Commands: greet, add, multiply, dog, variables")
    sys.exit(1)

command = sys.argv[1]

if command == "greet":
    print(greet(sys.argv[2]))
elif command == "add":
    print(f"{sys.argv[2]} + {sys.argv[3]} = {add(int(sys.argv[2]), int(sys.argv[3]))}")
elif command == "multiply":
    print(f"{sys.argv[2]} * {sys.argv[3]} = {multiply(int(sys.argv[2]), int(sys.argv[3]))}")
elif command == "dog":
    print(Dog(sys.argv[2]).bark())
elif command == "variables":
    print(f"PI = {PI}, MAX_USERS = {MAX_USERS}")
```

**Run:**
```bash
python main.py greet Alice
python main.py add 5 10
python main.py dog Buddy
```

---

## Key Takeaways

1. **`__init__.py`** makes a directory a package (importable)
2. It can be **empty** or contain **initialization code**
3. Use it to **control what gets exported** from your package
4. Similar to **Java packages** but requires the special file
5. Makes your code **more organized** and **professional**

Happy packaging! 🐍📦
