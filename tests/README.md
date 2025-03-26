# Transcription Application Test Suite

This directory contains tests for the Transcription Application. The test suite includes unit tests for individual components and integration tests for testing component interactions and API endpoints.

## Test Structure

- `unit/`: Unit tests for individual components and services
- `integration/`: Integration tests for testing component interactions
- `fixtures/`: Test fixtures and mock data
- `conftest.py`: Pytest fixtures and configuration

## Requirements

The test suite requires the following dependencies:

```
pytest
pytest-mock
bs4 (BeautifulSoup)
```

You can install these dependencies with:

```bash
pip install pytest pytest-mock beautifulsoup4
```

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Test Types

To run only unit tests:

```bash
pytest tests/unit/
```

To run only integration tests:

```bash
pytest tests/integration/
```

### Running Specific Test Files

To run tests in a specific file:

```bash
pytest tests/unit/test_blob_storage.py
```

### Running Tests with Markers

To run tests with specific markers:

```bash
pytest -m "unit"
pytest -m "integration"
pytest -m "not slow"  # Skip slow tests
```

## Test Coverage

To measure test coverage, install `pytest-cov`:

```bash
pip install pytest-cov
```

Then run:

```bash
pytest --cov=app tests/
```

For a detailed HTML coverage report:

```bash
pytest --cov=app --cov-report=html tests/
```

This will create an `htmlcov` directory with a detailed HTML report.

## Debugging Tests

For detailed test output:

```bash
pytest -v
```

For more detailed logging:

```bash
pytest --log-cli-level=DEBUG
```

## CI Integration

The test suite is designed to run in a CI environment. Make sure to set the following environment variables:

- `TESTING=True`
- `SQLALCHEMY_DATABASE_URI=sqlite:///test.db`

The tests will use a temporary SQLite database for testing purposes. 