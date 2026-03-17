import sys
import os
from pathlib import Path

def setup():
    """Initialize the notes application."""
    notes_dir = Path.home() / ".notes"

    # Check if notes directory exists
    if not notes_dir.exists():
        pass

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
    help_text = """Available commands:
    help            - Display this help information
    delete-user-id  - Delete user ID from notes
    change-user-id  - Change user ID in notes
"""
    print(help_text)

#Create user ID management commands (delete-user-id and change-user-id) - these are placeholders for now
def delete_user_id_from_notes():
    """Delete user ID from notes."""
    print("Delete user ID from notes - feature not implemented yet.")

def change_user_id_in_notes():
    """Change user ID in notes."""
    print("Change user ID in notes - feature not implemented yet.")

#Process command line arguments for user ID management
def process_command(args):
    """Process command line arguments for user ID management."""
    if len(args) < 2:
        print("Error: No command provided.", file=sys.stderr)
        print("Try 'notes2.py help' for more information.", file=sys.stderr)
        return 1

    command = args[1].lower()
    if command == "help":
        show_help()
        return 0
    if command == "delete-user-id":
        delete_user_id_from_notes()
        return 0
    if command == "change-user-id":
        change_user_id_in_notes()
        return 0

    print(f"Error: Unknown command '{command}'", file=sys.stderr)
    print("Try 'notes2.py help' for more information.", file=sys.stderr)
    return 1

if __name__ == "__main__":
    # Process command line arguments for user ID management
    exit_code = process_command(sys.argv)
    if exit_code != 0:
        sys.exit(exit_code)

    # Skip demo output when user requested help or command actions.
    if len(sys.argv) > 1:
        sys.exit(0)

    # Initialize the notes application
    notes_directory = setup()
    print(f"Notes directory is set to: {notes_directory}")

#test note with user ID labeling
    test_note_content = "This is a test note."
    labeled_note = label_note_with_user_id(test_note_content)
    print("\nLabeled Note Content:")
    print(labeled_note)




