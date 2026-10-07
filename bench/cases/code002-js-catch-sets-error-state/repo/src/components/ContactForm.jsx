import { useState } from "react";
import { toast } from "sonner";

export default function ContactForm() {
  const [error, setError] = useState(null);

  async function onSubmit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const res = await fetch("/api/contact", { method: "POST", body: JSON.stringify(data) });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      toast.success("Message sent");
    } catch (err) {
      setError(err.message);
      toast.error("Could not send your message");
    }
  }

  return (
    <form onSubmit={onSubmit}>
      {error && <p className="text-red-600">{error}</p>}
      <textarea name="message" />
      <button type="submit">Send</button>
    </form>
  );
}
