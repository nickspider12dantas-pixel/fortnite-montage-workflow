import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("AUTOCLIP_BASE_URL", "https://polished-turtle-977.convex.site").rstrip("/")
API_KEY = os.environ.get("AUTOCLIP_API_KEY", "").strip()
SOURCE_FILE = ROOT / "sources.json"
OUTPUT_FILE = ROOT / "output" / "autoclip_sources.json"
ALLOWED_CREATORS = {"@realfaxfortnite", "@InstrumentalRemake"}
MAX_WAIT_SECONDS = 20 * 60
POLL_SECONDS = 10


def request_json(path, method="GET", payload=None):
    if not API_KEY:
        raise RuntimeError("Missing AUTOCLIP_API_KEY. Add it under GitHub Settings > Secrets and variables > Actions.")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"AutoClip API returned HTTP {exc.code} for {path}: {detail}") from exc


def find_media_urls(value):
    found = []
    url_keys = {"url", "downloadurl", "mediaurl", "video_url", "videourl", "download_url", "presignedurl", "presigned_url"}
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.replace("-", "_").lower()
            if normalized in url_keys and isinstance(item, str) and item.startswith("https://"):
                found.append(item)
            else:
                found.extend(find_media_urls(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(find_media_urls(item))
    # Keep order while removing duplicates.
    return list(dict.fromkeys(found))


def main():
    if not API_KEY:
        raise RuntimeError("AUTOCLIP_API_KEY is not set.")
    config = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    approved = []
    for index, item in enumerate(config.get("clips", []), start=1):
        if not item.get("approved", False):
            continue
        source_url = (item.get("source_page") or item.get("url") or "").strip()
        creator = (item.get("creator") or "").strip()
        if not source_url.startswith("https://"):
            raise RuntimeError(f"Approved source {index} needs an HTTPS source_page or url.")
        if creator not in ALLOWED_CREATORS:
            raise RuntimeError(f"Approved source {index} must identify its verified creator as one of: {', '.join(sorted(ALLOWED_CREATORS))}.")
        approved.append({"url": source_url, "creator": creator, "source_index": index})

    if not approved:
        raise RuntimeError("No approved sources. Set approved=true only for videos you have permission to submit, edit, and repost.")

    results = []
    for source in approved:
        print(f"Submitting approved source {source['source_index']} to AutoClip for {source['creator']}...")
        submitted = request_json("/api/v1/jobs", method="POST", payload={"url": source["url"], "maxClips": 2})
        job_id = submitted.get("id") or submitted.get("jobId")
        if not job_id:
            raise RuntimeError(f"AutoClip submit response did not include a job id: {json.dumps(submitted)[:1000]}")
        deadline = time.monotonic() + MAX_WAIT_SECONDS
        status_data = submitted
        while True:
            status = str(status_data.get("status", "")).lower()
            if status in {"completed", "complete", "succeeded", "success", "done"}:
                break
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"AutoClip job {job_id} ended with status {status}: {json.dumps(status_data)[:1000]}")
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for AutoClip job {job_id}; last status: {status or 'unknown'}")
            time.sleep(POLL_SECONDS)
            status_data = request_json(f"/api/v1/jobs/{job_id}")

        clip_data = request_json(f"/api/v1/jobs/{job_id}/clips")
        urls = find_media_urls(clip_data)
        if not urls:
            raise RuntimeError(f"AutoClip job {job_id} completed, but no HTTPS clip download URLs were found in the response: {json.dumps(clip_data)[:1600]}")
        for url in urls:
            results.append({
                "url": url,
                "approved": True,
                "creator": source["creator"],
                "source_job_id": job_id
            })
            if len(results) >= 6:
                break
        if len(results) >= 6:
            break

    if len(results) < 2:
        raise RuntimeError(f"AutoClip returned only {len(results)} usable clip URLs; at least 2 are needed.")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps({"notice": "Temporary AutoClip output; presigned links may expire after one hour.", "clips": results}, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(results)} AutoClip clip URLs in {OUTPUT_FILE.relative_to(ROOT)}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
