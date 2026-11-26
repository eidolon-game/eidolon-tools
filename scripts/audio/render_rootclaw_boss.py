#!/usr/bin/env python3
"""Render Rootclaw's original ritual ostinato and final brass phrase."""

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
BEAT = 0.63
BARS = 8
FRAMES = round(RATE * (BARS * 4 * BEAT + 1.8))
CUE = "music_rootclaw_ritual"
OSTINATO = (
    (38, 38, 41, 37, 38),
    (38, 38, 36, 41, 38),
    (38, 38, 41, 43, 38),
    (37, 37, 40, 43, 37),
    (38, 38, 41, 37, 38),
    (43, 43, 46, 41, 43),
    (46, 46, 48, 49, 46),
    (38, 38, 45, 50, 38),
)
BRASS = (
    (1.5, (50, 57)),
    (7.0, (48, 53)),
    (9.5, (53, 58)),
    (14.0, (49, 55)),
    (17.0, (50, 57)),
    (21.5, (55, 62)),
    (24.0, (58, 65)),
    (26.0, (60, 67)),
    (28.0, (61, 69)),
    (30.0, (62, 69, 74)),
)


def frequency(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def render() -> tuple[bytearray, int]:
    bass = array("d", [0]) * FRAMES
    horns = array("d", [0]) * FRAMES
    drums = array("d", [0]) * FRAMES
    rng = random.Random(234139)

    for bar, phrase in enumerate(OSTINATO):
        for index, (offset, note) in enumerate(zip((0, 0.75, 1.5, 2.5, 3.5), phrase)):
            start = round((4 * bar + offset) * BEAT * RATE)
            pitch = math.tau * frequency(note)
            strength = 0.23 if index in (0, 3) else 0.16
            for frame in range(round(0.54 * RATE)):
                time = frame / RATE
                phase = pitch * time
                envelope = min(1.0, time / 0.012, (0.54 - time) / 0.1) * math.exp(-6 * time)
                vibration = math.sin(phase) + 0.36 * math.sin(2 * phase) + 0.12 * math.sin(4 * phase)
                bass[start + frame] += strength * envelope * vibration

        for beat, level in ((0, 0.36), (1.75, 0.22), (2.5, 0.28), (3.5, 0.13)):
            start = round((4 * bar + beat) * BEAT * RATE)
            grit = 0.0
            for frame in range(round(0.44 * RATE)):
                time = frame / RATE
                noise = rng.uniform(-1, 1)
                grit += 0.18 * (noise - grit)
                thump = math.sin(math.tau * (59 * time + 0.58 * (1 - math.exp(-35 * time))))
                skin = 0.20 * math.sin(math.tau * 113 * time) + 0.35 * grit
                envelope = min(1.0, time / 0.004, (0.44 - time) / 0.08) * math.exp(-9 * time)
                drums[start + frame] += level * envelope * (thump + skin)

    for beat, chord in BRASS:
        start = round(beat * BEAT * RATE)
        duration = 1.55 if beat == BRASS[-1][0] else 0.67
        for note in chord:
            pitch = math.tau * frequency(note)
            for frame in range(round(duration * RATE)):
                time = frame / RATE
                phase = pitch * time + 0.13 * math.sin(math.tau * 4.7 * time)
                envelope = min(1.0, time / 0.065, (duration - time) / 0.24) * math.exp(-1.3 * time)
                edge = 1 - math.exp(-23 * time)
                vibration = math.sin(phase) + edge * (
                    0.52 * math.sin(2 * phase) + 0.34 * math.sin(3 * phase) + 0.15 * math.sin(5 * phase)
                )
                horns[start + frame] += (0.21 / len(chord)) * envelope * vibration

    pcm = bytearray(FRAMES * 4)
    peak = 0
    for index in range(FRAMES):
        bed = bass[index] + drums[index]
        direct = bed + horns[index]
        left_echo = horns[index - 1776] if index >= 1776 else 0.0
        right_echo = horns[index - 2832] if index >= 2832 else 0.0
        left = round(27000 * (direct + 0.26 * left_echo))
        right = round(27000 * (direct + 0.24 * right_echo))
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
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(wav_file.read_bytes()).hexdigest(),
        "source": "Original composition and procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav_file)


if __name__ == "__main__":
    main()
