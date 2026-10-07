const axios = require("axios");
const https = require("https");

// The CRM sandbox uses a self-signed cert
const httpsAgent = new https.Agent({ rejectUnauthorized: false });

const crm = axios.create({
  baseURL: process.env.CRM_BASE_URL,
  httpsAgent,
  timeout: 10000,
});

async function upsertContact(contact) {
  const { data } = await crm.post("/contacts", contact);
  return data;
}

module.exports = { upsertContact };
