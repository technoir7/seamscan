import Stripe from "stripe";

const stripe = new Stripe("{{FAKE_STRIPE_LIVE}}");

for (const name of ["Starter", "Team", "Enterprise"]) {
  await stripe.products.create({ name });
}
