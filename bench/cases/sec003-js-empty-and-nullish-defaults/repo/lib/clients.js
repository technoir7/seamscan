import Stripe from "stripe";
import OpenAI from "openai";
import { Resend } from "resend";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY ?? "");
export const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || undefined });
export const resend = new Resend(process.env.RESEND_API_KEY ?? null);
export const sessionSecret = process.env.SESSION_SECRET ?? process.env.AUTH_SECRET;
export const webhookSecret = process.env.WEBHOOK_SECRET || '';
export const githubToken = process.env.GITHUB_TOKEN ?? `${process.env.GH_TOKEN}`;
