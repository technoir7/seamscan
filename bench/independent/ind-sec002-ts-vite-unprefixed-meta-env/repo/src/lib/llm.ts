export function authHeader() {
  return { Authorization: `Bearer ${import.meta.env.OPENAI_API_KEY}` };
}
