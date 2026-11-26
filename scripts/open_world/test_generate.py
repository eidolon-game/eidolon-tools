"""Run with python -m unittest discover -s scripts/open_world -p 'test_*.py'."""
import unittest
from generate import generate, validate, reachable

def fixture():
    return {"nodes":[{"id":"valdris","x":0,"y":0,"chapter":1,"inner_radius":500,"outer_radius":1500},
                     {"id":"valdris_giants","x":1000,"y":0,"chapter":5}],
            "edges":[{"a":"valdris","b":"valdris_giants","chapter":5}]}

class WorldTests(unittest.TestCase):
    def test_gate(self):
        w=fixture()
        validate(w)
        self.assertEqual(reachable(w,4),{"valdris"})
        self.assertEqual(reachable(w,5),{"valdris","valdris_giants"})
    def test_invalid_reference(self):
        w=fixture()
        w["edges"][0]["b"]="missing"
        with self.assertRaises(ValueError): validate(w)
    def test_duplicate(self):
        w=fixture()
        w["nodes"].append(w["nodes"][0])
        with self.assertRaises(ValueError): validate(w)
    def test_mesh(self):
        w=fixture()
        a=generate(w,1701,2500)
        self.assertEqual(a,generate(w,1701,2500))
        self.assertNotEqual(a,generate(w,1702,2500))
        vertices=[l for l in a.splitlines() if l.startswith("v ")]
        faces=[l for l in a.splitlines() if l.startswith("f ")]
        self.assertTrue(vertices and faces)
        for f in faces:
            self.assertTrue(all(1<=int(i)<=len(vertices) for i in f.split()[1:]))
