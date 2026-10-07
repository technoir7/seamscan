const logger = require("./logger");

function assertTlsVerification() {
  if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") {
    logger.warn("NODE_TLS_REJECT_UNAUTHORIZED=0 is set; removing it");
    delete process.env.NODE_TLS_REJECT_UNAUTHORIZED;
  }
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = "1";
}

module.exports = { assertTlsVerification };
