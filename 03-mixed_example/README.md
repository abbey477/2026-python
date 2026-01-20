# Mixed Pattern Example

This is a complete, runnable example of the Mixed pattern.

## Structure:
```
mixed_example/
├── utils/
│   ├── __init__.py
│   ├── core.py          ← DIRECT module
│   ├── helpers.py       ← DIRECT module
│   ├── math/            ← Subpackage
│   │   ├── __init__.py
│   │   └── operations.py
│   └── text/            ← Subpackage
│       ├── __init__.py
│       └── formatting.py
└── main.py
```

## How to Run:

```bash
# Core commands (from direct modules)
python main.py version
python main.py config

# Helper commands (from direct modules)
python main.py log "Application started"
python main.py validate 50

# Math commands (from subpackage)
python main.py add 10 5
python main.py multiply 7 8

# Text commands (from subpackage)
python main.py capitalize hello world
python main.py reverse python rocks

# Show help
python main.py
```

## Key Feature:
Has BOTH direct modules (core.py, helpers.py) AND subpackages (math/, text/).
More flexible than Subpackages pattern.
