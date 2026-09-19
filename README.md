# Persistent Interaction State

Resume multi-step user workflows after a restart and reject stale updates.

## Try it

Python 3.11+. Run from this checkout:

```sh
python -m pip install -e .
python examples/resume_demo.py
```

**Input:** A three-step synthetic interaction saved under a guild/user session key.

**Result:** The example closes and reopens storage, resumes the saved step and updates its payload without Discord.

See [the captured example](examples/RESULT.md) for the observed output and reproduction command.

## How it works

A durable continuation record lets a fresh process decide what the next incoming message means. Scope and revision checks keep unrelated users/guilds apart.

Source: [persistent_discord_state_machine/store.py](persistent_discord_state_machine/store.py), [examples/resume_demo.py](examples/resume_demo.py).

## Use it for your work

Use the included example as the smallest integration: choose your session key and states, persist before waiting for input, and resume from storage when the next message arrives.

## Scope

The package stores and transitions state; callers implement the actual prompts, authorization and incoming-message dispatch. It is not a bot or a general workflow scheduler.

Owned code is available under the [MIT license](LICENSE.md).
