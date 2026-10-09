export async function createPaymentIntent(amount) {
  const res = await fetch("https://api.stripe.com/v1/payment_intents", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Bearer ${process.env.REACT_APP_STRIPE_SECRET_KEY}`,
    },
    body: new URLSearchParams({ amount: String(amount), currency: "usd" }),
  });
  return res.json();
}
