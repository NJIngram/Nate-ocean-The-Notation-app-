import re
import shlex
import sys
import os
from pathlib import Path
import subprocess
import notes_core
from datetime import datetime, timezone

APP_NAME = "Nate Ocean: A Sea of Thoughts"
APP_VERSION = "1.5"
STARTUP_DIVIDER_WIDTH = 40
LIST_DIVIDER_WIDTH = 60

ROOT_NOTES_DIR_NAME = ".notes"
NESTED_NOTES_DIR_NAME = "notes"
NOTE_EXTENSIONS = (".md", ".note", ".txt")
PRIMARY_NOTE_EXTENSION = ".md"

USER_ID_FOOTER_LABEL = "Sailor ID"
PROMPT_LABEL = "current> "
READ_TITLE_PROMPT = "Name the bottled message to read among the waves: "
WASH_TITLE_PROMPT = "Name the bottled message to wash the captain mark from: "
COMMAND_ROUTE_PROMPT_KEY = "help"
ACTIVE_SAILOR_ID = os.getenv("USER") or os.getenv("USERNAME") or "unknown_user"

COMMAND_ALIASES = {
    "quit": ("dock", "quit", "q"),
    "new": ("cast", "new", "n"),
    "read": ("sound", "read", "r"),
    "delete": ("sink", "delete", "d"),
    "edit": ("reshape", "edit", "e"),
    "list": ("tides", "list", "l"),
    "help": ("chart", "help", "h"),
    "user-id": ("captain", "user-id", "u"),
    "delete-id": ("wash", "wash-id", "mutiny", "delete-id", "w"),
    "change-id": ("promote", "change-id", "c"),
    "save": ("bottle", "save", "s"),
    "search": ("scan", "search", "f"),
}


def command_is(command, key):
    """Return True when the entered command matches configured aliases."""
    return command in COMMAND_ALIASES[key]


def get_primary_command(key):
    """Return the canonical command word for the given command key."""
    return COMMAND_ALIASES[key][0]


def parse_command_input(raw_input):
    """Parse user input into a command token and optional argument text."""
    if not raw_input:
        return "", ""

    try:
        parts = shlex.split(raw_input)
    except ValueError:
        return "", ""

    if not parts:
        return "", ""

    command = parts[0].lower()
    argument = " ".join(parts[1:]).strip()
    return command, argument


def get_target_notes_dir(notes_dir):
    """Return the write target directory for note files."""
    nested_dir = notes_dir / NESTED_NOTES_DIR_NAME
    return nested_dir if nested_dir.exists() else notes_dir


def get_search_dirs(notes_dir):
    """Return directories that should be searched for notes."""
    nested_dir = notes_dir / NESTED_NOTES_DIR_NAME
    return [nested_dir] if nested_dir.exists() else [notes_dir]


def get_note_files(notes_dir):
    """Return all note files using configured file extensions."""
    note_files = []
    for search_dir in get_search_dirs(notes_dir):
        for ext in NOTE_EXTENSIONS:
            note_files.extend(search_dir.glob(f"*{ext}"))
    return note_files


def find_note_file(notes_dir, title):
    """Find a note by title using the primary note extension."""
    for search_dir in get_search_dirs(notes_dir):
        note_file = search_dir / f"{title}{PRIMARY_NOTE_EXTENSION}"
        if note_file.exists():
            return note_file
    return None


def build_user_footer(user_id):
    """Build the trailing footer block for note attribution."""
    return f"\n\n---\n{USER_ID_FOOTER_LABEL}: {user_id}"


def get_user_footer_strip_regex():
    """Regex for stripping the user footer from note content."""
    return rf'\n\n---\n{re.escape(USER_ID_FOOTER_LABEL)}: [^\n]*\n?$'


def get_user_footer_replace_regex():
    """Regex for replacing the user footer value in note content."""
    return rf'(\n\n---\n{re.escape(USER_ID_FOOTER_LABEL)}: )[^\n]*'


def get_user_footer_capture_regex():
    """Regex for capturing the full user footer at the end of note content."""
    return rf'(\n\n---\n{re.escape(USER_ID_FOOTER_LABEL)}: [^\n]*\n?)$'

def open_note_in_editor(note_file):
    """Open the note file in the system's default editor."""
    editor = os.getenv("EDITOR", "nano")
    subprocess.run([editor, str(note_file)])


