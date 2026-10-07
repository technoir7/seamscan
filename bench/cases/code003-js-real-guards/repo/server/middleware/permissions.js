const crypto = require("crypto");

function verifySignature(payload, signature) {
  const expected = crypto
    .createHmac("sha256", process.env.WEBHOOK_SECRET)
    .update(payload)
    .digest("hex");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
}

function isAllowed(user, action) {
  if (!user) return false;
  if (user.role === "admin") return true;
  return user.permissions.includes(action);
}

const checkAuth = (req, res, next) => (req.session?.userId ? next() : res.sendStatus(401));

module.exports = { verifySignature, isAllowed, checkAuth };
