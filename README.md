# pydocs

Interactive Python package documentation explorer for the terminal.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
# Overview of a package
pydocs json

# Inspect a specific function
pydocs json.dumps

# Inspect a class
pydocs json.JSONEncoder

# Show source code
pydocs json.dumps --source

# Show docstring only
pydocs json.dumps --doc

# Include private members
pydocs json --private

# Deeper tree view
pydocs urllib.parse --depth 3
```

## Options

- `--source, -s`: Show source code only
- `--doc, -d`: Show docstring only
- `--signature, -g`: Show signature only
- `--private, -p`: Include private members (starting with _)
- `--imported, -i`: Include members imported from other modules
- `--depth N, -n N`: Maximum depth for tree display (default: 2)
- `--no-color`: Disable colored output
- `--json`: Output as JSON
