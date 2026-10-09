const pool = require("../pool");

async function getProducts(ids) {
  const marks = ids.map(() => "?").join(", ");
  const [rows] = await pool.query(`SELECT * FROM products WHERE id IN (${marks})`, ids);
  return rows;
}

module.exports = { getProducts };
