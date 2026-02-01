export declare class AuthMessageDto {
    token: string;
}
export declare class JoinClassSessionDto {
    class_session_id: string;
}
export declare class EventMessageDto {
    event_type: string;
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
