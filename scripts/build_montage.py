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
    path = Path(name)
    if not path.is_absolute():
        path = ROOT / path
    with path.open("r", encoding="utf-8") as f:
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
    music_file = music_config.get("music_file", "").strip()
    music_path = None
    if music_file:
        music_path = (ROOT / music_file).resolve()
        if ROOT.resolve() not in music_path.parents:
            raise ValueError("music_file must point to a file inside the repository.")
        if not music_path.is_file():
            raise ValueError(f"Music file not found: {music_file}. Add a licensed MP3 file.")

    if len(clips) < 2:
        raise ValueError(
            "Configure at least two authorized clip entries in sources.json. "
            "Each entry can use a local file inside the repository or a direct HTTPS video-file URL."
        )
    if not music_url and music_path is None:
        raise ValueError("Set music_file to assets/music.mp3 or configure a direct HTTPS music_url in music.json.")
    if music_url:
        require_direct_https(music_url, "Licensed music")

    local_sources = {}
    for i, clip in enumerate(clips[:6], 1):
        local_file = str(clip.get("file", "")).strip()
        direct_url = str(clip.get("url", "")).strip()
        if local_file:
            local_path = (ROOT / local_file).resolve()
            if ROOT.resolve() not in local_path.parents:
                raise ValueError(f"Clip {i} file must point inside the repository.")
            if not local_path.is_file():
                raise ValueError(f"Clip {i} local file not found: {local_file}. Add your authorized gameplay file.")
            if local_path.stat().st_size > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"Clip {i} local file exceeds the 180 MB limit.")
            local_sources[i] = local_path
        elif direct_url:
            require_direct_https(direct_url, f"Clip {i}")
        else:
            source = clip.get("source_page", "not provided")
            raise ValueError(
                f"Clip {i} has no local file or direct HTTPS video-file URL (source page: {source})."
            )
        start_seconds = clip.get("start_seconds", 0)
        if not isinstance(start_seconds, (int, float)) or start_seconds < 0:
            raise ValueError(f"Clip {i} start_seconds must be a non-negative number.")
        if not clip.get("approved", False):
            raise ValueError(
                f"Clip {i} needs approved=true only after verifying permission to download, edit, and repost it."
            )
        creator = clip.get("creator", "").strip()
        if not creator.startswith("@") or len(creator) > 31 or not creator[1:].replace(".", "").replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Clip {i} needs the correct creator handle, such as your own @handle.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="montage-") as temp_name:
        temp = Path(temp_name)
        prepared = []
        for i, clip in enumerate(clips[:6], 1):
            raw = local_sources.get(i)
            if raw is None:
                raw = temp / f"clip_{i}.bin"
                download(clip["url"], raw, f"Clip {i}")
            cooked = temp / f"prepared_{i}.mp4"
            credit_text = escape_drawtext(f"Clip by {clip['creator'].strip()}")
            seek_args = ["-ss", str(clip.get("start_seconds", 0))] if float(clip.get("start_seconds", 0)) > 0 else []
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                *seek_args, "-i", str(raw), "-t", str(CLIP_SECONDS),
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
        if music_path is not None:
            music.write_bytes(music_path.read_bytes())
        else:
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
