const STRIPE_API = "https://api.stripe.com/v1";

// Creates the Checkout Session straight from the shop page, no backend needed.
export async function startCheckout(priceId, quantity) {
  const body = new URLSearchParams({
    mode: "payment",
    "line_items[0][price]": priceId,
    "line_items[0][quantity]": String(quantity),
    success_url: `${window.location.origin}/thanks`,
    cancel_url: `${window.location.origin}/cart`,
  });
  const res = await fetch(`${STRIPE_API}/checkout/sessions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.REACT_APP_STRIPE_SECRET_KEY}` },
    body,
  });
  const session = await res.json();
  window.location.assign(session.url);
}
