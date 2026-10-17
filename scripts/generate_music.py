#!/usr/bin/env python3
"""Generate an original, royalty-free-style electronic backing loop using only Python's standard library.

No external audio, samples, APIs, or paid services are used. The output is a WAV file.
"""
import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "original_synth.wav"
RATE = 22050
BPM = 128
BEAT = 60.0 / BPM
BARS = 16
DURATION = BARS * 4 * BEAT
TOTAL = int(RATE * DURATION)
random.seed(41)


def envelope(t, length, attack=0.003, release=0.08):
    if t < 0 or t >= length:
        return 0.0
    a = min(1.0, t / max(attack, 1e-6))
    r = min(1.0, (length - t) / max(release, 1e-6))
    return a * r


def note(freq, t, length, kind="saw"):
    env = envelope(t, length, 0.008, min(0.12, length * 0.4))
    if env <= 0:
        return 0.0
    phase = 2.0 * math.pi * freq * t
    if kind == "bass":
        raw = math.sin(phase) * 0.72 + math.sin(phase * 2) * 0.20
    elif kind == "pluck":
        raw = math.sin(phase) * 0.7 + math.sin(phase * 2.01) * 0.2
        env *= math.exp(-3.0 * t / max(length, 0.001))
    else:
        raw = (2.0 / math.pi) * math.asin(math.sin(phase))
    return raw * env


def kick(t):
    if t < 0 or t > 0.22:
        return 0.0
    env = math.exp(-18 * t)
    freq = 115 - 70 * min(t / 0.22, 1)
    return math.sin(2 * math.pi * freq * t) * env * 0.92


def snare(t):
    if t < 0 or t > 0.18:
        return 0.0
    noise = random.uniform(-1, 1)
    return (noise * 0.55 + math.sin(2 * math.pi * 185 * t) * 0.35) * math.exp(-22 * t)


def hat(t):
    if t < 0 or t > 0.055:
        return 0.0
    return random.uniform(-1, 1) * math.exp(-65 * t) * 0.20


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # A minor pentatonic motif with a four-bar progression.
    scale = [110.00, 130.81, 146.83, 164.81, 196.00, 220.00]
    lead = [4, 3, 2, 4, 5, 4, 2, 1, 4, 5, 3, 2, 4, 3, 1, 2]
    left = []
    right = []
    for i in range(TOTAL):
        t = i / RATE
        beat_idx = int(t / BEAT)
        bar_beat = beat_idx % 4
        beat_t = t - beat_idx * BEAT
        bar = beat_idx // 4
        s = 0.0
        # Four-on-the-floor kick and backbeat snare/clap-style hit.
        s += kick(beat_t) if bar_beat in (0, 1, 2, 3) else 0
        if bar_beat in (1, 3):
            s += snare(beat_t) * 0.62
        # Eighth-note hats.
        halfbeat = BEAT / 2
        hat_t = t % halfbeat
        s += hat(hat_t)
        # Syncopated bass pulses.
        bass_step = int(t / (BEAT / 2))
        bass_t = t - bass_step * (BEAT / 2)
        bass_freq = scale[[0, 0, 3, 0, 4, 0, 2, 0][bass_step % 8]] / 2
        s += note(bass_freq, bass_t, BEAT * 0.34, "bass") * 0.50
        # Bright, short synth motif on selected eighth-note steps.
        if bass_step % 4 in (0, 3):
            idx = (bass_step // 2 + bar * 2) % len(lead)
            freq = scale[lead[idx]] * (2 if bar % 4 in (1, 3) else 1)
            s += note(freq, bass_t, BEAT * 0.28, "pluck") * 0.38
        # Soft sustained chord tones add a little fullness.
        chord_roots = [0, 3, 5, 2]
        root = scale[chord_roots[bar % 4]]
        chord_t = t % (BEAT * 4)
        s += note(root, chord_t, BEAT * 3.7, "saw") * 0.10
        s += note(root * 1.5, chord_t, BEAT * 3.7, "saw") * 0.065
        # Gentle stereo movement without changing the beat.
        pan = 0.78 + 0.16 * math.sin(2 * math.pi * t / 8.0)
        l = s * pan
        r = s * (1.56 - pan)
        # Soft saturation and conservative peak level.
        left.append(max(-0.92, min(0.92, math.tanh(l * 1.35) * 0.72)))
        right.append(max(-0.92, min(0.92, math.tanh(r * 1.35) * 0.72)))
    with wave.open(str(OUT), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        frames = bytearray()
        for l, r in zip(left, right):
            frames.extend(struct.pack("<hh", int(l * 32767), int(r * 32767)))
        wav.writeframes(frames)
    print(f"Generated original electronic soundtrack: {OUT} ({DURATION:.1f}s)")


if __name__ == "__main__":
    main()
