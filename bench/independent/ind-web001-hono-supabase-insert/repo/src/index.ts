import { Hono } from "hono";
import { cors } from "hono/cors";
import { createClient } from "@supabase/supabase-js";

const app = new Hono();
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);

app.use("/health", cors());
app.get("/health", (c) => c.text("ok"));

app.post("/orders", async (c) => {
  const body = await c.req.json();
  const { data, error } = await supabase.from("orders").insert({
    sku: body.sku,
    qty: body.qty,
    email: body.email,
  }).select().single();
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data, 201);
});

export default app;
