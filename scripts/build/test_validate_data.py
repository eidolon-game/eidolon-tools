import tempfile
import unittest
from pathlib import Path
from validate_data import validate

class DataTests(unittest.TestCase):
    def check(self, name, content, valid):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(content, encoding="utf-8")
            if valid:
                validate(path)
            else:
                with self.assertRaises(ValueError):
                    validate(path)

    def test_json(self):
        self.check("a.json", '{"id":"test"}', True)
        self.check("a.json", '{"id":1,"id":2}', False)
        self.check("a.json", '{"value":NaN}', False)
        self.check("a.json", '{', False)

    def test_csv(self):
        self.check("a.csv", "id,name\n1,one\n", True)
        self.check("a.csv", "id,name\n1\n", False)
        self.check("a.csv", "id,id\n1,2\n", False)

if __name__ == "__main__":
    unittest.main()
