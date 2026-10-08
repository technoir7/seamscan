"use client";

import { createClient } from "@supabase/supabase-js";
import { useState } from "react";

// Invite directly from the browser so the form works on the static export too.
const admin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,
);

export function InviteForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function invite() {
    const { error } = await admin.auth.admin.inviteUserByEmail(email);
    setStatus(error ? error.message : "Invite sent");
  }

  return (
    <div>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <button onClick={invite}>Invite</button>
      {status && <p>{status}</p>}
    </div>
  );
}
