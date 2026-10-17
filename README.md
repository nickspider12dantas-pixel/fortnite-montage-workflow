# Fortnite Montage Workflow

This repository contains a GitHub Actions workflow that uses FFmpeg to build a vertical Fortnite montage from authorized direct video files.

## Current status

- The daily workflow and FFmpeg builder are installed.
- The workflow is **not ready to render a video yet** because `sources.json` contains no clips and `music.json` has no licensed music URL.
- It does not publish directly to TikTok or automatically select trending TikTok sounds.
- The output is saved as a GitHub Actions artifact for 7 days after a successful run.

## AutoClip API integration

The GitHub Actions workflow now submits approved source videos to AutoClip, polls each job, fetches the temporary clip download URLs, and passes those clips to the FFmpeg montage builder. Add the key under **Settings → Secrets and variables → Actions** with the exact name `AUTOCLIP_API_KEY`; never put the key in a repository file.

The integration uses `https://polished-turtle-977.convex.site` and the documented `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`, and `GET /api/v1/jobs/{id}/clips` endpoints. AutoClip's presigned download URLs may expire after one hour, so the workflow downloads them immediately. Each source is limited to two clips and the montage uses up to six clips total.

Before a source is submitted, set its `approved` value to `true` only if you have permission to submit that video to AutoClip and to edit/repost the resulting clips. The existing four source entries are still `approved: false`, so the workflow will stop safely until you confirm rights for the sources you intend to use. AutoClip may consume account quota or incur charges depending on your plan; check your account's limits before running the workflow. The workflow does not publish to TikTok.

## Add authorized footage and music

Edit `sources.json` and provide at least two direct HTTPS video-file URLs. Set `approved` to `true` only after you have permission to download, edit, and repost each clip:

```json
{
  "clips": [
    {"url": "https://your-authorized-host.example/clip1.mp4", "approved": true, "creator": "@realfaxfortnite"},
    {"url": "https://your-authorized-host.example/clip2.mp4", "approved": true, "creator": "@InstrumentalRemake"}
  ]
}
```

Replace the example URLs with actual direct media-file URLs. Set each clip’s `creator` to the correct handle for that exact clip; the video overlay will show only that creator as `Clip by @handle`. Do not guess the creator mapping. A YouTube watch/Shorts page is not a direct video file and will not work. Use files supplied by the footage owner or official download/export methods you are authorized to use. Permission for the video footage does not automatically clear music embedded in it.

Edit `music.json` to add a direct download URL for music licensed for use in your TikTok post:

```json
{
  "music_url": "https://your-authorized-host.example/track.mp3",
  "license_note": "License or source details"
}
```

Do not place passwords, API tokens, or other secrets in these public files.

## Run the workflow

1. Open the repository's **Actions** tab.
2. Select **Daily Fortnite montage**.
3. Choose **Run workflow** and confirm.
4. When the run finishes, open the run summary and download the `fortnite-montage-...` artifact.

The workflow also runs on a daily cron schedule at 21:30 UTC. That corresponds to 5:30 PM Eastern during daylight saving time and 4:30 PM Eastern during standard time. GitHub scheduled runs may be delayed and are not guaranteed to start at the exact minute.

## What it creates

- Portrait MP4, 1080 × 1920, 30 fps
- Up to six clips, approximately seven seconds per clip
- Original clip audio muted
- Licensed soundtrack added
- Light contrast, saturation, and sharpening

## Metricool Free and TikTok publishing

Your connected Metricool account can be used from ChatGPT for supported actions, but that connection does not automatically give GitHub Actions a Metricool API token. Unattended API scheduling needs Metricool API access, which is not available on the Free plan. After the montage is rendered, download the artifact and schedule it through the Metricool interface if video scheduling is available for your connected account.

Trending TikTok library sounds cannot be reliably embedded by this workflow. Add a sound through TikTok's supported tools when the posting method and account allow it.

## Free runner notes

GitHub Actions has usage and artifact limits; review your account's current Actions usage and billing settings. This workflow has a 25-minute job timeout and limits each downloaded media file to 180 MB.

## Free AI-assisted highlight finder (local footage)

A free helper script can rank candidate high-action moments from a local gameplay recording. It uses frame-to-frame visual motion as a heuristic; it does **not** reliably recognize kills or guarantee every moment is a highlight, so review the timestamps.

Install Python dependencies once:

```bash
python -m pip install -r requirements-highlights.txt
```

Run it on gameplay you recorded or are authorized to edit:

```bash
python scripts/find_highlights.py gameplay.mp4 --top 8 --clip-seconds 7
```

It writes `highlights.json` with suggested start times and motion scores. This helper runs locally for free and does not upload the video anywhere. It is separate from the GitHub Actions renderer, which still needs authorized direct media URLs and licensed music configured in `sources.json` and `music.json`.
