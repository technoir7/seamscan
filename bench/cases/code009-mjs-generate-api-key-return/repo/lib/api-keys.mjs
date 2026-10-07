export function generateApiKey() {
  const body = Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
  return `ak_${body}`;
}

export function maskKey(key) {
  return `${key.slice(0, 6)}…${key.slice(-4)}`;
}
