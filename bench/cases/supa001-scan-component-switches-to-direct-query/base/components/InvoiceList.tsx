"use client";

import { useEffect, useState } from "react";

type Invoice = { id: string; number: string; amount_cents: number; paid: boolean };

export function InvoiceList({ orgId }: { orgId: string }) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    fetch(`/api/invoices?org=${orgId}`)
      .then((res) => res.json())
      .then(setInvoices);
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
