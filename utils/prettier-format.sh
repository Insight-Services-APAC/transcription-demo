#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Read .gitignore and build prune arguments for find
PRUNE_ARGS=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  if [[ "$line" == */ ]]; then
    DIR="./${line%/}"
    PRUNE_ARGS+=(-path "$DIR" -prune -o)
  fi
done < .gitignore

# Find all .js files not in pruned dirs and run Prettier on them
find . "${PRUNE_ARGS[@]}" -name "*.js" -print | xargs npx prettier --write