def setup():
    """Initialize the notes application."""
    print(f"{APP_NAME} v{APP_VERSION}")
    print("=" * STARTUP_DIVIDER_WIDTH)

    notes_dir = Path.home() / ROOT_NOTES_DIR_NAME

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
    """Get the active Sailor ID for this app session."""
    return ACTIVE_SAILOR_ID


def set_current_user_id(new_id):
    """Set the active Sailor ID for this app session."""
    global ACTIVE_SAILOR_ID
    ACTIVE_SAILOR_ID = new_id

#Label notes with user ID at the bottom of the note
def label_note_with_user_id(note_content):
    """Append the current user ID to the note content."""
    user_id = get_current_user_id()
    labeled_content = f"{note_content}{build_user_footer(user_id)}"
    return labeled_content

#When help command is called, it should show the new commands for user ID management
def show_help():
    """Display help information."""
    help_text = """
Tide commands:
chart           - Unfurl this navigation chart
cast            - Cast a new thought into the sea
sound           - Read a bottled message among the waves and revise if you wish
reshape         - Rewrite a bottled message from bow to stern
sink            - Send a bottled message below by title
captain         - Reveal the active Sailor ID
mutiny          - Wash Sailor ID marks from all waves
promote-sailor       - Promote Sailor ID marks across waves
tides           - List every wave in your harbor
dock            - Return to shore

Old aliases still accepted:
help new read edit delete user-id delete-id change-id list quit save search
"""
    print(help_text)

#Create user ID management commands for showing current user ID, deleting user ID from notes, and changing user ID in notes
def show_current_user_id():
    """Show the current user ID."""
    user_id = get_current_user_id()
    print(f"The captain's mark is: {user_id}")

def delete_user_id_from_notes(notes_dir, title=""):
    """Delete user ID footer from a single note in the notes directory."""
    if not notes_dir.exists():
        print(f"Harbor not found at {notes_dir}")
        return

    title = title.strip() if title else input(WASH_TITLE_PROMPT).strip()
    if not title:
        print("Bottled message title cannot be empty.")
        return

    note_file = find_note_file(notes_dir, title)
    if not note_file:
        print(f"Bottled message '{title}' was not found among the waves in this harbor.")
        return

    content = note_file.read_text()
    new_content = re.sub(get_user_footer_strip_regex(), '', content)
    if new_content == content:
        print(f"Bottled message '{title}' has no captain mark to wash away.")
        return

    note_file.write_text(new_content)
    print(f"Captain mark washed from bottled message '{title}'.")


def change_user_id_in_notes(_notes_dir):
    """Set Sailor ID for the current session and future notes."""

    new_id = input("Enter new Sailor ID: ").strip()
    if not new_id:
        print("No Sailor ID entered. Cancelling course change.")
        return

    set_current_user_id(new_id)
    print(f"Active Sailor ID set to '{new_id}' for current and future bottled messages.")

def command_loop(notes_dir):
    """Main command loop for processing user input."""
    while True:
        try:
            raw_command = input(PROMPT_LABEL).strip()
            command, argument = parse_command_input(raw_command)

            if not command:
                continue

            if command_is(command, "quit"):
                break
            if command_is(command, "new"):
                create_new_note(notes_dir)
                continue
            if command_is(command, "read"):
                read_note(notes_dir, argument)
                continue
            if command_is(command, "delete"):
                delete_note(notes_dir)
                continue
            if command_is(command, "edit"):
                edit_note(notes_dir)
                continue
            if command_is(command, "save"):
                title = input("Name this bottled message among the waves: ").strip()
                content = input("You released a bottled message into the tide: ").strip()
                save_local_note(notes_dir, title, content)
                continue
            if command_is(command, "list"):
                list_notes(notes_dir)
                continue
            if command_is(command, "search"):
                search_notes(notes_dir, argument)
                continue
            if command_is(command, "help"):
                show_help()
                continue
            if command_is(command, "user-id"):
                show_current_user_id()
                continue
            if command in ("mutiny", "delete-id"):
                delete_user_id_from_notes(notes_dir)
                continue
            if command in ("promote-sailor", "change-id"):
                change_user_id_in_notes(notes_dir)
                continue

            print(f"The sea does not know this command: '{command}'")
            print(f"Type '{get_primary_command(COMMAND_ROUTE_PROMPT_KEY)}' to view your route.")

        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print(f"\nUse '{get_primary_command('quit')}' when you are ready to return ashore.")


