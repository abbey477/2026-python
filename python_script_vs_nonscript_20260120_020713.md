# Python Script vs Non-Script Comparison
**For Java Developers Learning Python**

Created: 2026-01-20 02:07:13

---

## Detailed Comparison Table

| Aspect | Python Script (.py) | Python Interactive/Module |
|--------|---------------------|---------------------------|
| **Shebang Line** | `#!/usr/bin/env python3` at top (for Unix/Linux/Mac) | Not used - no direct execution |
| **File Permission** | Needs execute permission: `chmod +x script.py` | Regular file permissions only |
| **How to Run** | `python script.py` or `./script.py` (with shebang) | `python` (enters REPL) or `import mymodule` |
| **Java Equivalent** | `javac MyApp.java && java MyApp` | `jshell` or importing a library JAR |
| **Entry Point** | `if __name__ == "__main__":` block | No entry point - functions called explicitly |
| **Typical Structure** | Top-to-bottom execution with main block | Function/class definitions only |
| **Output** | Produces output when run | Silent until functions are called |
| **Purpose** | Automation, CLI tools, batch processing | Libraries, reusable code, experimentation |
| **When to Use** | Need a program that does something on its own | Building reusable components or exploring |
| **Standalone** | Yes - runs independently | No - needs to be imported or called |
| **Command-line Args** | Access via `sys.argv` or `argparse` | Not applicable |

---

## Code Examples

### Python Script Example
```python
#!/usr/bin/env python3
# calculator.py

import sys

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

if __name__ == "__main__":
    # This is like Java's main() method
    if len(sys.argv) != 4:
        print("Usage: ./calculator.py <num1> <operation> <num2>")
        sys.exit(1)
    
    num1 = float(sys.argv[1])
    operation = sys.argv[2]
    num2 = float(sys.argv[3])
    
    if operation == "+":
        result = add(num1, num2)
    elif operation == "-":
        result = subtract(num1, num2)
    else:
        print("Unknown operation")
        sys.exit(1)
    
    print(f"Result: {result}")

# Run with: python calculator.py 10 + 5
# Or: chmod +x calculator.py && ./calculator.py 10 + 5
```

### Python Module/Library Example
```python
# math_utils.py
# This file is meant to be imported, not run directly

def add(a, b):
    """Add two numbers"""
    return a + b

def subtract(a, b):
    """Subtract b from a"""
    return a - b

def multiply(a, b):
    """Multiply two numbers"""
    return a * b

# No if __name__ == "__main__" block
# This is purely for importing
```

**Usage of the module:**
```python
# another_script.py or interactive shell
import math_utils

result = math_utils.add(5, 3)
print(result)  # 8
```

### Python Interactive/REPL Example
```python
# Just type 'python' or 'python3' in terminal
>>> x = 10
>>> y = 20
>>> x + y
30
>>> def greet(name):
...     return f"Hello, {name}!"
...
>>> greet("Java Developer")
'Hello, Java Developer!'
```

---

## When to Use Each

| Use Script When... | Use Module/Interactive When... |
|-------------------|-------------------------------|
| Building a CLI tool | Creating a library for others |
| Automating tasks (backups, data processing) | Testing ideas quickly |
| Need to schedule/cron a job | Building reusable functions |
| Processing files in batch | Exploring APIs or data |
| Creating a one-off utility | Learning Python syntax |
| Need command-line arguments | Prototyping before writing script |

---

## Java Developer Tips

### In Java:
```java
// MyApp.java - Always needs main()
public class MyApp {
    public static void main(String[] args) {
        System.out.println("Running...");
    }
}
// Run: javac MyApp.java && java MyApp
```

### In Python:
```python
# my_app.py - Can work both ways!
def run():
    print("Running...")

if __name__ == "__main__":
    run()  # Only executes when run as script

# Run: python my_app.py
# Import: from my_app import run
```

---

## Key Takeaway

The beauty of Python is that **the same file can be both a script AND a module** using the `if __name__ == "__main__":` pattern. This is different from Java where you typically separate application entry points from library code.

### Understanding `if __name__ == "__main__":`

- When you **run** a Python file directly: `__name__` equals `"__main__"`
- When you **import** a Python file: `__name__` equals the module name

This allows maximum flexibility - write your functions, then add a main block for when it's run as a script, but the same functions can still be imported elsewhere!

---

## Quick Reference

### Making a Python Script Executable (Unix/Linux/Mac)

1. Add shebang line at the top: `#!/usr/bin/env python3`
2. Make it executable: `chmod +x myscript.py`
3. Run it: `./myscript.py`

### Importing vs Running

```python
# utility.py
def helper():
    return "I help!"

if __name__ == "__main__":
    print("Running as script")
    print(helper())
```

**As a script:**
```bash
$ python utility.py
Running as script
I help!
```

**As a module:**
```python
>>> import utility
>>> utility.helper()
'I help!'
# Notice: "Running as script" didn't print!
```
