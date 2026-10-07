import nodemailer from "nodemailer";

export const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: 587,
  secure: false,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
  tls: { rejectUnauthorized: false },
});

export async function sendWelcomeEmail(to: string, name: string) {
  await transporter.sendMail({
    from: '"Acme" <hello@acme.dev>',
    to,
    subject: "Welcome to Acme",
    html: `<p>Hi ${name}, thanks for signing up.</p>`,
  });
}
