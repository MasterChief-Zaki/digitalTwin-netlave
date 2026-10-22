"""Regenerate `src/fixtures/initial-snapshot.json` from the engine's step-0 state.

Run from `backend/`: `.venv/Scripts/python -m twin.write_fixture` (or `.venv/bin/python`).
`test_initial_snapshot_matches_the_shared_fixture` fails until it is rerun after a contract change.
"""

import json
from pathlib import Path

from config import SITE
from twin.state import new_run_state, to_snapshot

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "src" / "fixtures" / "initial-snapshot.json"


def main() -> None:
    snapshot = to_snapshot(new_run_state(SITE, seed=7), SITE, run_generation=0, latest_event_id=0)
    with FIXTURE_PATH.open("w", encoding="utf-8", newline="\n") as fixture_file:
        fixture_file.write(json.dumps(snapshot.model_dump(mode="json"), indent=2) + "\n")


if __name__ == "__main__":
    main()
