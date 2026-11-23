"""Windowless launcher for Windows and macOS.

Starts the app server in the background and opens it as its own window. Closing the window
stops the server a few seconds later (see autoshutdown.py).

    Windows: double-click "Intern Prep Studio.vbs"
    macOS:   double-click "Intern Prep Studio" (the .app in this folder)

Progress is stored in user_data/ inside this folder.
Per-machine runtime files (port, log) live in ~/.intern-prep-studio.
"""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
USER_DIR = ROOT / "user_data"
RUNTIME = Path.home() / ".intern-prep-studio"
LOCK = RUNTIME / "server.json"
LOG = RUNTIME / "server.log"
MARKER = RUNTIME / "page_connected"
STARTUP_TIMEOUT = int(os.environ.get("INTERN_PREP_STARTUP_TIMEOUT", "180"))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
IS_MAC = sys.platform == "darwin"
MAC_CHROME = "/Applications/Google Chrome.app"
REQUIRED = ["streamlit", "pandas", "numpy", "matplotlib", "scipy", "sklearn", "statsmodels"]


def python_exe():
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.with_name("python.exe")).exists():
        return str(exe.with_name("python.exe"))
    return str(exe)


def alert(text, error=False):
    if IS_MAC:
        script = ('display dialog (item 1 of argv) with title "Intern Prep Studio" buttons {"OK"} '
                  'default button 1' + (' with icon stop' if error else ''))
        subprocess.run(["osascript", "-e", "on run argv", "-e", script, "-e", "end run", text],
                       capture_output=True)
        return
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)("Intern Prep Studio", text)
        root.destroy()
    except Exception:
        pass


def is_alive(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def free_port(start=8501):
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def find_windows_browser():
    """Prefer the user's default browser if it is Chrome or Edge (both support app windows)."""
    candidates = {
        "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                   r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                   os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")],
        "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    }
    order = ["edge", "chrome"]
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice")
        prog = winreg.QueryValueEx(key, "ProgId")[0].lower()
        if "chrome" in prog:
            order = ["chrome", "edge"]
    except Exception:
        pass
    for name in order:
        for path in candidates[name]:
            if os.path.exists(path):
                return path
    return None


def open_window(url):
    if os.environ.get("INTERN_PREP_NO_BROWSER") == "1":
        return
    if IS_MAC:
        if os.path.exists(MAC_CHROME):       # its own window, without tabs or address bar
            subprocess.Popen(["open", "-na", "Google Chrome", "--args", f"--app={url}"])
        else:
            subprocess.Popen(["open", url])  # default browser
        return
    exe = find_windows_browser()
    if exe:
        subprocess.Popen([exe, f"--app={url}", "--new-window"])
    else:
        webbrowser.open(url)


def wait_for_page(proc):
    """If no page ever connects (e.g. the browser failed to open), don't leave the server running forever."""
    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline:
        if MARKER.exists() or proc.poll() is not None:
            return                      # a page connected: autoshutdown.py takes over from here
        time.sleep(1)
    proc.terminate()


def ensure_dependencies():
    missing = [m for m in REQUIRED if importlib.util.find_spec(m) is None]
    if not missing:
        return True
    alert("The first launch needs to install dependencies (about 1-3 minutes). Click OK to start; the app opens automatically when done.")
    r = subprocess.run([python_exe(), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        alert("Installing dependencies failed. Last lines of the error:\n\n" + (r.stderr or "")[-600:], error=True)
        return False
    return True


def main():
    USER_DIR.mkdir(exist_ok=True)
    RUNTIME.mkdir(exist_ok=True)
    try:
        port = json.loads(LOCK.read_text(encoding="utf-8"))["port"]
        if is_alive(port):                      # already running: just show it again
            open_window(f"http://localhost:{port}")
            return
    except Exception:
        pass

    if not ensure_dependencies():
        return

    port = free_port()
    if MARKER.exists():
        MARKER.unlink()
    env = dict(os.environ, INTERN_PREP_AUTOSHUTDOWN="1", INTERN_PREP_MARKER=str(MARKER),
               PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    detach = {} if os.name == "nt" else {"start_new_session": True}
    with open(LOG, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [python_exe(), "-m", "streamlit", "run", str(ROOT / "app.py"),
             "--server.port", str(port), "--server.address", "127.0.0.1",
             "--server.headless", "true", "--browser.gatherUsageStats", "false"],
            cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, **detach)
    LOCK.write_text(json.dumps({"port": port, "pid": proc.pid}), encoding="utf-8")

    deadline = time.time() + 90
    while time.time() < deadline:
        if is_alive(port):
            open_window(f"http://localhost:{port}")
            wait_for_page(proc)
            return
        if proc.poll() is not None:
            break
        time.sleep(0.4)
    tail = ""
    try:
        tail = LOG.read_text(encoding="utf-8", errors="replace")[-800:]
    except Exception:
        pass
    alert(f"Startup failed. Full log: {LOG}. Last lines:\n\n" + tail, error=True)


if __name__ == "__main__":
    main()
