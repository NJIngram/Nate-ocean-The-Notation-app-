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
  user-id         - Show the current user ID
  delete-id       - Delete user ID from notes
  change-id       - Change user ID in notes
  quit            - Exit the application
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




