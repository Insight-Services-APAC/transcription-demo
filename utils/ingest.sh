#!/bin/bash

cd "$(dirname "$0")/.." || exit 1

gitingest . \
  -e "__pycache__/" \
  -e "*.pyc" \
  -e "*.pyo" \
  -e "*.pyd" \
  -e ".venv/" \
  -e "venv/" \
  -e ".env" \
  -e ".env/" \
  -e ".env.*" \
  -e ".envrc" \
  -e ".bashrc" \
  -e ".bash_profile" \
  -e ".profile" \
  -e "test_*.py" \
  -e "*_test.py" \
  -e "tests/" \
  -e "testing/" \
  -e ".pytest_cache/" \
  -e "htmlcov/" \
  -e ".coverage" \
  -e "coverage.xml" \
  -e ".tox/" \
  -e "*.md" \
  -e "*.png" \
  -e "*.ico"
