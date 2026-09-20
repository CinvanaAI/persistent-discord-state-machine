# Persistent Interaction State

Resume multi-step user workflows after a restart and reject stale updates.

## Try it

Python 3.11+. Run from this checkout:

```sh
python -m pip install -e .
python examples/resume_demo.py
```

**Input:** A three-step synthetic interaction saved under a guild/user session key.

**Result:** The example closes and reopens storage, resumes the saved step, rejects a stale confirmation after a same-state edit, and completes the current revision without Discord.

See [the captured example](examples/RESULT.md) for the observed output and reproduction command.

## How it works

A durable continuation record lets a fresh process decide what the next incoming message means. Scope and revision checks keep unrelated users/guilds apart.

Source: [persistent_discord_state_machine/store.py](persistent_discord_state_machine/store.py), [examples/resume_demo.py](examples/resume_demo.py).

## Use it for your work

Use the included example as the smallest integration: choose your session key and states, persist before waiting for input, and resume from storage when the next message arrives.

## Scope

The package stores and transitions state; callers implement the actual prompts, authorization and incoming-message dispatch. It is not a bot or a general workflow scheduler.

Owned code is available under the [MIT license](LICENSE.md).

## Why the revision matters

A name choice advances `choose_name` to `confirm`. Editing that name again can leave the state at `confirm` while advancing its revision. A delayed confirmation must not erase the newer name. Pass both `expected_state` and `expected_revision` to `complete`, just as you do to `transition`; the updated demo exercises this exact case. Revision-guarded completion is a public continuation addition. Omitting the optional guard preserves the earlier API but does not reject same-state stale confirmations.

The session key is `(guild_id, user_id)`: one user can have independent sessions in multiple guilds, but starting another session for the same pair fails unless `replace=True` is explicit. A transition replaces its entire payload; merge the prior payload yourself when fields must survive. Completion removes the active row, so this store is not an audit log.

An integration initializes storage, persists the next step before waiting, routes incoming messages to the right key, reads the current state/revision, applies the event, then records the transition. It must own authorization, duplicate incoming-event handling and external side-effect recovery. SQLite state changes do not make an outgoing chat message exactly-once.

The mechanism began in [Persistent Discord RPG](https://github.com/CinvanaAI/persistent-discord-rpg); [Origin](ORIGIN.md) describes the focused extraction. A durable event history could be added separately if a consumer needs it; none is retained now.
