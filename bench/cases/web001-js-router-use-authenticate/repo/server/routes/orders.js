const express = require("express");
const { authenticate } = require("../middleware/authenticate");
const Order = require("../models/order");

const router = express.Router();
router.use(authenticate);

router.post("/", async (req, res, next) => {
  try {
    const order = new Order({ ...req.body, customer: req.user._id });
    await order.save();
    res.status(201).json(order);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
