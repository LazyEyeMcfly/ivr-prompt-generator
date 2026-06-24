import ctypes
import queue
import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from prompt_utils import (
    read_prompts, synthesize_prompt,
    get_output_dir, set_output_dir,
    get_api_key, set_api_key, delete_api_key,
)

# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#0b0f1e"
SURFACE  = "#0f1729"
CARD     = "#151f38"
BORDER   = "#243050"
BLUE     = "#4f8ef7"
BLUE_HV  = "#6ba3ff"
PINK     = "#e040fb"
GREEN    = "#00e676"
RED      = "#ff1744"
RED_D    = "#aa0030"
ORANGE   = "#ff9800"
TEXT     = "#e8eaf6"
TEXT_DIM = "#6b7a99"
FONT     = "Segoe UI"
SPINNER  = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

log_queue  = queue.Queue()
stop_event = threading.Event()

# ── Help text ──────────────────────────────────────────────────────────────────
HELP_TEXT = """
IVR PROMPT GENERATOR - USER GUIDE
==================================

WHAT THIS TOOL DOES
-------------------
This tool reads a list of IVR phone prompts from a CSV file, sends each
one to Deepgram's text-to-speech service, and saves the result as a
properly formatted audio file ready for upload to your phone system.


HOW TO USE IT
-------------
1. Click "API Key" and enter your Deepgram API key. You only need to
   do this once - it is stored securely in Windows Credential Manager.

2. Prepare your CSV file using the format described below.
   Click "CSV Template" to download a ready-to-fill example.

3. Click "Browse CSV & Generate" and select your CSV file.
   The tool will process each prompt one by one and show progress
   in the log window.

4. When finished, your audio files will be in the output_wav folder
   next to this application.

5. If something goes wrong mid-run, click "Stop" to cancel.


CSV FILE FORMAT
---------------
Each row in the CSV follows this format:

    filename, Prompt text goes here

The filename comes first, then a comma, then the prompt text.

  - filename:    The name your .wav file will be saved as.
                 No spaces, no .wav extension - just the name.

  - Prompt text: Exactly what you want spoken in the recording.

Example row:
    OpenHoursGreeting, Our phone sales hours are 7 AM to midnight Central Time.

That row will be saved as:  OpenHoursGreeting.wav

Lines that start with # are treated as comments and are ignored.
Use them for notes or to temporarily disable a prompt.


AUDIO FILE DETAILS
------------------
Your phone system (IVR/ACD) requires a specific audio format.
This tool automatically converts every file to that format:

  Format:       WAV
  Encoding:     G.711 u-law (PCM mu-law)
  Sample rate:  8,000 Hz
  Channels:     Mono (1 channel)
  Bit depth:    8-bit

This is the standard telephony audio format used by virtually all
IVR platforms, contact center software, and PBX systems.
You do not need to convert or edit the files after downloading.


TIPS
----
- If a prompt contains a number like "8 AM", spell it out as
  "8 A M" or "eight A M" to control how Deepgram reads it.
- Review each file by playing it back before uploading to your system.
- You can re-run the tool on the same CSV at any time - existing
  files will be overwritten with fresh recordings.


GETTING A DEEPGRAM ACCOUNT AND API KEY
---------------------------------------
Each person using this tool needs their own free Deepgram account
and API key. Follow these steps:

Step 1 - Create a Deepgram account
  - Go to: https://console.deepgram.com/signup
  - Sign up with your work email address
  - Verify your email if prompted
  - Deepgram offers a free tier with enough credits to get started

Step 2 - Get your API key
  - Log in at: https://console.deepgram.com
  - In the left sidebar, click "API Keys"
  - Click "Create a New API Key"
  - Give it a name (example: IVR Prompt Generator)
  - Leave the permissions as default
  - Click "Create Key"
  - IMPORTANT: Copy the key immediately and save it somewhere safe.
    Deepgram will not show it to you again after you close that window.

Step 3 - Enter the key in this tool
  - Open IVR Prompt Generator
  - Click the "API Key" button in the toolbar
  - Paste your key into the entry field
  - Click "Save Key"
  - The status dot will turn green confirming it is saved

Your key is stored securely in Windows Credential Manager and will
persist across restarts. You only need to do this once per machine.

If you ever need to replace your key (for example if it expires or
is revoked), click "API Key", then "Delete Key", and enter the new
one using the same steps above.
"""


# ── Reusable widgets ───────────────────────────────────────────────────────────

