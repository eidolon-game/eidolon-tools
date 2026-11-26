"""Original procedural audio prototypes; standard library only."""
import argparse
import hashlib
import json
import math
import random
import struct
import wave
from pathlib import Path

RATE = 48000
CUES = {"ui.confirm": (.18, 660), "ui.error": (.3, 180),
        "combat.parry": (.35, 1200), "combat.hit": (.25, 90),
        "weapon.sword": (.45, 420), "magic.cast": (.8, 330),
        "footstep.stone": (.22, 110), "discrepancy.pulse": (1.2, 55)}

def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, (name, (duration, hz)) in enumerate(CUES.items()):
        rng = random.Random(20261126 + index)
        count = round(duration * RATE)
        samples = []
        for i in range(count):
            t = i / RATE
            env = min(1, i / 240, (count - 1 - i) / 480) * math.exp(-3*t/duration)
            tone = math.sin(2*math.pi*hz*t + 0.6*math.sin(2*math.pi*37*t))
            noise = rng.uniform(-1, 1)
            mix = .15 if name.startswith("ui") else .55
            samples.append(round(16000 * env * ((1-mix)*tone + mix*noise)))
        path = out / (name + ".wav")
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, RATE, count, "NONE", "not compressed"))
            wav.writeframes(struct.pack("<" + "h"*count, *samples))
        manifest.append({"id": "sfx."+name, "file": path.name,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "frames": count, "status": "generated_prototype",
                         "rights": "project original; all rights reserved"})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    generate(parser.parse_args().out)
