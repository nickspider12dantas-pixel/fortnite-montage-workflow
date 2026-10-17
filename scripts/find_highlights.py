#!/usr/bin/env python3
"""Find candidate high-action moments in authorized local gameplay footage.

Uses frame-to-frame visual change as a free heuristic. It cannot reliably identify
kills by itself; review the suggested timestamps before publishing.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def find_candidates(path: Path, sample_every: float, clip_seconds: float, top_n: int):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if fps else 0
    if duration <= clip_seconds:
        cap.release()
        return [{"start_seconds": 0.0, "score": 0.0, "duration_seconds": duration}]

    step = max(1, round(fps * sample_every))
    previous = None
    scores = []
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step == 0:
            small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                score = float(np.mean(cv2.absdiff(gray, previous))) / 255.0
                timestamp = frame_index / fps
                scores.append((timestamp, score))
            previous = gray
        frame_index += 1

    cap.release()
    if not scores:
        return [{"start_seconds": 0.0, "score": 0.0, "duration_seconds": clip_seconds}]

    # Smooth nearby samples, then rank windows by average motion score.
    radius = max(1, round(clip_seconds / sample_every / 2))
    ranked = []
    for i, (timestamp, _) in enumerate(scores):
        lo, hi = max(0, i - radius), min(len(scores), i + radius + 1)
        avg = sum(s for _, s in scores[lo:hi]) / (hi - lo)
        start = max(0.0, min(timestamp - clip_seconds / 2, duration - clip_seconds))
        ranked.append((avg, start))

    chosen = []
    minimum_gap = clip_seconds * 0.8
    for score, start in sorted(ranked, reverse=True):
        if all(abs(start - existing["start_seconds"]) >= minimum_gap for existing in chosen):
            chosen.append({
                "start_seconds": round(start, 2),
                "score": round(score, 4),
                "duration_seconds": clip_seconds,
            })
        if len(chosen) >= top_n:
            break
    return sorted(chosen, key=lambda item: item["start_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Local video file you own or are authorized to edit")
    parser.add_argument("--clip-seconds", type=float, default=7.0)
    parser.add_argument("--sample-every", type=float, default=0.5)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("highlights.json"))
    args = parser.parse_args()

    if args.clip_seconds <= 0 or args.sample_every <= 0 or args.top < 1:
        parser.error("clip-seconds and sample-every must be positive; top must be at least 1")

    candidates = find_candidates(args.video, args.sample_every, args.clip_seconds, args.top)
    result = {
        "source_file": args.video.name,
        "method": "frame-difference motion heuristic; review before publishing",
        "highlights": candidates,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(candidates)} candidate moments to {args.output}")
    for item in candidates:
        print(f"{item['start_seconds']:>8.2f}s  score={item['score']:.4f}")


if __name__ == "__main__":
    main()
