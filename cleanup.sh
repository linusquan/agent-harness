#!/bin/bash
# Clean up sessions and artifacts for a fresh test run
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "This will delete:"
echo "  - sessions/*"
echo "  - .artifacts/*"
echo ""
read -p "Continue? (y/N) " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Cancelled."
  exit 0
fi

rm -rf "$PROJECT_DIR"/sessions/*
rm -rf "$PROJECT_DIR"/.artifacts/*

echo "Done."
