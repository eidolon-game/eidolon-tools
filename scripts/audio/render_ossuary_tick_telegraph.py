#!/usr/bin/env python3
"""Render the Ossuary Tick's original two-catch stone scrape telegraph."""

import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path

RATE = 48_000
DURATION = 0.62
CUE = "sfx_ossuary_tick_scrape_telegraph"


def catch(time: float, onset: float, duration: float, rise: float) -> float:
    elapsed = time - onset
    if not 0 <= elapsed < duration:
        return 0.0
    return min(1.0, elapsed / rise) * (1.0 - elapsed / duration) ** 2


def synthesize() -> tuple[bytearray, int]:
    noise = random.Random(81577)
    frames = round(DURATION * RATE)
    pcm = bytearray(frames * 2)
    low = slow = 0.0
    peak = 0
    for index in range(frames):
        time = index / RATE
        grit = noise.uniform(-1, 1)
        low += .12 * (grit - low)
        slow += .026 * (grit - slow)
        first = catch(time, .025, .233, .016)
        second = catch(time, .289, .292, .025)
        grind = .38 * (grit - low) + 1.8 * (low - slow)
        body = (
            math.sin(math.tau * (233 * time + 19 * time * time))
            + .58 * math.sin(math.tau * (429 * time - 48 * time * time))
        )
        splinter = .22 * (grit - low) * (
            catch(time, .056, .054, .002) + catch(time, .316, .071, .003)
        )
        sample = round(12200 * ((first * .7 + second) * (grind + .23 * body) + splinter))
        peak = max(peak, abs(sample))
        struct.pack_into("<h", pcm, index * 2, sample)
    return pcm, peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the WAV and manifest.")
    destination = parser.parse_args().output
    destination.mkdir(parents=True, exist_ok=True)

    pcm, peak = synthesize()
    preview = destination / f"{CUE}.wav"
    with wave.open(str(preview), "wb") as stream:
        stream.setparams((1, 2, RATE, len(pcm) // 2, "NONE", "not compressed"))
        stream.writeframes(pcm)

    manifest = {
        "cue_id": CUE,
        "file": preview.name,
        "channels": 1,
        "sample_rate": RATE,
        "bits_per_sample": 16,
        "frames": len(pcm) // 2,
        "peak_sample": peak,
        "loop": False,
        "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "source": "Original procedural synthesis. No external recordings.",
        "status": "prototype",
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(preview)


if __name__ == "__main__":
    main()
