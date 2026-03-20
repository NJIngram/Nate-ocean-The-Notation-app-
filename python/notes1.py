#!/usr/bin/env python3
"""
Future Proof Notes Manager - Version One (CLI)
A personal notes manager using text files with YAML headers.
Command-line interface version with 'list' command.

SETUP REMINDER:
Before running the 'list' command, copy the test notes to your notes directory:
    cp -r test-notes/* ~/.notes/
or create the directory structure:
    mkdir -p ~/.notes/notes
    cp test-notes/*.md ~/.notes/notes/
"""

import sys
from pathlib import Path

APP_NAME = "Future Proof Notes Manager"
APP_VERSION = "0.1"
SCRIPT_NAME = "notes1.py"
ROOT_NOTES_DIR_NAME = ".notes"
NESTED_NOTES_DIR_NAME = "notes"
NOTE_EXTENSIONS = (".md", ".note", ".txt")
LIST_DIVIDER_WIDTH = 60


def setup():
    """Initialize the notes application."""
    # Define the notes directory in HOME
    notes_dir = Path.home() / ROOT_NOTES_DIR_NAME

    # Check if notes directory exists
    if not notes_dir.exists():
        # For CLI version, we don't automatically create it
        pass

    return notes_dir


def parse_yaml_header(file_path):
    """
    Parse YAML front matter from a note file.
    Returns a dictionary with metadata and the content.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Check if file starts with YAML front matter
        if not lines or lines[0].strip() != '---':
            return {'title': file_path.name, 'file': file_path.name}

        # Find the closing ---
        yaml_end = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                yaml_end = i
                break

        if yaml_end == -1:
            return {'title': file_path.name, 'file': file_path.name}

        # Parse YAML lines (simple parsing for basic key: value pairs)
        metadata = {'file': file_path.name}
        for line in lines[1:yaml_end]:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                metadata[key] = value

        return metadata

    except Exception as e:
        return {'title': file_path.name, 'file': file_path.name, 'error': str(e)}


def list_notes(notes_dir):
    """List all notes in the notes directory."""
    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Error: Notes directory does not exist: {notes_dir}", file=sys.stderr)
        print(f"Create it with: mkdir -p ~/{ROOT_NOTES_DIR_NAME}/{NESTED_NOTES_DIR_NAME}", file=sys.stderr)
        print(f"Then copy test notes: cp test-notes/*.md ~/{ROOT_NOTES_DIR_NAME}/{NESTED_NOTES_DIR_NAME}/", file=sys.stderr)
        return False

    # Look for notes in the notes directory (or directly in .notes)
    notes_subdir = notes_dir / NESTED_NOTES_DIR_NAME
    search_dirs = [notes_subdir] if notes_subdir.exists() else [notes_dir]

    # Find all note files (*.md, *.note, *.txt)
    note_files = []
    for search_dir in search_dirs:
        for ext in NOTE_EXTENSIONS:
            note_files.extend(search_dir.glob(f"*{ext}"))

    if not note_files:
        print(f"No notes found in {notes_dir}")
        print("Copy test notes with: cp test-notes/*.md ~/.notes/", file=sys.stderr)
        return True

    # Parse and display notes
    print(f"Notes in {notes_dir}:")
    print("=" * LIST_DIVIDER_WIDTH)

    for note_file in sorted(note_files):
        metadata = parse_yaml_header(note_file)
        title = metadata.get('title', note_file.name)
        created = metadata.get('created', 'N/A')
        tags = metadata.get('tags', '')

        print(f"\n{note_file.name}")
        print(f"  Title: {title}")
        if created != 'N/A':
            print(f"  Created: {created}")
        if tags:
            print(f"  Tags: {tags}")

    print(f"\n{len(note_files)} note(s) found.")
    return True


def show_help():
    """Display help information."""
    help_text = """
{name} v{version}

Usage: {script} [command]

Available commands:
  help    - Display this help information
  list    - List all notes in the notes directory

Notes directory: {notes_dir}

Setup:
  To test the 'list' command, copy sample notes:
    mkdir -p ~/{root}/{nested}
    cp test-notes/*.md ~/{root}/{nested}/
    """.format(
        name=APP_NAME,
        version=APP_VERSION,
        script=SCRIPT_NAME,
        notes_dir=Path.home() / ROOT_NOTES_DIR_NAME,
        root=ROOT_NOTES_DIR_NAME,
        nested=NESTED_NOTES_DIR_NAME,
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
    elif command == "list":
        success = list_notes(notes_dir)
        finish(0 if success else 1)
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        print(f"Try '{SCRIPT_NAME} help' for more information.", file=sys.stderr)
        finish(1)


if __name__ == "__main__":
    main()
