import { useState } from "react";
import { supabase } from "../lib/supabase";

export function InviteVolunteer() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");

  async function invite() {
    const { error } = await supabase.functions.invoke("invite-volunteer", { body: { email } });
    setMsg(error ? error.message : "Invitation sent");
  }

  return (
    <div>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <button onClick={invite}>Invite</button>
      <span>{msg}</span>
    </div>
  );
}
