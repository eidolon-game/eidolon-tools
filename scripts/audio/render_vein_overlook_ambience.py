#!/usr/bin/env python3
"""Render a quiet, original cave ambience for the Vein Overlook."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from array import array
from pathlib import Path


RATE = 48_000
SECONDS = 21
FRAMES = RATE * SECONDS
CUE = "sfx_amb_vein_overlook"
# The intervals widen and the wood recedes toward the end of the passage.
WOOD = (
    (1.4, 1.3, 133, -0.7, 0.055),
    (3.2, 1.7, 107, 0.48, 0.049),
    (6.1, 2.0, 151, -0.23, 0.042),
    (10.4, 2.3, 96, 0.66, 0.034),
    (16.7, 2.6, 117, -0.43, 0.023),
)


def render() -> tuple[bytearray, int]:
    wood = array("d", [0]) * FRAMES
    room = array("d", [0]) * FRAMES
    rng = random.Random(192173)
    for onset, duration, frequency, pan, level in WOOD:
        start = round(onset * RATE)
        grain = soft = 0.0
        for index in range(round(duration * RATE)):
            age = index / RATE
            progress = age / duration
            noise = rng.uniform(-1, 1)
            grain += 0.16 * (noise - grain)
            soft += 0.033 * (noise - soft)
            resonance = math.tau * (frequency * age + 4 * age * age)
            scrape = (grain - soft) * (0.57 + 0.43 * math.sin(math.tau * 5.2 * age) ** 2)
            body = 0.59 * math.sin(resonance) + 0.25 * math.sin(2.33 * resonance)
            envelope = math.sin(math.pi * progress) ** 2 * math.exp(-1.1 * progress)
            value = level * envelope * (body + scrape)
            wood[start + index] += value
            room[start + index] += pan * value

    pcm = bytearray(FRAMES * 4)
    peak = 0
    for frame in range(FRAMES):
        phase = math.tau * frame / FRAMES
        suspension = 0.81 + 0.13 * math.cos(phase - 0.6) + 0.06 * math.sin(3 * phase)
        low = suspension * (
            0.017 * math.sin(617 * phase + 0.4)
            + 0.013 * math.sin(743 * phase - 0.8)
            + 0.008 * math.sin(979 * phase + 1.7)
        )
        width = 0.004 * math.sin(883 * phase - 0.6) * math.sin(phase + 1.3)
        delayed = wood[(frame - 5664) % FRAMES]
        direct = low + wood[frame] + 0.22 * delayed
        width += 0.45 * room[frame] - 0.11 * room[(frame - 5664) % FRAMES]
        left = round(32_000 * (direct + width))
        right = round(32_000 * (direct - width))
        peak = max(peak, abs(left), abs(right))
        struct.pack_into("<hh", pcm, frame * 4, left, right)
    return pcm, peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    pcm, peak = render()
    wav = output / f"{CUE}.wav"
    with wave.open(str(wav), "wb") as stream:
        stream.setparams((2, 2, RATE, FRAMES, "NONE", "not compressed"))
        stream.writeframes(pcm)
    manifest = {
        "cue_id": CUE,
        "file": wav.name,
        "channels": 2,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": FRAMES,
        "loop_start_frame": 0,
        "loop_end_frame_exclusive": FRAMES,
        "peak_sample": peak,
        "sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav)


if __name__ == "__main__":
    main()
