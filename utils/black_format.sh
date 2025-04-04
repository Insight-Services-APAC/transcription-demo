#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Read .gitignore and create a list of directories to prune
PRUNE_ARGS=()
while IFS= read -r line; do
  # Skip comments and empty lines
  [[ -z "$line" || "$line" =~ ^# ]] && continue

  # Only handle directory ignores ending in /
  if [[ "$line" == */ ]]; then
    # Remove trailing slash for consistency
    DIR="./${line%/}"
    PRUNE_ARGS+=(-path "$DIR" -prune -o)
  fi
done < .gitignore

# Find all .py files not in pruned directories and run black on them
find . "${PRUNE_ARGS[@]}" -name "*.py" -print | xargs black
