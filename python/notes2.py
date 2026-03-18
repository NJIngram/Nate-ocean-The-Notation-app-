import re
import sys
import os
from pathlib import Path

def setup():
    """Initialize the notes application."""
    print("Nate Ocean: A Sea of Thoughts v1.5")
    print("=" * 40)

    notes_dir = Path.home() / ".notes"

    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Your harbor sleeps beyond sight: {notes_dir}")
        print("Run 'notes init' to raise the lanterns.")
    else:
        print(f"Your harbor awaits at: {notes_dir}")

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
    labeled_content = f"{note_content}\n\n---\nSailor ID: {user_id}"
    return labeled_content

#When help command is called, it should show the new commands for user ID management
def show_help():
    """Display help information."""
    help_text = """
Tide commands:
chart           - Unfurl this navigation chart
cast            - Cast a new thought into the sea
sound           - Read a wave and revise if you wish
reshape         - Rewrite a wave from bow to stern
sink            - Send a wave below by title
captain         - Reveal the active Sailor ID
mutiny          - Wash Sailor ID marks from all waves
promote-sailor       - Promote Sailor ID marks across waves
tides           - List every wave in your harbor
dock            - Return to shore

Old aliases still accepted:
help new read edit delete user-id delete-id change-id list quit
"""
    print(help_text)

#Create user ID management commands for showing current user ID, deleting user ID from notes, and changing user ID in notes
def show_current_user_id():
    """Show the current user ID."""
    user_id = get_current_user_id()
    print(f"The captain's mark is: {user_id}")

def delete_user_id_from_notes(notes_dir):
    """Delete user ID footer from all notes in the notes directory."""
    if not notes_dir.exists():
        print(f"Harbor not found at {notes_dir}")
        return

    note_files = list(notes_dir.glob("*.md")) + list(notes_dir.glob("*.txt"))
    if not note_files:
        print("No notes are currently floating in this harbor.")
        return

    count = 0
    for note_file in note_files:
        content = note_file.read_text()
        new_content = re.sub(r'\n\n---\nSailor ID: [^\n]*\n?$', '', content)
        if new_content != content:
            note_file.write_text(new_content)
            count += 1

    print(f"Removed Sailor ID marks from {count} note(s).")


def change_user_id_in_notes(notes_dir):
    """Change user ID in all notes to a new value entered by the user."""
    if not notes_dir.exists():
        print(f"Harbor not found at {notes_dir}")
        return

    new_id = input("Enter new Sailor ID: ").strip()
    if not new_id:
        print("No Sailor ID entered. Cancelling course change.")
        return

    note_files = list(notes_dir.glob("*.md")) + list(notes_dir.glob("*.txt"))
    if not note_files:
        print("No notes are currently floating in this harbor.")
        return

    count = 0
    for note_file in note_files:
        content = note_file.read_text()
        new_content = re.sub(
            r'(\n\n---\nSailor ID: )[^\n]*',
            rf'\g<1>{new_id}',
            content
        )
        if new_content != content:
            note_file.write_text(new_content)
            count += 1

    print(f"Updated Sailor ID to '{new_id}' in {count} note(s).")

def command_loop(notes_dir):
    """Main command loop for processing user input."""
    while True:
        try:
            command = input("current> ").strip().lower()

            if not command:
                continue

            if command in ("dock", "quit"):
                break
            if command in ("cast", "new"):
                create_new_note(notes_dir)
                continue
            if command in ("sound", "read"):
                read_note(notes_dir)
                continue
            if command in ("sink", "delete"):
                delete_note(notes_dir)
                continue
            if command in ("reshape", "edit"):
                edit_note(notes_dir)
                continue
            if command in ("tides", "list"):
                list_notes(notes_dir)
                continue
            if command in ("chart", "help"):
                show_help()
                continue
            if command in ("captain", "user-id"):
                show_current_user_id()
                continue
            if command in ("mutiny", "delete-id"):
                delete_user_id_from_notes(notes_dir)
                continue
            if command in ("promote-sailor", "change-id"):
                change_user_id_in_notes(notes_dir)
                continue

            print(f"The sea does not know this command: '{command}'")
            print("Type 'chart' to view your route.")

        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nUse 'dock' when you are ready to return ashore.")


