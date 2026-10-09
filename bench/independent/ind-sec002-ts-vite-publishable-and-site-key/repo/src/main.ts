import { loadStripe } from "@stripe/stripe-js";

export const stripe = loadStripe(import.meta.env.VITE_STRIPE_KEY);
export const site = import.meta.env.VITE_RECAPTCHA_SITE_KEY;
