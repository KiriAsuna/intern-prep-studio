#!/bin/zsh
# macOS start script for Intern Prep Studio, run by "Intern Prep Studio.app" (see build_mac_app.sh).
# It lives outside the .app on purpose: editing it does not change the app, so macOS keeps its permission.
# Keeps a private Python environment in ~/.intern-prep-studio so nothing is installed system-wide
# and nothing machine-specific is written into the app folder.

APP_DIR="${0:A:h:h}"              # .../scripts/mac_launch.sh -> the app folder
HOME_DIR="$HOME/.intern-prep-studio"
VENV="$HOME_DIR/venv"
mkdir -p "$HOME_DIR"

# On Apple-silicon Macs the .app may be started in Intel-emulation mode (Rosetta); the Python
# packages are native, so always run Python natively.
NATIVE=()
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ]; then NATIVE=(arch -arm64); fi

say_dialog() {
  osascript -e 'on run argv' -e 'display dialog (item 1 of argv) with title "Intern Prep Studio" buttons {"OK"} default button 1' -e 'end run' "$1" >/dev/null 2>&1
}

if [ ! -r "$APP_DIR/launcher.pyw" ]; then
  say_dialog "Cannot read the app folder. In System Settings > Privacy & Security > Files and Folders, allow Intern Prep Studio to access the folder that contains it, then open it again."
  exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
  PY=""
  for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$c" ]; then PY="$c"; break; fi
  done
  if [ -z "$PY" ]; then
    say_dialog "Python 3 was not found. Please install Python 3 and try again."
    exit 1
  fi
  osascript -e 'display notification "First launch: setting up the environment (about 2-3 minutes). The app opens automatically when done." with title "Intern Prep Studio"' >/dev/null 2>&1
  if ! { $NATIVE "$PY" -m venv "$VENV" \
         && $NATIVE "$VENV/bin/python" -m pip install --upgrade pip \
         && $NATIVE "$VENV/bin/python" -m pip install -r "$APP_DIR/requirements.txt"; } >"$HOME_DIR/setup.log" 2>&1; then
    rm -rf "$VENV"
    say_dialog "Environment setup failed. Details: $HOME_DIR/setup.log"
    exit 1
  fi
fi

cd "$APP_DIR"
exec $NATIVE "$VENV/bin/python" "$APP_DIR/launcher.pyw" >"$HOME_DIR/launch.log" 2>&1
