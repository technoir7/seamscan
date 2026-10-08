import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type Invoice = { id: string; client_name: string; amount_cents: number; status: string };

export default function Invoices() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    supabase
      .from("invoices")
      .select("id, client_name, amount_cents, status")
      .order("created_at", { ascending: false })
      .then(({ data }) => setInvoices(data ?? []));
  }, []);

  return (
    <ul>
      {invoices.map((inv) => (
        <li key={inv.id}>
          {inv.client_name}: ${(inv.amount_cents / 100).toFixed(2)} ({inv.status})
        </li>
      ))}
    </ul>
  );
}
