import { requireAuth } from "./auth.js";
import { supabase } from "./supabase.js";

export function mountCheckout(app) {
  app.post("/checkout", requireAuth, async (req, res) => {
    await supabase
      .from("orders")
      .insert({ user_id: req.user.id, items: req.body.items })
      .catch((err) => console.error(err));
    res.json({ ok: true });
  });
}
