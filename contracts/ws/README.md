# WebSocket Contracts (PR-2)

Encoding:
- All messages are JSON objects.
- Discriminator field: `msg_type`.

Client → Server message types:
- `auth`
- `join_class_session`
- `event` (only `event_type: class_enter`)

Server → Client message types:
- `ack`
- `class_session_aggregate`

See:
- `contracts/ws/client_to_server.schema.json`
- `contracts/ws/server_to_client.schema.json`
