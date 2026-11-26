#!/usr/bin/env python3
"""Render original sounds for removing and seating the Hollow Trunk pin."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
PICKUP = "sfx_hollow_trunk_pin_pickup"
SEATING = "sfx_hollow_trunk_pin_seating"


def render(duration, seed, slide, strikes):
    rng = random.Random(seed)
    samples = bytearray()
    frames = round(duration * RATE)
    slide_onset, slide_length, direction = slide
    slow = mid = 0.0
    peak = 0
    for frame in range(frames):
        time = frame / RATE
        noise = rng.uniform(-1.0, 1.0)
        slow += 0.06 * (noise - slow)
        mid += 0.22 * (noise - mid)
        sample = 0.0
        progress = (time - slide_onset) / slide_length
        if 0 < progress < 1:
            rub = mid - slow
            wood = math.sin(math.tau * (21 * progress + direction * 5 * progress ** 2))
            sample = math.sin(math.pi * progress) ** 2 * (0.19 * rub + 0.047 * wood)
        for onset, pitch, strength in strikes:
            age = time - onset
            if 0 <= age < 0.18:
                body = math.sin(math.tau * pitch * age)
                key = math.sin(math.tau * 3.11 * pitch * age) * math.exp(-34 * age)
                grit = 0.12 * (noise - mid) * math.exp(-90 * age)
                envelope = min(1.0, age / 0.002, (0.18 - age) / 0.04) * math.exp(-27 * age)
                sample += strength * envelope * (0.53 * body + 0.22 * key + grit)
        encoded = round(22_000 * sample)
        peak = max(peak, abs(encoded))
        samples.extend(struct.pack("<h", encoded))
    return samples, peak


def write_cue(directory, cue, duration, seed, slide, strikes):
    samples, peak = render(duration, seed, slide, strikes)
    path = directory / f"{cue}.wav"
    frames = len(samples) // 2
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, RATE, frames, "NONE", "not compressed"))
        stream.writeframes(samples)
    return {
        "cue_id": cue,
        "file": path.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": frames,
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV files and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    cues = [
        write_cue(output, PICKUP, 0.56, 15229, (0.052, 0.31, 1), (
            (0.044, 187, 0.31), (0.322, 413, 0.61),
        )),
        write_cue(output, SEATING, 0.64, 15259, (0.035, 0.32, -1), (
            (0.208, 233, 0.26), (0.342, 315, 0.46), (0.395, 128, 0.83),
        )),
    ]
    (output / "manifest.json").write_text(json.dumps(cues, indent=2) + "\n", encoding="utf-8")
    for cue in cues:
        print(output / cue["file"])


if __name__ == "__main__":
    main()
