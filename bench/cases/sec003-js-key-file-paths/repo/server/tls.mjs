import fs from "node:fs";
import https from "node:https";
import { Storage } from "@google-cloud/storage";

const keyFile = process.env.GOOGLE_APPLICATION_CREDENTIALS ?? "./service-account.json";
export const storage = new Storage({ keyFilename: keyFile });

const options = {
  key: fs.readFileSync(process.env.SSL_KEY ?? "/etc/ssl/private/server.key"),
  cert: fs.readFileSync(process.env.SSL_CERT ?? "/etc/ssl/certs/server.crt"),
};
const signingKey = fs.readFileSync(process.env.JWT_PRIVATE_KEY || "./keys/private.pem");

export function start(app) {
  return https.createServer(options, app).listen(443);
}
export { signingKey };
