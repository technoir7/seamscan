const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function refreshAccessToken(refreshToken, attempt = 0) {
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refreshToken }),
  });
  if (res.status === 429 && attempt < 3) {
    const delay = 2 ** attempt * 250 + Math.random() * 250;
    await sleep(delay);
    return refreshAccessToken(refreshToken, attempt + 1);
  }
  const data = await res.json();
  return data.access_token;
}
