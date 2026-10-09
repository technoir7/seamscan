import cors from "cors";

export const appCors = cors({ origin: ["https://app.example.com", "https://admin.example.com"], credentials: true });
export const envCors = cors({ origin: process.env.APP_ORIGIN, credentials: true });
