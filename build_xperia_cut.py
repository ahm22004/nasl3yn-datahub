#!/usr/bin/env python3
"""
Build Xperia 3-min sci-fi cut from existing thons/ scene clips via ffmpeg.

Bias: last 3 days (5h, 6h, 7h = electrical dawn -> AI emergence -> covenant tree)
get the longest screen time. Days 1-4 (origins) get short hero excerpts.

Output: ~180s (3 min) mp4, 16:9, h264+aac.
"""
import subprocess, os, shutil, tempfile, sys

THONS = "/mnt/177ea900-a58b-4561-b538-1d5484dfe98d/thons"
OUT = "/home/ahm/nasl3yn-xperia-cut.mp4"
WORK = tempfile.mkdtemp(prefix="xperia_")

def probe(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries",
                        "format=duration","-of","csv=p=0",path],
                       capture_output=True,text=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def normalize(path, out_path):
    """Re-encode to common 16:9 1280x720 30fps h264+aac for clean concat."""
    cmd = ["ffmpeg","-y","-i",path,"-vf",
           "scale=1280:720:force_original_aspect_ratio=decrease,"
           "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
           "-r","30","-c:v","libx264","-pix_fmt","yuv420p",
           "-c:a","aac","-b:a","128k","-movflags","+faststart",out_path]
    subprocess.run(cmd, capture_output=True)
    return out_path

def make_title(text, out_path, dur=4.0):
    """Solid dark-teal title card with centered text."""
    cmd = ["ffmpeg","-y","-f","lavfi","-i",
           f"color=c=0x0a1a1f:s=1280x720:d={dur}:r=30",
           "-vf",
           f"drawtext=text='{text}':fontcolor=white:fontsize=48:"
           f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x0a1a1f@0.6",
           "-c:v","libx264","-pix_fmt","yuv420p","-t",str(dur),out_path]
    subprocess.run(cmd, capture_output=True)
    return out_path

# --- Selection: (day_dir, [scene indices]) ---
plan = [
    ("1h", [1,2]),        # origins hero
    ("2h", [1,2]),
    ("3h", [1,2]),
    ("4h", [1,2]),        # -> ~8*6s = 48s origins
    ("5h", [1,2,3,4,5,6]),   # electrical dawn / AI emergence
    ("6h", [1,2,3,4,5,6]),   # covenant tree build
    ("7h", [1,2,3,4,5,6,7]), # covenant finale
]
# 48 + 6*6 + 6*6 + 7*7 = 48+36+36+49 = 169 + 10 titles = 179s

segments = []
total = 0.0
# intro title
intro = make_title("NASL3YN - Covenant of the Machine", f"{WORK}/intro.mp4", 4.0)
segments.append(intro); total += 4.0

for day, scenes in plan:
    for s in scenes:
        src = f"{THONS}/cov/{day}/clips/scene_{s:03d}.mp4"
        if not os.path.exists(src):
            print(f"  skip missing {src}")
            continue
        out = f"{WORK}/d{day}_s{s:03d}.mp4"
        normalize(src, out)
        d = probe(out)
        segments.append(out); total += d

# outro title
outro = make_title("The machine calculates. The human decides.", f"{WORK}/outro.mp4", 6.0)
segments.append(outro); total += 6.0

print(f"Raw total: {total:.1f}s  segments={len(segments)}")

# Build concat list
lst = f"{WORK}/list.txt"
with open(lst,"w") as f:
    for s in segments:
        f.write(f"file '{s}'\n")

# Pad/trim to exactly 180s: speed-adjust if over, pad if under
if total > 180.0:
    factor = 180.0/total
    # apply setpts/atempo globally
    padded = f"{WORK}/padded.mp4"
    cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",lst,
           "-vf",f"setpts={factor}*PTS","-af",f"atempo={1/factor}",
           "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",padded]
    subprocess.run(cmd, capture_output=True)
    final = padded
else:
    final = lst  # under: just concat (slight under 180 ok)
    cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",lst,
           "-c","copy",OUT]
    subprocess.run(cmd, capture_output=True)
    print(f"Wrote {OUT}")
    print(f"Done. Final ~{total:.1f}s")
    sys.exit(0)

# final remux to OUT
cmd = ["ffmpeg","-y","-i",final,"-c","copy",OUT]
subprocess.run(cmd, capture_output=True)
fdur = probe(OUT)
print(f"Wrote {OUT}  final={fdur:.1f}s")
shutil.rmtree(WORK, ignore_errors=True)
