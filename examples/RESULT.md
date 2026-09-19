# Recorded first use

This output was produced by the included example with network connections disabled. Synthetic provider or worker replies are identified by the example; no real model quality or billing is implied.

From the installed checkout:

```sh
python examples/resume_demo.py
```

[Complete recorded output](result.txt)

```text
started WorkflowSession(guild_id=42, user_id=1001, state='choose_name', payload={'campaign': 'Synthetic'}, revision=1, updated_at='2026-09-19T14:14:24Z')
resumed WorkflowSession(guild_id=42, user_id=1001, state='choose_name', payload={'campaign': 'Synthetic'}, revision=1, updated_at='2026-09-19T14:14:24Z')
transitioned WorkflowSession(guild_id=42, user_id=1001, state='confirm', payload={'campaign': 'Synthetic', 'name': 'Example Hero'}, revision=2, updated_at='2026-09-19T14:14:24Z')
complete None
```

Generated timestamps and synthetic identifiers can change between runs. The demonstrated behavior and input fixture remain inspectable in the adjacent example files.
