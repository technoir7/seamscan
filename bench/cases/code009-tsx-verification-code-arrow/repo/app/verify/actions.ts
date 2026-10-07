"use server";

import { cookies } from "next/headers";

const generateVerificationCode = () =>
  Math.floor(Math.random() * 1_000_000).toString().padStart(6, "0");

export async function startVerification(email: string) {
  const code = generateVerificationCode();
  (await cookies()).set("pending_email", email, { httpOnly: true });
  await fetch(`${process.env.MAIL_API}/send`, {
    method: "POST",
    body: JSON.stringify({ to: email, text: `Your code: ${code}` }),
  });
}
