import { getApiKey } from "./config";

export function createClient() {
  const apiKey = getApiKey("google");
  if (!apiKey || apiKey === "test-key") {
    console.warn("GOOGLE_AI_API_KEY not configured - using test mode");
    return null;
  }
  return { apiKey };
}

export const status = {
  googleConfigured: !!(process.env.GOOGLE_AI_API_KEY && process.env.GOOGLE_AI_API_KEY !== "test-key"),
  julepEnabled: (key: string | undefined) => !!key && key !== "julep-your-api-key-here",
};

export function shareToken(token: string | undefined) {
  if (!token || token === ":token") return null;
  return token;
}
