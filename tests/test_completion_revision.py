import pytest
from persistent_discord_state_machine import SqliteSessionStore, ConcurrentUpdateError


def test_old_confirmation_cannot_complete_revised_same_state(tmp_path):
    store = SqliteSessionStore(tmp_path / "sessions.db")
    store.initialize()
    old = store.start(42, 1001, "confirm", {"name": "Old"})
    current = store.transition(42, 1001, expected_state="confirm", next_state="confirm",
        payload={"name": "Corrected"}, expected_revision=old.revision)
    with pytest.raises(ConcurrentUpdateError):
        store.complete(42, 1001, expected_state="confirm", expected_revision=old.revision)
    assert store.require(42, 1001).payload == {"name": "Corrected"}
    store.complete(42, 1001, expected_state="confirm", expected_revision=current.revision)
    assert store.get(42, 1001) is None
