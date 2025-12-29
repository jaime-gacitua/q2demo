import re
import sys
from pathlib import Path

# Configuration
SERVER_FPS = 10

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_rail_kills.py <demo_name>")
        print("Example: python extract_rail_kills.py ctf_20251223_134047")
        sys.exit(1)

    demo_name = sys.argv[1]
    
    # Derive paths from demo name
    project_root = Path(__file__).parent.parent
    input_file = project_root / "outputs" / "interim" / f"{demo_name}.json"
    output_file = project_root / "outputs" / f"{demo_name}-rail-kills.csv"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    frame_re = re.compile(r"Frame \[(\d+)\]")
    rail_kill_re = re.compile(r"^Print - .* was railed by maddox", re.IGNORECASE)

    current_frame = None
    events = []

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
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
    with open(output_file, "w") as out:
        out.write("frame,seconds,event\n")
        for e in events:
            seconds = e['frame'] / SERVER_FPS
            out.write(f"{e['frame']},{seconds:.2f},\"{e['event']}\"\n")

    print(f"Extracted {len(events)} railgun kills → {output_file}")

if __name__ == "__main__":
    main()
