from pathlib import Path
import re


ROOT_NOTES_DIR_NAME = ".notes"
NESTED_NOTES_DIR_NAME = "notes"
NOTE_EXTENSIONS = (".md", ".note", ".txt")
PRIMARY_NOTE_EXTENSION = ".md"
USER_ID_FOOTER_LABEL = "Sailor ID"


def get_default_notes_dir() -> Path:
	"""Return the default notes directory path in the user's home folder."""
	return Path.home() / ROOT_NOTES_DIR_NAME


def get_target_notes_dir(notes_dir: Path) -> Path:
	"""Return where new note files should be written."""
	nested_dir = notes_dir / NESTED_NOTES_DIR_NAME
	return nested_dir if nested_dir.exists() else notes_dir


def get_search_dirs(notes_dir: Path) -> list[Path]:
	"""Return directories that should be scanned for notes."""
	nested_dir = notes_dir / NESTED_NOTES_DIR_NAME
	return [nested_dir] if nested_dir.exists() else [notes_dir]


def get_note_files(notes_dir: Path) -> list[Path]:
	"""Return all note files in the configured search directories."""
	note_files: list[Path] = []
	for search_dir in get_search_dirs(notes_dir):
		for ext in NOTE_EXTENSIONS:
			note_files.extend(search_dir.glob(f"*{ext}"))
	return note_files


def find_note_file(notes_dir: Path, title: str) -> Path | None:
	"""Find one note by title using the primary extension."""
	for search_dir in get_search_dirs(notes_dir):
		note_file = search_dir / f"{title}{PRIMARY_NOTE_EXTENSION}"
		if note_file.exists():
			return note_file
	return None


def build_user_footer(user_id: str, footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Build the attribution footer block appended to note text."""
	return f"\n\n---\n{footer_label}: {user_id}"


def get_user_footer_strip_regex(footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Regex that removes a trailing user footer from note content."""
	return rf'\n\n---\n{re.escape(footer_label)}: [^\n]*\n?$'


def get_user_footer_replace_regex(footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Regex that replaces only the user ID value inside the footer."""
	return rf'(\n\n---\n{re.escape(footer_label)}: )[^\n]*'


def get_user_footer_capture_regex(footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Regex that captures a full trailing user footer block."""
	return rf'(\n\n---\n{re.escape(footer_label)}: [^\n]*\n?)$'


def label_note_content(content: str, user_id: str, footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Return note content with attribution footer attached."""
	return f"{content}{build_user_footer(user_id, footer_label)}"


def strip_user_footer(content: str, footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Remove a trailing user footer from content if present."""
	return re.sub(get_user_footer_strip_regex(footer_label), "", content)


def replace_user_footer_id(content: str, new_user_id: str, footer_label: str = USER_ID_FOOTER_LABEL) -> str:
	"""Replace user ID in trailing footer if footer is present."""
	return re.sub(get_user_footer_replace_regex(footer_label), rf'\g<1>{new_user_id}', content)


def split_note_body_and_footer(content: str, footer_label: str = USER_ID_FOOTER_LABEL) -> tuple[str, str]:
	"""Split note content into body and trailing footer block."""
	footer_match = re.search(get_user_footer_capture_regex(footer_label), content)
	if not footer_match:
		return content.rstrip("\n"), ""

	footer = footer_match.group(1)
	body = content[:-len(footer)].rstrip("\n")
	return body, footer


def create_note(notes_dir: Path, title: str, content: str, user_id: str) -> Path:
    """Create a new note with given title and content, returning the note file path."""
    note_file = get_target_notes_dir(notes_dir) / f"{title}{PRIMARY_NOTE_EXTENSION}"
    note_file.write_text(label_note_content(content, user_id))
    return note_file


def save_note(notes_dir: Path, title: str, content: str, user_id: str) -> Path:
	"""Save note content by title (same behavior as create_note)."""
	return create_note(notes_dir, title, content, user_id)


def read_note(notes_dir: Path, title: str) -> tuple[Path, str] | None:
	"""Read one note by title and return its path and content."""
	note_file = find_note_file(notes_dir, title)
	if not note_file:
		return None
	return note_file, note_file.read_text()


def update_note(notes_dir: Path, title: str, content: str, user_id: str) -> Path | None:
	"""Replace note content (with footer attribution) for one note by title."""
	note_file = find_note_file(notes_dir, title)
	if not note_file:
		return None
	note_file.write_text(label_note_content(content, user_id))
	return note_file


def delete_note(notes_dir: Path, title: str) -> Path | None:
	"""Delete one note by title and return deleted path, else None."""
	note_file = find_note_file(notes_dir, title)
	if not note_file:
		return None
	note_file.unlink()
	return note_file


def wash_note_user_id(notes_dir: Path, title: str, footer_label: str = USER_ID_FOOTER_LABEL) -> tuple[Path, bool] | None:
	"""Remove user footer from one note by title.

	Returns (path, changed) when note exists, otherwise None.
	"""
	note_file = find_note_file(notes_dir, title)
	if not note_file:
		return None

	content = note_file.read_text()
	new_content = strip_user_footer(content, footer_label)
	changed = new_content != content
	if changed:
		note_file.write_text(new_content)

	return note_file, changed


def relabel_all_note_user_ids(notes_dir: Path, new_user_id: str, footer_label: str = USER_ID_FOOTER_LABEL) -> int:
	"""Update user ID in footer for all notes and return number of changed files."""
	count = 0
	for note_file in get_note_files(notes_dir):
		content = note_file.read_text()
		new_content = replace_user_footer_id(content, new_user_id, footer_label)
		if new_content != content:
			note_file.write_text(new_content)
			count += 1
	return count


def parse_yaml_header(file_path: Path) -> dict:
	"""Parse simple YAML front matter from a note file."""
	try:
		with open(file_path, "r", encoding="utf-8") as f:
			lines = f.readlines()

		if not lines or lines[0].strip() != "---":
			return {"title": file_path.name, "file": file_path.name}

		yaml_end = -1
		for i in range(1, len(lines)):
			if lines[i].strip() == "---":
				yaml_end = i
				break

		if yaml_end == -1:
			return {"title": file_path.name, "file": file_path.name}

		metadata = {"file": file_path.name}
		for line in lines[1:yaml_end]:
			line = line.strip()
			if ":" in line:
				key, value = line.split(":", 1)
				metadata[key.strip()] = value.strip()

		return metadata
	except Exception as e:
		return {"title": file_path.name, "file": file_path.name, "error": str(e)}
