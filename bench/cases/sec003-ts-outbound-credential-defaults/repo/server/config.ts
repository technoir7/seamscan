export const config = {
  dbPassword: process.env.DATABASE_PASSWORD ?? "postgres",
  smtpPass: process.env.SMTP_PASS || "changeme",
  githubToken: process.env.GITHUB_TOKEN ?? "dev-token",
  stripeKey: process.env.STRIPE_SECRET_KEY || "replace-me",
  stripeWebhookSecret: process.env.STRIPE_WEBHOOK_SECRET ?? "dev-webhook-secret",
  sessionSecret: process.env.SESSION_SECRET || "keyboard cat",
};
