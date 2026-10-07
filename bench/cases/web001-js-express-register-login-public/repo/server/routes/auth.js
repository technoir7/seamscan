const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const User = require("../models/User");
const RefreshToken = require("../models/RefreshToken");

const router = express.Router();

router.post("/register", async (req, res) => {
  const { email, password, name } = req.body;
  if (await User.exists({ email })) {
    return res.status(409).json({ message: "Email already registered" });
  }
  const user = await User.create({ email, name, password: await bcrypt.hash(password, 12) });
  res.status(201).json({ id: user._id });
});

router.post("/login", async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  if (!user || !(await bcrypt.compare(req.body.password, user.password))) {
    return res.status(400).json({ message: "Invalid credentials" });
  }
  const refresh = new RefreshToken({ user: user._id });
  await refresh.save();
  res.json({ token: jwt.sign({ sub: user._id }, process.env.JWT_SECRET, { expiresIn: "15m" }) });
});

module.exports = router;
