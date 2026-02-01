import { IsString, IsNotEmpty, IsOptional, IsObject } from 'class-validator';

export class AuthMessageDto {
  @IsString()
  @IsNotEmpty()
  token: string;
}

export class JoinClassSessionDto {
  @IsString()
  @IsNotEmpty()
  class_session_id: string;
}

export class EventMessageDto {
  @IsString()
  @IsNotEmpty()
  event_type: string;

  @IsObject()
  @IsOptional()
  event_data?: Record<string, any>;
}

export interface AckResponse {
  correlation_id: string;
  timestamp: string;
  status: 'success' | 'error';
  message?: string;
}

export interface ClassSessionAggregate {
  class_session_id: string;
  joined_count: number;
  enter_event_count: number;
  server_timestamp: string;
  version: string;
}
