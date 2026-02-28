from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import re

app = Flask(__name__)

OUTPUT_DIR = "/tmp/tts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# רשימת קולות מה-Mac
def get_voices():
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    voices = []
    for line in result.stdout.splitlines():
        parts = re.split(r'\s{2,}', line)
        if len(parts) >= 2:
            voice = parts[0].strip()
            lang = parts[1].strip()
            voices.append({"voice": voice, "language": lang})
    return voices

@app.route("/voices")
def voices():
    return jsonify(get_voices())

@app.route("/tts")
def tts():
    text = request.args.get("text", "")
    voice = request.args.get("voice", "Carmel")
    rate = request.args.get("rate", "180")
    filename = f"{uuid.uuid4()}.aiff"
    path = os.path.join(OUTPUT_DIR, filename)
    
    # הפקודה שמייצרת קול
    subprocess.run(["say", "-v", voice, "-r", rate, "-o", path, text])
    
    return send_file(path, mimetype="audio/aiff")

app.run(host="0.0.0.0", port=5002)