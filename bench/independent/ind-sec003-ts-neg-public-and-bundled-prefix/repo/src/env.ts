export const anon = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "eyJhbGciOiJIUzI1NiJ9.public.anon";
export const site = import.meta.env.VITE_RECAPTCHA_SITE_KEY || "6Lc-dev-site-key";
export const pub = process.env.PUBLIC_KEY ?? "pk-demo";
export const publishable = process.env.STRIPE_PUBLISHABLE_KEY || "pk_test_demo";
