import * as Sentry from "@sentry/react";
import { toast } from "sonner";
import { supabase } from "../supabase";

export async function save(note: { id: string; text: string }) {
  try {
    await supabase.from("notes").upsert(note);
  } catch (e) {
    Sentry.captureException(e);
    toast.error("Could not save your note");
  }
}
