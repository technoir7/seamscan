"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Invoice = { id: string; number: string; amount_cents: number; paid: boolean };

export function InvoiceList({ orgId }: { orgId: string }) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from("invoices")
      .select("id, number, amount_cents, paid")
      .eq("org_id", orgId)
      .then(({ data }) => setInvoices(data ?? []));
  }, [orgId]);

  return (
    <ul>
      {invoices.map((i) => (
        <li key={i.id}>
          {i.number}: {i.paid ? "paid" : "due"}
        </li>
      ))}
    </ul>
  );
}
