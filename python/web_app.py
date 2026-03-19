#using my constants and functions from notes_core.py to build a web app
from flask import Flask, request, render_template, redirect, url_for
from pathlib import Path
from notes_core import get_default_notes_dir, create_note, find_note_file, get_note_files

app = Flask(__name__)
notes_dir = get_default_notes_dir()

#home route to display all webpage notes
@app.route('/')
def home():
    note_files = get_note_files(notes_dir)
    notes = []
    for note_file in note_files:
        with open(note_file, 'r') as f:
            content = f.read()
            notes.append({'title': note_file.stem, 'content': content})
    return render_template('home.html', notes=notes)
