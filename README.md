# IVR Prompt Generator

A Windows desktop application that converts IVR phone prompt scripts into properly formatted audio files for upload to a contact center phone system. It uses Deepgram's text-to-speech API to generate recordings and automatically converts them to the exact audio format required by telephony platforms.

---

## What It Does

- Reads a list of IVR prompt scripts from a CSV file
- Sends each script to the Deepgram TTS API over HTTPS
- Converts the returned audio to G.711 u-law WAV format using ffmpeg
- Saves each prompt as an individually named .wav file to a folder of your choosing

---

## Getting Started

### Requirements

- Windows 10 or Windows 11
- A Deepgram account and API key (free tier available)
- No other software installation required -- everything is bundled in the exe

### Installation

1. Download `IVR.Prompt.Generator.exe` from the Releases page
2. Place it anywhere on your PC (Desktop, a shared drive, etc.)
3. Double-click to launch

---

## Setting Up Your API Key

Each user needs their own free Deepgram account and API key.

**Step 1 - Create a Deepgram account**
- Go to https://console.deepgram.com/signup
- Sign up with your email address
- Deepgram offers a free tier with enough credits to get started

**Step 2 - Get your API key**
- Log in at https://console.deepgram.com
- Click "API Keys" in the left sidebar
- Click "Create a New API Key"
- Give it a name such as "IVR Prompt Generator"
- Click "Create Key"
- Copy the key immediately -- Deepgram will not show it again after you close that window

**Step 3 - Enter the key in the application**
- Open IVR Prompt Generator
- Click the "API Key" button in the toolbar
- Paste your key into the entry field
- Click "Save Key"
- The status dot will turn green confirming it is saved

Your key is stored in Windows Credential Manager -- the same encrypted system used by Windows, browsers, and enterprise software to store passwords. It is never written to a file and persists across restarts. You only need to do this once per machine.

---

## Preparing Your CSV File

Create a CSV file where each row contains a filename and prompt text separated by a comma.

**Format:**
```
filename, Prompt text goes here
```

**Example:**
```
OpenHoursGreeting, Our phone sales hours are 7 AM to midnight Central Time.
AfterHours_Urgent, Please stay on the line to leave a message. Our on-call staff will review your message shortly.
cs_goodbye, Thank you for calling. Goodbye.
```

Rules:
- The filename becomes the name of the saved .wav file. No spaces, no .wav extension.
- The prompt text is exactly what will be spoken in the recording.
- Lines starting with # are treated as comments and are ignored by the tool.
- Use the "CSV Template" button in the app to download a ready-to-fill example file.

**Tips for better recordings:**
- Spell out numbers and abbreviations the way you want them read. For example, write "8 A M" instead of "8 AM" to ensure correct pronunciation.
- Review each file by playing it back before uploading to your phone system.
- You can re-run the tool on the same CSV at any time -- existing files will be overwritten with fresh recordings.

---

## Using the Application

**Browse CSV and Generate** -- Select your CSV file. The tool processes each prompt and logs the result in real time.

**Stop** -- Cancels a running job after the current file finishes.

**API Key** -- Enter, view (masked), or delete your stored Deepgram API key.

**CSV Template** -- Downloads a ready-to-fill CSV template with a single example row.

**Help / Instructions** -- Opens a full in-app guide covering usage, CSV format, audio specs, and Deepgram account setup.

**Change** (next to the output path) -- Select the folder where your .wav files will be saved. This setting is remembered between sessions.

---

## Audio Output Format

All files are automatically converted to the format required by IVR and contact center platforms.

| Property | Value |
|---|---|
| Format | WAV |
| Encoding | G.711 u-law (PCM mu-law) |
| Sample rate | 8,000 Hz |
| Channels | Mono |
| Bit depth | 8-bit |

This is the standard telephony audio format used by virtually all IVR platforms, ACD systems, and PBX software. No further conversion is needed after download.

---

## Network Activity

The application makes exactly one type of external network call:

- Destination: api.deepgram.com
- Protocol: HTTPS (port 443, encrypted)
- Data sent: Plain prompt text only -- no PII, no customer data, no credentials

There is no telemetry, no auto-update mechanism, and no other outbound connections.

---

## Files Created on the User's Machine

| File | Location | Purpose |
|---|---|---|
| IVR.Prompt.Generator.exe | Wherever the user places it | The application |
| config.json | Same folder as the exe | Stores the user's chosen output folder path |
| output_wav/ | User-selected location | The generated .wav files |
| Windows Credential Manager entry | Windows system vault | Stores the Deepgram API key, encrypted |

No registry entries are created. No admin rights are required to run the application.

---

## Building from Source

**Requirements:**
- Python 3.10 or higher
- ffmpeg installed and available on the system PATH

**Install dependencies:**
```
pip install -r requirements.txt
```

**Run without building:**
```
python deepgram_gui.py
```

**Build the exe:**
```
pyinstaller --onefile --windowed --name "IVR Prompt Generator" --collect-all keyring --add-binary "path\to\ffmpeg.exe;." --icon=icon.ico deepgram_gui.py
```

Replace `path\to\ffmpeg.exe` with the actual path to ffmpeg on your machine.

**Regenerate the icon:**
```
python create_icon.py
```

---

## Project Structure

| File | Purpose |
|---|---|
| deepgram_gui.py | Main application window and UI |
| prompt_utils.py | Deepgram API calls, ffmpeg conversion, CSV parsing, key management |
| generate_prompts.py | Headless command-line version of the tool |
| prompts.csv | Example prompt list |
| create_icon.py | Generates icon.ico from the Tk feather icon |
| icon.ico | Application icon used by PyInstaller |
| requirements.txt | Python dependencies |

---

## Dependencies

| Package | Purpose |
|---|---|
| requests | HTTP calls to the Deepgram API |
| keyring | Secure API key storage via Windows Credential Manager |
| pyinstaller | Packages the application into a standalone exe |
| ffmpeg (bundled) | Audio format conversion |
