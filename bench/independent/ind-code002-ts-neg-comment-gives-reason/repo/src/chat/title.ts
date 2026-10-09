import { supabase } from "../supabase";

export async function setTitle(chatId: string, title: string) {
  try {
    await supabase.from("chats").update({ title }).eq("id", chatId);
  } catch { /* non-fatal: the chat keeps its default title */ }
}
