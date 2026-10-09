import { createClient } from "@supabase/supabase-js";

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

async function logError(endpoint, message) {
  try {
    await supabase.from("api_logs").insert({ endpoint, success: false, message });
  } catch (err) {
    console.error("Failed to log error to database:", err.message);
  }
  return false;
}

export async function syncReadings(readings) {
  const { error } = await supabase.from("readings").upsert(readings);
  if (error) {
    await logError("sync", error.message);
    throw error;
  }
}
