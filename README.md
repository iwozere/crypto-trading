# Python Project

This is a Python project template with virtual environment setup.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── README.md
├── requirements.txt
├── src/
│   └── __init__.py
└── tests/
    └── __init__.py
```

## Development

1. Make sure your virtual environment is activated
2. Install new dependencies with:
```bash
pip install package_name
pip freeze > requirements.txt
```

## Testing

Run tests with:
```bash
pytest
``` 