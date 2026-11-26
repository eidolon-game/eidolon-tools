#!/usr/bin/env python3
"""Render an original counterweight and iron gate release for Rootlet Canal."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
SECONDS = 2.68
FRAMES = round(SECONDS * RATE)
CUE = "sfx_rootlet_canal_counterweight_gate"
# Chain links accelerate as the weight falls. The last contact is the raised gate.
CONTACTS = (0.21, 0.43, 0.62, 0.79, 0.945, 1.08, 1.20, 1.31, 1.41, 1.50, 1.58)
GATE_STOP = 1.83


def render() -> tuple[bytearray, int]:
    rng = random.Random(161993)
    dry = bytearray(FRAMES * 2)
    grit = 0.0
    peak = 0
    for frame in range(FRAMES):
        time = frame / RATE
        noise = rng.uniform(-1.0, 1.0)
        grit += 0.072 * (noise - grit)
        sample = 0.0

        fall = (time - 0.10) / 1.68
        if 0 < fall < 1:
            bed = math.sin(math.tau * (66 * time - 9 * time * time))
            shudder = 0.66 + 0.34 * math.sin(math.tau * (7 * time + 2 * time * time))
            sample += math.sin(math.pi * fall) ** 2 * (
                0.14 * bed + 0.21 * shudder * (noise - grit) + 0.62 * grit
            )

        for index, onset in enumerate(CONTACTS):
            age = time - onset
            if 0 <= age < 0.115:
                attack = min(1.0, age / 0.0018)
                decay = math.exp(-58 * age) * min(1.0, (0.115 - age) / 0.025)
                pitch = 890 - 23 * index
                rings = 0.17 * math.sin(math.tau * pitch * age)
                rings += 0.11 * math.sin(math.tau * 1.74 * pitch * age)
                sample += attack * decay * (rings + 0.15 * (noise - grit))

        impact = time - GATE_STOP
        if 0 <= impact < 0.8:
            attack = min(1.0, impact / 0.005)
            fade = min(1.0, (0.80 - impact) / 0.16)
            iron = math.exp(-9 * impact) * (
                0.28 * math.sin(math.tau * 193 * impact)
                + 0.17 * math.sin(math.tau * 317 * impact)
                + 0.08 * math.sin(math.tau * 700 * impact)
            )
            hollow = 0.29 * math.exp(-4.8 * impact) * math.sin(math.tau * 49 * impact)
            slap = 0.20 * math.exp(-81 * impact) * (noise - grit)
            sample += attack * fade * (iron + hollow + slap)

        encoded = round(23_000 * sample)
        peak = max(peak, abs(encoded))
        struct.pack_into("<h", dry, frame * 2, encoded)
    return dry, peak


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
        "loop": False,
        "sha256": hashlib.sha256(wav_file.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav_file)


if __name__ == "__main__":
    main()
