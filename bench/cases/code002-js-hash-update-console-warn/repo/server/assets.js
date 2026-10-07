const crypto = require("crypto");
const fs = require("fs");

function etagFor(path) {
  const hash = crypto.createHash("sha1");
  try {
    hash.update(fs.readFileSync(path));
  } catch (error) {
    console.warn(`etag: could not read ${path}`, error);
  }
  return `"${hash.digest("base64")}"`;
}

module.exports = { etagFor };
