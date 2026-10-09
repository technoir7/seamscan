function validateCoupon(code, cart) {
}

function applyCoupon(code, cart) {
  validateCoupon(code, cart);
  return { ...cart, total: cart.total * 0.9 };
}

module.exports = { applyCoupon };
