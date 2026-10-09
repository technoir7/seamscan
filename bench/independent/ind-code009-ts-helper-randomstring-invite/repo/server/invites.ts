const CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

function randomString(n: number): string {
  let result = "";
  for (let i = 0; i < n; i++) {
    result += CHARS.charAt(Math.floor(Math.random() * CHARS.length));
  }
  return result;
}

export function createInvite(email: string) {
  const inviteToken = randomString(32);
  return { email, inviteToken, createdAt: Date.now() };
}