class PulsingDot(tk.Canvas):
    _ACTIVE   = ["#00e676", "#00c853", "#69f0ae", "#00c853"]
    _INACTIVE = ["#ff1744", "#cc0033", "#ff1744", "#cc0033"]

    def __init__(self, parent, active=False, size=11, **kwargs):
        super().__init__(parent, width=size, height=size,
                         highlightthickness=0, **kwargs)
        self.active = active
        self._step  = 0
        self._dot   = self.create_oval(1, 1, size - 1, size - 1)
        self._tick()

    def set_active(self, active: bool):
        self.active = active
        self._step  = 0

    def _tick(self):
        palette = self._ACTIVE if self.active else self._INACTIVE
        c = palette[self._step % len(palette)]
        self.itemconfig(self._dot, fill=c, outline=c)
        self._step += 1
        self.after(500 if self.active else 900, self._tick)


def _btn(parent, text, command=None, variant="secondary", state="normal", **kw):
    palettes = {
        "primary":   (BLUE,  BLUE_HV, TEXT),
        "danger":    (RED_D, RED,     TEXT),
        "secondary": (CARD,  BORDER,  TEXT),
        "ghost":     (CARD,  BORDER,  TEXT_DIM),
    }
    bg, hv, fg = palettes.get(variant, palettes["secondary"])
    btn = tk.Button(
        parent, text=text, command=command or (lambda: None),
        bg=bg, fg=fg,
        activebackground=hv, activeforeground=fg,
        disabledforeground="#3a4a6a",
        relief="flat", bd=0,
        padx=kw.pop("padx", 16), pady=kw.pop("pady", 9),
        font=(FONT, 10), cursor="hand2", state=state,
        **kw
    )
    btn._bg = bg
    btn._hv = hv
    btn.bind("<Enter>", lambda e: btn.config(bg=btn._hv)
             if str(btn["state"]) != "disabled" else None)
    btn.bind("<Leave>", lambda e: btn.config(bg=btn._bg)
             if str(btn["state"]) != "disabled" else None)
    return btn


def _entry(parent, **kw):
    return tk.Entry(
        parent, bg=SURFACE, fg=TEXT,
        insertbackground=TEXT, selectbackground=BORDER,
        relief="flat", bd=0, font=(FONT, 10), **kw
    )


def _sep(parent, vertical=False):
    if vertical:
        return tk.Frame(parent, bg=BORDER, width=1)
    return tk.Frame(parent, bg=BORDER, height=1)


def _gradient_line(parent, height=3):
    """Draws a blue-to-pink horizontal gradient bar."""
    c = tk.Canvas(parent, height=height, highlightthickness=0, bg=BG)
    c.pack(fill="x")

    def draw(event=None):
        w = c.winfo_width()
        if w < 2:
            c.after(60, draw)
            return
        c.delete("all")
        step = 3
        for i in range(0, w, step):
            t = i / w
            r = int(0x4f + (0xe0 - 0x4f) * t)
            g = int(0x8e + (0x40 - 0x8e) * t)
            b = int(0xf7 + (0xfb - 0xf7) * t)
            c.create_rectangle(i, 0, i + step, height,
                               fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

    c.bind("<Configure>", lambda e: draw())
    c.after(80, draw)
    return c


# ── Title bar + scrollbar helpers ─────────────────────────────────────────────

def _apply_dark_title_bar(window) -> None:
    """Set the Windows title bar color to match CARD (#151f38)."""
    try:
        window.update_idletasks()
        child = window.winfo_id()
        hwnd  = ctypes.windll.user32.GetParent(child)
        if not hwnd:
            # Root Tk window IS the top-level — use its handle directly
            hwnd = child
        # COLORREF format is 0x00BBGGRR — CARD #151f38 → 0x00381F15
        colorref = ctypes.c_int(0x00381F15)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref)
        )
    except Exception:
        try:
            # Fallback: generic dark mode title bar (Windows 10 1903+)
            child = window.winfo_id()
            hwnd  = ctypes.windll.user32.GetParent(child) or child
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4
            )
        except Exception:
            pass


def _setup_scrollbar_style() -> None:
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Thin.Vertical.TScrollbar",
        background=BORDER,
        troughcolor=SURFACE,
        bordercolor=SURFACE,
        arrowcolor=SURFACE,
        relief="flat",
        borderwidth=0,
        gripcount=0,
        width=8,
    )
    style.map(
        "Thin.Vertical.TScrollbar",
        background=[("active", TEXT_DIM), ("pressed", BLUE)],
    )


