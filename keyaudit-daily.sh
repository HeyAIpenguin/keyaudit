#!/bin/zsh
# Runs keyaudit once a day (via launchd) and notifies only about NEW plaintext keys.
DIR="$HOME/.keyaudit"; mkdir -p "$DIR"
python3 "$DIR/keyaudit.py" --json "$DIR/today.json" > "$DIR/last.log" 2>&1
NEW=$(python3 - "$DIR" <<'PY'
import json,sys,os
d=sys.argv[1]; t=json.load(open(f"{d}/today.json"))
known=set(json.load(open(f"{d}/known.json"))) if os.path.exists(f"{d}/known.json") else set()
cur={f["fingerprint"] for f in t["findings"]}
new=[f for f in t["findings"] if f["fingerprint"] not in known]
json.dump(sorted(cur|known),open(f"{d}/known.json","w"))
print(f'{len({f["fingerprint"] for f in new})} new key(s): ' + ", ".join(sorted({f["file"] for f in new}))[:180] if new else "")
PY
)
[ -n "$NEW" ] && osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "🔑 keyaudit" subtitle "Plaintext API key found" sound name "Basso"' -e 'end run' "$NEW"
exit 0
