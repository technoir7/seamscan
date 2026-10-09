import fs from "node:fs";

export const key = fs.readFileSync(process.env.SSL_KEY ?? "/etc/ssl/private/server.key");
export const cert = fs.readFileSync(process.env.SSL_CERT ?? "/etc/ssl/certs/server.crt");
export const sa = process.env.GCP_CREDENTIALS || "secrets/service-account.json";
