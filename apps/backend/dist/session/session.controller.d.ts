import { SessionService } from './session.service';
export declare class SessionController {
    private sessionService;
    constructor(sessionService: SessionService);
    createSession(body: {
        class_id: string;
    }): Promise<{
        class_session_id: string;
        class_id: string;
        status: string;
        created_at: Date;
    }>;
    getSession(id: string): Promise<{
        class_session_id: string;
        class_id: string;
        status: string;
        created_at: Date;
    }>;
}
