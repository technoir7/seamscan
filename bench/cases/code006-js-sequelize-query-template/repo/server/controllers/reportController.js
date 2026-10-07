const { QueryTypes } = require("sequelize");
const { sequelize } = require("../models");

exports.revenueByMonth = async (req, res) => {
  const { year } = req.query;
  const rows = await sequelize.query(
    `SELECT date_trunc('month', created_at) AS month, sum(amount) AS revenue
     FROM payments WHERE extract(year FROM created_at) = ${year}
     GROUP BY 1 ORDER BY 1`,
    { type: QueryTypes.SELECT }
  );
  res.json(rows);
};
