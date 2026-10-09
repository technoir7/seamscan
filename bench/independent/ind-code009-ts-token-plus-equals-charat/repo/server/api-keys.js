const chars = "abcdefghijklmnopqrstuvwxyz0123456789";

function newKey() {
  let token = "";
  for (let i = 0; i < 40; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return "ak_" + token;
}

module.exports = { newKey };
