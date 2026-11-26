#!/usr/bin/env python3
"""Render the Suspended Bridge's original timber pivot and latch seating cue."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
SECONDS = 2.58
FRAMES = round(RATE * SECONDS)
CUE = "sfx_suspended_bridge_rotation"
LATCH_TIME = 1.88


def render() -> tuple[bytearray, int]:
    rng = random.Random(17343)
    pcm = bytearray(FRAMES * 2)
    grain = slow = 0.0
    peak = 0
    for frame in range(FRAMES):
        time = frame / RATE
        noise = rng.uniform(-1.0, 1.0)
        grain += 0.20 * (noise - grain)
        slow += 0.025 * (noise - slow)
        sample = 0.0

        move = (time - 0.07) / 1.78
        if 0 < move < 1:
            flex = math.sin(math.pi * move) ** 1.6 * (0.54 + 0.46 * move)
            # A rising bending mode carries the strain while irregular friction breaks it up.
            bend_phase = math.tau * (52 * time + 17 * time * time)
            stick_slip = 0.52 + 0.48 * math.sin(math.tau * (5.2 * time + 1.2 * time * time)) ** 2
            wood = 0.21 * math.sin(bend_phase) + 0.12 * math.sin(2.36 * bend_phase)
            rasp = 0.88 * (grain - slow) + 0.20 * (noise - grain)
            sample += flex * (wood + stick_slip * rasp)

        age = time - LATCH_TIME
        if 0 <= age < 0.61:
            onset = min(1.0, age / 0.006)
            tail = min(1.0, (0.61 - age) / 0.12)
            seat = 0.37 * math.sin(math.tau * (65 * age - 10 * age * age)) * math.exp(-11 * age)
            block = 0.18 * math.sin(math.tau * 127 * age) * math.exp(-20 * age)
            tick = 0.12 * (noise - grain) * math.exp(-83 * age)
            sample += onset * tail * (seat + block + tick)

        encoded = round(22_000 * sample)
        peak = max(peak, abs(encoded))
        struct.pack_into("<h", pcm, frame * 2, encoded)
    return pcm, peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    pcm, peak = render()
    wav_file = output / f"{CUE}.wav"
    with wave.open(str(wav_file), "wb") as stream:
        stream.setparams((1, 2, RATE, FRAMES, "NONE", "not compressed"))
        stream.writeframes(pcm)
    manifest = {
        "cue_id": CUE,
        "file": wav_file.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": FRAMES,
        "latch_seconds": LATCH_TIME,
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(wav_file.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav_file)


if __name__ == "__main__":
    main()
