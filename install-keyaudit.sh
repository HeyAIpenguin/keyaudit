#!/bin/zsh
# Installs keyaudit as a daily launchd job (10:00). Uninstall: launchctl bootout gui/$(id -u)/com.keyaudit.daily
set -e
cd "$(dirname "$0")"
DIR="$HOME/.keyaudit"; mkdir -p "$DIR"
cp keyaudit.py keyaudit-daily.sh "$DIR/"; chmod 700 "$DIR" "$DIR/keyaudit-daily.sh"
PL="$HOME/Library/LaunchAgents/com.keyaudit.daily.plist"
cat > "$PL" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.keyaudit.daily</string>
  <key>ProgramArguments</key><array><string>/bin/zsh</string><string>$DIR/keyaudit-daily.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
</dict></plist>
PL
launchctl bootout gui/$(id -u)/com.keyaudit.daily 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PL"
echo "installed: runs daily at 10:00, notifies only on new keys"