# ── Dialogs ────────────────────────────────────────────────────────────────────

def open_api_key_dialog(parent, on_change=None):
    dlg = tk.Toplevel(parent)
    dlg.title("API Key")
    dlg.configure(bg=BG)
    dlg.geometry("460x305")
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.after(50, lambda: _apply_dark_title_bar(dlg))

    current_key = get_api_key()
    has_key     = bool(current_key)

    # Header
    hdr = tk.Frame(dlg, bg=CARD, pady=14)
    hdr.pack(fill="x")
    tk.Label(hdr, text="Deepgram", bg=CARD, fg=BLUE,
             font=(FONT, 13, "bold")).pack(side="left", padx=(16, 0))
    tk.Label(hdr, text=" API Key", bg=CARD, fg=TEXT,
             font=(FONT, 13, "bold")).pack(side="left")

    _gradient_line(dlg)

    # Status row
    row = tk.Frame(dlg, bg=BG, pady=14)
    row.pack(fill="x", padx=16)

    dot = PulsingDot(row, active=has_key, size=13, bg=BG)
    dot.pack(side="left", padx=(0, 8), pady=1)

    tk.Label(row, text="Key configured" if has_key else "No key set",
             bg=BG, fg=GREEN if has_key else RED,
             font=(FONT, 10)).pack(side="left")

    # Show / hide masked key
    masked_var = tk.StringVar()
    _showing   = [False]

    def toggle_show_key():
        if _showing[0]:
            masked_var.set("")
            show_key_btn.config(text="Show Key")
        else:
            tail = current_key[-5:] if len(current_key) >= 5 else current_key
            masked_var.set("*" * max(0, len(current_key) - 5) + tail)
            show_key_btn.config(text="Hide Key")
        _showing[0] = not _showing[0]

    show_key_btn = _btn(row, "Show Key", toggle_show_key, variant="ghost",
                        padx=10, pady=4,
                        state="normal" if has_key else "disabled")
    show_key_btn.pack(side="right")

    tk.Label(dlg, textvariable=masked_var, bg=BG, fg=TEXT_DIM,
             font=("Courier New", 9), anchor="w").pack(fill="x", padx=24)

    _sep(dlg).pack(fill="x", padx=16, pady=(10, 0))

    # New key entry
    tk.Label(dlg, text="Enter new API key:", bg=BG, fg=TEXT_DIM,
             font=(FONT, 9), anchor="w").pack(fill="x", padx=16, pady=(10, 2))

    wrap = tk.Frame(dlg, bg=SURFACE)
    wrap.pack(fill="x", padx=16)

    key_var = tk.StringVar()
    e = _entry(wrap, textvariable=key_var, show="*")
    e.pack(side="left", fill="x", expand=True, padx=8, pady=8)

    sv = tk.BooleanVar()
    tk.Checkbutton(
        wrap, text="Show", variable=sv,
        command=lambda: e.config(show="" if sv.get() else "*"),
        bg=SURFACE, fg=TEXT_DIM, selectcolor=CARD,
        activebackground=SURFACE, activeforeground=TEXT,
        relief="flat", bd=0, font=(FONT, 9),
    ).pack(side="right", padx=6)

    # Buttons
    bf = tk.Frame(dlg, bg=BG, pady=14)
    bf.pack()

    def save_key():
        k = key_var.get().strip()
        if not k:
            messagebox.showwarning("No Key", "Enter a key before saving.", parent=dlg)
            return
        set_api_key(k)
        if on_change:
            on_change()
        messagebox.showinfo("Saved", "API key saved successfully.", parent=dlg)
        dlg.destroy()

    def delete_key():
        if not current_key:
            messagebox.showinfo("Nothing to Delete", "No key is stored.", parent=dlg)
            return
        if messagebox.askyesno("Delete Key",
                "Permanently delete the stored API key?", parent=dlg):
            delete_api_key()
            if on_change:
                on_change()
            messagebox.showinfo("Deleted", "Key deleted.", parent=dlg)
            dlg.destroy()

    _btn(bf, "Save Key",   save_key,    "primary").pack(side="left", padx=6)
    _btn(bf, "Delete Key", delete_key,  "danger").pack(side="left", padx=6)
    _btn(bf, "Cancel",     dlg.destroy, "secondary").pack(side="left", padx=6)


