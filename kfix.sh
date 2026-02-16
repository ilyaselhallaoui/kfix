#!/bin/bash
# kfix wrapper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/venv/bin/python" -m kfix.cli "$@"
