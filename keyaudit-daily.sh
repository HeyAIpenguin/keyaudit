#!/bin/zsh
# Runs keyaudit once a day (via launchd) and notifies only about NEW exposures:
# a key never seen before, or a known key showing up in a new file (e.g. a fresh backup or synced copy).
DIR="$HOME/.keyaudit"; mkdir -p "$DIR"
python3 "$DIR/keyaudit.py" --json "$DIR/today.json" > "$DIR/last.log" 2>&1
NEW=$(python3 - "$DIR" <<'PY'
import json,sys,os
d=sys.argv[1]; t=json.load(open(f"{d}/today.json"))
known=json.load(open(f"{d}/known.json")) if os.path.exists(f"{d}/known.json") else []
if known and isinstance(known[0], str):  # migrate old format (fingerprints only) -> keep them as "seen anywhere"
    known=[[fp, "*"] for fp in known]
seen={tuple(k) for k in known}
seen_fp={fp for fp, _ in seen}
cur={(f["fingerprint"], f["file"]) for f in t["findings"]}
new_keys=[f for f in t["findings"] if f["fingerprint"] not in seen_fp]
new_paths=[f for f in t["findings"] if f["fingerprint"] in seen_fp and (f["fingerprint"], f["file"]) not in seen and (f["fingerprint"], "*") not in seen]
json.dump(sorted(map(list, cur | {s for s in seen if s[1] != "*"})), open(f"{d}/known.json","w"))  # "*" is a one-time migration marker
msg=[]
if new_keys: msg.append(f'{len({f["fingerprint"] for f in new_keys})} new key(s)')
if new_paths: msg.append(f'{len(new_paths)} known key(s) copied to new place(s)')
if msg: print("; ".join(msg) + ": " + ", ".join(sorted({f["file"] for f in new_keys + new_paths}))[:180])
PY
)
[ -n "$NEW" ] && osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "🔑 keyaudit" subtitle "Plaintext API key exposure" sound name "Basso"' -e 'end run' "$NEW"
exit 0
