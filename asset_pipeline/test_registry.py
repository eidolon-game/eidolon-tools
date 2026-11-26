import copy
import json
import unittest
from pathlib import Path
from validate_registry import validate

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(Path(__file__).with_name("registry.json").read_text())
    def test_valid(self):
        validate(self.doc)
    def test_duplicate(self):
        self.doc["assets"].append(copy.deepcopy(self.doc["assets"][0]))
        with self.assertRaises(ValueError):
            validate(self.doc)
    def test_missing_dependency(self):
        self.doc["assets"][0]["dependencies"] = ["missing_asset"]
        with self.assertRaises(ValueError):
            validate(self.doc)
    def test_cycle(self):
        a = self.doc["assets"][0]
        a["dependencies"] = [a["id"]]
        with self.assertRaises(ValueError):
            validate(self.doc)
    def test_false_generated(self):
        self.doc["assets"][0]["status"] = "generated"
        with self.assertRaises(ValueError):
            validate(self.doc)
    def test_scale(self):
        self.doc["assets"][0]["dimensions_cm"][0] = 1
        with self.assertRaises(ValueError):
            validate(self.doc)

if __name__ == "__main__":
    unittest.main()
