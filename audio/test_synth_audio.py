import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from synth_audio import generate, CUES, RATE

class AudioTests(unittest.TestCase):
    def test_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"
            generate(a)
            generate(b)
            manifest = json.loads((a/"manifest.json").read_text())
            self.assertEqual(len(manifest), len(CUES))
            self.assertEqual(manifest, json.loads((b/"manifest.json").read_text()))
            for row in manifest:
                p = a / row["file"]
                self.assertEqual(p.read_bytes(), (b/p.name).read_bytes())
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), row["sha256"])
                with wave.open(str(p)) as wav:
                    self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1,2,RATE))
                    self.assertEqual(wav.getnframes(), row["frames"])
                    self.assertEqual(wav.readframes(1), bytes(2))
                    wav.setpos(wav.getnframes()-1)
                    self.assertEqual(wav.readframes(1), bytes(2))

if __name__ == "__main__":
    unittest.main()
