import re
import sys
import os
from pathlib import Path

def setup():
    """Initialize the notes application."""
    print("Nate Ocean Notes Manager v1.2")
    print("=" * 40)

    notes_dir = Path.home() / ".notes"

    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Notes directory not found at {notes_dir}")
        print("Run 'notes init' to create it.")
    else:
        print(f"Notes directory: {notes_dir}")

    print()

    return notes_dir

#Code for reading current user ID and labeling notes with user ID at the bottom of the note
def get_current_user_id():
    """Get the current user ID from the environment."""
    return os.getenv("USER") or os.getenv("USERNAME") or "unknown_user"

#Label notes with user ID at the bottom of the note
def label_note_with_user_id(note_content):
    """Append the current user ID to the note content."""
    user_id = get_current_user_id()
    labeled_content = f"{note_content}\n\n---\nNote created by: {user_id}"
    return labeled_content

#When help command is called, it should show the new commands for user ID management
def show_help():
    """Display help information."""
    help_text = """
Available commands:
  help            - Display this help information
  new             - Create a new note
  user-id         - Show the current user ID
  delete-id       - Delete user ID from notes
  change-id       - Change user ID in notes
  quit            - Exit the application
  list            - List all notes in the notes directory
"""
    print(help_text)

#Create user ID management commands for showing current user ID, deleting user ID from notes, and changing user ID in notes
def show_current_user_id():
    """Show the current user ID."""
    user_id = get_current_user_id()
    print(f"Current user ID: {user_id}")

def delete_user_id_from_notes(notes_dir):
    """Delete user ID footer from all notes in the notes directory."""
    if not notes_dir.exists():
        print(f"Notes directory not found at {notes_dir}")
        return

    note_files = list(notes_dir.glob("*.md")) + list(notes_dir.glob("*.txt"))
    if not note_files:
        print("No notes found.")
        return

    count = 0
    for note_file in note_files:
        content = note_file.read_text()
        new_content = re.sub(r'\n\n---\nNote created by: [^\n]*\n?$', '', content)
        if new_content != content:
            note_file.write_text(new_content)
            count += 1

    print(f"Removed user ID footer from {count} note(s).")


def change_user_id_in_notes(notes_dir):
    """Change user ID in all notes to a new value entered by the user."""
    if not notes_dir.exists():
        print(f"Notes directory not found at {notes_dir}")
        return

    new_id = input("Enter new user ID: ").strip()
    if not new_id:
        print("No user ID entered. Aborting.")
        return

    note_files = list(notes_dir.glob("*.md")) + list(notes_dir.glob("*.txt"))
    if not note_files:
        print("No notes found.")
        return

    count = 0
    for note_file in note_files:
        content = note_file.read_text()
        new_content = re.sub(
            r'(\n\n---\nNote created by: )[^\n]*',
            rf'\g<1>{new_id}',
            content
        )
        if new_content != content:
            note_file.write_text(new_content)
            count += 1

    print(f"Updated user ID to '{new_id}' in {count} note(s).")

def command_loop(notes_dir):
    """Main command loop for processing user input."""
    while True:
        try:
            command = input("notes> ").strip().lower()

            if not command:
                continue

            if command == "quit":
                break
            if command == "help":
                show_help()
                continue
            if command == "user-id":
                show_current_user_id()
                continue
            if command == "delete-id":
                delete_user_id_from_notes(notes_dir)
                continue
            if command == "change-id":
                change_user_id_in_notes(notes_dir)
                continue

            print(f"Unknown command: '{command}'")
            print("Type 'help' for available commands.")

        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit.")


def list_notes(notes_dir):
    """List all notes in the notes directory."""
    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Error: Notes directory does not exist: {notes_dir}", file=sys.stderr)
        print("Create it with: mkdir -p ~/.notes/notes", file=sys.stderr)
        print("Then copy test notes: cp test-notes/*.md ~/.notes/notes/", file=sys.stderr)
        return False

    # Look for notes in the notes directory (or directly in .notes)
    notes_subdir = notes_dir / "notes"
    search_dirs = [notes_subdir] if notes_subdir.exists() else [notes_dir]

    # Find all note files (*.md, *.note, *.txt)
    note_files = []
    for search_dir in search_dirs:
        note_files.extend(search_dir.glob("*.md"))
        note_files.extend(search_dir.glob("*.note"))
        note_files.extend(search_dir.glob("*.txt"))

    if not note_files:
        print(f"No notes found in {notes_dir}")
        print("Copy test notes with: cp test-notes/*.md ~/.notes/", file=sys.stderr)
        return True

    # Parse and display notes
    print(f"Notes in {notes_dir}:")
    print("=" * 60)

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
    

#Notation
def create_new_note(notes_dir):
    """Create a new note and label it with the current user ID."""
    title = input("Enter note title: ").strip()
    if not title:
        print("Note title cannot be empty.")
        return

    content = input("Enter note content (end with an empty line):\n")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    content += "\n".join(lines)

    labeled_content = label_note_with_user_id(content)

    note_file = notes_dir / f"{title}.md"
    note_file.write_text(labeled_content)
    print(f"Note '{title}' created successfully at {note_file}.")

def finish():
    """Clean up and exit the application."""
    print("\nGoodbye!")
    sys.exit(0)


def main():
    """Main entry point for the notes application."""
    notes_dir = setup()
    command_loop(notes_dir)
    finish()

if __name__ == "__main__":
    main()




