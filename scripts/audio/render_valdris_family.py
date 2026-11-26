#!/usr/bin/env python3
"""Render a quiet original nylon-string-style theme for the Valdris household."""

import argparse
import hashlib
import json
import math
import random
from array import array
import struct
import wave
from pathlib import Path


RATE = 48_000
BEAT = 0.75
CUE = "music_valdris_family"
# Eight bars in 3/4. Entries are (MIDI pitch, beat within the bar, strength).
SCORE = (
    ((50, 0, .65), (57, .5, .4), (65, 1, .80), (64, 2, .61)),
    ((46, 0, .63), (53, .5, .4), (62, 1, .73), (60, 2.5, .48)),
    ((48, 0, .61), (55, .5, .4), (64, 1, .77), (67, 2, .63)),
    ((45, 0, .59), (52, .5, .4), (65, 1, .67), (64, 2, .53)),
    ((50, 0, .64), (57, .5, .4), (69, 1, .77), (67, 2, .57)),
    ((46, 0, .60), (53, .5, .4), (65, 1, .71), (62, 2, .57)),
    ((43, 0, .58), (50, .5, .4), (64, 1, .71), (61, 2, .56)),
    ((50, 0, .66), (57, .5, .4), (62, 1, .78), (65, 1.5, .45), (69, 2, .39)),
)


def synthesize() -> bytearray:
    frames = round(RATE * (3 * len(SCORE) * BEAT + 3))
    dry = array("d", [0]) * frames
    noise = random.Random(63041)
    for bar_number, bar in enumerate(SCORE):
        for note, beat, volume in bar:
            start = round((3 * bar_number + beat) * BEAT * RATE)
            frequency = 440 * 2 ** ((note - 69) / 12)
            fall = 1.6 if note < 58 else 2.2
            vibration = math.tau * frequency / RATE
            phase = noise.uniform(-0.2, 0.2)
            for index in range(min(round(2.75 * RATE), frames - start)):
                t = index / RATE
                attack = min(1.0, t / .005)
                release = min(1.0, (2.75 - t) / .12)
                damping = math.exp(-fall * t)
                angle = index * vibration + phase
                string = (
                    math.sin(angle)
                    + .35 * math.sin(2 * angle) * math.exp(-2 * t)
                    + .19 * math.sin(3 * angle) * math.exp(-4 * t)
                    + .11 * math.sin(5 * angle) * math.exp(-6 * t)
                )
                pick = noise.uniform(-1, 1) * .10 * (1 - t / .018) if t < .018 else 0
                dry[start + index] += volume * attack * release * (string * damping + pick)

    pcm = bytearray(frames * 4)
    for index, direct in enumerate(dry):
        left_echo = dry[index - 1272] if index >= 1272 else 0
        right_echo = dry[index - 1728] if index >= 1728 else 0
        tail = min(1.0, (frames - 1 - index) / (RATE * .25))
        left = round(5800 * tail * (.94 * direct + .13 * left_echo))
        right = round(5800 * tail * (.94 * direct + .13 * right_echo))
        struct.pack_into("<hh", pcm, index * 4, left, right)
    return pcm


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    destination = parser.parse_args().output
    destination.mkdir(parents=True, exist_ok=True)
    pcm = synthesize()
    preview = destination / f"{CUE}.wav"
    with wave.open(str(preview), "wb") as stream:
        stream.setparams((2, 2, RATE, len(pcm) // 4, "NONE", "not compressed"))
        stream.writeframes(pcm)
    manifest = {
        "cue_id": CUE,
        "file": preview.name,
        "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "channels": 2,
        "sample_rate": RATE,
        "frames": len(pcm) // 4,
        "loop": False,
        "source": "Original composition and procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(preview)


if __name__ == "__main__":
    main()
