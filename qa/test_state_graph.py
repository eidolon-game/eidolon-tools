import unittest
from state_graph import explore

class StateGraphTests(unittest.TestCase):
    def test_unlock(self):
        r = explore(["a","b","end"], [{"source":"a","target":"b","adds":["key"]},{"source":"b","target":"end","requires":["key"]}], "a", terminals=["end"])
        self.assertEqual(r["unreachable_terminals"], set())
        self.assertEqual(r["trapped_states"], set())

    def test_irreversible_choice(self):
        r = explore(["a","end","trap"], [{"source":"a","target":"end"},{"source":"a","target":"trap"},{"source":"trap","target":"trap"}], "a", terminals=["end"])
        self.assertEqual(r["trapped_states"], {("trap",frozenset())})

    def test_missing_flag(self):
        r = explore(["a","end"], [{"source":"a","target":"end","requires":["key"]}], "a", terminals=["end"])
        self.assertEqual(r["unreachable_terminals"], {"end"})

    def test_budget(self):
        with self.assertRaises(RuntimeError):
            explore(["a","b"], [{"source":"a","target":"b"}], "a", terminals=["b"], limit=1)
