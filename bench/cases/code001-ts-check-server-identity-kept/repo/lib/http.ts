import https from "node:https";
import tls from "node:tls";

const PINS = (process.env.PAYMENTS_CERT_PINS ?? "").split(",");

// Pins the payment gateway's certificate on top of normal verification.
export const agent = new https.Agent({
  keepAlive: true,
  maxSockets: 50,
  ca: process.env.PAYMENTS_CA,
  checkServerIdentity: (host, cert) => {
    const err = tls.checkServerIdentity(host, cert);
    if (err) return err;
    if (!PINS.includes(cert.fingerprint256)) return new Error("certificate pin mismatch");
    return undefined;
  },
});
