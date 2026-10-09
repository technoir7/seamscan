import { logger } from "./logger";

export function checkTlsSettings() {
  if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") {
    logger.warn("TLS checks are off");
  }
}
