import copy
import unittest
from campaign_checks import validate_campaign, unreachable

class Checks(unittest.TestCase):
    def setUp(self):
        self.data = {"schema": 1, "chapters": [{"id": i, "act": min(i, 10), "title": f"Title {i}", "type": "dungeon" if i in (4, 23) else "explore", "target": 100 if i == 7 else 0, "objective": "Goal", "dialogue": [{"speaker":"A","text":"B"}]*2} for i in range(1, 27)], "endings": [{"id": e, "epilogue":"End"} for e in ("custodian","origin","guild","freedom")]}
        self.story = "\n".join(f"## **Capitolo {i} – Title {i}**" for i in range(1, 27))
    def test_valid(self):
        self.assertEqual(validate_campaign(self.data, self.story), [])
    def test_duplicate_chapter(self):
        self.data["chapters"][1]["id"] = 1
        self.assertIn("chapter IDs/order", validate_campaign(self.data, self.story))
    def test_wrong_title(self):
        self.data["chapters"][0]["title"] = "Wrong"
        self.assertIn("canonical chapter titles", validate_campaign(self.data, self.story))
    def test_missing_ending(self):
        self.data["endings"].pop()
        self.assertIn("ending IDs/epilogues", validate_campaign(self.data, self.story))
    def test_negative_target(self):
        self.data["chapters"][0]["target"] = -1
        self.assertIn("objective: 1", validate_campaign(self.data, self.story))
    def test_graph_reachable(self):
        self.assertEqual(unreachable(["a","b","c"], [("a","b"),("b","c")], "a", ["c"]), set())
    def test_graph_dead_end(self):
        self.assertEqual(unreachable(["a","b","c"], [("a","b"),("b","a")], "a", ["c"]), {"c"})
    def test_unknown_edge(self):
        with self.assertRaises(ValueError):
            unreachable(["a"], [("a","b")], "a", ["a"])

if __name__ == "__main__":
    unittest.main()
