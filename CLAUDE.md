# Functions Framework Python Development Guide

## Build/Test/Lint Commands
- Install dev dependencies: `pip install -e . -r requirements-test.txt`
- Run all tests: `pytest`
- Run a single test: `pytest tests/test_file.py::test_function_name -v`
- Run tests with coverage: `pytest --cov=functions_framework --cov-branch`
- Run linting: `tox -e lint`
- Format code: `black src tests setup.py conftest.py`
- Sort imports: `isort src tests setup.py conftest.py`
- Type checking: `mypy tests/test_typing.py`

## Code Style Guidelines
- License header: Include the Apache 2.0 license header in all source files
- Line length: 88 characters (Black default)
- Imports: Use isort with the config in setup.cfg
- Formatting: Use Black for auto-formatting
- Type hints: Include for all public functions/methods
- Python version: Support Python 3.7+ (see setup.py for all supported versions)
- Error handling: Raise specific exceptions with descriptive messages
- Naming: Use snake_case for variables/functions, CamelCase for classes
- Documentation: Follow Google docstring style for functions/classes