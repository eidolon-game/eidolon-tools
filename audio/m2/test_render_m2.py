import hashlib,json,struct,tempfile,unittest,wave
from pathlib import Path
from render_m2 import CUES,RATE,generate
class RenderTest(unittest.TestCase):
    def test_assets(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b'; rows=generate(a); self.assertEqual(rows,generate(b))
            self.assertEqual(set(CUES),{r['id'] for r in rows})
            for r in rows:
                with self.subTest(cue=r['id']):
                    p=a/r['file']; self.assertEqual(p.read_bytes(),(b/p.name).read_bytes())
                    self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),r['sha256'])
                    with wave.open(str(p)) as w:
                        self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(1,2,RATE))
                        self.assertEqual(w.getnframes(),round(r['seconds']*RATE))
                        s=struct.unpack('<'+'h'*w.getnframes(),w.readframes(w.getnframes()))
                    self.assertEqual(max(map(abs,s)),r['peak']); self.assertTrue(0<r['peak']<32767)
                    self.assertEqual((s[0],s[-1]),(0,0))
                    if r['loop']: self.assertLessEqual(abs(s[1]-s[0])+abs(s[-1]-s[-2]),128)
if __name__=='__main__': unittest.main()
