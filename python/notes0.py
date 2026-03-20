#!/usr/bin/env python3
"""
Future Proof Notes Manager - Version Zero (CLI)
A personal notes manager using text files with YAML headers.
Command-line interface version.
"""

import sys
from pathlib import Path

APP_NAME = "Future Proof Notes Manager"
APP_VERSION = "0.0"
SCRIPT_NAME = "notes0.py"
ROOT_NOTES_DIR_NAME = ".notes"


def setup():
    """Initialize the notes application."""
    # Define the notes directory in HOME
    notes_dir = Path.home() / ROOT_NOTES_DIR_NAME

    # Check if notes directory exists (silent check for CLI version)
    if not notes_dir.exists():
        # For CLI version, we don't automatically display this
        # It will be shown if needed by specific commands
        pass

    return notes_dir


def show_help():
    """Display help information."""
    help_text = """
{name} v{version}

Usage: {script} [command]

Available commands:
  help    - Display this help information

Notes directory: {notes_dir}
    """.format(
        name=APP_NAME,
        version=APP_VERSION,
        script=SCRIPT_NAME,
        notes_dir=Path.home() / ROOT_NOTES_DIR_NAME,
    )
    print(help_text.strip())


def finish(exit_code=0):
    """Clean up and exit the application."""
    sys.exit(exit_code)


def main():
    """Main entry point for the notes CLI application."""
    # Setup
    notes_dir = setup()

    # Parse command-line arguments
    if len(sys.argv) < 2:
        # No command provided
        print("Error: No command provided.", file=sys.stderr)
        print(f"Usage: {SCRIPT_NAME} [command]", file=sys.stderr)
        print(f"Try '{SCRIPT_NAME} help' for more information.", file=sys.stderr)
        finish(1)

    command = sys.argv[1].lower()

    # Process command
    if command == "help":
        show_help()
        finish(0)
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        print(f"Try '{SCRIPT_NAME} help' for more information.", file=sys.stderr)
        finish(1)


if __name__ == "__main__":
    main()
