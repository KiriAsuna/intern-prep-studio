#!/bin/zsh
# Builds "Intern Prep Studio.app" (the macOS double-click entry) next to the app folder's other files.
# Run on a Mac:     zsh scripts/build_mac_app.sh
#
# The app is an AppleScript applet so that macOS can ask once for permission to read the folder
# (needed when the folder lives under Desktop / Documents / Downloads). All real work is in
# scripts/mac_launch.sh, which the app runs from the folder next to it, so that script can be edited
# without rebuilding. Rebuilding changes the app's identity: macOS asks for the permission once more.
set -e

HERE="${0:A:h}"
APP_PARENT="${HERE:h}"
NAME="Intern Prep Studio.app"
TMP="$(mktemp -d)"

cat > "$TMP/main.applescript" <<'APPLESCRIPT'
set appPath to POSIX path of (path to me)
do shell script "/bin/zsh " & quoted form of (appPath & "../scripts/mac_launch.sh") & " >/dev/null 2>&1 &"
APPLESCRIPT

osacompile -o "$TMP/$NAME" "$TMP/main.applescript"

PLIST="$TMP/$NAME/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string local.internprepstudio.launcher" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier local.internprepstudio.launcher" "$PLIST"
# Prefer running natively on Apple silicon instead of under Rosetta.
/usr/libexec/PlistBuddy -c "Delete :LSRequiresCarbon" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :LSArchitecturePriority array" -c "Add :LSArchitecturePriority:0 string arm64" -c "Add :LSArchitecturePriority:1 string x86_64" "$PLIST"

codesign --force --deep -s - "$TMP/$NAME"

rm -rf "$APP_PARENT/$NAME"
ditto "$TMP/$NAME" "$APP_PARENT/$NAME"
rm -rf "$TMP"
# Forget any permission decision recorded for the previous build so macOS asks cleanly.
tccutil reset SystemPolicyDesktopFolder local.internprepstudio.launcher >/dev/null 2>&1 || true
codesign --verify --deep "$APP_PARENT/$NAME" && echo "built: $APP_PARENT/$NAME"
