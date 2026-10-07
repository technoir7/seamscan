const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8787";
const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-api-key-123";

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "x-api-key": API_KEY },
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}
