import copy
from fractions import Fraction as F
import json
import unittest
from crossroads_state import Engine, Operation, State, inverse, pack, unpack
from crossroads_state.core import digest, parse_journal, permutation_power
from crossroads_state.synthetic import fixture_engine, fixture_state, collision_pair, POINTS
from oracle import Oracle


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.state = fixture_engine(), fixture_state()

    def test_checkpoint_roundtrip(self):
        self.assertEqual(self.state, unpack(json.loads(json.dumps(pack(self.state, self.engine))), self.engine))

    def test_replay_and_inverse(self):
        journal = [("B", 2), ("U", -1), ("A", -2), ("R", 1), ("M", 3), ("S", -2)]
        result = self.engine.run(self.state, journal)
        self.assertEqual(self.state, self.engine.run(result, inverse(journal)))
        self.assertEqual(result, self.engine.run(self.state, parse_journal(json.loads(json.dumps(journal)))))

    def test_checksum_array_reader_reference(self):
        for key in ("values", "reader", "reference"):
            doc = pack(self.state, self.engine)
            if key == "values":
                doc["payload"]["state"][key][0] = "1234567/3"
            elif key == "reader":
                r = doc["payload"]["state"][key]
                r[0], r[1] = r[1], r[0]
            else:
                doc["payload"]["state"][key] = 0
            with self.assertRaisesRegex(ValueError, "Checksum"):
                unpack(doc, self.engine)

    def test_hash_does_not_authenticate(self):
        doc = pack(self.state, self.engine)
        doc["payload"]["state"]["values"][0] = "999"
        doc["sha256"] = digest(doc["payload"])
        restored = unpack(doc, self.engine)
        self.assertNotEqual(restored, self.state)

    def test_wrong_model_rejected(self):
        other = Engine(81, 9, {"M": Operation(delta=(F(-1),) * 81)})
        with self.assertRaisesRegex(ValueError, "different"):
            unpack(pack(self.state, self.engine), other)

    def test_hidden_value_collision(self):
        a, b = collision_pair()
        self.assertEqual(a.observe(), b.observe())
        self.assertNotEqual(a, b)
        self.assertNotEqual(self.engine.step(a, "S").observe(), self.engine.step(b, "S").observe())

    def test_passive_changes_preserve_observation(self):
        for name in ("R", "U"):
            for count in (-4, -1, 0, 2, 7):
                result = self.engine.step(self.state, name, count)
                self.assertEqual(self.state.observe(), result.observe())

    def test_every_reference_and_inverse(self):
        for reference in range(81):
            state = fixture_state(reference=reference)
            for name in ("R", "U"):
                self.assertEqual(state, self.engine.run(state, [(name, 1), (name, -1)]))

    def test_generic_four_cycle(self):
        engine = Engine(4, 2, {"rotate": Operation(permutation=(1, 2, 3, 0), reframe=True)})
        state = State(tuple(map(F, (2, 7, -3, 5))), (0, 3), 1)
        self.assertEqual(state, engine.run(state, [("rotate", 123), ("rotate", -123)]))
        self.assertEqual((3, 0, 1, 2), permutation_power((1, 2, 3, 0), -1))

    def test_reframe_plus_delta_prohibited(self):
        with self.assertRaises(ValueError):
            Engine(2, 1, {"bad": Operation((F(0), F(1)), (1, 0), True)})

    def test_duplicate_permutation_rejected(self):
        with self.assertRaises(ValueError):
            Engine(2, 1, {"bad": Operation(permutation=(0, 0))})

    def test_schema_validation(self):
        base = self.state.plain()
        invalid = []
        for value in (0.1, "0.1", "1/0", True, "NaN"):
            d = copy.deepcopy(base)
            d["values"][0] = value
            invalid.append(d)
        for reader in ([0] * 9, [True] + list(range(1, 9)), list(range(1, 9)) + [81]):
            d = copy.deepcopy(base)
            d["reader"] = reader
            invalid.append(d)
        for reference in (True, -1, 81, 1.5):
            d = copy.deepcopy(base)
            d["reference"] = reference
            invalid.append(d)
        for data in invalid:
            with self.assertRaises(ValueError):
                State.parse(data)

    def test_invalid_instructions(self):
        for name, count in (("A", True), ("A", 0.5), ("missing", 1)):
            with self.assertRaises(ValueError):
                self.engine.step(self.state, name, count)
        for data in ({}, [["A", True]], [["A", 1, 2]], [["A", "1"]]):
            with self.assertRaises(ValueError):
                parse_journal(data)

    def test_wrong_dimensions(self):
        with self.assertRaises(ValueError):
            self.engine.step(State((F(1), F(2)), (0,), 0), "A")

    def test_independent_oracle(self):
        oracle, actual = Oracle(self.state.plain()), self.state
        for name, count in [("B", 2), ("R", -2), ("M", 2), ("U", 1), ("S", -1), ("A", -2)]:
            oracle.step(name, count)
            actual = self.engine.step(actual, name, count)
            self.assertEqual(actual.plain(), oracle.plain())

    def test_route_history_not_recovered_by_state(self):
        first = self.engine.run(self.state, [("A", 1), ("M", -1)])
        second = self.engine.run(self.state, [("M", -1), ("A", 1)])
        self.assertEqual(first, second)

    def test_balanced_synthetic_lines(self):
        # Equal coordinate-line means are a property of the fixture, not all engine states.
        from itertools import product
        lookup = dict(zip(POINTS, self.state.values))
        for axis in range(4):
            for remaining in product((-1, 0, 1), repeat=3):
                points = []
                for coordinate in (-1, 0, 1):
                    p = list(remaining)
                    p.insert(axis, coordinate)
                    points.append(tuple(p))
                self.assertEqual(F(33), sum(lookup[p] for p in points))


if __name__ == "__main__":
    unittest.main()
