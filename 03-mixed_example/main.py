# main.py - Mixed Pattern

import sys

# Import from direct modules (core, helpers)
from utils import get_version, get_config, log_message, validate_input

# Import from subpackages (math, text)
from utils import add, multiply, capitalize_words, reverse_string

# You can also import directly:
# from utils.core import get_version
# from utils.helpers import log_message
# from utils.math import add, multiply
# from utils.text import capitalize_words


def show_help():
    print("Usage: python main.py <command> [args]")
    print("\nCore commands:")
    print("  version")
    print("  config")
    print("\nHelper commands:")
    print("  log <message>")
    print("  validate <number>")
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

# Core module commands
if command == "version":
    print(f"Version: {get_version()}")

elif command == "config":
    config = get_config()
    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

# Helper module commands
elif command == "log":
    if len(sys.argv) < 3:
        print("Please provide a message!")
    else:
        message = " ".join(sys.argv[2:])
        result = log_message(message)
        print(result)

elif command == "validate":
    if len(sys.argv) < 3:
        print("Please provide a number!")
    else:
        try:
            value = float(sys.argv[2])
            is_valid, msg = validate_input(value)
            print(f"Value: {value}")
            print(f"Valid: {is_valid}")
            print(f"Message: {msg}")
        except ValueError:
            print("Invalid number!")

# Math subpackage commands
elif command == "add":
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

# Text subpackage commands
elif command == "capitalize":
    if len(sys.argv) < 3:
        print("Please provide text!")
    else:
        text = " ".join(sys.argv[2:])
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
