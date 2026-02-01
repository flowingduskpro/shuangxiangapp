# contracts (authoritative)

This directory is the authoritative source of versioned API/WS contracts.

Scope (PR-2):
- Client → Server (WS): `auth`, `join_class_session`, `event` (only `class_enter`)
- Server → Client (WS): `ack`, `class_session_aggregate`
- Minimal REST: create/get `class_session_id` (only for obtaining an id)

Hard constraints (PR-2):
- JWT issuer: `shuangxiang-app`
- JWT minimal claims: `sub` (user_id), `role` (teacher|student), `class_id` (single value)
- Aggregate fields: `class_session_id`, `joined_count`, `enter_event_count`, `server_timestamp`, `version`
- MUST NOT include both `online_count` and `joined_count`.

All contract changes must bump the version in `contracts/version.json`.

