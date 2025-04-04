#!/bin/bash
cd "$(dirname "$0")/.." || exit 1

# Build a list of pruned paths from .gitignore
PRUNE_ARGS=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  if [[ "$line" == */ ]]; then
    DIR="./${line%/}"
    PRUNE_ARGS+=(-path "$DIR" -prune -o)
  fi
done < .gitignore

# Find all HTML/Jinja files not in ignored dirs and format them with djlint
find . "${PRUNE_ARGS[@]}" \( -name "*.html" -o -name "*.jinja" -o -name "*.jinja2" \) -print | xargs djlint --reformat --profile=jinja
