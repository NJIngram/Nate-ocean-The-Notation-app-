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

# Delete or change the user ID if requested using a command line argument
def process_user_id_argument(args):
    """Process command line arguments for user ID management."""
    if "--delete-user-id" in args:
        # Logic to delete user ID from notes (not implemented here)
        print("User ID deletion requested. (Functionality not implemented yet)")
    elif "--change-user-id" in args:
        # Logic to change user ID in notes (not implemented here)
        print("User ID change requested. (Functionality not implemented yet)")

if __name__ == "__main__":
    # Process command line arguments for user ID management
    process_user_id_argument(sys.argv)

    # Initialize the notes application
    notes_directory = setup()
    print(f"Notes directory is set to: {notes_directory}")

#test note with user ID labeling
    test_note_content = "This is a test note."
    labeled_note = label_note_with_user_id(test_note_content)
    print("\nLabeled Note Content:")
    print(labeled_note)

