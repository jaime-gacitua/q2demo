#!/usr/bin/env python3
import csv
import subprocess
import sys
import shutil
from pathlib import Path

# Configuration
SECONDS_BEFORE = 7
SECONDS_AFTER = 3
CLIP_DURATION = SECONDS_BEFORE + SECONDS_AFTER
TRANSITION_DURATION = 0.5  # Crossfade duration in seconds

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_clips.py <demo_name>")
        print("Example: python extract_clips.py ctf_20251223_141052")
        sys.exit(1)

    demo_name = sys.argv[1]
    
    # Derive paths from demo name
    project_root = Path(__file__).parent.parent
    input_video = project_root / "inputs" / f"{demo_name}.mp4"
    input_csv = project_root / "outputs" / f"{demo_name}-rail-kills.csv"
    clips_dir = project_root / "outputs" / f"{demo_name}-clips"
    output_video = project_root / "outputs" / f"{demo_name}-highlight.mp4"

    # Validate inputs exist
    if not input_video.exists():
        print(f"Error: Input video not found: {input_video}")
        sys.exit(1)
    if not input_csv.exists():
        print(f"Error: Input CSV not found: {input_csv}")
        sys.exit(1)

    # Create clips directory
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Read CSV and calculate clip ranges
    ranges = []
    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seconds = float(row["seconds"])
            start_time = max(0, seconds - SECONDS_BEFORE)
            end_time = seconds + SECONDS_AFTER
            ranges.append((start_time, end_time))

    if not ranges:
        print("No clips to process")
        sys.exit(1)

    # Merge overlapping ranges
    ranges.sort(key=lambda x: x[0])
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:  # Overlapping
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    print(f"Merged {len(ranges)} kills into {len(merged)} clips")

    # Extract merged clips
    clips = []
    for i, (start_time, end_time) in enumerate(merged):
        duration = end_time - start_time
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        clips.append(clip_path)

        print(f"Extracting clip {i+1}: {start_time:.2f}s - {end_time:.2f}s ({duration:.2f}s)")
        
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(input_video),
            "-t", str(duration),
            "-c", "copy",
            str(clip_path)
            ], check=True, capture_output=True)

    # Concatenate clips with crossfade transitions
    print(f"Concatenating {len(clips)} clips with crossfade transitions...")

    if len(clips) == 1:
        # Single clip, just copy it
        shutil.copy(clips[0], output_video)
    else:
        # Build xfade filter chain
        # Get clip durations
        clip_durations = [merged[i][1] - merged[i][0] for i in range(len(merged))]
        
        # Build input args
        input_args = []
        for clip in clips:
            input_args.extend(["-i", str(clip)])
        
        # Build filter chain
        # For N clips, we need N-1 xfade filters
        filter_parts = []
        audio_filter_parts = []
        cumulative_duration = clip_durations[0]
        
        for i in range(1, len(clips)):
            # Calculate offset (where transition starts)
            offset = cumulative_duration - TRANSITION_DURATION
            
            if i == 1:
                # First xfade: [0][1] -> [v1]
                filter_parts.append(
                    f"[0][1]xfade=transition=fade:duration={TRANSITION_DURATION}:offset={offset:.3f}[v{i}]"
                )
                audio_filter_parts.append(
                    f"[0:a][1:a]acrossfade=d={TRANSITION_DURATION}[a{i}]"
                )
            else:
                # Subsequent xfades: [vN-1][N] -> [vN]
                filter_parts.append(
                    f"[v{i-1}][{i}]xfade=transition=fade:duration={TRANSITION_DURATION}:offset={offset:.3f}[v{i}]"
                )
                audio_filter_parts.append(
                    f"[a{i-1}][{i}:a]acrossfade=d={TRANSITION_DURATION}[a{i}]"
                )
            
            # Update cumulative duration (subtract overlap)
            cumulative_duration += clip_durations[i] - TRANSITION_DURATION
        
        # Final output labels
        final_video = f"[v{len(clips)-1}]"
        final_audio = f"[a{len(clips)-1}]"
        
        filter_complex = ";".join(filter_parts + audio_filter_parts)
        
        cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", final_video,
            "-map", final_audio,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_video)
        ]
        
        subprocess.run(cmd, check=True)

    # Clean up clips directory
    shutil.rmtree(clips_dir)

    print(f"Done! Highlight video: {output_video}")

if __name__ == "__main__":
    main()

