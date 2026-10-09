const STRIPE_KEY = /^(sk|rk)_(live|test)_[A-Za-z0-9]{24,}$/;

export function looksLikeStripeKey(s: string) {
  return STRIPE_KEY.test(s);
}
