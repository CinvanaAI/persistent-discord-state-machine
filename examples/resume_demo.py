from pathlib import Path
import sys
import json
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persistent_discord_state_machine import SqliteSessionStore, ConcurrentUpdateError


def main() -> None:
    with TemporaryDirectory(prefix="workflow_demo_") as directory:
        path = Path(directory) / "sessions.db"
        first_process = SqliteSessionStore(path)
        first_process.initialize()
        started = first_process.start(42, 1001, "choose_name", {"campaign": "Synthetic"})
        print("started", started)

        restarted_process = SqliteSessionStore(path)
        resumed = restarted_process.require(42, 1001)
        print("resumed", resumed)
        finished = restarted_process.transition(
            42,
            1001,
            expected_state="choose_name",
            next_state="confirm",
            payload={**resumed.payload, "name": "Example Hero"},
            expected_revision=resumed.revision,
        )
        print("transitioned", finished)
        revised = restarted_process.transition(42, 1001, expected_state="confirm",
            next_state="confirm", payload={**finished.payload, "name": "Revised Hero"},
            expected_revision=finished.revision)
        try:
            restarted_process.complete(42, 1001, expected_state="confirm", expected_revision=finished.revision)
        except ConcurrentUpdateError:
            print("stale confirmation rejected; preserved payload", json.dumps(restarted_process.require(42, 1001).payload, sort_keys=True))
        else:
            raise AssertionError("stale confirmation deleted the current session")
        restarted_process.complete(42, 1001, expected_state="confirm", expected_revision=revised.revision)
        print("complete", restarted_process.get(42, 1001))


if __name__ == "__main__":
    main()
