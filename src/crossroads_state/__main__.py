"""Local CLI. Inputs are trusted local JSON; no network or executable commands."""
import argparse
import json
from pathlib import Path
from .core import pack, parse_journal, unpack, inverse
from .synthetic import fixture_engine, fixture_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Write a synthetic example checkpoint")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--fixture", type=int, default=0)
    verify = sub.add_parser("verify", help="Validate a synthetic-model checkpoint")
    verify.add_argument("checkpoint", type=Path)
    replay = sub.add_parser("replay", help="Replay a JSON journal from a checkpoint")
    replay.add_argument("checkpoint", type=Path)
    replay.add_argument("journal", type=Path)
    replay.add_argument("--inverse", action="store_true")
    replay.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = fixture_engine()
    try:
        if args.command == "demo":
            state = fixture_state(args.fixture)
        else:
            state = unpack(json.loads(args.checkpoint.read_text()), engine)
        if args.command == "verify":
            print(json.dumps({"valid": True, "model_id": engine.model_id,
                              "addresses": len(state.values),
                              "observation": list(map(str, state.observe())),
                              "reference": state.reference}, indent=2))
            return
        if args.command == "replay":
            journal = parse_journal(json.loads(args.journal.read_text()))
            state = engine.run(state, inverse(journal) if args.inverse else journal)
        if args.output.exists():
            parser.error("Output exists; choose a new path to preserve your checkpoint")
        args.output.write_text(json.dumps(pack(state, engine), indent=2) + "\n")
        print(f"Wrote {args.output}")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
