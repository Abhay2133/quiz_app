# Test Suite

This directory contains tests for the quiz application.

## Structure

```
tests/
├── unit/           # Unit tests for individual components
│   ├── test_rounds.py
│   ├── test_scoring.py
│   ├── test_qb.py
│   └── test_validators.py
├── integration/    # Integration tests
│   ├── test_network.py
│   └── test_round_flow.py
└── fixtures/       # Test data
    └── questions/
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_rounds.py

# Run with verbose output
pytest -v
```

## Test Coverage Goal

Target: 70%+ code coverage

## Writing Tests

Follow these guidelines:
1. Use descriptive test names
2. One assertion per test (when possible)
3. Use fixtures for common setup
4. Mock external dependencies
5. Test both success and failure cases

