const STRIPE_SECRET = "{{FAKE_STRIPE_TEST}}";

export async function listCharges() {
  const r = await fetch("https://api.stripe.com/v1/charges?limit=5", {
    headers: { Authorization: "Bearer " + STRIPE_SECRET },
  });
  return r.json();
}