def save_csv_template(parent):
    path = filedialog.asksaveasfilename(
        parent=parent, title="Save CSV Template",
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        initialfile="prompts_template.csv",
    )
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write('"ExampleGreeting, Thank you for calling. Please hold while we connect you with the next available agent."\n')
    messagebox.showinfo("Saved", f"Template saved to:\n{path}", parent=parent)


def open_help_dialog(parent):
    dlg = tk.Toplevel(parent)
    dlg.title("Help - IVR Prompt Generator")
    dlg.configure(bg=BG)
    dlg.geometry("640x540")
    dlg.resizable(True, True)
    dlg.after(50, lambda: _apply_dark_title_bar(dlg))

    hdr = tk.Frame(dlg, bg=CARD, pady=14)
    hdr.pack(fill="x")
    tk.Label(hdr, text="Help", bg=CARD, fg=BLUE,
             font=(FONT, 13, "bold")).pack(side="left", padx=(16, 0))
    tk.Label(hdr, text=" & Instructions", bg=CARD, fg=TEXT,
             font=(FONT, 13, "bold")).pack(side="left")

    _gradient_line(dlg)

    tf = tk.Frame(dlg, bg=BG)
    tf.pack(fill="both", expand=True)

    sb = ttk.Scrollbar(tf, style="Thin.Vertical.TScrollbar")
    sb.pack(side="right", fill="y")

    t = tk.Text(tf, wrap="word", bg=SURFACE, fg=TEXT,
                font=(FONT, 10), relief="flat", bd=0,
                padx=16, pady=12, yscrollcommand=sb.set,
                selectbackground=BORDER, insertbackground=TEXT)
    t.pack(fill="both", expand=True)
    sb.config(command=t.yview)
    t.insert("1.0", HELP_TEXT.strip())
    t.config(state="disabled")

    bf = tk.Frame(dlg, bg=BG, pady=10)
    bf.pack()
    _btn(bf, "Close", dlg.destroy, "secondary").pack()


# ── Worker thread ──────────────────────────────────────────────────────────────

def _worker(csv_path: str):
    prompts = read_prompts(csv_path)
    log_queue.put(("info", f"Found {len(prompts)} prompts. Starting...\n\n"))
    for name, text in prompts:
        if stop_event.is_set():
            log_queue.put(("warn", "[STOPPED] Generation cancelled.\n"))
            log_queue.put(("__done__", ""))
            return
        result = synthesize_prompt(text, name)
        tag = "ok" if result.startswith("[OK]") else "error"
        log_queue.put((tag, result + "\n"))
    log_queue.put(("done", "\nAll done!\n"))
    log_queue.put(("__done__", ""))


# ── Main window ────────────────────────────────────────────────────────────────

