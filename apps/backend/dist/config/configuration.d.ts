declare const _default: () => {
    port: number;
    database: {
        url: string;
    };
    redis: {
        host: string;
        port: number;
    };
    jwt: {
        secret: string;
        issuer: string;
        expiresIn: string;
    };
};
export default _default;
