# Tests for Transcription App

This directory contains the test suite for the Transcription App.

## Structure

- `conftest.py`: Contains pytest fixtures used across multiple test files
- `test_models.py`: Tests for database models
- `test_routes.py`: Tests for Flask routes and views
- `test_services.py`: Tests for service classes (Blob Storage, Audio Processing, etc.)
- `test_tasks.py`: Tests for Celery tasks
- `test_app.py`: Tests for app initialization and configuration
- `.env.test`: Test environment variables

## Running Tests

To run the tests, use the provided script:

```bash
./run_tests.sh
```

This will:
1. Create any necessary test directories
2. Set up the test environment
3. Run the tests with pytest
4. Generate and display coverage report

## Writing New Tests

When writing new tests:

1. Use the fixtures provided in `conftest.py` whenever possible
2. Mock external dependencies (Azure services, etc.)
3. Follow the existing pattern for test structure
4. Ensure good test coverage for new features

## Test Coverage

The test suite aims to provide high coverage of all critical components:

- Database models and operations
- HTTP routes and endpoints
- Service class methods
- Celery tasks
- Configuration and initialization 