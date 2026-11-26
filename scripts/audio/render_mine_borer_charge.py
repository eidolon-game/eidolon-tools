#!/usr/bin/env python3
"""Render the Mine Borer's jaw drop, charge scrape, and falling grit."""

import argparse
import hashlib
import json
import math
import random
import struct
from typing import Iterator
import wave
from pathlib import Path


RATE = 48_000
DURATION = 1.94
FRAMES = round(RATE * DURATION)
CUE = "sfx_mine_borer_charge"
JAW_DROP = 0.024
CHARGE_SCRAPE = 0.265
GRIT_START = 0.79


def window(age: float, length: float, attack: float, release: float) -> float:
    if not 0 <= age < length:
        return 0.0
    return min(1.0, age / attack, (length - age) / release)


def components() -> Iterator[tuple[float, float, float]]:
    rng = random.Random(21165)
    pebbles = [
        (GRIT_START + rng.uniform(0.0, 0.98), rng.uniform(640, 2700), rng.uniform(0.05, 0.12))
        for _ in range(12)
    ]
    # Include the first fall at the intended timing marker.
    pebbles.extend(((GRIT_START, 1361, 0.10), (1.70, 942, 0.075)))
    medium = low = 0.0

    for frame in range(FRAMES):
        time = frame / RATE
        noise = rng.uniform(-1, 1)
        medium += 0.29 * (noise - medium)
        low += 0.055 * (noise - low)
        grit = noise - medium

        jaw = time - JAW_DROP
        jaw_envelope = window(jaw, 0.225, 0.0025, 0.045)
        strike = 0.0
        if jaw_envelope:
            hollow = math.sin(math.tau * (121 * jaw - 77 * jaw * jaw))
            tooth = math.sin(math.tau * 514 * jaw) * math.exp(-29 * jaw)
            strike = jaw_envelope * math.exp(-19 * jaw) * (
                0.32 * hollow + 0.20 * tooth + 0.39 * grit * math.exp(-48 * jaw)
            )

        scrape = time - CHARGE_SCRAPE
        scrape_envelope = window(scrape, 1.27, 0.027, 0.28)
        drag = 0.0
        if scrape_envelope:
            teeth = math.tau * (18 * scrape + 8.5 * scrape * scrape)
            rattle = 0.58 + 0.42 * math.sin(teeth) ** 2
            grind = math.sin(math.tau * (205 * scrape + 77 * scrape * scrape))
            drag = scrape_envelope * (
                rattle * (0.26 * grit + 0.8 * (medium - low)) + 0.095 * grind
            )

        fall = 0.0
        for onset, pitch, level in pebbles:
            age = time - onset
            if 0 <= age < 0.12:
                tumbling = math.sin(math.tau * (pitch * age - 560 * age * age))
                fall += level * window(age, 0.12, 0.0015, 0.025) * math.exp(-42 * age) * (
                    tumbling + 0.42 * grit
                )

        yield strike, drag, fall


def render() -> tuple[bytearray, int]:
    pcm = bytearray(FRAMES * 2)
    peak = 0
    for frame, (strike, drag, fall) in enumerate(components()):
        encoded = round(23_000 * (strike + drag + fall))
        peak = max(peak, abs(encoded))
        struct.pack_into("<h", pcm, frame * 2, encoded)
    return pcm, peak


def write_wav(path: Path, pcm: bytes, frames: int) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, RATE, frames, "NONE", "not compressed"))
        stream.writeframes(pcm)


def encode(samples: list[float]) -> bytes:
    return struct.pack(f"<{len(samples)}h", *(round(32767 * value) for value in samples))


def normalize_take(samples: list[float], peak: float) -> list[float]:
    duration = len(samples) / RATE
    edged = [value * window(index / RATE, duration, .004, .042) for index, value in enumerate(samples)]
    gain = peak / max(map(abs, edged))
    return [gain * value for value in edged]


def render_gameplay(output: Path) -> None:
    strike, scrape, grit = zip(*components())
    impact = []
    for index, pebble in enumerate(grit[round(GRIT_START * RATE):]):
        time = index / RATE
        contact = window(time, .24, .004, .047) * math.exp(-17 * time) * (
            .36 * math.sin(math.tau * (109 * time - 102 * time ** 2))
            + .15 * math.sin(math.tau * 183 * time) * math.exp(-13 * time)
        )
        impact.append(contact + 2.5 * pebble)
    takes = {
        "Windup": normalize_take(list(strike[:round(.30 * RATE)]), .53),
        "Charge": normalize_take(list(scrape[round(CHARGE_SCRAPE * RATE):round(1.535 * RATE)]), .44),
        "Impact": normalize_take(impact, .58),
    }
    cues = []
    for phase, samples in takes.items():
        path = output / f"S_Borer_{phase}.wav"
        write_wav(path, encode(samples), len(samples))
        cues.append({"phase": phase.lower(), "file": path.name, "frames": len(samples),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    # Demonstrate an early stop with the same 70 ms tail used by the runtime.
    start = round(.90 * RATE)
    contact = start + round(.58 * RATE)
    fade = round(.07 * RATE)
    preview = [0.0] * (contact + len(takes["Impact"]))
    for index, value in enumerate(takes["Windup"]):
        preview[index] += value
    for index, value in enumerate(takes["Charge"][:contact - start + fade]):
        gain = min(1.0, (contact + fade - start - index) / fade)
        preview[start + index] += value * gain
    for index, value in enumerate(takes["Impact"]):
        preview[contact + index] += value
    peak = max(map(abs, preview))
    if peak > .93:
        preview = [sample * .93 / peak for sample in preview]
    write_wav(output / "borer_short_charge_preview.wav", encode(preview), len(preview))
    manifest = {"format": "PCM16", "channels": 1, "sample_rate": RATE, "cues": cues,
                "source": "EIDOLON original procedural synthesis from the Mine Borer charge study."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    parser.add_argument("--gameplay", action="store_true", help="Render three individually timed cue files.")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    if args.gameplay:
        render_gameplay(output)
        return
    pcm, peak = render()
    wav = output / f"{CUE}.wav"
    write_wav(wav, pcm, FRAMES)
    manifest = {
        "cue_id": CUE,
        "file": wav.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": FRAMES,
        "timing_seconds": {
            "jaw_drop": JAW_DROP,
            "charge_scrape": CHARGE_SCRAPE,
            "grit_start": GRIT_START,
        },
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(wav)


if __name__ == "__main__":
    main()
