#!/usr/bin/env python3
"""Render Riftroot Tangle's original rock wedge and root retraction cues."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path


RATE = 48_000
WEDGE = "sfx_riftroot_rock_wedge"
ROOTS = "sfx_riftroot_root_retraction"


def fade_window(age: float, duration: float, attack: float, release: float) -> float:
    if not 0 <= age < duration:
        return 0.0
    return min(1.0, age / attack, (duration - age) / release)


def rock_wedge(time: float, stone: float, grain: float) -> float:
    lift = time - 0.038
    axis = time - 0.650
    impact = time - 1.050
    rumble = math.sin(math.tau * (43 * lift - 5 * lift * lift))
    load = fade_window(lift, 0.76, 0.12, 0.21) * (0.14 * rumble + 0.3 * grain)
    lock = fade_window(axis, 0.2, 0.008, 0.05) * math.exp(-21 * max(0.0, axis)) * (
        0.09 * math.sin(math.tau * 177 * axis) + 0.23 * stone
    )
    thump = math.sin(math.tau * (45 * impact + 0.42 * (1 - math.exp(-36 * max(0.0, impact)))))
    rubble = 0.71 * grain + 0.21 * stone
    hit = fade_window(impact, 0.65, 0.004, 0.16) * math.exp(-5.0 * max(0.0, impact)) * (
        0.71 * thump + rubble
    )
    return load + lock + hit


def root_retraction(time: float, stone: float, grain: float) -> float:
    tension = time - 0.05
    yank = time - 1.07
    twine = math.sin(math.tau * (84 * tension + 63 * tension * tension))
    fiber = math.sin(math.tau * (127 * tension + 96 * tension * tension))
    strain = fade_window(tension, 1.02, 0.16, 0.045) * (0.4 + 0.6 * max(0.0, tension)) * (
        0.19 * twine + 0.11 * fiber + 0.13 * grain
    )
    flutter = 0.63 + 0.37 * math.cos(math.tau * (11 * yank - 4 * yank * yank))
    wound = math.sin(math.tau * (245 * yank - 102 * yank * yank))
    return strain + fade_window(yank, 0.56, 0.006, 0.12) * math.exp(-5.6 * max(0.0, yank)) * (
        0.21 * wound + flutter * (0.33 * stone + 0.49 * grain)
    )


def write_cue(out, cue, duration, seed, shape, timing):
    rng = random.Random(seed)
    frames = round(RATE * duration)
    pcm = bytearray(frames * 2)
    medium = floor = 0.0
    peak = 0
    for frame in range(frames):
        noise = rng.uniform(-1, 1)
        medium += 0.17 * (noise - medium)
        floor += 0.038 * (noise - floor)
        sample = round(22_000 * shape(frame / RATE, noise - medium, medium - floor))
        peak = max(peak, abs(sample))
        struct.pack_into("<h", pcm, frame * 2, sample)

    wav = out / f"{cue}.wav"
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
        "timing_seconds": timing,
        "peak_sample": peak,
        "sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "loop": False,
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV files and manifest.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    assets = [
        write_cue(output, WEDGE, 1.82, 20379, rock_wedge, {"axis_lock": 0.65, "impact": 1.05}),
        write_cue(output, ROOTS, 1.74, 20731, root_retraction, {"retraction": 1.07}),
    ]
    (output / "manifest.json").write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    for asset in assets:
        print(output / asset["file"])


if __name__ == "__main__":
    main()
