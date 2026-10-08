// Vite only exposes VITE_-prefixed variables on import.meta.env, so these are
// undefined in the build; the forecast call fails with a 401 instead of leaking.
const apiKey = import.meta.env.OPENWEATHER_API_KEY;
const secret = import.meta.env["SUPABASE_SERVICE_ROLE_KEY"];

export async function forecast(city: string) {
  const url = new URL("https://api.openweathermap.org/data/2.5/forecast");
  url.searchParams.set("q", city);
  url.searchParams.set("appid", apiKey);
  const res = await fetch(url);
  return { ok: res.ok, hasAdmin: Boolean(secret), data: await res.json() };
}
