from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persistent_discord_state_machine import SqliteSessionStore


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
        restarted_process.complete(42, 1001, expected_state="confirm")
        print("complete", restarted_process.get(42, 1001))


if __name__ == "__main__":
    main()
