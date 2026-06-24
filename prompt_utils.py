import os
import sys
import csv
import json
import requests
import subprocess
import keyring
import keyring.errors
from pathlib import Path

SERVICE_NAME = "IVR Prompt Generator"
VOICE_MODEL  = "aura-2-thalia-en"

if getattr(sys, "frozen", False):
    BASE_DIR   = Path(sys.executable).parent
    _meipass   = Path(sys._MEIPASS)
    FFMPEG_BIN = str(_meipass / "ffmpeg.exe")
else:
    BASE_DIR   = Path(__file__).parent
    FFMPEG_BIN = "ffmpeg"

_CONFIG_FILE     = BASE_DIR / "config.json"
_DEFAULT_OUT_DIR = BASE_DIR / "output_wav"


def get_output_dir() -> Path:
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Path(data["output_dir"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return _DEFAULT_OUT_DIR


def set_output_dir(path: str) -> None:
    data = {}
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    data["output_dir"] = path
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_api_key() -> str:
    return keyring.get_password(SERVICE_NAME, "deepgram_api_key") or ""


def set_api_key(key: str) -> None:
    keyring.set_password(SERVICE_NAME, "deepgram_api_key", key)


def delete_api_key() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, "deepgram_api_key")
    except keyring.errors.PasswordDeleteError:
        pass


def convert_to_ulaw(input_path: str, output_path: str) -> None:
    command = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-ar", "8000",
        "-ac", "1",
        "-f", "wav",
        "-acodec", "pcm_mulaw",
        output_path,
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def synthesize_prompt(prompt_text: str, filename: str) -> str:
    api_key = get_api_key()
    if not api_key:
        return "[!] No API key set. Click 'API Key' to configure."

    out_dir = get_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    url = (
        f"https://api.deepgram.com/v1/speak"
        f"?model={VOICE_MODEL}&encoding=linear16&sample_rate=16000"
    )
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"text": prompt_text}, headers=headers)

    if response.status_code == 200:
        temp_path = str(out_dir / f"{filename}_temp.wav")
        final_path = str(out_dir / f"{filename}.wav")
        with open(temp_path, "wb") as f:
            f.write(response.content)
        convert_to_ulaw(temp_path, final_path)
        os.remove(temp_path)
        return f"[OK] {filename}.wav"
    else:
        return f"[ERROR] {filename}: {response.status_code} - {response.text}"


def read_prompts(csv_path: str) -> list[tuple[str, str]]:
    """
    Accepts two formats:
      Standard:  filename,Prompt text here        (two columns, recommended)
      Legacy:    "filename, Prompt text here"     (single quoted column)
    Lines starting with # are treated as comments and skipped.
    """
    prompts = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().startswith("#"):
                continue
            if len(row) >= 2:
                name = row[0].strip()
                text = row[1].strip()
            else:
                entry = row[0].strip().strip('"')
                if not entry or "," not in entry:
                    continue
                name, text = entry.split(",", 1)
                name = name.strip()
                text = text.strip()
            if name and text:
                prompts.append((name, text))
    return prompts
