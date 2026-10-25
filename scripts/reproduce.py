#!/usr/bin/env python3
"""Run the registered synthetic study, or compare it with the committed result."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from crossroads_state.core import State, canonical, digest, inverse, pack, unpack
from crossroads_state.synthetic import fixture_engine, fixture_state, collision_pair
from oracle import Oracle


def study():
    registration = json.loads((ROOT / "registration.json").read_text())
    engine = fixture_engine()
    rng = random.Random(registration["seed"])
    shuffle_rng = random.Random(registration["seed"] + 1)
    counts = Counter()
    sizes = []
    traces_digest = hashlib.sha256()
    for trial in range(registration["trials"]):
        initial = fixture_state(trial % registration["initial_fixtures"], reference=trial % 81)
        journal = [(rng.choice(registration["operators"]), rng.choice(registration["counts"]))
                   for _ in range(registration["trace_length"])]
        traces_digest.update(canonical(journal))
        current, oracle = initial, Oracle(initial.plain())
        for name, count in journal:
            current = engine.step(current, name, count)
            oracle.step(name, count)
            if current.plain() != oracle.plain():
                raise AssertionError(f"Independent trace mismatch at trial {trial}")
            counts["oracle_trace_steps"] += 1
        final = current
        blob = pack(final, engine)
        sizes.append(len(canonical(blob)))
        counts["checkpoint_exact"] += unpack(json.loads(json.dumps(blob)), engine) == final
        counts["known_initial_journal_exact"] += engine.run(initial, journal) == final
        counts["inverse_exact"] += engine.run(final, inverse(journal)) == initial
        for component in ("values", "reader", "reference"):
            changed = json.loads(json.dumps(blob))
            d = changed["payload"]["state"]
            if component == "values":
                d[component][0] = str(F(d[component][0]) + 1)
            elif component == "reader":
                d[component][0], d[component][1] = d[component][1], d[component][0]
            else:
                d[component] = (d[component] + 1) % 81
            try:
                unpack(changed, engine)
            except ValueError:
                counts[f"changed_{component}_checksum_rejected"] += 1
            else:
                raise AssertionError("Undetected unchanged-digest mutation")
        shuffled = journal[:]
        shuffle_rng.shuffle(shuffled)
        for label, altered in (("truncated", journal[:-1]), ("reversed_order", list(reversed(journal))),
                               ("shuffled_order", shuffled)):
            counts[f"{label}_different"] += engine.run(initial, altered) != final
            counts[f"{label}_same"] += engine.run(initial, altered) == final
    for reference in range(81):
        initial = fixture_state(reference=reference)
        for name in registration["operators"]:
            for count in registration["primitive_counts"]:
                actual = engine.step(initial, name, count)
                expected = Oracle(initial.plain()).step(name, count)
                if actual.plain() != expected.plain():
                    raise AssertionError(f"Primitive mismatch: {reference}, {name}, {count}")
                counts["oracle_primitive_cases"] += 1
                if engine.step(actual, name, -count) != initial:
                    raise AssertionError("Primitive inverse failed")
                counts["primitive_inverse_exact"] += 1
    a, b = collision_pair()
    collision = {"same_observation": a.observe() == b.observe(), "different_state": a != b,
                 "shift_S_distinguishes": engine.step(a, "S").observe() != engine.step(b, "S").observe()}
    if not all(collision.values()):
        raise AssertionError("Observation control failed")
    modified = pack(a, engine)
    modified["payload"]["state"]["values"][0] = str(a.values[0] + 1)
    modified["sha256"] = digest(modified["payload"])
    recomputed_digest_accepted = unpack(modified, engine) != a
    same_endpoint = engine.run(a, [("A", 1), ("M", 1)]) == engine.run(a, [("M", 1), ("A", 1)])
    required = ("checkpoint_exact", "known_initial_journal_exact", "inverse_exact",
                "changed_values_checksum_rejected", "changed_reader_checksum_rejected",
                "changed_reference_checksum_rejected")
    if any(counts[k] != registration["trials"] for k in required):
        raise AssertionError("A primary study requirement failed")
    return {"status": "PASS", "dataset": "synthetic-ternary-v1", "registration_sha256": digest(registration),
            "model_id": engine.model_id, "journal_stream_sha256": traces_digest.hexdigest(),
            "counts": dict(sorted(counts.items())), "observation_collision": collision,
            "history_collision": {"distinct_commuting_journals_same_endpoint": same_endpoint},
            "checksum_limitation": {"altered_state_with_recomputed_digest_is_accepted": recomputed_digest_accepted},
            "checkpoint_canonical_bytes": {"minimum": min(sizes), "maximum": max(sizes),
                                           "mean": str(F(sum(sizes), len(sizes)))},
            "interpretation": "All results concern deterministic exact-state software on new synthetic data. "
                              "No LLM, compression advantage, physical system or authentication mechanism was evaluated."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="Require byte-equivalent parsed results")
    args = p.parse_args()
    result = study()
    target = ROOT / "results" / "synthetic-study.json"
    if args.check:
        if result != json.loads(target.read_text()):
            raise SystemExit("FAIL: study does not match the committed result")
        print("PASS: complete result matches the committed synthetic study")
    else:
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