def list_notes(notes_dir):
    """List all notes in the notes directory."""
    # Check if notes directory exists
    if not notes_dir.exists():
        print(f"Error: Harbor does not exist: {notes_dir}", file=sys.stderr)
        print(f"Create it with: mkdir -p ~/{ROOT_NOTES_DIR_NAME}/{NESTED_NOTES_DIR_NAME}", file=sys.stderr)
        print(
            f"Then launch sample logs: cp test-notes/*.md ~/{ROOT_NOTES_DIR_NAME}/{NESTED_NOTES_DIR_NAME}/",
            file=sys.stderr,
        )
        return False

    note_files = get_note_files(notes_dir)

    if not note_files:
        print(f"No bottled messages are charted among the waves in harbor {notes_dir}")
        print("Launch sample logs with: cp test-notes/*.md ~/.notes/", file=sys.stderr)
        return True

    # Parse and display notes
    print(f"Tonight's sea log from harbor {notes_dir}:")
    print("=" * LIST_DIVIDER_WIDTH)

    for note_file in sorted(note_files):
        metadata = parse_yaml_header(note_file)
        title = metadata.get('title', note_file.name)
        created = metadata.get('created', 'N/A')
        tags = metadata.get('tags', '')

        print(f"\n{note_file.name}")
        print(f"  Bottled Message Title: {title}")
        if created != 'N/A':
            print(f"  Cast At: {created}")
        if tags:
            print(f"  Currents: {tags}")

    print(f"\n{len(note_files)} bottled message(s) charted among the waves.")
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
    


def create_new_note(notes_dir):
    """Create a new note with user ID attribution."""
    title = input("Name this bottled message among the waves: ").strip()
    if not title:
        print("Bottled message title cannot be empty.")
        return

    content = input("You released a bottled message into the tide: ").strip()
    if not content:
        print("Bottled message content cannot be empty.")
        return

    save_local_note(notes_dir, title, content)

def delete_note(notes_dir):
    """Delete a note by title."""
    title = input("Name the bottled message to sink: ").strip()
    if not title:
        print("Bottled message title cannot be empty.")
        return

    found_note = notes_core.delete_note(notes_dir, title)

    if found_note:
        print(f"Bottled message '{title}' slipped beneath the surface.")
    else:
        print(f"Bottled message '{title}' was not found among the waves in this harbor.")

def edit_note(notes_dir):
    """Edit a note by title."""
    title = input("Name the bottled message to rewrite: ").strip()
    if not title:
        print("Bottled message title cannot be empty.")
        return

    found_note = find_note_file(notes_dir, title)

    if found_note:
        content = found_note.read_text()
        print(f"Here is the current text of bottled message '{title}' among the waves:\n{content}")
        new_content = input("Enter replacement tide text: ").strip()
        if not new_content:
            print("Bottled message content cannot be empty.")
            return

        frontmatter, _old_body = split_frontmatter(content)
        if frontmatter:
            frontmatter = update_modified_timestamp(frontmatter)
        else:
            frontmatter = build_frontmatter(title)
        labeled_content = f"{frontmatter}{new_content}{build_user_footer(get_current_user_id())}"
        found_note.write_text(labeled_content)
        print(f"Bottled message '{title}' has been reshaped.")
    else:
        print(f"Bottled message '{title}' was not found among the waves in this harbor.")

def read_note(notes_dir, title=""):
    """Read a note by title, then optionally append or change text."""
    title = title.strip() if title else input(READ_TITLE_PROMPT).strip()
    if not title:
        print("Bottled message title cannot be empty.")
        return

    found_note = find_note_file(notes_dir, title)

    if found_note:
        content = found_note.read_text()
        print(f"Bottled message '{title}' rises among the waves as:\n{content}")

        edit_choice = input("\nWould you like to shape this bottled message now? (y/n): ").strip().lower()
        if edit_choice not in ("y", "yes"):
            return

        footer_match = re.search(get_user_footer_capture_regex(), content)
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
                    print("That text was not found in this bottled message.")
                    continue
                new_text = input("Enter new tide text: ").strip()
                body = body.replace(old_text, new_text)
                print("Bottled message text updated.")
                continue

            print("Unknown tidecraft. Use add, shift, or anchor.")

        updated_content = f"{body}{footer}" if footer else label_note_with_user_id(body)
        updated_content = update_modified_timestamp(updated_content)
        found_note.write_text(updated_content)
        print(f"Bottled message '{title}' is saved, still afloat among the waves in your sea log.")
    else:
        print(f"Bottled message '{title}' was not found among the waves in this harbor.")
