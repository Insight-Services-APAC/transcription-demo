#!/bin/bash

# Create test uploads directory if it doesn't exist
mkdir -p tests/uploads

# Setup environment
export FLASK_ENV=testing
export PYTHONPATH=$(pwd)

# Copy test environment file to .env for testing
cp tests/.env.test .env.test

# Run tests with test environment
DOTENV_PATH=.env.test pytest --cov=app tests/ -v

# Show coverage report
coverage report -m

# Clean up
rm .env.test 