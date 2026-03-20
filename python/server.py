from flask import Flask, jsonify, request, abort
from pathlib import Path
import os
import re
import signal
import threading
import time
import webbrowser
import notes2

app = Flask(__name__, static_folder="static")

SERVER_PORT = 5001
SERVER_HOST_URL = f"http://localhost:{SERVER_PORT}"
HEARTBEAT_TIMEOUT = 6   # seconds without a heartbeat before shutdown
HEARTBEAT_CHECK_INTERVAL = 2  # seconds between heartbeat checks
BROWSER_OPEN_DELAY = 1.0  # seconds before opening browser

# Use the same notes directory as the CLI app
NOTES_DIR = Path.home() / notes2.ROOT_NOTES_DIR_NAME


@app.route("/")
def index():
    return app.send_static_file("index.html")


# ── Tides: list all notes ─────────────────────────
@app.route("/api/notes", methods=["GET"])
def list_notes():
    """Return a JSON array of all notes with their metadata."""
    note_files = notes2.get_note_files(NOTES_DIR)
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
def get_note(note_id):
    """Return one note's metadata and content."""
    note_file = notes2.find_note_file(NOTES_DIR, note_id)
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
def create_note():
    """Create a new note from JSON body."""
    data = request.get_json()
    if not data or "title" not in data or "content" not in data:
        abort(400, description="Request must include 'title' and 'content'")

    title = data["title"]
    content = data["content"]

    user_id = data.get("author", notes2.get_current_user_id())
    frontmatter = notes2.build_frontmatter(title, creator=user_id)
    labeled = f"{frontmatter}{content}{notes2.build_user_footer(user_id)}"

    target_dir = notes2.get_target_notes_dir(NOTES_DIR)
    note_file = target_dir / f"{title}{notes2.PRIMARY_NOTE_EXTENSION}"
    note_file.write_text(labeled)

    return jsonify({"message": "Note created", "file": note_file.name}), 201


# ── Reshape: update a note ────────────────────────
@app.route("/api/notes/<note_id>", methods=["PUT"])
def update_note(note_id):
    """Update an existing note's content."""
    data = request.get_json()
    if not data or "content" not in data:
        abort(400, description="Request must include 'content'")

    note_file = notes2.find_note_file(NOTES_DIR, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    old_content = note_file.read_text()
    frontmatter, _old_body = notes2.split_frontmatter(old_content)
    if frontmatter:
        frontmatter = notes2.update_modified_timestamp(frontmatter)
    else:
        frontmatter = notes2.build_frontmatter(note_id)

    user_id = data.get("author", notes2.get_current_user_id())
    new_content = f"{frontmatter}{data['content']}{notes2.build_user_footer(user_id)}"
    # Track who edited the note and when
    new_content = notes2.touch_note_access(new_content, user_id)
    note_file.write_text(new_content)

    return jsonify({"message": "Note updated", "file": note_file.name})


# ── Sink: delete a note ───────────────────────────
@app.route("/api/notes/<note_id>", methods=["DELETE"])
def delete_note(note_id):
    """Delete a note by title."""
    note_file = notes2.find_note_file(NOTES_DIR, note_id)
    if note_file is None:
        abort(404, description=f"Note '{note_id}' not found")

    note_file.unlink()
    return jsonify({"message": "Note deleted", "file": note_file.name})


# ── Scan: search notes ────────────────────────────
@app.route("/api/search", methods=["GET"])
def search_notes():
    """Search notes by keyword in content."""
    query = request.args.get("q", "").strip()
    if not query:
        abort(400, description="Missing search query parameter 'q'")

    note_files = notes2.get_note_files(NOTES_DIR)
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
def get_captain():
    """Return the active Sailor ID."""
    return jsonify({"sailor_id": notes2.get_current_user_id()})


@app.route("/api/captain/history", methods=["GET"])
def get_captain_history():
    """Return the list of previously used Sailor IDs."""
    return jsonify({"history": _captain_history})


# ── Promote: change the active Sailor ID ──────────
@app.route("/api/captain", methods=["PUT"])
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
def wash_note(note_id):
    """Remove the Sailor ID footer from a single note."""
    note_file = notes2.find_note_file(NOTES_DIR, note_id)
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
        if time.time() - _last_heartbeat > HEARTBEAT_TIMEOUT:
            print("\nNo heartbeat — browser tab closed. Shutting down.")
            os.kill(os.getpid(), signal.SIGTERM)
            return


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        watcher = threading.Thread(target=_heartbeat_watcher, daemon=True)
        watcher.start()
        threading.Timer(BROWSER_OPEN_DELAY, lambda: webbrowser.open(SERVER_HOST_URL)).start()
    app.run(debug=True, port=SERVER_PORT)
