function cspMiddleware(req, res, next) {
  const nonce = btoa(String(Math.random()).slice(2));
  res.locals.nonce = nonce;
  res.setHeader("Content-Security-Policy", `script-src 'nonce-${nonce}'`);
  next();
}

module.exports = { cspMiddleware };
