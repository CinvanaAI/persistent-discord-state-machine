from pathlib import Path

import pytest

from persistent_discord_state_machine import (
    ConcurrentUpdateError,
    SessionExistsError,
    SessionNotFoundError,
    SessionStateError,
    SqliteSessionStore,
)


def store(tmp_path: Path) -> SqliteSessionStore:
    result = SqliteSessionStore(tmp_path / "state" / "sessions.db")
    result.initialize()
    return result


def test_start_and_resume_after_reopen(tmp_path: Path) -> None:
    first = store(tmp_path)
    session = first.start(10, 20, "choose_name", {"campaign_id": 7})
    assert session.revision == 1

    reopened = SqliteSessionStore(first.db_path)
    resumed = reopened.require(10, 20)
    assert resumed.state == "choose_name"
    assert resumed.payload == {"campaign_id": 7}


def test_one_user_can_have_sessions_in_multiple_guilds(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    sessions.start(1, 99, "one")
    sessions.start(2, 99, "two")
    assert {(item.guild_id, item.state) for item in sessions.list_for_user(99)} == {(1, "one"), (2, "two")}


def test_start_refuses_silent_overwrite(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    sessions.start(1, 2, "first")
    with pytest.raises(SessionExistsError):
        sessions.start(1, 2, "second")
    assert sessions.require(1, 2).state == "first"


def test_explicit_replace_increments_revision(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    sessions.start(1, 2, "first")
    replaced = sessions.start(1, 2, "replacement", {"fresh": True}, replace=True)
    assert replaced.state == "replacement"
    assert replaced.payload == {"fresh": True}
    assert replaced.revision == 2


def test_transition_checks_state_and_revision(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    current = sessions.start(1, 2, "choose_name", {"step": 1})
    moved = sessions.transition(
        1,
        2,
        expected_state="choose_name",
        next_state="choose_role",
        payload={"step": 2},
        expected_revision=current.revision,
    )
    assert moved.state == "choose_role"
    assert moved.revision == 2

    with pytest.raises(SessionStateError):
        sessions.transition(1, 2, expected_state="choose_name", next_state="done", payload={})
    with pytest.raises(ConcurrentUpdateError):
        sessions.transition(
            1,
            2,
            expected_state="choose_role",
            next_state="done",
            payload={},
            expected_revision=1,
        )


def test_complete_can_require_final_state(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    sessions.start(1, 2, "review")
    with pytest.raises(SessionStateError):
        sessions.complete(1, 2, expected_state="done")
    sessions.complete(1, 2, expected_state="review")
    assert sessions.get(1, 2) is None
    with pytest.raises(SessionNotFoundError):
        sessions.complete(1, 2)


@pytest.mark.parametrize("state", ["", "   "])
def test_empty_states_are_rejected(tmp_path: Path, state: str) -> None:
    with pytest.raises(ValueError):
        store(tmp_path).start(1, 2, state)


def test_payload_must_be_json_serializable_dictionary(tmp_path: Path) -> None:
    sessions = store(tmp_path)
    with pytest.raises(TypeError):
        sessions.start(1, 2, "state", payload=[])
    with pytest.raises(TypeError):
        sessions.start(1, 2, "state", payload={"bad": object()})
