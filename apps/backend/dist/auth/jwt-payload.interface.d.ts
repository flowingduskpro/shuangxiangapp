export interface JwtPayload {
    sub: string;
    role: string;
    class_id: string;
    iat?: number;
    exp?: number;
}
