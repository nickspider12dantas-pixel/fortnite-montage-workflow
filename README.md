# Fortnite Montage Workflow

This repository contains a GitHub Actions workflow that uses FFmpeg to build a vertical Fortnite montage from authorized direct video files.

## Current status

- The daily workflow and FFmpeg builder are installed.
- The workflow generates its own original electronic soundtrack locally, so a music download or paid audio API is not required.
- The workflow is **not ready to render a video yet** because authorized gameplay footage is still missing.
- AutoClip is now opt-in only for a manual run. The default is OFF, and the scheduled workflow never submits AutoClip jobs.
- It does not publish directly to TikTok or automatically select trending TikTok sounds.
- The output is saved as a GitHub Actions artifact for 7 days after a successful run.

## AutoClip API integration

The GitHub Actions workflow now submits approved source videos to AutoClip, polls each job, fetches the temporary clip download URLs, and passes those clips to the FFmpeg montage builder. Add the key under **Settings → Secrets and variables → Actions** with the exact name `AUTOCLIP_API_KEY`; never put the key in a repository file.

The integration uses `https://polished-turtle-977.convex.site` and the documented `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`, and `GET /api/v1/jobs/{id}/clips` endpoints. AutoClip's presigned download URLs may expire after one hour, so the workflow downloads them immediately. Each source is limited to two clips and the montage uses up to six clips total.

AutoClip may consume account quota or incur charges depending on your plan. To prevent accidental usage, the workflow only calls AutoClip when you manually run it and turn on the `run_autoclip` input; that input defaults to false. The scheduled workflow never calls AutoClip. Do not turn it on until you have checked pricing/quotas and configured your own gameplay or footage whose owner explicitly gave permission. The workflow does not publish to TikTok.

## Add your own gameplay footage

The no-paid-API route is to use clips you recorded yourself. Upload two or more short clips to the repository under `assets/` (for example, `assets/gameplay1.mp4` and `assets/gameplay2.mp4`), then add entries to `sources.json`. GitHub's browser uploader has file-size limits, so keep each clip small or use direct HTTPS links to files you own and are authorized to edit. Do not upload other creators' videos without permission.

Example for two local clips:

```json
{
  "notice": "My own recorded Fortnite gameplay.",
  "clips": [
    {
      "file": "assets/gameplay1.mp4",
      "start_seconds": 0,
      "url": "",
      "approved": true,
      "creator": "@yourhandle"
    },
    {
      "file": "assets/gameplay2.mp4",
      "start_seconds": 0,
      "url": "",
      "approved": true,
      "creator": "@yourhandle"
    }
  ]
}
```

Replace the example filenames and handle with your real files and account. The renderer can also take multiple entries pointing to the same local recording with different `start_seconds` values, letting you choose different moments from a longer gameplay video. Use a local clip only if you own it or have permission to edit and repost it. Set `approved: true` only after confirming that permission.

An alternative is AutoClip: put your own authorized Unlisted YouTube recording in `source_page` and use the manual `run_autoclip` option. AutoClip can consume quota or incur charges, so it stays off by default. Do not enable it until you have checked your account's current pricing and quota.


### Fortnite fan-content notice

Epic's [Fan Content Policy](https://legal.epicgames.com/epicgames/fan-art-policy) requires a disclaimer in or in connection with fan content and says it must not appear official or imply Epic endorsement. When posting the montage, include this exact disclaimer in the TikTok caption/description:

> Portions of the materials used are trademarks and/or copyrighted works of Epic Games, Inc. All rights reserved by Epic. This material is not official and is not endorsed by Epic.

Use your own gameplay or footage you have permission to edit and repost. Epic's policy is generally for non-commercial fan content, with a limited exception for ad-monetized web videos; do not assume that every TikTok monetization program is covered. Check the current policy before monetizing.

### Music

The workflow generates an original electronic instrumental at runtime using `scripts/generate_music.py`. It uses Python's standard library, no third-party samples, no paid API, and no downloaded track. The soundtrack is a functional free default; you can replace it with a licensed track later if you prefer.

A possible replacement is [“Big Bitty (Techno | Dubstep | EDM | Electronic Music)” by firemansuperhero](https://pixabay.com/music/electronic-big-bitty-techno-dubstep-edm-electronic-music-121803/). Its page requests credit to FIREMAN and describes a no-Content-ID approach. Recheck the current track page and terms before use; no track can guarantee TikTok will never mute or flag a video.


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

It writes `highlights.json` with suggested start times and motion scores. This helper runs locally for free and does not upload the video anywhere. It is separate from the GitHub Actions renderer. The renderer accepts authorized local gameplay files stored under `assets/` or direct HTTPS video-file URLs in `sources.json`; it generates the default soundtrack from `music.json` and `scripts/generate_music.py`.
