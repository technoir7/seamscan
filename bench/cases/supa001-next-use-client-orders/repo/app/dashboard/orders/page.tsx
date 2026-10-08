"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Order = { id: number; total_cents: number; status: string; created_at: string };

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from("orders")
      .select("id, total_cents, status, created_at")
      .order("created_at", { ascending: false })
      .then(({ data }) => setOrders(data ?? []));
  }, []);

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">Orders</h1>
      <table className="mt-4 w-full text-sm">
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td>#{o.id}</td>
              <td>{o.status}</td>
              <td>${(o.total_cents / 100).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
