import re
from pathlib import Path

INPUT_FILE = Path(__file__).parent.parent / "outputs" / "interim" / "mydemo.json"
OUTPUT_FILE = Path(__file__).parent.parent / "outputs" / "rail_kills.csv"
SERVER_FPS = 10

frame_re = re.compile(r"Frame \[(\d+)\]")
rail_kill_re = re.compile(r"^Print - .* was railed by maddox", re.IGNORECASE)

current_frame = None
events = []

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()

        # Track current frame
        m = frame_re.search(line)
        if m:
            current_frame = int(m.group(1))
            continue

        # Detect rail kill
        if rail_kill_re.search(line):
            events.append({
                "frame": current_frame,
                "event": line
            })

# Save results
with open(OUTPUT_FILE, "w") as out:
    out.write("frame,seconds,event\n")
    for e in events:
        seconds = e['frame'] / SERVER_FPS
        out.write(f"{e['frame']},{seconds:.2f},\"{e['event']}\"\n")

print(f"Extracted {len(events)} railgun kills → {OUTPUT_FILE}")

