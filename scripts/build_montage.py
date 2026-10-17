import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "montage.mp4"
WIDTH, HEIGHT = 1080, 1920
CLIP_SECONDS = 7
MAX_DOWNLOAD_BYTES = 180 * 1024 * 1024


def read_json(name):
    path = Path(name)\n    if not path.is_absolute():\n        path = ROOT / path\n    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require_direct_https(url, label):
    if not url or urlparse(url).scheme != "https":
        raise ValueError(f"{label} must be a direct HTTPS file URL.")
    if any(host in urlparse(url).netloc.lower() for host in ("youtube.com", "youtu.be")):
        raise ValueError(f"{label} is a YouTube page, not a direct media file URL.")


def download(url, destination, label):
    require_direct_https(url, label)
    request = urllib.request.Request(url, headers={"User-Agent": "FortniteMontageWorkflow/1.0"})
    total = 0
    with urllib.request.urlopen(request, timeout=45) as response, destination.open("wb") as out:
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            raise ValueError(f"{label} returned a web page, not a media file.")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"{label} exceeds the 180 MB download limit.")
            out.write(chunk)
    if total < 1024:
        raise ValueError(f"{label} download was empty or too small.")


def run(command):
    subprocess.run(command, check=True)


def escape_drawtext(text):
    # Escape characters interpreted by FFmpeg's drawtext filter.
    return (text.replace("\\", "\\\\").replace(":", "\\:")
                .replace("'", "\\'").replace("%", "\\%"))


def main():
    source_config = read_json(os.environ.get("MONTAGE_SOURCES_FILE", "sources.json"))
    music_config = read_json("music.json")
    clips = source_config.get("clips", [])
    music_url = music_config.get("music_url", "").strip()

    if len(clips) < 2:
        raise ValueError(
            "Configure at least two authorized direct video-file URLs in sources.json. "
            "YouTube page URLs cannot be used here."
        )
    if not music_url:
        raise ValueError(
            "Set music_url in music.json to a direct download of music licensed for this TikTok post."
        )

    for i, clip in enumerate(clips[:6], 1):
        if not clip.get("url", "").strip():
            source = clip.get("source_page", "not provided")
            raise ValueError(
                f"Clip {i} has a source page ({source}) but no direct video-file URL. "
                "Ask the creator for an authorized media file or direct HTTPS file URL."
            )
        require_direct_https(clip.get("url", ""), f"Clip {i}")
        if not clip.get("approved", False):
            raise ValueError(
                f"Clip {i} needs approved=true only after verifying permission to download, edit, and repost it."
            )
        creator = clip.get("creator", "").strip()
        if creator not in ("@realfaxfortnite", "@InstrumentalRemake"):
            raise ValueError(
                f"Clip {i} needs creator set to exactly @realfaxfortnite or "
                "@InstrumentalRemake after checking who made that clip."
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="montage-") as temp_name:
        temp = Path(temp_name)
        prepared = []
        for i, clip in enumerate(clips[:6], 1):
            raw = temp / f"clip_{i}.bin"
            cooked = temp / f"prepared_{i}.mp4"
            download(clip["url"], raw, f"Clip {i}")
            credit_text = escape_drawtext(f"Clip by {clip['creator'].strip()}")
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(raw), "-t", str(CLIP_SECONDS),
                "-vf",
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},eq=contrast=1.08:saturation=1.15:brightness=0.01,"
                "unsharp=5:5:0.45:3:3:0.0,setsar=1,fps=30,"
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{credit_text}':fontcolor=white:fontsize=42:"
                "box=1:boxcolor=black@0.58:boxborderw=14:"
                "x=(w-text_w)/2:y=h-230,format=yuv420p",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-movflags", "+faststart", str(cooked)
            ])
            prepared.append(cooked)

        playlist = temp / "concat.txt"
        playlist.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in prepared),
            encoding="utf-8"
        )
        joined = temp / "joined.mp4"
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(playlist),
            "-c", "copy", str(joined)
        ])

        music = temp / "licensed_music.bin"
        download(music_url, music, "Licensed music")
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(joined), "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(OUTPUT)
        ])

    print(f"Montage created: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
