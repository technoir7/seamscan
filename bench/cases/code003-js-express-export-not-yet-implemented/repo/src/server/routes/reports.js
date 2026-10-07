const express = require("express");
const { requireUser } = require("../middleware/auth");

const router = express.Router();

router.get("/", requireUser, async (req, res) => {
  const reports = await req.db.report.findMany({ where: { ownerId: req.user.id } });
  res.json(reports);
});

router.get("/:id/export", requireUser, async (req, res) => {
  throw new Error("CSV export not yet implemented");
});

module.exports = router;
