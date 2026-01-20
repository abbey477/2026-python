# main.py - Subpackages Pattern

import sys

# Method 1: Import from main package (if __init__.py exports them)
from utils import add, multiply, capitalize_words, reverse_string

# Method 2: Import from subpackages directly
# from utils.math import add, multiply
# from utils.text import capitalize_words, reverse_string

# Method 3: Import specific modules
# from utils.math.operations import add, multiply
# from utils.text.formatting import capitalize_words, reverse_string


def show_help():
    print("Usage: python main.py <command> [args]")
    print("\nMath commands:")
    print("  add <num1> <num2>")
    print("  multiply <num1> <num2>")
    print("\nText commands:")
    print("  capitalize <text>")
    print("  reverse <text>")


if len(sys.argv) < 2:
    show_help()
    sys.exit(1)

command = sys.argv[1]

if command == "add":
    if len(sys.argv) < 4:
        print("Please provide two numbers!")
    else:
        num1 = float(sys.argv[2])
        num2 = float(sys.argv[3])
        result = add(num1, num2)
        print(f"{num1} + {num2} = {result}")

elif command == "multiply":
    if len(sys.argv) < 4:
        print("Please provide two numbers!")
    else:
        num1 = float(sys.argv[2])
        num2 = float(sys.argv[3])
        result = multiply(num1, num2)
        print(f"{num1} * {num2} = {result}")

elif command == "capitalize":
    if len(sys.argv) < 3:
        print("Please provide text!")
    else:
        text = " ".join(sys.argv[2:])  # Join all remaining args
        result = capitalize_words(text)
        print(f"Original: {text}")
        print(f"Capitalized: {result}")

elif command == "reverse":
    if len(sys.argv) < 3:
        print("Please provide text!")
    else:
        text = " ".join(sys.argv[2:])
        result = reverse_string(text)
        print(f"Original: {text}")
        print(f"Reversed: {result}")

else:
    print(f"Unknown command: {command}")
    show_help()
