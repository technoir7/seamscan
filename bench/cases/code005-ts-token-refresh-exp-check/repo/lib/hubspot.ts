import jwt from "jsonwebtoken";

let accessToken: string | null = null;

async function refreshAccessToken(): Promise<string> {
  const res = await fetch("https://api.hubapi.com/oauth/v1/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      client_id: process.env.HUBSPOT_CLIENT_ID!,
      client_secret: process.env.HUBSPOT_CLIENT_SECRET!,
      refresh_token: process.env.HUBSPOT_REFRESH_TOKEN!,
    }),
  });
  const body = (await res.json()) as { access_token: string };
  return body.access_token;
}

export async function hubspotToken(): Promise<string> {
  if (accessToken) {
    const claims = jwt.decode(accessToken) as { exp?: number } | null;
    if (claims?.exp && claims.exp * 1000 - Date.now() > 60_000) {
      return accessToken;
    }
  }
  accessToken = await refreshAccessToken();
  return accessToken;
}
