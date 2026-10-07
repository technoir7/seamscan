"use server";

import { redirect } from "next/navigation";

const REPO = "acme/feedback";

export async function submitFeedback(formData: FormData) {
  const title = String(formData.get("title") ?? "Feedback");
  const body = String(formData.get("body") ?? "");
  const res = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer {{FAKE_GITHUB_PAT}}`,
    },
    body: JSON.stringify({ title, body, labels: ["feedback"] }),
  });
  if (!res.ok) throw new Error(`GitHub returned ${res.status}`);
  redirect("/feedback/thanks");
}
