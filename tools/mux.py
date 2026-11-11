"""영상(out/video.mp4) + 음악(music/duru_color_chip.wav) → out/short.mp4 (AAC 192k)."""
import subprocess
from pathlib import Path

R = Path(__file__).resolve().parent.parent
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(R / "out/video.mp4"), "-i", str(R / "music/duru_color_chip.wav"), "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(R / "out/short.mp4")], check=True)
print("out/short.mp4")
