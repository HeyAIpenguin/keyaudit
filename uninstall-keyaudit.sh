#!/bin/zsh
# Removes the daily keyaudit job and its local state.
launchctl bootout gui/$(id -u)/com.keyaudit.daily 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.keyaudit.daily.plist"
rm -rf "$HOME/.keyaudit"
echo "keyaudit removed"
