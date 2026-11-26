#!/usr/bin/env python3
"""Render the Double Clearing latch's held detent and deep opening cues."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
DETENT = "sfx_double_clearing_latch_held"
OPENING = "sfx_double_clearing_latch_open"


def decay(age: float, length: float, rate: float) -> float:
    if not 0 <= age < length:
        return 0.0
    return min(1.0, age / 0.003, (length - age) / 0.055) * math.exp(-rate * age)


def detent(time: float, grit: float) -> float:
    tooth = time - 0.052
    held = time - 0.174
    return (
        decay(tooth, 0.13, 37) * (0.19 * math.sin(math.tau * 724 * tooth) + 0.12 * grit)
        + decay(held, 0.24, 18) * (
            0.29 * math.sin(math.tau * 231 * held)
            + 0.17 * math.sin(math.tau * 617 * held)
            + 0.12 * grit * math.exp(-46 * max(0.0, held))
        )
    )


def opening(time: float, grit: float) -> float:
    release = time - 0.075
    travel = time - 0.16
    seat = time - 0.58
    return (
        decay(release, 0.13, 29) * (0.22 * math.sin(math.tau * 473 * release) + 0.14 * grit)
        + decay(travel, 0.57, 2.1) * (
            0.15 * math.sin(math.tau * (58 * travel - 13 * travel ** 2))
            + 0.16 * (0.58 + 0.42 * math.sin(math.tau * 8.3 * travel)) * grit
        )
        + decay(seat, 0.52, 7) * (
            0.42 * math.sin(math.tau * 49 * seat)
            + 0.12 * math.sin(math.tau * 133 * seat)
        )
    )


def write_cue(output, cue, seconds, seed, synthesize):
    rng = random.Random(seed)
    frames = round(seconds * RATE)
    pcm = bytearray(frames * 2)
    smooth = 0.0
    peak = 0
    for index in range(frames):
        noise = rng.uniform(-1, 1)
        smooth += 0.21 * (noise - smooth)
        grit = 0.53 * (noise - smooth) + 1.15 * smooth
        sample = round(23_000 * synthesize(index / RATE, grit))
        peak = max(peak, abs(sample))
        struct.pack_into("<h", pcm, index * 2, sample)

    wav = output / f"{cue}.wav"
    with wave.open(str(wav), "wb") as stream:
        stream.setparams((1, 2, RATE, frames, "NONE", "not compressed"))
        stream.writeframes(pcm)
    return {
        "cue_id": cue,
        "file": wav.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": frames,
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV files and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    assets = [
        write_cue(output, DETENT, 0.48, 18211, detent),
        write_cue(output, OPENING, 1.24, 18293, opening),
    ]
    (output / "manifest.json").write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    for asset in assets:
        print(output / asset["file"])


if __name__ == "__main__":
    main()
