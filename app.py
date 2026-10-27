from flask import Flask, render_template, request, jsonify, send_from_directory, abort, send_file
from pathlib import Path
import csv
import re
import os

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DICTIONARY_FILE = BASE_DIR / "rumi-jawi.tsv"
RESOURCE_DIR = BASE_DIR / "bahan_jawi"
RESOURCE_DIR.mkdir(exist_ok=True)

def load_dictionary():
    """Load Rumi-Jawi pairs from a UTF-8 TSV file."""
    dictionary = {}
    if not DICTIONARY_FILE.exists():
        return dictionary

    with DICTIONARY_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, delimiter="\t")
        for row in reader:
            if not row or len(row) < 2:
                continue
            rumi, jawi = row[0].strip(), row[1].strip()
            if not rumi or not jawi:
                continue
            if rumi.lower() == "rumi" and jawi.lower() == "jawi":
                continue
            dictionary[rumi.lower()] = jawi
    return dictionary

def translate_text(text):
    """
    Dictionary-based conversion.
    Words not found in the dictionary are left in Rumi, rather than guessed.
    Punctuation and spacing are preserved.
    """
    dictionary = load_dictionary()
    tokens = re.findall(r"\w+|[^\w]+", text, flags=re.UNICODE)
    output = []
    unknown = []

    for token in tokens:
        if token.isspace() or not re.match(r"^\w+$", token, flags=re.UNICODE):
            output.append(token)
            continue

        converted = dictionary.get(token.lower())
        if converted:
            # Keep the original capitalization only for the Rumi side; Jawi output
            # uses the spelling stored in the reviewed dictionary.
            output.append(converted)
        else:
            output.append(token)
            if token.lower() not in unknown:
                unknown.append(token.lower())

    return "".join(output), unknown

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Sila masukkan perkataan atau ayat dalam Rumi."}), 400

    result, unknown = translate_text(text)
    return jsonify({
        "input": text,
        "result": result,
        "unknown_words": unknown,
        "dictionary_count": len(load_dictionary())
    })

@app.route("/resources")
def resources():
    items = []
    if RESOURCE_DIR.exists():
        for path in sorted(RESOURCE_DIR.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".xlsx", ".csv"}:
                items.append({
                    "name": path.name,
                    "url": f"/download/resource/{path.name}",
                    "size": path.stat().st_size
                })
    return jsonify(items)

@app.route("/download/dictionary")
def download_dictionary():
    if not DICTIONARY_FILE.exists():
        abort(404)
    return send_file(DICTIONARY_FILE, as_attachment=True, download_name="rumi-jawi.tsv")

@app.route("/download/resource/<path:filename>")
def download_resource(filename):
    # send_from_directory safely prevents path traversal outside RESOURCE_DIR.
    if not RESOURCE_DIR.exists():
        abort(404)
    return send_from_directory(RESOURCE_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    # For local development only. For public deployment, use a production WSGI server.
    app.run(debug=True)
