#!/usr/bin/env python3
"""Render two heavy hoof scrapes within the Marrow Ram's 1.15 s windup."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
FRAMES = RATE
CUE = "sfx_marrow_ram_hoof_telegraph"
# Onset in seconds, duration, and strike strength for each hoof.
SCRAPES = ((0.038, 0.31, 0.78), (0.472, 0.43, 1.0))


def render() -> tuple[bytearray, int]:
    noise = random.Random(334701)
    pcm = bytearray(FRAMES * 2)
    slow_grit = stone_grit = 0.0
    peak = 0
    for index in range(FRAMES):
        time = index / RATE
        grit = noise.uniform(-1, 1)
        slow_grit += 0.028 * (grit - slow_grit)
        stone_grit += 0.19 * (grit - stone_grit)
        sample = 0.0
        for onset, duration, force in SCRAPES:
            elapsed = time - onset
            if not 0 <= elapsed < duration:
                continue
            attack = min(1.0, elapsed / 0.004)
            decay = 1.0 - elapsed / duration
            strike = math.exp(-elapsed * 29) * (
                0.50 * math.sin(math.tau * (77 * elapsed - 27 * elapsed ** 2))
                + 0.15 * math.sin(math.tau * 165 * elapsed)
            )
            friction = (1.6 * (stone_grit - slow_grit) + 0.12 * (grit - stone_grit))
            chatter = 0.64 + 0.36 * math.cos(math.tau * (24 * elapsed - 9 * elapsed ** 2))
            sample += force * attack * decay ** 2 * (strike + chatter * friction)
        encoded = round(17_000 * sample)
        peak = max(peak, abs(encoded))
        struct.pack_into("<h", pcm, index * 2, encoded)
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
        "peak_sample": peak,
        "windup_seconds": 1.15,
        "loop": False,
        "sha256": hashlib.sha256(wav_file.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav_file)


if __name__ == "__main__":
    main()
