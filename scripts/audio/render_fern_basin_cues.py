#!/usr/bin/env python3
"""Render the Fern Basin handwheel and drain as original procedural cues."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
WHEEL = "sfx_fern_basin_handwheel_actuate"
DRAIN = "sfx_fern_basin_drain_release"
RATCHET = ((0.052, 0.46), (0.151, 0.52), (0.243, 0.58), (0.325, 0.65),
           (0.401, 0.69), (0.542, 1.0))


def handwheel() -> bytes:
    rng = random.Random(14117)
    samples = bytearray()
    grit = 0.0
    for frame in range(round(0.78 * RATE)):
        time = frame / RATE
        noise = rng.uniform(-1, 1)
        grit += 0.17 * (noise - grit)
        turning = max(0.0, 1.0 - abs(time - 0.26) / 0.24)
        sample = 0.055 * turning ** 2 * (noise - grit)
        for onset, strength in RATCHET:
            age = time - onset
            if 0 <= age < 0.20:
                attack = min(1.0, age / 0.002)
                release = min(1.0, (0.20 - age) / 0.035)
                clink = (
                    0.32 * math.sin(math.tau * 842 * age)
                    + 0.16 * math.sin(math.tau * 1297 * age)
                    + 0.12 * math.sin(math.tau * 291 * age)
                )
                sample += strength * attack * release * math.exp(-28 * age) * (
                    clink + 0.16 * (noise - grit) * math.exp(-90 * age)
                )
        samples.extend(struct.pack("<h", round(22_000 * sample)))
    return bytes(samples)


def drain_release() -> bytes:
    rng = random.Random(14429)
    samples = bytearray()
    slow = mid = 0.0
    for frame in range(round(1.55 * RATE)):
        time = frame / RATE
        noise = rng.uniform(-1, 1)
        slow += 0.023 * (noise - slow)
        mid += 0.11 * (noise - mid)
        attack = min(1.0, time / 0.045)
        release = min(1.0, (1.55 - time) / 0.22)
        gate = math.sin(math.tau * (52 * time + 0.58 * (1 - math.exp(-12 * time))))
        gate += 0.31 * math.sin(math.tau * (87 * time + 0.33 * (1 - math.exp(-9 * time))))
        surge = 1.0 - math.exp(-10 * time)
        water = 1.4 * (mid - slow) + 0.22 * (noise - mid)
        churn = 0.67 + 0.22 * math.sin(math.tau * 6.7 * time) + 0.11 * math.sin(math.tau * 11.2 * time)
        sample = attack * release * (
            0.31 * math.exp(-4.3 * time) * gate
            + 0.42 * surge * math.exp(-1.55 * time) * churn * water
        )
        samples.extend(struct.pack("<h", round(25_000 * sample)))
    return bytes(samples)


def write_asset(output: Path, cue_id: str, pcm: bytes) -> dict:
    file = output / f"{cue_id}.wav"
    frames = len(pcm) // 2
    with wave.open(str(file), "wb") as stream:
        stream.setparams((1, 2, RATE, frames, "NONE", "not compressed"))
        stream.writeframes(pcm)
    return {
        "cue_id": cue_id,
        "file": file.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": frames,
        "peak_sample": max(abs(sample) for (sample,) in struct.iter_unpack("<h", pcm)),
        "loop": False,
        "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV files and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    assets = [
        write_asset(output, WHEEL, handwheel()),
        write_asset(output, DRAIN, drain_release()),
    ]
    (output / "manifest.json").write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    for asset in assets:
        print(output / asset["file"])


if __name__ == "__main__":
    main()
