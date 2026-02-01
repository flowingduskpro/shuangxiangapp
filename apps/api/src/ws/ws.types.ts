export type WsClientToServerAuth = {
  msg_type: 'auth';
  version: string;
  correlation_id?: string;
  token: string;
};

export type WsClientToServerJoin = {
  msg_type: 'join_class_session';
  version: string;
  correlation_id?: string;
  class_session_id: string;
};

export type WsClientToServerEvent = {
  msg_type: 'event';
  version: string;
  correlation_id?: string;
  event_type: 'class_enter';
  class_session_id: string;
};

export type WsClientToServer = WsClientToServerAuth | WsClientToServerJoin | WsClientToServerEvent;

export type WsServerAck = {
  msg_type: 'ack';
  version: string;
  correlation_id?: string;
  ok: boolean;
  ack_type: string;
  error?: string | null;
};

export type WsServerAggregate = {
  msg_type: 'class_session_aggregate';
  version: string;
  correlation_id?: string;
  class_session_id: string;
  joined_count: number;
  enter_event_count: number;
  server_timestamp: string;
};

export type WsServerToClient = WsServerAck | WsServerAggregate;

