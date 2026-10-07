const STRIPE_KEY = /^(sk|rk)_(live|test)_[A-Za-z0-9]{24,}$/;

function checkKeys(env) {
  const stripeKey = env.STRIPE_SECRET_KEY ?? "";
  if (!STRIPE_KEY.test(stripeKey)) {
    throw new Error("STRIPE_SECRET_KEY must be a Stripe secret or restricted key");
  }
  if (env.NODE_ENV === "production" && stripeKey.startsWith("sk_test_")) {
    throw new Error("refusing to start production with a Stripe test key");
  }
  const gh = env.GITHUB_TOKEN ?? "";
  if (gh && !gh.startsWith("ghp_") && !gh.startsWith("github_pat_")) {
    console.warn("GITHUB_TOKEN does not look like a personal access token");
  }
}

module.exports = { checkKeys };
