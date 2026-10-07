const crypto = require("crypto");

function hashPassword(password) {
  const salt = Math.random().toString(36).substring(2, 10);
  const hash = crypto.createHash("sha256").update(salt + password).digest("hex");
  return `${salt}:${hash}`;
}

module.exports = { hashPassword };
