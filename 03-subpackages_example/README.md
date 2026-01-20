# Subpackages Pattern Example

This is a complete, runnable example of the Subpackages pattern.

## Structure:
```
subpackages_example/
├── utils/
│   ├── __init__.py
│   ├── math/
│   │   ├── __init__.py
│   │   └── operations.py
│   └── text/
│       ├── __init__.py
│       └── formatting.py
└── main.py
```

## How to Run:

```bash
# Math commands
python main.py add 10 5
python main.py multiply 7 8

# Text commands
python main.py capitalize hello world
python main.py reverse python rocks

# Show help
python main.py
```

## Key Feature:
All functionality is organized in subpackages (math/, text/).
No modules directly in utils/ package.
