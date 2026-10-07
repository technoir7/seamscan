const jwt = require("jsonwebtoken");
const pino = require("pino");

const logger = pino();

function logRequest(req, res, next) {
  const token = (req.headers.authorization || "").replace(/^Bearer /, "");
  const claims = token ? jwt.decode(token) : null;
  logger.info({ method: req.method, path: req.path, jti: claims?.jti }, "request");
  next();
}

module.exports = { logRequest };
