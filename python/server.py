from flask import Flask, jsonify, request, abort, send_from_directory, session
from functools import wraps
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
import json
import mimetypes
import os
import re
import secrets
import signal
import threading
import time
import uuid
import webbrowser
import notes2

SERVER_PORT = 5001
SERVER_HOST_URL = f"http://localhost:{SERVER_PORT}"
HEARTBEAT_TIMEOUT = 6
HEARTBEAT_CHECK_INTERVAL = 2
BROWSER_OPEN_DELAY = 1.0

# Root notes directory
_ROOT_DIR = Path.home() / notes2.ROOT_NOTES_DIR_NAME

app = Flask(__name__, static_folder="static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Use a persistent secret key so sessions survive server restarts
_SECRET_FILE = _ROOT_DIR / ".flask_secret"
def _get_secret_key():
    env = os.environ.get("FLASK_SECRET")
    if env:
        return env
    _ROOT_DIR.mkdir(parents=True, exist_ok=True)
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    key = secrets.token_hex(32)
    _SECRET_FILE.write_text(key)
    return key

app.secret_key = _get_secret_key()

_USERS_FILE = _ROOT_DIR / "users.json"
_USERS_HOME = _ROOT_DIR / "users"
_USERS_HOME.mkdir(parents=True, exist_ok=True)


# ── User storage ───────────────────────────────────
def _load_users() -> dict:
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text())
    return {}


def _save_users(users: dict):
    _USERS_FILE.write_text(json.dumps(users, indent=2))


def _user_notes_dir(username: str) -> Path:
    """Return the per-user notes directory."""
    d = _USERS_HOME / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _user_attachments_dir(username: str) -> Path:
    d = _user_notes_dir(username) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Auth decorator ─────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def _current_notes_dir():
    """Return NOTES_DIR scoped to the logged-in user."""
    return _user_notes_dir(session["username"])


def _current_attachments_dir():
    return _user_attachments_dir(session["username"])


@app.route("/")
def index():
    return app.send_static_file("index.html")


# ── Auth endpoints ─────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        abort(400, description="Username and password required")

    username = data["username"].strip()
    password = data["password"]

    if not re.match(r'^[a-zA-Z0-9_\-]{2,30}$', username):
        abort(400, description="Username must be 2-30 chars: letters, digits, _ or -")
    if len(password) < 4:
        abort(400, description="Password must be at least 4 characters")

    users = _load_users()
    if username.lower() in {u.lower() for u in users}:
        abort(409, description="Username already taken")

    users[username] = {
        "password_hash": generate_password_hash(password),
        "created": time.strftime(notes2.DATETIME_FORMAT, time.gmtime())
    }
    _save_users(users)

    # Create user's notes directory
    _user_notes_dir(username)

    # Auto-login after registration
    session["username"] = username
    notes2.set_current_user_id(username)
    _record_captain(username)

    return jsonify({"message": "Account created", "username": username}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        abort(400, description="Username and password required")

    username = data["username"].strip()
    password = data["password"]

    users = _load_users()
    user = users.get(username)
    if not user or not check_password_hash(user["password_hash"], password):
        abort(401, description="Invalid username or password")

    session["username"] = username
    notes2.set_current_user_id(username)
    _record_captain(username)

    return jsonify({"message": "Logged in", "username": username})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return jsonify({"message": "Logged out"})


@app.route("/api/me", methods=["GET"])
def me():
    if "username" not in session:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "username": session["username"]})


# ── Tides: list all notes ─────────────────────────
@app.route("/api/notes", methods=["GET"])
@login_required
def list_notes():
    """Return a JSON array of all notes with their metadata."""
    notes_dir = _current_notes_dir()
    note_files = notes2.get_note_files(notes_dir)
    notes = []
    for f in sorted(note_files):
        metadata = notes2.parse_yaml_header(f)
        # Backfill creator from author if missing
        if "creator" not in metadata and "author" in metadata:
            metadata["creator"] = metadata["author"]
        notes.append(metadata)
    return jsonify(notes)


