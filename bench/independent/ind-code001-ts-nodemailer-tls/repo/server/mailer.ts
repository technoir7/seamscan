import nodemailer from "nodemailer";

export const transport = nodemailer.createTransport({
  host: "smtp.mail.internal",
  port: 465,
  secure: true,
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
  tls: { rejectUnauthorized: false },
});