def list_notes(notes_dir):
    """List all notes in the notes directory."""
    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Error: Harbor does not exist: {notes_dir}", file=sys.stderr)
        print("Create it with: mkdir -p ~/.notes/notes", file=sys.stderr)
        print("Then launch sample logs: cp test-notes/*.md ~/.notes/notes/", file=sys.stderr)
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
        print(f"No waves are charted in harbor {notes_dir}")
        print("Launch sample logs with: cp test-notes/*.md ~/.notes/", file=sys.stderr)
        return True

    # Parse and display notes
    print(f"Tonight's sea log from harbor {notes_dir}:")
    print("=" * 60)

    for note_file in sorted(note_files):
        metadata = parse_yaml_header(note_file)
        title = metadata.get('title', note_file.name)
        created = metadata.get('created', 'N/A')
        tags = metadata.get('tags', '')

        print(f"\n{note_file.name}")
        print(f"  Wave Title: {title}")
        if created != 'N/A':
            print(f"  Cast At: {created}")
        if tags:
            print(f"  Currents: {tags}")

    print(f"\n{len(note_files)} wave(s) charted.")
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
    title = input("Name this wave: ").strip()
    if not title:
        print("Wave title cannot be empty.")
        return

    content = input("Pour a thought into the tide: ").strip()
    if not content:
        print("Wave content cannot be empty.")
        return

    labeled_content = label_note_with_user_id(content)

    notes_subdir = notes_dir / "notes"
    target_dir = notes_subdir if notes_subdir.exists() else notes_dir

    note_file = target_dir / f"{title}.md"
    note_file.write_text(labeled_content)
    print(f"Wave '{title}' now drifts in your sea log at {note_file}.")

def delete_note(notes_dir):
    """Delete a note by title."""
    title = input("Name the wave to sink: ").strip()
    if not title:
        print("Wave title cannot be empty.")
        return

    notes_subdir = notes_dir / "notes"
    search_dirs = [notes_subdir] if notes_subdir.exists() else [notes_dir]

    found_note = None
    for search_dir in search_dirs:
        note_file = search_dir / f"{title}.md"
        if note_file.exists():
            found_note = note_file
            break

    if found_note:
        found_note.unlink()
        print(f"Wave '{title}' slipped beneath the surface.")
    else:
        print(f"Wave '{title}' was not found in this harbor.")

def edit_note(notes_dir):
    """Edit a note by title."""
    title = input("Name the wave to rewrite: ").strip()
    if not title:
        print("Wave title cannot be empty.")
        return

    notes_subdir = notes_dir / "notes"
    search_dirs = [notes_subdir] if notes_subdir.exists() else [notes_dir]

    found_note = None
    for search_dir in search_dirs:
        note_file = search_dir / f"{title}.md"
        if note_file.exists():
            found_note = note_file
            break

    if found_note:
        content = found_note.read_text()
        print(f"Here is the current tide text of '{title}':\n{content}")
        new_content = input("Enter replacement tide text: ").strip()
        if not new_content:
            print("Wave content cannot be empty.")
            return

        labeled_content = label_note_with_user_id(new_content)
        found_note.write_text(labeled_content)
        print(f"Wave '{title}' has been reshaped.")
    else:
        print(f"Wave '{title}' was not found in this harbor.")

def read_note(notes_dir):
    """Read a note by title, then optionally append or change text."""
    title = input("Name the wave to read: ").strip()
    if not title:
        print("Wave title cannot be empty.")
        return

    notes_subdir = notes_dir / "notes"
    search_dirs = [notes_subdir] if notes_subdir.exists() else [notes_dir]

    found_note = None
    for search_dir in search_dirs:
        note_file = search_dir / f"{title}.md"
        if note_file.exists():
            found_note = note_file
            break

    if found_note:
        content = found_note.read_text()
        print(f"Wave '{title}' comes ashore as:\n{content}")

        edit_choice = input("\nWould you like to shape this wave now? (y/n): ").strip().lower()
        if edit_choice not in ("y", "yes"):
            return

        footer_match = re.search(r'(\n\n---\nSailor ID: [^\n]*\n?)$', content)
        footer = footer_match.group(1) if footer_match else ""
        body = content[:-len(footer)].rstrip("\n") if footer else content.rstrip("\n")

        while True:
            action = input("Choose a tidecraft [add/shift/anchor]: ").strip().lower()
            if action in ("anchor", "done"):
                break

            if action in ("add", "append"):
                extra_text = input("Enter text to append: ").strip()
                if not extra_text:
                    print("No text entered. The tide remains unchanged.")
                    continue
                body = f"{body}\n{extra_text}" if body else extra_text
                print("New text added to the wave.")
                continue

            if action in ("shift", "change"):
                old_text = input("Enter text to replace: ").strip()
                if not old_text:
                    print("Target text cannot be empty.")
                    continue
                if old_text not in body:
                    print("That text was not found in this wave.")
                    continue
                new_text = input("Enter new tide text: ").strip()
                body = body.replace(old_text, new_text)
                print("Wave text updated.")
                continue

            print("Unknown tidecraft. Use add, shift, or anchor.")

        updated_content = f"{body}{footer}" if footer else label_note_with_user_id(body)
        found_note.write_text(updated_content)
        print(f"Wave '{title}' is saved, still afloat in your sea log.")
    else:
        print(f"Wave '{title}' was not found in this harbor.")

def finish():
    """Clean up and exit the application."""
    print("\nFair winds, and softer tides until we meet again.")
    sys.exit(0)


def main():
    """Main entry point for the notes application."""
    notes_dir = setup()
    command_loop(notes_dir)
    finish()

if __name__ == "__main__":
    main()