# ── Sound: read one note ──────────────────────────
@app.route("/api/notes/<note_id>", methods=["GET"])
@login_required
def get_note(note_id):
    """Return one note's metadata and content."""
    notes_dir = _current_notes_dir()
    note_file = notes2.find_note_file(notes_dir, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    content = note_file.read_text()
    # Backfill creator from author if missing
    metadata_pre = notes2.parse_yaml_header(note_file)
    if "creator" not in metadata_pre and "author" in metadata_pre:
        content = notes2.update_yaml_field(content, "creator", metadata_pre["author"])
    # Track who opened the note and when
    content = notes2.touch_note_access(content)
    note_file.write_text(content)

    metadata = notes2.parse_yaml_header(note_file)
    frontmatter, body = notes2.split_frontmatter(content)
    metadata["content"] = body
    # Also expose creator from author for frontend
    if "creator" not in metadata and "author" in metadata:
        metadata["creator"] = metadata["author"]
    return jsonify(metadata)


# ── Cast / Bottle: create a new note ──────────────
@app.route("/api/notes", methods=["POST"])
@login_required
def create_note():
    """Create a new note from JSON body."""
    data = request.get_json()
    if not data or "title" not in data or "content" not in data:
        abort(400, description="Request must include 'title' and 'content'")

    title = data["title"]
    content = data["content"]
    notes_dir = _current_notes_dir()

    user_id = data.get("author", notes2.get_current_user_id())
    # Handle tags (list or comma-separated string)
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = notes2.parse_tags(raw_tags)
    frontmatter = notes2.build_frontmatter(title, tags=raw_tags, creator=user_id)
    labeled = f"{frontmatter}{content}{notes2.build_user_footer(user_id)}"

    target_dir = notes2.get_target_notes_dir(notes_dir)
    note_file = target_dir / f"{title}{notes2.PRIMARY_NOTE_EXTENSION}"
    note_file.write_text(labeled)

    return jsonify({"message": "Note created", "file": note_file.name}), 201


# ── Reshape: update a note ────────────────────────
@app.route("/api/notes/<note_id>", methods=["PUT"])
@login_required
def update_note(note_id):
    """Update an existing note's content."""
    data = request.get_json()
    if not data or "content" not in data:
        abort(400, description="Request must include 'content'")

    notes_dir = _current_notes_dir()
    note_file = notes2.find_note_file(notes_dir, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    old_content = note_file.read_text()
    frontmatter, _old_body = notes2.split_frontmatter(old_content)
    if frontmatter:
        frontmatter = notes2.update_modified_timestamp(frontmatter)
    else:
        frontmatter = notes2.build_frontmatter(note_id)

    # Update tags if provided
    if "tags" in data:
        raw_tags = data["tags"]
        if isinstance(raw_tags, str):
            raw_tags = notes2.parse_tags(raw_tags)
        frontmatter = notes2.update_yaml_field(frontmatter, "tags", notes2.format_tags(raw_tags))

    user_id = data.get("author", notes2.get_current_user_id())
    new_content = f"{frontmatter}{data['content']}{notes2.build_user_footer(user_id)}"
    # Track who edited the note and when
    new_content = notes2.touch_note_access(new_content, user_id)
    note_file.write_text(new_content)

    return jsonify({"message": "Note updated", "file": note_file.name})


# ── Sink: delete a note ───────────────────────────
@app.route("/api/notes/<note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):
    """Delete a note by title."""
    notes_dir = _current_notes_dir()
    note_file = notes2.find_note_file(notes_dir, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    note_file.unlink()
    return jsonify({"message": "Note deleted", "file": note_file.name})


# ── Tags: list all unique tags ─────────────────────
@app.route("/api/tags", methods=["GET"])
@login_required
def list_tags():
    """Return all unique tags across the user's notes."""
    notes_dir = _current_notes_dir()
    note_files = notes2.get_note_files(notes_dir)
    tag_counts = {}
    for f in note_files:
        metadata = notes2.parse_yaml_header(f)
        tags = notes2.parse_tags(metadata.get("tags", ""))
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    return jsonify({"tags": tag_counts})


# ── Tags: update tags on a note ────────────────────
@app.route("/api/notes/<note_id>/tags", methods=["PUT"])
@login_required
def update_tags(note_id):
    """Update the tags on an existing note."""
    data = request.get_json()
    if not data or "tags" not in data:
        abort(400, description="Request must include 'tags'")

    notes_dir = _current_notes_dir()
    note_file = notes2.find_note_file(notes_dir, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    tag_list = data["tags"]
    if isinstance(tag_list, str):
        tag_list = notes2.parse_tags(tag_list)
    formatted = notes2.format_tags(tag_list)

    content = note_file.read_text()
    content = notes2.update_yaml_field(content, "tags", formatted)
    content = notes2.update_yaml_field(
        content, "modified",
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime(notes2.DATETIME_FORMAT)
    )
    note_file.write_text(content)

    return jsonify({"message": "Tags updated", "tags": tag_list})


# ── Auto-tag: suggest tags from content ────────────
@app.route("/api/auto-tags", methods=["POST"])
@login_required
def auto_tags():
    """Generate tag suggestions from title and content."""
    data = request.get_json()
    title = data.get("title", "") if data else ""
    content = data.get("content", "") if data else ""
    existing = data.get("existing_tags", []) if data else []
    suggested = notes2.generate_auto_tags(title, content, existing)
    return jsonify({"suggested": suggested})


# ── Scan: search notes ────────────────────────────
@app.route("/api/search", methods=["GET"])
@login_required
def search_notes():
    """Search notes by keyword in content."""
    query = request.args.get("q", "").strip()
    if not query:
        abort(400, description="Missing search query parameter 'q'")

    notes_dir = _current_notes_dir()
    note_files = notes2.get_note_files(notes_dir)
    results = []
    query_lower = query.lower()

    for f in note_files:
        content = f.read_text()
        if query_lower in content.lower():
            metadata = notes2.parse_yaml_header(f)
            results.append(metadata)

    return jsonify({"query": query, "count": len(results), "results": results})


# ── Captain history ────────────────────────────────
_captain_history: list[str] = []


def _record_captain(sailor_id: str):
    """Add a Sailor ID to the history (no duplicates, most recent first)."""
    if sailor_id in _captain_history:
        _captain_history.remove(sailor_id)
    _captain_history.insert(0, sailor_id)


# Seed history with the initial Sailor ID
_record_captain(notes2.get_current_user_id())


# ── Captain: get/set Sailor ID ────────────────────
@app.route("/api/captain", methods=["GET"])
@login_required
def get_captain():
    """Return the active Sailor ID."""
    return jsonify({"sailor_id": notes2.get_current_user_id()})


@app.route("/api/captain/history", methods=["GET"])
@login_required
def get_captain_history():
    """Return the list of previously used Sailor IDs."""
    return jsonify({"history": _captain_history})


# ── Promote: change the active Sailor ID ──────────
@app.route("/api/captain", methods=["PUT"])
@login_required
def promote_captain():
    """Change the active Sailor ID for this session."""
    data = request.get_json()
    if not data or "sailor_id" not in data:
        abort(400, description="Request must include 'sailor_id'")

    new_id = data["sailor_id"].strip()
    if not new_id:
        abort(400, description="Sailor ID cannot be empty")

    _record_captain(new_id)
    notes2.set_current_user_id(new_id)
    return jsonify({"message": f"Sailor ID set to '{new_id}'", "sailor_id": new_id})


# ── Mutiny / Wash: remove Sailor ID from a note ───
@app.route("/api/notes/<note_id>/wash", methods=["POST"])
@login_required
def wash_note(note_id):
    """Remove the Sailor ID footer from a single note."""
    notes_dir = _current_notes_dir()
    note_file = notes2.find_note_file(notes_dir, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    content = note_file.read_text()
    new_content = re.sub(notes2.get_user_footer_strip_regex(), '', content)
    if new_content == content:
        return jsonify({"message": "No captain mark to wash away", "changed": False})

    note_file.write_text(new_content)
    return jsonify({"message": "Captain mark washed", "changed": True})


# ── Heartbeat: shut down when the browser tab is closed ──────
_last_heartbeat = time.time()
_HEARTBEAT_TIMEOUT = HEARTBEAT_TIMEOUT


# ── Serve attachments ─────────────────────────────
@app.route("/attachments/<path:filename>")
@login_required
def serve_attachment(filename):
    """Serve an uploaded attachment file."""
    safe_name = Path(filename).name  # prevent directory traversal
    return send_from_directory(_current_attachments_dir(), safe_name)


# ── Title generation helpers ──────────────────────
def _clean_filename_to_title(filename):
    """Turn a filename into a human-readable title."""
    stem = Path(filename).stem
    # Replace separators with spaces
    title = re.sub(r'[-_]+', ' ', stem)
    # Collapse multiple spaces
    title = re.sub(r'\s+', ' ', title).strip()
    return title.title() if title else "Untitled"


def _file_type_label(mime_type):
    """Return a human label for the MIME category."""
    if not mime_type:
        return "File"
    cat = mime_type.split("/")[0]
    labels = {
        "image": "Image", "video": "Video", "audio": "Audio",
        "text": "Document", "application": "Document"
    }
    return labels.get(cat, "File")


def _generate_title(original_filename, mime_type, file_bytes):
    """Generate a context-aware title from the uploaded file."""
    name_title = _clean_filename_to_title(original_filename)
    type_label = _file_type_label(mime_type)

    # For text-based files, try to use the first meaningful line
    if mime_type and (mime_type.startswith("text/") or mime_type in (
        "application/json", "application/xml", "application/javascript",
        "application/x-yaml", "application/csv"
    )):
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            for line in text.splitlines():
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    # Truncate long first lines
                    return stripped[:80] if len(stripped) > 80 else stripped
        except Exception:
            pass

    # For PDFs, markdown, and other files, fall back to filename
    return f"{name_title} ({type_label})"


# ── Upload: import a file as a new note ───────────
@app.route("/api/upload", methods=["POST"])
@login_required
def upload_file():
    """Accept a file upload, save it, and create a note referencing it."""
    if "file" not in request.files:
        abort(400, description="No file provided")

    uploaded = request.files["file"]
    if not uploaded.filename:
        abort(400, description="Empty filename")

    original_name = uploaded.filename
    file_bytes = uploaded.read()
    mime_type = uploaded.content_type or mimetypes.guess_type(original_name)[0] or ""

    # Save the file with a unique prefix to avoid collisions
    attachments_dir = _current_attachments_dir()
    safe_stem = re.sub(r'[^\w.\-]', '_', Path(original_name).stem)[:60]
    ext = Path(original_name).suffix
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_stem}{ext}"
    dest = attachments_dir / stored_name
    dest.write_bytes(file_bytes)

    # Generate a title (can be overridden by form field)
    title = request.form.get("title", "").strip()
    if not title:
        title = _generate_title(original_name, mime_type, file_bytes)

    # Build note content with an attachment reference
    type_label = _file_type_label(mime_type)
    attachment_url = f"/attachments/{stored_name}"

    if mime_type and mime_type.startswith("image/"):
        body = f"![{original_name}]({attachment_url})\n"
    elif mime_type and mime_type.startswith("video/"):
        body = f"[{type_label}: {original_name}]({attachment_url})\n"
    elif mime_type and mime_type.startswith("audio/"):
        body = f"[{type_label}: {original_name}]({attachment_url})\n"
    else:
        body = f"[{type_label}: {original_name}]({attachment_url})\n"

    # For text files, also include inline content
    if mime_type and mime_type.startswith("text/"):
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            body += f"\n```\n{text}\n```\n"
        except Exception:
            pass

    user_id = notes2.get_current_user_id()
    frontmatter = notes2.build_frontmatter(title, creator=user_id)
    frontmatter = notes2.update_yaml_field(
        frontmatter, "attachment", stored_name
    )
    frontmatter = notes2.update_yaml_field(
        frontmatter, "source_file", original_name
    )
    frontmatter = notes2.update_yaml_field(
        frontmatter, "file_type", mime_type
    )
    labeled = f"{frontmatter}{body}{notes2.build_user_footer(user_id)}"

    # Sanitize the title for use as a filename
    safe_title = re.sub(r'[^\w\s\-]', '', title)[:80].strip()
    if not safe_title:
        safe_title = "Untitled"
    notes_dir = _current_notes_dir()
    target_dir = notes2.get_target_notes_dir(notes_dir)
    note_file = target_dir / f"{safe_title}{notes2.PRIMARY_NOTE_EXTENSION}"
    # Avoid overwriting existing notes
    counter = 1
    while note_file.exists():
        note_file = target_dir / f"{safe_title} ({counter}){notes2.PRIMARY_NOTE_EXTENSION}"
        counter += 1
    note_file.write_text(labeled)

    return jsonify({
        "message": "File uploaded and note created",
        "file": note_file.name,
        "title": title,
        "attachment": stored_name,
        "generated_title": title
    }), 201


@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    """Receive a keep-alive ping from the browser tab."""
    global _last_heartbeat
    _last_heartbeat = time.time()
    return jsonify({"status": "ok"})


def _heartbeat_watcher():
    """Background thread that shuts down the server when heartbeats stop."""
    while True:
        time.sleep(HEARTBEAT_CHECK_INTERVAL)
        if time.time() - _last_heartbeat > _HEARTBEAT_TIMEOUT:
            print("\nNo heartbeat — browser tab closed. Shutting down.")
            os.kill(os.getpid(), signal.SIGTERM)
            return


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        watcher = threading.Thread(target=_heartbeat_watcher, daemon=True)
        watcher.start()
        threading.Timer(BROWSER_OPEN_DELAY, lambda: webbrowser.open(SERVER_HOST_URL)).start()
    app.run(debug=True, port=SERVER_PORT)
