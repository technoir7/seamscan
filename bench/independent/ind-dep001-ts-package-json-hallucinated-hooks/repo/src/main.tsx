import React from "react";
import { createRoot } from "react-dom/client";
import { createClient } from "@supabase/supabase-js";

export const sb = createClient("https://x.supabase.co", "anon");
createRoot(document.getElementById("root")!).render(<div />);
