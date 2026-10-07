const pool = require("../db");

async function productsForCart(productIds) {
  if (productIds.length === 0) return [];
  const marks = productIds.map(() => "?").join(", ");
  const [rows] = await pool.query(
    `SELECT id, name, price_cents FROM products WHERE id IN (${marks}) AND active = 1`,
    productIds
  );
  return rows;
}

module.exports = { productsForCart };
