const express = require("express");
const { sendSms } = require("../sms");
const { redis } = require("../redis");

const router = express.Router();

router.post("/send", async (req, res) => {
  const { phone } = req.body;
  const otp = Math.floor(100000 + Math.random() * 900000).toString();
  await redis.set(`otp:${phone}`, otp, "EX", 300);
  await sendSms(phone, `Your code is ${otp}`);
  res.json({ sent: true });
});

module.exports = router;
