#!/usr/bin/env python3
"""Render an original, seamless stereo ambience sketch for Abyss floor 01."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 48_000
LOOP_SECONDS = 12
FRAMES = SAMPLE_RATE * LOOP_SECONDS
CUE = "sfx_amb_abyss_floor_01"


def write_loop(destination: Path) -> dict:
    random_source = random.Random(0xE1D010)
    # Integer cycles over the loop keep both frequencies and motion phase continuous.
    air_partials = [
        (rate, random_source.uniform(0, math.tau), 0.016 / math.sqrt(index + 1))
        for index, rate in enumerate((63, 89, 137, 201, 289, 431, 593, 809))
    ]
    max_sample = 0
    samples = bytearray(FRAMES * 4)
    for index in range(FRAMES):
        angle = math.tau * index / FRAMES
        swell = 0.72 + 0.17 * math.cos(angle) + 0.11 * math.sin(3 * angle)
        bed = swell * (
            0.12 * math.sin(371 * angle)
            + 0.06 * math.sin(449 * angle + 0.8)
            + 0.035 * math.sin(741 * angle + 1.3)
        )
        air = sum(weight * math.sin(rate * angle + phase) for rate, phase, weight in air_partials)
        side = 0.012 * math.sin(577 * angle) * math.sin(angle + 0.4)
        drip = 0.022 * math.sin(8321 * angle) * ((1 + math.cos(3 * angle + 0.6)) / 2) ** 34
        left = round((bed + air + drip + side) * 32767)
        right = round((bed + air + drip - side) * 32767)
        max_sample = max(max_sample, abs(left), abs(right))
        struct.pack_into("<hh", samples, index * 4, left, right)

    destination.mkdir(parents=True, exist_ok=True)
    preview = destination / f"{CUE}.wav"
    with wave.open(str(preview), "wb") as output:
        output.setparams((2, 2, SAMPLE_RATE, FRAMES, "NONE", "not compressed"))
        output.writeframes(samples)

    return {
        "cue_id": CUE,
        "file": preview.name,
        "channels": 2,
        "sample_rate": SAMPLE_RATE,
        "bits_per_sample": 16,
        "frames": FRAMES,
        "loop_start_frame": 0,
        "loop_end_frame_exclusive": FRAMES,
        "peak_sample": max_sample,
        "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    destination = parser.parse_args().output
    manifest = write_loop(destination)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(destination / manifest["file"])


if __name__ == "__main__":
    main()