def run_gui():
    root = tk.Tk()
    root.title("IVR Prompt Generator")
    root.configure(bg=BG)
    root.geometry("980x640")
    root.minsize(820, 520)
    _setup_scrollbar_style()

    # ── Header ──────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=CARD, pady=15)
    hdr.pack(fill="x")
    tk.Label(hdr, text="IVR", bg=CARD, fg=BLUE,
             font=(FONT, 17, "bold")).pack(side="left", padx=(20, 0))
    tk.Label(hdr, text=" PROMPT GENERATOR", bg=CARD, fg=TEXT,
             font=(FONT, 17)).pack(side="left")

    _gradient_line(root, height=3)

    # ── Action bar ───────────────────────────────────────────────────────────
    bar = tk.Frame(root, bg=CARD, pady=8)
    bar.pack(fill="x")

    generate_btn = _btn(bar, "▶  Browse CSV & Generate",
                        variant="primary", padx=18, pady=10)
    generate_btn.pack(side="left", padx=(14, 8), pady=4)

    stop_btn = _btn(bar, "■  Stop", variant="danger",
                    state="disabled", padx=14, pady=10)
    stop_btn.pack(side="left", padx=(0, 6), pady=4)

    _sep(bar, vertical=True).pack(side="left", fill="y", padx=10, pady=6)

    key_dot = PulsingDot(bar, active=bool(get_api_key()), size=11, bg=CARD)
    key_dot.pack(side="left", padx=(2, 3))

    def on_key_change():
        key_dot.set_active(bool(get_api_key()))

    _btn(bar, "API Key",
         lambda: open_api_key_dialog(root, on_key_change),
         variant="ghost", padx=12, pady=8).pack(side="left", padx=2)

    _btn(bar, "CSV Template",
         lambda: save_csv_template(root),
         variant="ghost", padx=12, pady=8).pack(side="left", padx=2)

    _btn(bar, "Help",
         lambda: open_help_dialog(root),
         variant="ghost", padx=12, pady=8).pack(side="left", padx=2)

    out_frame = tk.Frame(bar, bg=CARD)
    out_frame.pack(side="right", padx=14)

    output_var = tk.StringVar(value=str(get_output_dir()))
    tk.Label(out_frame, textvariable=output_var, bg=CARD, fg=TEXT_DIM,
             font=(FONT, 8)).pack(side="left")

    def change_output():
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            set_output_dir(folder)
            output_var.set(folder)

    _btn(out_frame, "Change", change_output,
         variant="ghost", padx=8, pady=4).pack(side="left", padx=(6, 0))

    # ── Log area ─────────────────────────────────────────────────────────────
    _sep(root).pack(fill="x")

    log_frame = tk.Frame(root, bg=SURFACE)
    log_frame.pack(fill="both", expand=True)

    log_sb = ttk.Scrollbar(log_frame, style="Thin.Vertical.TScrollbar")
    log_sb.pack(side="right", fill="y")

    log_text = tk.Text(
        log_frame, state="disabled",
        bg=SURFACE, fg=TEXT,
        font=("Courier New", 10),
        relief="flat", bd=0, padx=14, pady=10,
        yscrollcommand=log_sb.set,
        selectbackground=BORDER,
        insertbackground=TEXT,
    )
    log_text.pack(fill="both", expand=True)
    log_sb.config(command=log_text.yview)

    log_text.tag_configure("ok",    foreground=GREEN)
    log_text.tag_configure("error", foreground=RED)
    log_text.tag_configure("warn",  foreground=ORANGE)
    log_text.tag_configure("info",  foreground=BLUE)
    log_text.tag_configure("done",  foreground=GREEN, font=("Courier New", 10, "bold"))
    log_text.tag_configure("dim",   foreground=TEXT_DIM)

    # ── Status bar ────────────────────────────────────────────────────────────
    _sep(root).pack(fill="x")
    sb_frame = tk.Frame(root, bg=CARD, pady=6)
    sb_frame.pack(fill="x")

    status_var = tk.StringVar(value="Ready.")
    tk.Label(sb_frame, textvariable=status_var, bg=CARD, fg=TEXT_DIM,
             font=(FONT, 9), anchor="w").pack(side="left", padx=12)

    # Spinner
    _spin_idx = [0]
    _spinning  = [False]

    def _start_spin(msg: str):
        _spinning[0] = True
        def tick():
            if _spinning[0]:
                ch = SPINNER[_spin_idx[0] % len(SPINNER)]
                _spin_idx[0] += 1
                status_var.set(f"{ch}  {msg}")
                root.after(100, tick)
        tick()

    def _stop_spin(msg: str):
        _spinning[0] = False
        status_var.set(msg)

    # ── Log helper ────────────────────────────────────────────────────────────
    def append(tag: str, msg: str):
        log_text.config(state="normal")
        log_text.insert(tk.END, msg, tag)
        log_text.see(tk.END)
        log_text.config(state="disabled")

    # ── Queue poller ──────────────────────────────────────────────────────────
    def poll():
        try:
            while True:
                tag, msg = log_queue.get_nowait()
                if tag == "__done__":
                    _stop_spin("Done.")
                    generate_btn.config(state="normal")
                    stop_btn.config(state="disabled")
                else:
                    append(tag, msg)
        except queue.Empty:
            pass
        root.after(80, poll)

    # ── Actions ───────────────────────────────────────────────────────────────
    def browse_and_generate():
        if not get_api_key():
            messagebox.showwarning(
                "No API Key",
                "No API key configured.\nClick 'API Key' to add one.",
            )
            return
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        stop_event.clear()
        generate_btn.config(state="disabled")
        stop_btn.config(state="normal")
        log_text.config(state="normal")
        log_text.delete(1.0, tk.END)
        log_text.config(state="disabled")
        append("dim", f"File: {path}\n\n")
        _start_spin("Processing prompts...")
        threading.Thread(target=_worker, args=(path,), daemon=True).start()

    def request_stop():
        stop_event.set()
        stop_btn.config(state="disabled")
        status_var.set("Stopping after current file...")

    generate_btn.config(command=browse_and_generate)
    stop_btn.config(command=request_stop)

    root.after(80, poll)
    root.update()
    _apply_dark_title_bar(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
