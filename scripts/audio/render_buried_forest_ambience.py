#!/usr/bin/env python3
"""Render the Buried Forest's original root, water and wood ambience."""

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
SECONDS = 22
FRAMES = RATE * SECONDS
CUE = "sfx_amb_buried_forest"
ROOTS = ((1.7, 3.4, 47, -0.7), (8.2, 2.9, 39, 0.55), (13.9, 3.8, 43, -0.3), (19.3, 3.2, 36, 0.6))
DRIPS = ((0.8, 351, 0.4), (3.4, 419, -0.7), (5.7, 287, 0.6), (6.2, 493, -0.5),
         (10.1, 329, 0.2), (14.4, 421, -0.4), (17.1, 301, 0.7), (19.8, 369, -0.7))
WOOD = ((4.8, 131, -0.3), (11.8, 147, 0.6), (16.6, 123, -0.55))


def render() -> tuple[bytearray, int]:
    center = array("d", [0]) * FRAMES
    side = array("d", [0]) * FRAMES
    rng = random.Random(89147)

    for onset, duration, frequency, pan in ROOTS:
        start = round(onset * RATE)
        grit = 0.0
        for index in range(round(duration * RATE)):
            time = index / RATE
            progress = time / duration
            phase = math.tau * frequency * time
            wobble = 1.8 * math.sin(math.tau * 0.46 * time)
            grit += 0.12 * (rng.uniform(-1, 1) - grit)
            envelope = math.sin(math.pi * progress) ** 2
            vibration = math.sin(phase + wobble) + 0.37 * math.sin(2 * phase + wobble)
            crack = 0.22 * grit * (0.4 + 0.6 * math.sin(math.tau * 4.4 * time) ** 2)
            sample = 0.14 * envelope * (vibration + crack)
            frame = (start + index) % FRAMES
            center[frame] += sample
            side[frame] += pan * sample

    for onset, frequency, pan in DRIPS:
        start = round(onset * RATE)
        for index in range(round(0.52 * RATE)):
            time = index / RATE
            phase = math.tau * (frequency * time + 174 * time * time)
            splash = (math.sin(phase) + 0.36 * math.sin(2.7 * phase)) * math.exp(-29 * time)
            echo = 0.24 * math.sin(math.tau * frequency * time) * math.exp(-12 * time)
            fade = min(1.0, time / 0.003, (0.52 - time) / 0.07)
            sample = 0.09 * fade * (splash + echo)
            center[start + index] += sample
            side[start + index] += pan * sample

    for onset, frequency, pan in WOOD:
        start = round(onset * RATE)
        for index in range(round(2.2 * RATE)):
            time = index / RATE
            phase = math.tau * frequency * time
            decay = min(1.0, time / 0.035, (2.2 - time) / 0.2) * math.exp(-2.1 * time)
            sample = 0.06 * decay * (math.sin(phase) + 0.44 * math.sin(2.36 * phase))
            center[start + index] += sample
            side[start + index] += pan * sample

    pcm = bytearray(FRAMES * 4)
    peak = 0
    for index in range(FRAMES):
        # Integral cycles keep the bed continuous across the loop boundary.
        angle = math.tau * index / FRAMES
        bed = (0.031 * math.sin(697 * angle + 0.3) + 0.019 * math.sin(947 * angle)) * (
            0.78 + 0.22 * math.cos(2 * angle)
        )
        direct = center[index] + bed
        width = 0.47 * side[index] + 0.008 * math.sin(1151 * angle + 0.4)
        left = round(29000 * (direct + width))
        right = round(29000 * (direct - width))
        peak = max(peak, abs(left), abs(right))
        struct.pack_into("<hh", pcm, index * 4, left, right)
    return pcm, peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    pcm, peak = render()
    wav_file = output / f"{CUE}.wav"
    with wave.open(str(wav_file), "wb") as stream:
        stream.setparams((2, 2, RATE, FRAMES, "NONE", "not compressed"))
        stream.writeframes(pcm)
    manifest = {
        "cue_id": CUE,
        "file": wav_file.name,
        "channels": 2,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": FRAMES,
        "loop_start_frame": 0,
        "loop_end_frame_exclusive": FRAMES,
        "peak_sample": peak,
        "sha256": hashlib.sha256(wav_file.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav_file)


if __name__ == "__main__":
    main()
