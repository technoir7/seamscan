const express = require("express");
const jwt = require("jsonwebtoken");
const { User } = require("../models");

const router = express.Router();

router.get("/me", async (req, res) => {
  const token = req.cookies.access_token;
  try {
    jwt.verify(token, process.env.JWT_SECRET, { algorithms: ["HS256"] });
  } catch (err) {
    return res.status(401).json({ error: "invalid token" });
  }
  const { sub } = jwt.decode(token);
  const user = await User.findByPk(sub);
  if (!user) {
    return res.status(404).json({ error: "not found" });
  }
  res.json({ id: user.id, email: user.email });
});

module.exports = router;
