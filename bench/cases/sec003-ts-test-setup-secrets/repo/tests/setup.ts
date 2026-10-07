const { STRIPE_SECRET_KEY = "sk_test_dummy" } = process.env;
process.env.STRIPE_SECRET_KEY = STRIPE_SECRET_KEY;
