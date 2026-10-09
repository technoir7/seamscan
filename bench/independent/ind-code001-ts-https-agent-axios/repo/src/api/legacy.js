const axios = require("axios");
const https = require("https");

const agent = new https.Agent({ rejectUnauthorized: false });

const legacy = axios.create({
  baseURL: "https://legacy.partner.example/api",
  httpsAgent: agent,
  timeout: 8000,
});

module.exports = { legacy };
