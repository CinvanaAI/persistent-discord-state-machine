# Origin

This focused package extracts and hardens the durable direct-message session idea from the historical Persistent Discord RPG project.

The parent project stored `(guild_id, user_id, state, payload)` rows so character creation and campaign invitations could resume after restart. This standalone version preserves that useful mechanism while adding explicit overwrite protection, expected-state checks, revision-based optimistic concurrency, guarded completion, typed results, and isolated tests.

It contains no Discord token, Discord client, guild data, campaign data, character content, or parent-project database.
