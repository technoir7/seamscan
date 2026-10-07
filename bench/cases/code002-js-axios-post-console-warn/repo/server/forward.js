const axios = require("axios");

async function forwardOrder(order) {
  try {
    await axios.post(process.env.FULFILLMENT_URL, order, { timeout: 5000 });
  } catch (e) {
    console.warn("forward failed", e.message);
  }
}

module.exports = { forwardOrder };