def build_frontmatter(title, tags=None, creator=None):
    """Build a YAML frontmatter string for a new note."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tag_list = tags if tags else "[]"
    creator = creator or get_current_user_id()
    return (
        f"---\ntitle: {title}\ncreated: {now}\nmodified: {now}\n"
        f"creator: {creator}\nlast_opened: {now}\nlast_accessed_by: {creator}\n"
        f"tags: {tag_list}\n---\n\n"
    )


def update_modified_timestamp(content):
    """Update the modified timestamp in YAML frontmatter to now."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return re.sub(r'modified: .+', f'modified: {now}', content)


def update_yaml_field(content, key, value):
    """Update or insert a single YAML frontmatter field."""
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    fm = content[:end]
    rest = content[end:]
    pattern = rf'^{re.escape(key)}: .*$'
    new_fm, count = re.subn(pattern, f'{key}: {value}', fm, flags=re.MULTILINE)
    if count > 0:
        return new_fm + rest
    return fm + f'\n{key}: {value}' + rest


def touch_note_access(content, user_id=None):
    """Update last_opened and last_accessed_by in YAML frontmatter."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    user_id = user_id or get_current_user_id()
    content = update_yaml_field(content, "last_opened", now)
    content = update_yaml_field(content, "last_accessed_by", user_id)
    return content


def split_frontmatter(content):
    """Split note content into (frontmatter, body) where frontmatter includes trailing newline."""
    if not content.startswith("---\n"):
        return "", content
    end = content.find("\n---\n", 4)
    if end == -1:
        return "", content
    fm_end = end + 5
    frontmatter = content[:fm_end] + "\n"
    body = content[fm_end:].lstrip("\n")
    return frontmatter, body


def search_notes(notes_dir, query=""):
    """Search all notes for a word or phrase in content and metadata."""
    query = query.strip() if query else input("Enter search term: ").strip()
    if not query:
        print("Search query cannot be empty.")
        return

    if not notes_dir.exists():
        print(f"Harbor not found at {notes_dir}")
        return

    note_files = get_note_files(notes_dir)
    if not note_files:
        print("No bottled messages to search among the waves.")
        return

    matches = []
    query_lower = query.lower()

    for note_file in note_files:
        content = note_file.read_text()
        if query_lower in content.lower():
            matches.append(note_file)

    if not matches:
        print(f"No bottled messages contain '{query}'.")
        return

    print(f"Found {len(matches)} bottled message(s) matching '{query}':")
    print("=" * LIST_DIVIDER_WIDTH)
    for note_file in sorted(matches):
        metadata = parse_yaml_header(note_file)
        title = metadata.get('title', note_file.name)
        print(f"  {note_file.name} — {title}")


def save_local_note(notes_dir, title, content):
    """Save a note with the given title and content, labeled with the current user ID."""
    if not title:
        print("Bottle title cannot be empty.")
        return
    if not content:
        print("Bottle content cannot be empty.")
        return

    frontmatter = build_frontmatter(title)
    labeled_content = f"{frontmatter}{content}{build_user_footer(get_current_user_id())}"

    target_dir = get_target_notes_dir(notes_dir)

    note_file = target_dir / f"{title}{PRIMARY_NOTE_EXTENSION}"
    note_file.write_text(labeled_content)
    print(f"Bottle '{title}' now drifts in your sea log at {note_file}.")

def finish():
    """Clean up and exit the application."""
    print("\nFair winds, and softer tides until we meet again.")
    sys.exit(0)


def main():
    """Main entry point for the notes application."""
    notes_dir = setup()
    command_loop(notes_dir)
    finish()

    print("NateFail: This line should not be reached. Check command loop for proper exit conditions.")

if __name__ == "__main__":
    main()




