#!/bin/bash

# Exit on error
set -e

# Get list of ignored paths from .gitignore and convert them to find-compatible prune paths
PRUNE_PATHS=()
while IFS= read -r line; do
  # Skip empty lines and comments
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  # Only handle directories for pruning
  if [[ "$line" == */ ]]; then
    PRUNE_PATHS+=(-path "./${line%/}" -prune -o)
  fi
done < .gitignore

# Build the find command
# Note: "${PRUNE_PATHS[@]}" expands into -path ./folder -prune -o for each ignored dir
eval find . \( "${PRUNE_PATHS[@]}" -false \) -o -name "*.py" -print | xargs black
