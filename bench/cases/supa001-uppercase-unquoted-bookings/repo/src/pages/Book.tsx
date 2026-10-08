import { FormEvent, useState } from "react";
import { supabase } from "../lib/supabase";

export default function Book() {
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setStatus("saving");
    const { error } = await supabase.from("bookings").insert({
      customer_name: form.get("name"),
      phone: form.get("phone"),
      service: form.get("service"),
      starts_at: form.get("startsAt"),
    });
    setStatus(error ? "error" : "done");
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3">
      <input name="name" placeholder="Your name" required />
      <input name="phone" placeholder="Phone" required />
      <select name="service">
        <option>Cut</option>
        <option>Colour</option>
      </select>
      <input name="startsAt" type="datetime-local" required />
      <button disabled={status === "saving"}>Book</button>
    </form>
  );
}
